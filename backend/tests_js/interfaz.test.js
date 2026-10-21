/**
 * Test de la interfaz SIN navegador.
 *
 * Carga `app.js` de verdad, con un DOM simulado, contra un servidor simulado, y
 * comprueba que sale la pantalla de inicio con sus seis botones. No sustituye a
 * probarlo en un móvil de verdad —eso exige la prueba con tres agricultores—, pero
 * sí caza lo que más duele y es más difícil de ver a ojo: que el fichero no cargue,
 * que una función no exista, que un texto de la interfaz no se encuentre y las
 * preguntas salgan en blanco.
 *
 * Decisión: el simulador es mínimo a propósito. Si `app.js` necesitara un DOM de
 * verdad para arrancar, este test no podría existir, y entonces la primera noticia
 * de un fallo sería un agricultor delante de una pantalla en blanco.
 */

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import vm from "node:vm";

import { montajes, montajesDelMarco } from "../web/react/montar.js";

// ---------------------------------------------------------------------------
// React y htm en los globales, como los deja `index.html`
//
// La pantalla de inicio se pinta con React (`web/react/pantallas/inicio.js`). Aquí se cargan
// los dos ficheros de `vendor` que NO necesitan navegador —`react` y `htm` son JavaScript
// corriente— para poder comprobar **qué** se le pide a React con los datos de la aplicación.
//
// El de ReactDOM (el que sí necesita un navegador de verdad) NO se carga, y eso es a
// propósito: `montar.js` está hecho para que, cuando no hay ReactDOM, la pantalla se apunte y
// la aplicación arranque igual. Gracias a eso este fichero puede seguir probando toda la
// interfaz sin navegador, que es lo que ha hecho desde el principio.
// ---------------------------------------------------------------------------

// Los ficheros de `vendor` son UMD: cuando no hay un sistema de módulos se asignan a `self`,
// que es lo que existe en un navegador. Node no tiene `self`, así que se le pone.
globalThis.self = globalThis;

function cargarDeVendor(nombre) {
  const codigo = readFileSync(new URL(`../web/vendor/${nombre}`, import.meta.url), "utf8");
  vm.runInThisContext(codigo, { filename: nombre });
}

cargarDeVendor("react.production.min.js");
cargarDeVendor("htm.umd.js");

// ---------------------------------------------------------------------------
// Un DOM de mentira, lo justo para que arranque
// ---------------------------------------------------------------------------

function crearNodo(id = "") {
  const clases = new Set();
  return {
    id,
    innerHTML: "",
    textContent: "",
    className: "",
    dataset: {},
    classList: {
      add: (c) => clases.add(c),
      remove: (c) => clases.delete(c),
      contains: (c) => clases.has(c),
      toggle: (c) => (clases.has(c) ? clases.delete(c) : clases.add(c)),
    },
    appendChild() {},
    remove() {},
    click() {},
  };
}

function montarEntorno() {
  const nodos = new Map();
  // `marco` es el armazón del ordenador (el menú lateral y la barra de arriba): tiene que estar, como en
  // `index.html`, o el armazón no se monta y las pruebas de cableado no podrían mirarlo.
    // *Y `aviso-cargas`, que es el de D03: **el arnés tiene que tener los mismos nodos que `index.html`**, o la
  // aplicación no encuentra el suyo y no se puede probar que un fallo se enseña.*
  for (const id of ["pantalla", "aviso-pendientes", "aviso-cargas", "cabecera-texto", "pie", "marco"]) {
    nodos.set(id, crearNodo(id));
  }

  const almacen = new Map();
  const cuerpo = crearNodo("body");
  const manejadores = {};
  // El historial de mentira (T04, 02/10/2026): la aplicación escribe direcciones de verdad con
  // `history.pushState`, así que el entorno tiene que tener uno y **apuntar lo que se escribe**, que es
  // justo lo que hay que comprobar (una dirección por pantalla, sin duplicados y sin perderse).
  const historial = [];

  const entorno = {
    nodos,
    manejadores,
    historial,
    document: {
      getElementById: (id) => nodos.get(id) || null,
      createElement: () => crearNodo(),
      // Se guarda el manejador para poder pulsar botones de verdad en los tests.
      addEventListener: (tipo, manejador) => {
        manejadores[tipo] = manejador;
      },
      body: cuerpo,
    },
    window: {
      // Se guardan **todos** los manejadores (el de `click` y el de `popstate`), cada uno con su tipo: sin
      // esto, escuchar «atrás» en la aplicación pisaría el manejador de los clics y no se podría pulsar
      // nada.
      addEventListener: (tipo, manejador) => {
        manejadores[tipo] = manejador;
      },
      scrollTo() {},
      confirm: () => true,
      // La dirección y el historial: `pushState` cambia la dirección **y** deja constancia, que es lo que
      // hace un navegador de verdad (y no dispara `popstate`, por eso la aplicación no se mueve en bucle).
      location: { hash: "" },
      history: {
        pushState(_estado, _titulo, url) {
          historial.push(url);
          entorno.window.location.hash = url;
        },
        replaceState(_estado, _titulo, url) {
          historial.push(url);
          entorno.window.location.hash = url;
        },
      },
      localStorage: {
        getItem: (clave) => (almacen.has(clave) ? almacen.get(clave) : null),
        setItem: (clave, valor) => almacen.set(clave, String(valor)),
        removeItem: (clave) => almacen.delete(clave),
      },
    },
    navigator: { onLine: true },
    URL: { createObjectURL: () => "blob:x", revokeObjectURL() {} },
  };

  // Ya "dentro" desde el principio, para que la aplicación cargue la pantalla de
  // inicio y no la de entrar.
  almacen.set("cuedigital.token", "token-de-prueba");

  return entorno;
}

// ---------------------------------------------------------------------------
// Un servidor de mentira que contesta lo mismo que el de verdad
// ---------------------------------------------------------------------------

/**
 * La declaración de medidas preventivas como la devuelve el servidor.
 *
 * Se devuelven SIEMPRE las diez preguntas, marcadas o no: la pantalla enseña las diez
 * casillas y el agricultor marca las que haga. Si solo llegaran las marcadas, no habría
 * forma de marcar la primera.
 */
function declaracionDeMedidas(aplicadas = [], observaciones = {}) {
  const catalogo = [
    ["rotacion", "¿Cambias de cultivo de un año a otro?", "Rotación de cultivos"],
    ["muestreo", "¿Miras el campo antes de decidir echar algo?", "Muestreo y respeto de los umbrales de tratamiento"],
    ["higiene", "¿Limpias la máquina al pasar de una parcela a otra?", "Higiene y limpieza de equipos y maquinaria"],
  ];
  return {
    medidas: catalogo.map(([codigo, pregunta, etiqueta]) => ({
      codigo,
      pregunta,
      etiqueta,
      aplicada: aplicadas.includes(codigo),
      observaciones: observaciones[codigo] || null,
    })),
    aplicadas,
    declarada: aplicadas.length > 0 || Object.keys(observaciones).length > 0,
    cuantas: aplicadas.length,
    mensaje:
      aplicadas.length === 0
        ? "Todavía no has dicho qué haces sin echar producto."
        : `Tienes marcadas ${aplicadas.length} medidas. Se pueden cambiar cuando quieras.`,    explicacion: "Antes de echar producto, la ley pide haber probado otras cosas.",
    descartadas: [],
  };
}

const BOTONES = [  { id: "echar_producto", icono: "💧", texto: "HE ECHADO PRODUCTO", pista: "bichos, hierbas", principal: true },
  { id: "abonar", icono: "🟤", texto: "HE ABONADO", pista: "abono", principal: false },
  { id: "trabajo", icono: "🚜", texto: "HE HECHO UN TRABAJO", pista: "sembrar", principal: false },
  { id: "mi_cuaderno", icono: "📖", texto: "MI CUADERNO", pista: "ver lo apuntado", principal: false },
  { id: "papel", icono: "🖨️", texto: "SACAR EN PAPEL", pista: "imprimir", principal: false },
  { id: "ayuda", icono: "❓", texto: "NO SÉ QUÉ PULSAR", pista: "ayuda", principal: false },
];

const RESPUESTAS = {
  // ***Las rutas que al arnes le faltaban*** (21/10/2026, D03): *la aplicacion las pedia con `.catch(() => [])`, que
  // las convertia en «no hay datos» y **nadie notaba que el servidor de mentira no las tenia**. Al apuntar los
  // fallos (D03) salieron: sin esto, la carga «limpia» del arnes tenia diez secciones en fallo que no lo estan en la
  // aplicacion de verdad. **Si el arnes no tiene la ruta, la prueba mide el arnes, no el programa.***
  "/api/documentos": null,
  "/api/tratamientos": [],
  "/api/fertilizaciones": [],
  "/api/labores": [],
  "/api/firmas": [],
  "/api/cuaderno/resumen": null,
  "/api/ventas/tabla": null,
  "/api/facturas-emitidas": [],
  "/api/cobros": [],
  "/api/maquinaria/avisos": [],
  "/api/interfaz": {
    pantalla_inicio: {
      saludo: "Hola",
      pregunta: "¿Qué has hecho hoy?",
      botones: BOTONES,
      repetir: {
        texto: "LO MISMO QUE LA ÚLTIMA VEZ",
        vacio: "Nada apuntado todavía.",
        sin_poder_repetir: "Ya has apuntado cosas, pero ningún tratamiento.",
      },
    },
    pantalla_entrar: { titulo: "Mi cuaderno" },
    // Lo que se dice si los ficheros de React de `web/vendor` no llegan a cargarse. Sin esto
    // en la copia, la aplicación arrancaría con el aviso de emergencia en blanco y ninguna
    // prueba lo vería.
    react: {
      sin_react: "Esta pantalla no se ha podido abrir. Vuelve a abrir la aplicación; si sigue igual, dile a quien te la instaló que falta un fichero del programa.",
      recargar: "VOLVER A ABRIRLA",
    },
    trabajos: [{ id: "siembra", icono: "🌱", texto: "HE SEMBRADO" }],
    // Las semillas (T10, 03/10/2026, del otro agente): el rótulo de su renglón del menú. Sin esto en
    // la copia, el renglón salía **sin nombre** y la prueba del armazón lo decía («el módulo semillas
    // no lleva su nombre»), que es exactamente para lo que está.
    semillas: { titulo: "Mis semillas" },
    // Las prácticas de «otro trabajo». En la ronda 14 se añadió el paso que las pregunta,
    // porque hasta entonces todo lo que no fuera sembrar, plantar, regar o coger la cosecha
    // acababa en el cajón de «otra» sin decir cuál. La cubierta y el pastoreo los nombra el
    // documento oficial de la Junta.
    trabajos_de_labor: [
      { id: "laboreo", icono: "🚜", texto: "HE LABRADO LA TIERRA" },
      { id: "cubierta", icono: "🌾", texto: "HE MANTENIDO LA CUBIERTA" },
      { id: "pastoreo", icono: "🐑", texto: "HA PASTADO EL GANADO" },
      { id: "otra", icono: "🔧", texto: "OTRA COSA" },
    ],
    etiquetas_labor: {
      laboreo: "Laboreo",
      cubierta: "Mantenimiento de la cubierta",
      pastoreo: "Pastoreo",
      otra: "Otro trabajo",
    },
    cesta: {
      titulo: "Lo que tengo en el almacén",
      explica: "Cuánto compraste, cuánto llevas echado y cuánto te queda.",
      vacia: "Todavía no has apuntado ningún producto.",
      comprado: "Compraste",
      gastado: "Llevas echado",
      queda: "Te queda",
      // **Los dos «te queda», cada uno con su nombre** (T21, 06/10/2026), copiados de `textos.CESTA`: el
      // del almacén (el que manda cuando se sabe) y el de los papeles. Sin estas cuatro en la copia, la
      // fila salía con la etiqueta en blanco, que es lo que caza esta copia.
      queda_en_el_almacen: "Te queda (lo que hay en el almacén)",
      queda_en_el_almacen_pista:
        "Es lo que hay de verdad: lo que ha entrado por albarán menos lo que ha salido del almacén.",
      queda_segun_los_papeles: "Según los papeles (lo comprado menos lo echado)",
      no_se_sabe_lo_que_hay: "Lo que hay en el almacén todavía no se puede decir",
      apuntes: "En {cuantos} apuntes",
      cuando: "Cuándo",
      donde_lo_compraste: "Dónde lo compraste",
      // Las etiquetas de estado de cada producto (ronda 90). Faltaban en esta copia, y sin ellas el
      // chip salía vacío: es justo el fallo que caza `test_que_no_falte_ningun_texto.py`, pero en la
      // copia de la prueba hay que añadirlas a mano.
      cuadra: "Las cuentas cuadran",
      mirar: "Míralo",
      sin_cantidad: "Sin saber cuánto compraste",
      no_se_puede_comparar: "No se puede comparar",
      // De dónde sale el número de lo comprado (30/09/2026): lo manda el servidor y ahora se enseña en el
      // panel de al lado de la tabla.
      de_las_facturas: "Sale de tus facturas",
      de_la_ficha: "Lo escribiste en la ficha del producto",
      para_que_sirve: "Si un día te preguntan, esto es la respuesta.",
      como_apuntarlo: "Cuánto compraste se apunta en la ficha del producto.",
      ir_a_productos: "MIS PRODUCTOS",
      // ── El libro del almacén (T09, 03/10/2026) ────────────────────────────────────────────────
      //
      // Copiados **uno a uno** de `textos.LIBRO_DEL_ALMACEN` (`backend/app/textos.py`), que es lo que el
      // servidor sirve **dentro del bloque del almacén** (`cesta`): el porqué de que vivan ahí está
      // escrito en el propio `textos.py`. Copiarlos es la regla de esta casa —si se inventaran aquí, las
      // pruebas comprobarían una pantalla que el agricultor no tiene— y hay una prueba al final de este
      // fichero («la copia de los textos del almacén dice lo mismo que el servidor») que avisa si esta
      // copia se queda vieja: **una copia que se queda atrás deja la prueba pasando en blanco**.
      libro_titulo: "El libro del almacén",
      libro_explica: "Aquí se apunta lo que entra y lo que sale, envase por envase: el día que llegó el albarán, de qué lote era y hasta cuándo vale, y de qué lote salió lo que has echado. Sirve para lo que no se puede saber de otra forma: si un día el fabricante avisa de un lote, aquí se ve dónde se fue.",
      libro_para_que: "En una inspección, el cuaderno dice lo que hiciste y el lote dice con qué. Y para ti sirve para no comprar de más: cada envase lleva su cuenta, así que sabes lo que te queda antes de bajar al pueblo.",
      libro_como_funciona: "Lo que mete mercancía en el almacén es el albarán, no la factura. La factura dice cuánto costó y de quién era; la mercancía entra el día que llega el camión. Por eso, si apuntas una factura y todavía no has apuntado su albarán, aquí no sale existencia: no es que se haya perdido, es que aún no ha entrado.",
      libro_cargando: "Buscando lo que hay en el almacén…",
      libro_entrada: "Entró",
      libro_salida: "Salió",
      libro_merma: "Se perdió",
      libro_ajuste: "Conteo distinto",
      libro_entradas: "Entró",
      libro_salidas: "Salió",
      libro_mermas: "Se perdió",
      libro_ajustes: "Diferencia del conteo",
      libro_queda: "Queda",
      libro_no_se_sabe_lo_que_queda: "No se puede saber lo que queda",
      libro_lote: "Lote",
      libro_sin_numero_de_lote: "Sin número de lote",
      libro_sin_numero_de_lote_pista: "El envase no lo trae o no lo has mirado. Apúntalo cuando lo mires: es lo que permite seguirle la pista si el fabricante avisa.",
      libro_caducidad: "Caduca",
      libro_sin_caducidad: "No se sabe cuándo caduca",
      libro_sin_caducidad_pista: "No es que no caduque: es que no lo has mirado. Míralo en el envase.",
      libro_caducado: "Caducado",
      libro_caducado_pista: "Este envase está pasado de fecha. Míralo antes de usarlo: no se puede dar por bueno solo porque esté en el almacén.",
      libro_en_plazo: "En fecha",
      libro_envase: "Envase",
      libro_donde_esta: "Dónde está",
      libro_categoria_fitosanitario: "Productos de tratamiento",
      libro_categoria_abono: "Abonos",
      libro_categoria_semilla: "Semillas",
      libro_categoria_otros: "Otras cosas",
      libro_recepciones: "Lo que ha llegado",
      libro_recepciones_vacio: "Todavía no has apuntado ningún albarán. Cuando llegue el próximo pedido, apúntalo aquí: es lo que mete la mercancía en el almacén.",
      libro_cuantos_albaranes: "Tienes {cuantos} albaranes apuntados.",
      libro_cuantos_albaranes_uno: "Tienes 1 albarán apuntado.",
      libro_nuevo_albaran: "APUNTAR UN ALBARÁN",
      libro_nuevo_albaran_pista: "Lo que llegó el día que vino el camión",
      libro_abrir_albaran: "ABRIR ESTE ALBARÁN",
      libro_albaran_numero: "Albarán {numero}",
      libro_albaran_sin_numero: "Un albarán sin número",
      libro_albaran_pista: "Sin número no se puede comprobar si ya estaba apuntado",
      libro_fecha_albaran: "¿De qué día es?",
      libro_proveedor: "¿De quién es?",
      libro_numero_albaran: "¿Qué número tiene el albarán?",
      libro_numero_albaran_pista: "Lo que ponga en el papel. Si no lleva número, déjalo en blanco y dilo.",
      libro_numero_de_albaran: "Número del albarán",
      libro_notas_albaran: "¿Quieres apuntar algo más?",
      libro_lineas: "Lo que venía",
      libro_cuantas_lineas_uno: "1 línea",
      libro_cuantas_lineas: "{cuantas} líneas",
      libro_cuantas_entradas_uno: "1 entrada en el almacén",
      libro_cuantas_entradas: "{cuantas} entradas en el almacén",
      libro_albaran_titulo: "Apuntar un albarán",
      libro_albaran_explica: "Copia lo que pone el papel: quién lo trajo, qué venía y de qué lote. Lo que no ponga el papel se deja en blanco, y el programa dirá que no lo sabe en vez de suponerlo.",
      libro_albaran_guardar: "SÍ, GUARDAR EL ALBARÁN",
      libro_albaran_guardando: "Guardando el albarán…",
      libro_albaran_anadir_linea: "AÑADIR OTRA LÍNEA",
      libro_albaran_quitar_linea: "QUITAR ESTA LÍNEA",
      libro_linea_titulo: "Línea {numero}",
      libro_linea_que_es: "¿Qué ha llegado?",
      libro_linea_que_es_pista: "Elige el producto o el abono de tu lista —así el almacén habla de lo mismo que tu cuaderno— o escribe el nombre tal y como sale en el papel.",
      libro_linea_libre: "No está en mi lista: lo que pone el papel",
      libro_linea_nombre: "El nombre que pone el albarán",
      libro_linea_cantidad: "¿Cuánto?",
      libro_linea_cantidad_pista: "Lo que trae el papel, sin la dosis por hectárea",
      libro_linea_unidad: "¿En qué se mide?",
      libro_linea_unidad_pista: "Lo que ponga el papel. Si no lo pone, déjalo sin decir.",
      libro_linea_sin_unidad: "El papel no lo dice",
      libro_linea_numero_lote: "¿Qué número de lote trae?",
      libro_linea_numero_lote_pista: "El número impreso en el envase. Si no lo trae o no lo has mirado, déjalo en blanco: se apunta igual y se dice que no se sabe.",
      libro_linea_caducidad: "¿Hasta cuándo vale?",
      libro_linea_caducidad_pista: "La fecha del envase. Si no la has mirado, déjalo en blanco: no es que no caduque, es que no lo sabes todavía.",
      libro_linea_envase: "¿Cómo viene el envase?",
      libro_linea_envase_pista: "Una garrafa de 5 litros, un saco de 25 kilos…",
      libro_linea_contenido: "¿Cuánto trae cada envase?",
      libro_linea_donde: "¿Dónde lo vas a guardar?",
      libro_linea_donde_pista: "La nave, el almacén, el rincón donde lo pongas",
      libro_de_quien: "De quién es",
      libro_de_que_dia: "De qué día es",
      libro_sin_fecha: "Sin fecha",
      libro_cuanto_metio: "Lo que metió en el almacén",
      libro_sin_entradas: "Este albarán no ha metido nada en el almacén: sus entradas no cuentan, pero lo que decía el papel sigue aquí.",
      libro_anulado: "Anulado",
      libro_anulado_con_motivo: "Anulado: {motivo}",
      libro_anulado_ok: "Anulado. Sus entradas ya no cuentan en el almacén, pero el albarán sigue aquí con lo que dijo el papel.",
      libro_anular: "ANULAR",
      libro_anular_pregunta: "¿Por qué anulas este albarán?",
      libro_anular_pista: "En dos palabras: me equivoqué de papel, venía otra cosa, ya estaba…",
      libro_anular_si: "SÍ, ANULARLO",
      libro_anular_no: "MEJOR NO",
      libro_volver_al_libro: "VOLVER AL LIBRO DEL ALMACÉN",
      libro_volver_al_albaran: "VOLVER AL ALBARÁN",
      libro_guardado: "El albarán está apuntado.",
      libro_guardado_pista: "La mercancía ya está en el almacén: lo que has apuntado es lo que ha entrado. Si algo no cuadra, anula el albarán y lo apuntas otra vez.",
      libro_encolado: "El albarán se ha quedado apuntado en el móvil.",
      libro_ya_estaba: "Ese albarán ya estaba apuntado",
      libro_ya_estaba_explica: "No se ha vuelto a apuntar, así que no se ha contado dos veces. Si el que había estaba mal, anúlalo y apunta este.",
      libro_no_se_pudo_comprobar: "Como este albarán no lleva número (o no dice de quién es), no se ha podido comprobar si ya estaba apuntado. Míralo en la lista y anula el que sobre.",
      libro_existencias_titulo: "Lo que queda en el almacén",
      libro_existencias_pista: "Cada envase lleva su cuenta por separado: lo que queda de un lote es de ese lote, no del total del producto.",
      libro_sin_articulos: "Todavía no hay nada apuntado en el almacén. Cuando apuntes el primer albarán, aquí verás lo que queda de cada envase.",
      libro_cuantos_articulos: "En el almacén llevas {cuantos} cosas apuntadas.",
      libro_cuantos_articulos_uno: "En el almacén llevas 1 cosa apuntada.",
      libro_sin_movimientos: "De este envase no se ha apuntado todavía nada.",
      libro_lote_numero: "Lote {numero}",
      libro_lotes_de: "Los envases de este producto",
      libro_sin_lotes: "De este producto no hay ningún envase apuntado todavía.",
      libro_compras_sin_albaran: "De esto tienes compras apuntadas en facturas pero no ha entrado nada al almacén: apunta el albarán cuando llegue y aquí saldrá la existencia.",
      libro_compras_sin_albaran_una: "De esto tienes 1 compra apuntada en una factura pero no ha entrado nada al almacén: apunta el albarán cuando llegue y aquí saldrá la existencia.",
      libro_movimientos_titulo: "Lo que ha pasado en el almacén",
      libro_movimientos_pista: "Todo lo que entró, salió, se perdió y se contó distinto, lo último primero.",
      libro_sin_movimientos_ninguno: "Todavía no se ha movido nada en el almacén. Cuando apuntes un albarán, aquí verás lo que entró y lo que ha salido después.",
      libro_no_cuenta: "No cuenta",
      libro_de_un_albaran: "Entró con un albarán",
      libro_de_un_apunte: "Sale de un apunte de tu cuaderno",
      libro_de_una_factura: "Sale de una factura",
      libro_a_mano: "Se apuntó a mano",
      libro_merma_titulo: "Apuntar que se ha perdido",
      libro_merma_pista: "Un envase roto, algo que se ha estropeado. No es que lo hayas echado en la tierra: por eso se apunta aparte y no cuenta como producto gastado.",
      libro_ajuste_titulo: "Apuntar lo que he contado",
      libro_ajuste_pista: "Al contar había otra cantidad de la que dice el libro. Si había de más, ponlo en positivo; si había de menos, con un menos delante.",
      libro_entrada_titulo: "Apuntar que ha entrado",
      libro_entrada_pista: "Para lo que ya estaba en el almacén antes de usar el programa. Si lo que ha llegado trae albarán, apúntalo como albarán: así queda el papel detrás.",
      libro_movimiento_articulo: "¿De qué es?",
      libro_movimiento_articulo_pista: "Lo que hay dado de alta en el almacén",
      libro_movimiento_lote: "¿De qué envase?",
      libro_movimiento_lote_pista: "Si no sabes el número, se apunta sin él.",
      libro_movimiento_cantidad: "¿Cuánto?",
      libro_movimiento_cantidad_pista: "El total, no la dosis por hectárea. Y en qué se mide: litros, kilos, unidades.",
      libro_movimiento_unidad: "¿En qué se mide?",
      libro_movimiento_sin_unidad: "Sin decir en qué se mide",
      libro_movimiento_fecha: "¿De qué día es?",
      libro_movimiento_motivo: "¿Por qué?",
      libro_movimiento_motivo_pista: "En dos palabras: se rompió, se contó distinto, llegó sin cantidad…",
      libro_movimiento_guardar: "SÍ, APUNTARLO",
      libro_movimiento_guardando: "Apuntándolo…",
      libro_movimiento_guardado: "Apuntado en el libro del almacén.",
      libro_movimiento_guardado_pista: "Con esto el envase ya lleva su cuenta. Si te has equivocado, anula el movimiento y apúntalo otra vez.",
      libro_salida_titulo: "Sacar del almacén lo que has echado",
      libro_salida_apunte: "El apunte del que sale",
      libro_salida_explica: "Esto sale de un apunte de tu cuaderno, y la cantidad la dice el apunte: aquí solo dices de qué envase salió. Así, si un día el fabricante avisa de un lote, se sabe dónde se fue.",
      libro_salida_de_que_lote: "¿De qué envase ha salido?",
      libro_salida_lote: "SACAR DE ESTE ENVASE",
      libro_salida_guardada: "Apuntado: eso es lo que ha salido del envase.",
      libro_salida_total: "Lo que se ha sacado del envase",
      libro_salida_por_hectarea: "Cuánto por hectárea",
      libro_salida_hectareas: "Hectáreas del apunte",
      libro_salida_total_pista: "El total que se gastó, no lo que se echa en cada hectárea",
      libro_salida_cantidad: "¿Cuánto has sacado en total?",
      libro_salida_cantidad_pista: "El apunte solo tiene lo que se echa en cada hectárea, y eso no es lo que se gastó. Escribe el total, o completa el apunte con la cantidad total.",
      libro_salida_descuadre_si: "SÍ, LA DIFERENCIA ES DE VERDAD",
      libro_salida_corregir: "CORREGIR LA CANTIDAD",
      libro_sin_articulos_de_eso: "De esto no hay nada apuntado todavía en el almacén. Apunta el albarán cuando llegue y entonces podrás decir de qué envase salió.",
      libro_ver_el_libro: "VER EL LIBRO DEL ALMACÉN",
      libro_ver_la_cesta: "VER LO QUE TENGO EN EL ALMACÉN",
      libro_nueva_entrada: "APUNTAR QUE HA ENTRADO",
      libro_nueva_merma: "APUNTAR QUE SE HA PERDIDO",
      libro_nuevo_ajuste: "APUNTAR LO QUE HE CONTADO",
      libro_nueva_salida: "SACAR DE UN LOTE",
      libro_factura_enganchada: "Esta factura ya está enganchada a su albarán. La mercancía no se cuenta otra vez: entró una vez, el día que llegó.",
      libro_factura_sin: "Sin factura apuntada",
      libro_factura_de: "La factura de este albarán",
      libro_engancharla: "DECIR DE QUÉ FACTURA ES",
      libro_factura_titulo: "Decir de qué factura es este albarán",
      libro_factura_explica: "La mercancía ya entró el día del albarán: la factura solo dice de quién era y cuánto costó. Por eso engancharla no cambia ni un litro de lo que hay en el almacén.",
      libro_factura_elige: "¿Cuál de tus facturas es?",
      libro_factura_nada_apuntado: "Elegir una de esta lista no apunta nada: el programa solo mira si puede ser la de este albarán y te lo dice.",
      libro_factura_nada: "No tienes ninguna factura apuntada. Sube la factura y vuelve aquí: entonces podrás decir cuál es la de este albarán.",
      libro_factura_es_esta: "ES ESTA",
      libro_factura_propuesta: "El programa cree que esta factura es la de este albarán. Míralo y dilo tú: todavía no está apuntado nada.",
      libro_factura_no_propuesta: "Esta factura no parece la de este albarán. Míralas otra vez: el proveedor o el número no coinciden. Si de todas formas estás seguro, puedes decir que sí.",
      libro_factura_como: "Por qué se propone",
      libro_factura_lineas: "Lo que parece el mismo producto",
      libro_factura_si: "SÍ, ES ESTA",
      libro_factura_si_igual: "SÍ, ES ESTA AUNQUE NO CUADRE",
      libro_factura_otra: "ELEGIR OTRA FACTURA",
      libro_factura_comprobando: "MIRANDO SI ES ESA…",
      libro_factura_enganchada_ok: "Enganchada. La mercancía no se cuenta otra vez: entró una vez, el día que llegó el albarán.",
      libro_factura_sin_comprobar: "No se ha podido preguntar si esta factura es la de este albarán. Prueba otra vez cuando tengas cobertura: hasta que lo digas tú, no se apunta nada.",
    },
    cultivos: {
      titulo: "Qué hay sembrado",
      explica: "Dinos qué hay este año en cada parcela.",
      decir: "DECIR QUÉ HAY SEMBRADO",
      cambiar: "CAMBIARLO",
      falta_decirlo: "Todavía no has dicho qué hay aquí este año.",
      tiene: "Este año hay",
      cuando: "Desde",
      hasta: "Hasta",
      otros_anos: "Otros años",
      repite: "Aquí has puesto lo mismo que el año pasado.",
      la_especie: "¿Qué hay sembrado?",
      la_especie_pista: "Por ejemplo: trigo blando, cebada, girasol",
      variedad: "¿De qué variedad?",
      variedad_pista: "Si lo sabes",
      sistema: "¿Es de secano o de regadío?",
      desde_cuando: "¿Desde cuándo está?",
      hasta_cuando: "¿Hasta cuándo?",
      fechas_pista: "Si no lo sabes, déjalo en blanco",
      guardado: "Apuntado.",
      // Cambiar y quitar lo que ya dijiste (ronda 93). Faltaban en esta copia y el final del quitado
      // salía sin título: es el mismo aviso que el comentario de arriba, un texto que falta **no revienta
      // nada**, solo deja un hueco en la pantalla.
      corrigiendo: "ESTÁS CAMBIANDO LO QUE DIJISTE",
      quitar: "QUITAR EL CULTIVO DE ESTE AÑO",
      quitar_pista: "Si esta tierra está en barbecho, quítalo.",
      quitado_titulo: "Quitado",
      quitado: "Esa tierra vuelve a salir como una a la que le falta decir qué tiene este año.",
      para_que: "Sirve para el cuaderno de cada año.",
      // Las dos etiquetas de estado de cada tierra (ronda 90). Faltaban en esta copia, y desde el 30/09/2026
      // también se usan en la tabla del ordenador: sin ellas, la columna «Estado» salía vacía (lo caza la
      // prueba de la tabla de qué hay sembrado).
      al_dia: "Al día",
      falta_rellenar: "Falta rellenar",
      otros_anos: "Otros años",
      repite: "Aquí has puesto lo mismo que el año pasado.",
      // El filtro de las que faltan (30/09/2026), del diseño de escritorio de esta pantalla.
      ver_las_que_faltan: "VER SOLO LAS QUE FALTAN",
      verlas_todas: "VERLAS TODAS",
    },
    grupos: {
      titulo: "Parcelas que se llevan igual",
      explica: "Cuando varias parcelas se labran igual, se apuntan de una vez.",
      para_que: "El cuaderno sigue diciendo qué se hizo en cada parcela.",
      sin_grupos: "Todavía no has juntado ninguna parcela.",
      calcular: "JUNTARLAS TÚ SOLO",
      automatico: "Lo juntó el programa.",
      creados: "Ya están juntas: {cuantos} grupos nuevos.",
      no_hay_nada_que_juntar: "No hay parcelas que se puedan juntar.",
      faltan_cultivos: "Para juntarlas hace falta saber qué hay sembrado en cada una.",
      en_varias: "En varias parcelas a la vez",
      en_varias_pista: "Un apunte para todas las del grupo",
      cuantas: "{cuantas} parcelas",
      sin_grupos_al_apuntar: "Si tienes varias parcelas con lo mismo, junta las.",
      por_sin_cultivo: "Hay parcelas de las que no sabemos qué tienen sembrado.",
      por_sin_forma: "Hay parcelas que no tienen su forma puesta en el mapa.",
    },
    // Los años del cuaderno (ronda 93). Sin estos textos, la pantalla nueva sale con todo en blanco.
    campanas: {
      titulo: "Los años de mi cuaderno",
      explica: "Tu cuaderno se lleva por años: lo que apuntas va al año en el que estás.",
      rotulo: "Año del cuaderno",
      el_que_llevo: "Estás apuntando en este",
      cerrado: "Año cerrado",
      abierto: "Año abierto",
      empieza: "Empieza",
      termina: "Termina",
      dentro_uno: "Tiene 1 cosa apuntada dentro",
      dentro_varios: "Tiene {cuantos} cosas apuntadas dentro",
      vacio: "No tiene nada apuntado",
      // **Qué tiene dentro, dicho por lo que es** (30/09/2026): los apuntes del cuaderno y, detrás, lo que
      // hay dentro que no son apuntes (las tierras con su cultivo dicho y las demás cosas).
      apuntes_uno: "1 apunte",
      apuntes: "{cuantos} apuntes",
      cultivo_dicho_uno: "1 tierra con su cultivo dicho",
      cultivo_dicho: "{cuantas} tierras con su cultivo dicho",
      otras_cosas_uno: "1 cosa más dentro",
      otras_cosas: "{cuantas} cosas más dentro",
      no_se_puede_quitar_corto: "Hay cosas dentro",
      no_se_puede_quitar: "Aquí dentro hay cosas apuntadas: primero quítalas y después podrás quitar el año.",
      anadir: "EMPEZAR UN AÑO NUEVO",
      anadir_pista: "Cuando empiece el año que viene, hazlo aquí: lo que apuntes irá a ese año.",
      guardado: "Año guardado. Ya puedes apuntar en él.",
      sin_campanas: "Todavía no hay ningún año en tu cuaderno.",
      abrir: "LOS AÑOS DE MI CUADERNO",
      pista_anadir: "Un año en tu cuaderno no tiene por qué empezar en enero.",
    },
    unidades_producto: ["L", "kg", "mL", "g", "cc"],
    cuaderno: { titulo: "Mi cuaderno", sin_nada: "Nada", ver_papel: "SACAR EN PAPEL", sacar_datos: "GUARDAR LOS DATOS EN UN FICHERO", datos_pista: "Se abre con Excel", ley_pista: "Llevar el cuaderno es obligatorio; mandarlo a la Junta, no: es voluntario (artículo 10.2 del Real Decreto 1054/2022).", falta_titulo: "Lo que falta", falta_vacio: "Todo apuntado.", falta_sin_empezar: "Aqui saldra lo que te falte cuando apuntes algo.", apunte_numero: "Apunte {numero}", apuntes_titulo_uno: "1 apunte en el cuaderno", apuntes_titulo_varios: "{cuantas} apuntes en el cuaderno", tierra_y_parcela: "Tierra y parcela", hectareas_tratadas: "Hectáreas tratadas", cuanto_por_hectarea: "Cuánto por hectárea", el_cultivo: "Cultivo", apuntar_otro: "APUNTAR OTRO TRATAMIENTO", apuntar_uno: "APUNTAR UN TRATAMIENTO", pendiente_uno: "Te falta 1 cosa por apuntar", pendientes_varios: "Te faltan {cuantas} cosas por apuntar", pendientes_ninguno: "No te falta nada por apuntar" },
    // Corregir y borrar lo que uno ha introducido (ronda 91): los dos botones de cada apunte, el
    // título y la pista de cuando se está corrigiendo y la pantalla que pregunta si de verdad se
    // quiere borrar. Sin estos textos, los botones saldrían en blanco.
    corregir: {
      boton: "CORREGIR",
      borrar: "BORRAR",
      pregunta: "Corregir lo que apuntaste",
      pista: "Está puesto lo que apuntaste. Cambia lo que esté mal y guárdalo.",
      boton_guardar: "GUARDAR LOS CAMBIOS",
      // Lo que dice el asistente **en cada paso** mientras se corrige, y el botón de volver (diseño de
      // Stitch de la ronda 92): con la pantalla llena de datos puestos, creer que ya se ha guardado algo
      // es la forma más fácil de perder un arreglo.
      modificando: "CORRIGIENDO LO APUNTADO",
      volver_sin_guardar: "VOLVER SIN GUARDAR",
      hecho_titulo: "Corregido",
      hecho: "Ya está cambiado.",
      pregunta_borrar: "¿Seguro que quieres borrarlo?",
      borrar_pista: "De tu cuaderno desaparece del todo.",
      lo_que_desaparece: "Lo que va a desaparecer de tu cuaderno",
      borrar_mejor_corregir: "Si solo te has equivocado al escribirlo, mejor CORREGIRLO.",
      borrar_queda_rastro: "El programa guarda por dentro qué había apuntado.",
      rastro_titulo: "Qué queda guardado",
      esta_firmado: "Este apunte está firmado, así que no se puede borrar.",
      que_es_anular: "Anular no borra el apunte: se queda tachado, con el día y el motivo.",
      anular_este: "ANULARLO",
      anulado_ok: "Anulado.",
      boton_borrar_si: "SÍ, BORRARLO",
      boton_mejor_corregirlo: "MEJOR CORREGIRLO",
      borrado_titulo: "Borrado",
      borrado_ok: "Ese apunte ya no está en tu cuaderno.",
      volver_al_cuaderno: "VOLVER AL CUADERNO",
      que_es_producto: "Producto",
      que_es_abono: "Abono",
      que_es_trabajo: "Trabajo",
      que_es_cosecha: "Cosecha",
      // Las tierras y los grupos (ronda 92): lo mismo, para lo que no es un apunte del cuaderno.
      que_es_tierra: "Tierra",
      que_es_grupo: "Grupo de tierras",
      // Y las demás cosas (ronda 93): cada una con su nombre, para el primer renglón de su ficha.
      que_es_analisis: "Análisis",
      que_es_venta: "Venta",
      que_es_plan: "Plan de abono",
      que_es_aplicador: "Quién aplica",
      que_es_asesor: "Asesor",
      que_es_equipo: "Máquina",
      que_es_instalacion: "Nave o almacén",
      que_es_campana: "Año del cuaderno",
      volver_a_los_anos: "VOLVER A LOS AÑOS",
      borrado_ok_cosa: "Ya no está en tu cuaderno.",
      volver_a_las_tierras: "VOLVER A MIS TIERRAS",
      volver_a_los_grupos: "VOLVER A LOS GRUPOS",
      borrado_ok_tierra: "Esa tierra ya no está en tu cuaderno.",
      borrado_ok_grupo: "Ese grupo ya no está: las tierras siguen ahí.",
      borrar_tierra_pista: "Si te has equivocado al darla de alta, mejor CORREGIRLA.",
      borrar_grupo_pista: "Un grupo es solo una forma de apuntar de una vez: las tierras no se tocan.",
    },
    mapa: {
      titulo: "Buscar mi tierra en el mapa",
      explica: "Muévete por el mapa y toca tu trozo de tierra.",
      pista_mover: "Mueve el mapa con el dedo hasta poner tu tierra en la cruz del centro, y pulsa ESTA ES MI TIERRA.",
      necesita_conexion: "El mapa necesita conexión. Si no tienes, puedes apuntar la parcela con su referencia.",
      sin_conexion: "No se puede cargar el mapa ahora mismo: para el mapa hace falta conexión.",
      sin_centro: "No se puede saber por dónde empezar el mapa. Pulsa ESTOY AQUÍ, o apunta primero una parcela por su referencia y el mapa se abrirá en tu tierra.",
      sin_ubicacion: "No se ha podido saber dónde estás.",
      acercar: "ACERCAR",
      alejar: "ALEJAR",
      estoy_aqui: "ESTOY AQUÍ",
      elegir_en_el_mapa: "VER EL MAPA Y ELEGIRLA AHÍ",
      poner_en_el_centro: "ESTA ES MI TIERRA",
      cargando: "Cargando el mapa…",
      encontrado_titulo: "Esta es la parcela que hay ahí",
      pregunta: "¿Es tuya esta tierra?",
      no_hay_nada: "Ahí no hay ninguna parcela del SIGPAC.",
      apuntarla: "SÍ, APUNTARLA",
      no_es_mia: "NO ES ESA",
      superficie: "Superficie",
      pueblo: "Pueblo",
      referencia_catastral: "Referencia catastral",
      zona_nitratos: "Zona de nitratos",
      zona_nitratos_si: "Sí: tu tierra está en zona de nitratos",
      zona_nitratos_parte: "Solo una parte: el {porcentaje} % de tu tierra está en zona de nitratos",
      zona_nitratos_no: "No está en zona de nitratos",
      zona_nitratos_no_se: "No se ha podido comprobar si está en zona de nitratos.",
      la_foto: "La foto del campo",
      los_linderos: "Los linderos",
      el_cultivo: "Lo que se declaró",
      no_se_pudo_apuntar: "No se ha podido apuntar la parcela.",
    },
    // Traer las tierras del cuaderno que el agricultor descarga de la aplicación de la Junta (el
    // Cuecyl). Las claves son las que pide `pantallaCuadernoDeLaJunta`.
    cuaderno_cyl: {
      titulo: "Traer mis tierras del cuaderno de la Junta",
      explica: "Si ya llevas el cuaderno en la aplicación de la Junta, sube aquí ese fichero y el programa apunta tus tierras por ti.",
      como_se_hace: "Entra en la aplicación de la Junta con tu certificado, descarga el cuaderno de la campaña y súbelo aquí.",
      traer: "TRAER MIS TIERRAS",
      eligiendo: "Abriendo el cuaderno…",
      que_fichero: "El fichero del cuaderno (el que se llama CuadernoExplotacion…)",
      resumen_titulo: "Esto es lo que trae tu cuaderno",
      resumen_campana: "Campaña",
      resumen_lineas: "Tierras apuntadas en el papel",
      resumen_tierras: "Tierras distintas",
      resumen_hectareas: "Hectáreas que declaras",
      resumen_pueblos: "Pueblos",
      resumen_cultivos: "Lo que tienes sembrado",
      resumen_nitratos: "Tierras en zona de nitratos",
      resumen_partidas: "Tierras que el papel parte en trozos",
      resumen_titular: "Titular",
      lineas_titulo: "Las tierras que va a apuntar",
      confirmar: "SÍ, SON MIS TIERRAS",
      volver: "NO, VOLVER",
      importando: "Apuntando tus tierras…",
      hecho_titulo: "Tus tierras ya están apuntadas",
      creadas: "Tierras nuevas: {cuantas}",
      con_cultivo: "Tierras que ya tenías y les he puesto lo que siembras: {cuantas}",
      ya_estaban: "Tierras que ya estaban apuntadas: {cuantas}",
      no_vinieron: "Líneas que no se han podido apuntar: {cuantas}",
      titular_rellenado: "De tus datos de titular he rellenado: {cuales}",
      titular_ya_estaba: "Tus datos de titular ya estaban puestos: no he tocado nada.",
      avisos_titulo: "Cosas que conviene que mires",
      otra_vez: "Puedes subir el cuaderno las veces que quieras: la misma tierra no se apunta dos veces.",
      ver_tierras: "VER MIS TIERRAS",
      sacar_titulo: "Sacar mi cuaderno para la Junta",
      sacar_explica: "El programa escribe tu cuaderno con las 25 hojas de la Junta y todo lo que tienes apuntado. Lo que falte sale en blanco, nunca con un dato inventado.",
      sacar: "SACAR MI CUADERNO",
      hojas_datos: "{cuantas} hojas de 25 llevan datos tuyos",
      que_falta_titulo: "Lo que te falta para tenerlo completo",
      que_falta_pista: "Cada cosa dice dónde se apunta, para que la puedas arreglar.",
      donde: "Dónde se apunta",
      hoja: "Hoja",
      a_mano_en_el_fichero: "Se rellena a mano en el fichero",
      todo_completo: "No le falta nada de lo que pide el cuaderno.",
      sin_conexion: "Para subir el cuaderno hace falta conexión. El fichero lo tienes en tu móvil: prueba cuando tengas cobertura.",
      no_se_pudo: "No se ha podido abrir el cuaderno. Mira que sea el fichero que descargas de la aplicación de la Junta.",
    },
    // Qué es el registro electrónico, dónde se apunta y los sitios oficiales con su dirección.
    registro_electronico: {
      titulo: "Dónde apunto lo que hago",
      que_es: "El registro electrónico es lo mismo que apuntas ahora en el papel, pero guardado en un programa.",
      donde: "Lo apuntas aquí, en esta aplicación, o en la aplicación de la Junta (el Cuecyl).",
      desde_cuando: "Hasta el 31 de diciembre de 2026 puedes seguir apuntando en papel. Desde el 1 de enero de 2027 tiene que ser electrónico.",
      es_voluntario: "Apuntarlo es obligatorio. Mandarlo a la Junta por internet es voluntario.",
      enlaces_titulo: "Los sitios oficiales, para lo que hay que traer de fuera",
      enlaces: [
        { texto: "Descargar tu cuaderno de la Junta (Cuecyl)", url: "https://particulares.ayg.jcyl.es" },
        { texto: "Actualizar tus parcelas y tus cultivos (Reacyl)", url: "https://agriculturaganaderia.jcyl.es/web/es/registro-explotaciones-agrarias-castilla.html" },
        { texto: "Productos autorizados y su número de registro (MAPA)", url: "https://www.mapa.gob.es/es/agricultura/temas/sanidad-vegetal/productos-fitosanitarios/registro-productos/" },
      ],
    },
    // Los datos del titular y de la finca: la portada del cuaderno de la Junta.
    // Las fincas de una cuenta y quién entra en ellas (ronda 89). Este bloque faltaba: los textos estaban
    // en `textos.py` y el servidor no los servía, así que la pantalla salía con los botones en blanco.
    fincas: {
      titulo: "Quién entra en mi finca",
      explica:
        "En tu finca puede entrar más de una cuenta: la tuya y la de quien te ayude (tu mujer, tu hijo, el técnico). Todos ven lo mismo y apuntan en el mismo cuaderno. Tú decides quién entra.",
      cambiar_titulo: "En qué finca estás trabajando",
      cambiar_explica:
        "Si puedes entrar en más de una finca, aquí eliges en cuál estás apuntando. Lo que apuntes va a la finca que elijas.",
      estas_en: "Estás en",
      entrar_en: "PONME EN ESTA FINCA",
      la_tuya: "Tuya",
      papel_ayudante: "Ayudas en ella",
      anadir: "AÑADIR UNA CUENTA",
      que_correo: "¿Con qué correo entra?",
      que_correo_pista: "El correo con el que se dio de alta esa persona",
      anadir_pista:
        "La otra persona tiene que tener ya su cuenta hecha con ese correo: tú no puedes ponerle la clave.",
      quitar: "QUITARLE EL ACCESO",
      titular: "Tú (titular)",
      papel_titular: "El titular de la finca",
      ayudante: "Ayuda en la finca",
      tu_cuenta: "Tu cuenta",
      eres_el_titular: "Eres el titular de esta finca: puedes añadir y quitar cuentas.",
      no_eres_el_titular:
        "En esta finca decide el titular quién entra. Si quieres que entre otra persona, pídeselo al titular.",
      solo_una: "De momento solo entras tú.",
      anadida: "Ya puede entrar en tu finca.",
      quitada: "Ya no entra en tu finca.",
      confirmar_quitar: "¿Quitarle el acceso a esta cuenta? Podrás volver a añadirla cuando quieras.",
      no_existe: "Esa finca no está.",
      no_es_tuya: "Esa finca no es tuya o ya no tienes acceso a ella.",
      solo_el_titular: "Solo el titular de la finca puede decidir quién más entra.",
      cuenta_que_no_existe:
        "No hay ninguna cuenta con ese correo. Que se dé de alta primero (con su correo y su clave) y vuelve a añadirla.",
      cuenta_no_activa: "Esa cuenta está desactivada.",
      ya_eres_tu: "Esa cuenta es la tuya: ya entras en esta finca.",
      ya_estaba: "Esa cuenta ya puede entrar en esta finca.",
      no_entra: "Esa cuenta no entra en esta finca.",
      el_titular_no_se_quita:
        "El titular de la finca no se puede quitar: una finca sin titular se queda sin quien la gestiona.",
      no_se_pudo_quitar: "No se ha podido quitar el acceso.",
    },
    mis_datos: {
      titulo: "Mis datos",
      explica: "Estos son los datos que van en la primera hoja del cuaderno: quién eres y cómo se llama tu explotación.",
      nombre: "¿Cómo te llamas?",
      nombre_pista: "Como viene en el cuaderno de la Junta",
      nif: "Tu NIF",
      nif_pista: "Con la letra",
      registro_autonomico: "Nº de registro de tu explotación",
      registro_autonomico_pista: "Lo trae tu cuaderno de la Junta",
      registro_nacional: "Nº de registro nacional (si lo tienes)",
      registro_nacional_pista: "Si no lo sabes, déjalo en blanco",
      direccion: "Tu dirección",
      direccion_pista: "La calle y el número",
      localidad: "Tu pueblo o ciudad",
      codigo_postal: "Código postal",
      provincia: "Provincia",
      municipio: "Pueblo donde tienes las tierras",
      municipio_pista: "El principal",
      telefono: "Un teléfono",
      telefono_pista: "Por si hay que avisarte",
      correo: "Tu correo",
      guardar: "GUARDAR MIS DATOS",
      guardado: "Tus datos están guardados. La portada del cuaderno ya los lleva.",
    },
    // Las facturas de compra: subirlas, leerlas y confirmarlas.
    // Los papeles: su título lo necesita también el menú del ordenador (el renglón «Los papeles»).
    documentos: {
      titulo: "Los papeles",
      explica: "Aquí guardas los papeles que acompañan al cuaderno.",
    },
    facturas: {
      titulo: "Mis facturas",
      resumen_cifras: "Los números de tus facturas",
      numero_de_facturas: "Facturas",
      sin_papel_numero: "Sin el papel",
      explica: "Aquí guardas las facturas de lo que compras. Hazle una foto al papel o sube el fichero que te manda el proveedor: el programa lee lo que pone y te lo enseña para que lo confirmes.",
      para_que_sirven: "Sirven para tres cosas: saber cuánto producto tienes comprado, rellenar el cuaderno cuando te pida la empresa que te lo vendió y el número de factura, y tener el papel a mano si te lo piden.",
      anadir: "AÑADIR UNA FACTURA",
      que_fichero: "La factura: una foto o el fichero del proveedor",
      como_se_hace: "Hazle la foto al papel entero, con luz y sin torcerlo. Si tienes el fichero, súbelo: se lee mejor y no hay que adivinar nada.",
      leyendo: "Leyendo la factura…",
      leer: "LEER LA FACTURA",
      a_mano: "ESCRIBIRLA A MANO",
      guardando: "Guardando la factura…",
      sin_conexion: "Para leer la factura hace falta conexión. El fichero lo tienes en tu móvil: prueba cuando tengas cobertura.",
      no_se_pudo: "No se ha podido leer la factura. Prueba otra vez o escríbela a mano.",
      sin_proveedor: "Sin decir quién",
      interpretacion_titulo: "Esto es lo que he leído",
      interpretacion_pista: "Míralo y corrige lo que esté mal. Lo que se guarda es lo que tú digas, no lo que yo haya entendido.",
      avisos_titulo: "Mira esto antes de guardar",
      de_donde_sale_la_lectura: "Leída de",
      leida_pdf: "El fichero que traía el texto",
      leida_foto: "Una foto (repasa las palabras con tilde)",
      leida_escaneo: "Un papel escaneado (repasa las palabras con tilde)",
      leida_mano: "Escrita a mano por ti",
      campo_proveedor: "¿Quién te lo ha vendido?",
      campo_proveedor_pista: "El nombre de la empresa, como viene en la factura",
      campo_nif: "Su NIF",
      campo_numero: "¿Qué número tiene la factura?",
      campo_numero_pista: "Lo pide el cuaderno, así que no lo dejes en blanco",
      campo_fecha: "¿De qué día es?",
      campo_base: "Base imponible",
      campo_iva: "Cuota de IVA",
      campo_tipo_iva: "Tipo de IVA (%)",
      campo_total: "Total de la factura",
      campo_notas: "¿Quieres apuntar algo más?",
      lineas_titulo: "Lo que has comprado",
      lineas_pista: "Cada línea es un producto. Si alguna no te cuadra, corrígela o bórrala antes de guardar.",
      linea_descripcion: "Qué es",
      linea_cantidad: "Cuánto",
      linea_unidad: "En qué se mide",
      linea_precio: "A cómo",
      linea_importe: "Cuánto suma",
      linea_producto: "¿Es uno de tus productos?",
      linea_crear_producto: "No lo tengo apuntado: créalo con estos datos",
      linea_registro: "Número de registro que viene en la factura",
      linea_sin_producto: "No es de la cesta (una reparación, unas botas…)",
      linea_sugerida: "Es este: {producto}, {como}",
      linea_cuadra: "La cuenta cuadra",
      linea_no_cuadra: "La cuenta no cuadra: mira la cantidad, el precio y el importe",
      confirmar: "SÍ, GUARDAR ESTA FACTURA",
      volver: "VOLVER",
      guardada: "Factura guardada.",
      guardada_pista: "Ya cuenta para saber cuánto producto tienes comprado. La verás en «lo que tengo en el almacén».",
      ya_estaba: "Esta misma factura ya la has subido (nº {numero}). Si la guardas otra vez, la contarás dos veces.",
      sin_facturas: "Todavía no has subido ninguna factura.",
      sin_facturas_pista: "Cuando subas la primera, aquí verás lo que has comprado y de quién.",
      ver_almacen: "VER LO QUE TENGO EN EL ALMACÉN",
      // El papel de cada factura y su cuenta (ronda 90): sin esto, la lista sale sin la cuenta y sin los
      // botones de ver o subir el papel.
      papel_guardado: "Foto del papel guardada",
      papel_falta: "Falta el papel",
      ver_fichero: "VER LA FACTURA",
      subir_el_papel: "SUBIR LA FOTO DEL PAPEL",
      sin_fichero: "Esta factura no tiene ni la foto ni el fichero.",
      cuantas_uno: "1 factura guardada",
      cuantas: "{cuantas} facturas guardadas",
    },
    // El panel de detalle, al lado de la tabla (fase 3, 30/09/2026).
    panel: {
      etiqueta: "La ficha de lo que has elegido",
      tierra: "La tierra que has elegido",
      tierra_pueblo: "Pueblo",
      vacio: "Toca el nombre de una tierra de la lista y la verás aquí, con sus datos.",
      // La ficha del producto del almacén, en el mismo panel (30/09/2026).
      producto: "El producto que has elegido",
      producto_vacio: "Toca el nombre de un producto de la lista y lo verás aquí, con sus cuentas.",
      producto_origen: "De dónde sale",
      // Lo que se enseña en el panel de una tierra, debajo de sus datos (30/09/2026): sus últimos apuntes del
      // año, que es lo que se pregunta al mirar una tierra en el despacho. Lo pide el diseño de escritorio de
      // esa pantalla.
      tierra_ultimos: "Lo último que le has hecho",
      // **El botón que abre la historia de esa tierra** (T15, 05/10/2026), en la ficha de la tierra. La
      // frase se llama igual que el título de la pantalla a la que lleva.
      tierra_historia: "LO QUE HA PASADO EN ESTA TIERRA",
    },
    rotulos: { hectareas: "Hectáreas", hectareas_corto: "ha", kilos_corto: "kg", unidad_kilos: "Kilos", kilos_por_hectarea: "Kilos por hectárea", ya_cosechado: "Hasta aquí no puedes coger la cosecha" },
    // Los nombres de las columnas de las tablas del ordenador (30/09/2026).
    tabla: {
      tierras_etiqueta: "Tus tierras, en una tabla",
      numero: "Nº",
      nombre: "Nombre",
      sigpac: "Referencia SIGPAC",
      pueblo: "Pueblo",
      hectareas: "Hectáreas",
      cultivo: "Qué tiene este año",
      acciones: "Acciones",
      decirlo: "DECIRLO",
      ver_cultivo: "VER",
      ordenar_por: "Ordenar por: {columna}",
      resumen_tierras_uno: "1 tierra · {hectareas} ha",
      resumen_tierras: "{cuantas} tierras · {hectareas} ha",
      resumen_filtrado: "{cuantas} de {total} tierras · {hectareas} ha",
      // La tabla del cuaderno (30/09/2026).
      apuntes_etiqueta: "Lo que has apuntado este año, en una tabla",
      fecha: "Fecha",
      clase: "Clase",
      que: "Qué",
      tierra: "Tierra",
      firmado: "Firmado",
      resumen_apuntes_uno: "1 apunte · {hectareas} ha tratadas",
      resumen_apuntes: "{cuantas} apuntes · {hectareas} ha tratadas",
      // Al pie del cuaderno, cuántos apuntes están firmados (30/09/2026).
      firmados: "{cuantos} firmados",
      firmados_uno: "1 firmado",
      // Y **lo que falta por saber, cuando un pie suma** (A14, 05/10/2026): las sumas de los pies y de las
      // tarjetas del panel ya no convierten un hueco en un cero, y dicen cuántos apuntes, tierras o ventas
      // no traen su número. Con sus dos formas, que es lo que exige el guardián del singular.
      tierras_sin_hectareas: "{cuantas} tierras sin decir sus hectáreas",
      tierras_sin_hectareas_uno: "1 tierra sin decir sus hectáreas",
      apuntes_sin_hectareas: "{cuantas} apuntes sin decir sus hectáreas",
      apuntes_sin_hectareas_uno: "1 apunte sin decir sus hectáreas",
      ventas_sin_kilos: "{cuantas} ventas sin decir sus kilos",
      ventas_sin_kilos_uno: "1 venta sin decir sus kilos",
      // La tabla de los años del cuaderno y la de las facturas (30/09/2026).
      anos_etiqueta: "Los años de tu cuaderno, en una tabla",
      ano: "Año",
      empieza: "Empieza",
      termina: "Termina",
      dentro: "Qué tiene dentro",
      estado: "Estado",
      resumen_anos_uno: "1 año en tu cuaderno",
      resumen_anos: "{cuantas} años en tu cuaderno",
      facturas_etiqueta: "Tus facturas, en una tabla",
      proveedor: "Quién te lo vendió",
      numero_factura: "Nº de factura",
      base: "Base",
      iva: "IVA",
      total: "Total",
      papel: "El papel",
      resumen_facturas_uno: "1 factura · {total} €",
      resumen_facturas: "{cuantas} facturas · {total} €",
      resumen_facturas_sin_total_uno: "1 factura · falta decir el total",
      resumen_facturas_sin_total: "{cuantas} facturas · falta el total de alguna",
      // La tabla de lo que tengo en el almacén (30/09/2026) y la etiqueta corta de la tierra a la que le
      // falta decir qué tiene.
      cesta_etiqueta: "Lo que tienes en el almacén, en una tabla",
      producto: "Producto",
      registro: "Nº de registro",
      comprado: "Comprado",
      echado: "Echado",
      te_queda: "Te queda",
      sin_decir: "Falta decirlo",
      // Las etiquetas cortas del estado de un producto, para la celda de la tabla (30/09/2026).
      estado_cuadra: "Cuadra",
      estado_mirar: "Míralo",
      estado_sin_dato: "Falta el dato",
      estado_no_se_compara: "No se compara",
      resumen_cesta_uno: "1 producto en el almacén",
      resumen_cesta: "{cuantas} productos en el almacén",
      resumen_cesta_mirar_uno: "1 hay que mirarlo",
      resumen_cesta_mirar: "{cuantas} hay que mirarlos",
      // La tabla de lo que hay sembrado (30/09/2026).
      cultivos_etiqueta: "Qué hay sembrado este año, en una tabla",
      este_ano: "Este año hay",
      otros_anos: "Otros años",
      // La columna de la alerta de rotación (30/09/2026), del diseño de escritorio de esa pantalla.
      rotacion: "Rotación",
      cambiarlo: "CAMBIARLO",
      repite_el_ano_pasado: "Repite lo del año pasado",
      resumen_cultivos_uno: "1 tierra",
      resumen_cultivos: "{cuantas} tierras",
      resumen_cultivos_dichas_uno: "1 con su cultivo dicho",
      resumen_cultivos_dichas: "{cuantas} con su cultivo dicho",
      resumen_cultivos_filtrado: "{cuantas} de {total} tierras",
      // ── La tabla de la maquinaria (T14, 03/10/2026) ──
      //
      // Estas claves están aquí porque **este fichero es el que vigila que el menú del ordenador lleve
      // todos los módulos con su nombre**: el renglón de la maquinaria pide `maquinaria.titulo`, y sin él
      // el renglón salía en blanco (lo cazó la prueba del armazón). Lo que se ve dentro de la pantalla se
      // comprueba en `tests_js/maquinaria.test.js`, contra el componente.
      maquinaria_etiqueta: "Tu maquinaria, en una tabla",
      maquina: "Máquina",
      tipo_maquina: "Tipo",
      matricula_o_serie: "Matrícula o serie",
      propiedad: "Tuya o alquilada",
      horas: "Horas",
      proxima_revision: "Próxima revisión",
      documentacion: "Papeles",
      disponibilidad: "Disponibilidad",
      resumen_maquinaria_uno: "1 máquina",
      resumen_maquinaria: "{cuantas} máquinas",
      resumen_maquinaria_filtrado: "{cuantas} de {total} máquinas",
    },
    // La maquinaria (T14, 03/10/2026): el título de su renglón del menú, que es lo que pide el armazón.
    // El resto de sus palabras se prueban en `tests_js/maquinaria.test.js`.
    maquinaria: {
      titulo: "Mi maquinaria",
    },
    // **Las cuentas (T13, 05/10/2026)**: el título de su renglón del menú. Aquí va **el bloque entero
    // del servidor** (`textos.GASTOS` se sirve tal cual y la pantalla lee de él muchas frases), porque
    // su copia de verdad es `tests_js/gastos.test.js`: aquí solo hace falta que el armazón encuentre
    // `gastos.titulo`, que es lo que pide su renglón y sin lo cual el renglón saldría sin nombre.
    gastos: {
      titulo: "Mis cuentas",
      // Y las dos formas del resumen, que `app.js` monta con `conCuenta`: el singular y el plural
      // tienen que estar los dos, porque «Tienes 1 gastos» es lo primero que hace desconfiar.
      cuantas: "Tienes {cuantos} gastos apuntados.",
      cuantas_uno: "Tienes 1 gasto apuntado.",
      // **Las palabras del reparto** (06/10/2026), copiadas de `textos.GASTOS`: con ellas `app.js`
      // monta la lista de tierras que se marcan y la unidad de lo que le toca a cada una. Sin la de
      // «TODAS» el botón ni se pinta, y una prueba que no encuentra el botón no prueba el reparto.
      campo_tierras: "¿Entre qué tierras?",
      campo_tierras_pista:
        "Marca las tierras a las que va este gasto. Se reparte entre las que marques, y de cada una se dice lo que le toca.",
      marcar_todas: "TODAS MIS TIERRAS",
      campo_horas: "Horas",
      campo_litros: "Litros o kilos",
      campo_euros_del_trozo: "Lo que le toca (€)",
    },
    // **Los trabajos (T15, 05/10/2026)**: lo mismo, el título de su renglón del menú. El bloque entero
    // (`AGENDA`) está en su copia, `tests_js/trabajos.test.js`.
    agenda: {
      titulo: "Los trabajos",
      // Y la frase que impide el malentendido del ticket, que la agenda pinta en cada plan: **lo
      // pensado no ha gastado nada del almacén**. Se copia de `textos.AGENDA`, como todo lo de aquí.
      lo_previsto_no_gasta: "Lo pensado no ha gastado nada del almacén.",
      // Y la frase de un plan **ya cumplido**: la lista de lo pensado trae también los que ya se hicieron,
      // y a esos no se les puede ofrecer «YA LO HE HECHO» otra vez (el servidor contesta 409). Se copia de
      // `textos.AGENDA`, como todo lo de aquí.
      ya_esta_hecho: "Ya lo apuntaste como hecho:",
      // **«Sin decir»**, que es lo que se lee cuando un dato no consta: un plan sin día no se rellena
      // con el de hoy ni con el de mañana, y un hueco se dice como hueco.
      sin_decir: "Sin decir",
      // Y los rótulos que `app.js` necesita para montar cada línea de la agenda y del historial (los
      // mismos que la ficha usa como etiquetas de sus campos). Copiados de `textos.AGENDA`: si uno
      // cambia allí y no aquí, esta prueba enseñaría un hueco y no lo que se lee de verdad.
      dia: "Qué día lo hiciste",
      dia_previsto: "Para qué día lo tienes pensado",
      hectareas: "Cuántas hectáreas has trabajado",
      hectareas_previstas: "Cuántas hectáreas piensas trabajar",
      horas: "Cuántas horas has estado",
      horas_previstas: "Cuántas horas piensas estar",
      maquina: "Con qué máquina",
      tipo: "Qué trabajo",
      insumo: "Qué gastaste del almacén",
    },
    // El panel de mando del ordenador (fase 4, 30/09/2026): sus textos van con los de la pantalla de
    // inicio, porque es la misma pantalla mirada de otra forma.
    panel_de_mando: {
      titulo: "Panel de mando",
      explica: "Cómo va el cuaderno de este año, de un vistazo.",
      apuntes: "Apuntes este año",
      hectareas: "Hectáreas tratadas",
      hectareas_detalle: "de {hectareas} ha de tus tierras",
      vendido: "Lo que has vendido",
      tierras: "Tus tierras",
      tierras_sin_decir_uno: "1 sin decir qué tiene este año",
      tierras_sin_decir: "{cuantas} sin decir qué tienen este año",
      tierras_al_dia: "Todas con su cultivo dicho",
      falta_titulo: "Lo que falta por completar",
      falta_uno: "1 cosa por completar",
      falta: "{cuantas} cosas por completar",
      falta_vacio: "No te falta nada: el cuaderno está al día.",
      ultimos_titulo: "Los últimos apuntes",
      ultimos_vacio: "Todavía no has apuntado nada este año.",
      ver_todos_uno: "Ver el apunte del año",
      ver_todos: "Ver los {cuantas} apuntes del año",
      apuntar_titulo: "Apuntar algo de hoy",
      cierre_titulo: "Cierre y trámites",
      cierre_explica: "Lo que se saca del programa.",
    },
    // El armazón del ordenador (30/09/2026): el menú lateral y la barra de arriba. Faltaban en esta copia y
    // todos los renglones del menú salían sin nombre (lo caza la prueba de cableado del armazón).
    // La búsqueda global (07/10/2026): su nombre sale del servidor, como el de los demás módulos.
  buscar: { titulo: "Buscar" },
  menu: {
      titulo: "Menú",
      etiqueta: "El menú de la aplicación",
      panel: "Panel",
      cuenta: "Tu cuenta",
      sin_cuenta: "Tu cuenta",
      campana: "Campaña",
      sin_campana: "Sin año",
      apuntar: "APUNTAR",
      letra: "A+",
      letra_etiqueta: "Poner la letra más grande",
      salir: "Salir",
      salir_etiqueta: "Salir de la cuenta",
    },
  // **La normativa** (07/10/2026): las mismas frases que sirve el servidor.
  normativa: {
    titulo: "La normativa",
    pista: "Lo que hay que cumplir en el cuaderno, con su fuente oficial para poder comprobarlo.",
    fuente: "Fuente oficial",
    fuentes: "Fuentes oficiales",
    sin_clasificar: "Sin clasificar",
    sin_tipo: "Todavia no se ha clasificado esta regla: puede ser una obligacion o una recomendacion.",
    sin_estado: "Todavia no se ha revisado si esta regla esta en vigor.",
    como_se_lee: "Es un resumen para el cuaderno. Lo que dice la norma, entero, esta en su fuente oficial.",
    sin_normativa: "No hay ninguna regla cargada.",
  },
    ayuda: {
      pantalla: {
        titulo: "Ayuda",
        ley_titulo: "Qué te obliga la ley, y qué no",
        // Cada punto de la ley con su nombre (ronda 83): sin estos títulos los seis párrafos salían con el
        // mismo rótulo del apartado y se leían como un muro.
        ley_llevar_titulo: "Llevar el cuaderno al día",
        ley_mandar_titulo: "Mandar los datos a la Junta",
        ley_programa_titulo: "Con un programa tuyo",
        ley_fechas_titulo: "Las fechas que importan",
        ley_cuando_obligatorio_titulo: "Cuándo será obligatorio del todo",
        ley_sin_confirmar_titulo: "Lo que todavía no está aclarado",
        ley_llevar: "Llevar el cuaderno al día y poder enseñarlo: eso sí es obligatorio.",
        ley_mandar: "Mandar los datos a la Junta por internet es voluntario (artículo 10.2 del Real Decreto 1054/2022).",
        ley_programa: "Puedes llevar el cuaderno con un programa tuyo (artículo 10.3).",
        ley_fechas: "El cuaderno en papel deja de valer el 31 de diciembre de 2026.",
        ley_cuando_obligatorio: "El cuaderno electrónico solo será obligatorio para las fincas grandes.",
        ley_sin_confirmar: "Si hay que ir mandando los datos cada cierto tiempo, está preguntado.",
      },
      porques: {
        // Dos porqués de verdad, con su título aparte, para poder comprobar que `app.js` los junta: en la
        // pantalla cada uno tiene que salir **con su nombre** (ronda 83).
        para_que_sirve: "Desde 2013, si echas productos para las plagas, la ley te obliga a apuntarlo.",
        papel_o_digital: "Puedes llevarlo en papel hasta el 31 de diciembre de 2026.",
      },
      porque_titulos: {
        para_que_sirve: "Para qué sirve el cuaderno",
        papel_o_digital: "En papel o en el móvil",
      },
      campos: [
        {
          campo: "explotacion.nif",
          titulo: "Tu NIF",
          que_es: "El número que te identifica en tus papeles.",
          por_que: "Con él se sabe de qué finca son los apuntes.",
          ejemplo: "70922320A",
          si_falta: "Sin NIF no se puede identificar la finca en el cuaderno.",
        },
        {
          // La ayuda del campo de las hectáreas: es la que se comprueba que **viaja con el campo** al
          // pedírselo a React (el campo solo pone el hueco; el texto lo trae el servidor).
          campo: "tratamiento.superficie_tratada_ha",
          titulo: "¿Cuántas hectáreas has tratado?",
          que_es: "La parte de la tierra que has tratado de verdad.",
          por_que: "Es lo que decide cuánto producto has gastado.",
          ejemplo: "Si has tratado media tierra de 2 hectáreas, pon 1.",
          si_falta: "Sin esto el cuaderno no cuadra con lo que has comprado.",
        },
        {
          // Y la del motivo, que es la pregunta que sostiene el cuaderno entero.
          campo: "tratamiento.justificacion",
          titulo: "¿Por qué lo has echado?",
          que_es: "El problema que tenías en el campo.",
          por_que: "Es lo que justifica el tratamiento delante de la Junta.",
          ejemplo: "«Vi pulgón», «aviso de la Junta», «me lo dijo mi técnico».",
          si_falta: "Sin el motivo, el tratamiento no se puede justificar.",
        },
      ],
      // Los cuatro rótulos de la ayuda de un campo: desde la ronda 55 salen del servidor y no del
      // JavaScript (antes estaban escritos dentro de `ayudaDeCampo()`, donde no pasaban por la
      // prueba de la jerga).
      rotulos_de_un_campo: {
        que_es: "Qué es:",
        por_que: "Por qué te lo piden:",
        ejemplo: "Ejemplo:",
        si_falta: "Si te falta:",
      },
    },
    acciones: {
      volver: "VOLVER",
      apuntar: "APUNTARLO",
      seguir: "SEGUIR",
      dejarlo: "DEJARLO",
      // Los que usan las pantallas para pintar un sí o un no (la herramienta del plan, el ganado
      // del pastoreo…). Faltaban en esta copia de los textos.
      si: "Sí",
      no: "No",
      no_se: "No lo sé",
    },
    aviso: {
      cargando: "Un momento…",
      pendientes: "{cuantos} pendientes",
      // El singular del aviso de la cabecera (ronda 84): «1 cosas apuntadas» se lee fatal, y ese aviso sale
      // justo cuando el agricultor está en el campo sin cobertura.
      pendientes_uno: "1 pendiente",
      apuntado_ok: "Apuntado.",
      pie: "Pie",
      no_hay_parcelas: "Todavía no tienes parcelas. Añade la primera.",
      no_hay_productos: "Todavía no has apuntado ningún producto comprado.",
      no_hay_abonos: "Todavía no has apuntado ningún abono.",
      no_hay_instalaciones: "Todavía no tienes ninguna nave ni almacén apuntado.",
      // Este faltaba en la copia, y lo usa la pantalla al subir un papel: sin él, el aviso salía
      // vacío en los tests y nadie comprobaba que el agricultor se entera de que no se ha subido.
      no_se_pudo: "No se ha podido mandar. No te preocupes: sigue guardado en el móvil.",
    },
    rotulos: { hectareas_corto: "ha", kilos_corto: "kg", hectareas: "Hectáreas", kilos_por_hectarea: "Kilos por hectárea", unidad_kilos: "Kilos", ya_cosechado: "Hasta aquí no puedes coger la cosecha:", apuntes_de_producto: "apuntes de producto", apunte_de_producto: "apunte de producto", dias_espera_corto: "días de espera", itv_hasta: "ITV hasta", unidad_hectareas: "hectáreas", elegida: "ELEGIDA", paso: "Paso {numero} de {total}", tierra_en_nitratos: "Está en zona de nitratos", tierra_masa_agua: "Tiene una masa de agua cerca" },
    mensajes: {
      V8_dias_de_espera: "Podrás cogerla a partir del {fin}.",
      sin_cobertura: "No hay cobertura.",
      no_se_pudo: "No se ha podido mandar.",
      V10_sin_justificacion: "Pon por qué lo has echado.",
      V18_sin_parcela: "Dinos en qué parcela.",
      V4_superficie_excedida: "La parcela tiene {parcela} hectáreas y has puesto {usada}.",
      // Los mensajes del libro del almacén (T09) que la aplicación usa **antes** de llamar al servidor
      // (los tres finales: se dice qué falta en vez de mandarlo y que lo rechacen). Copiados de
      // `textos.MENSAJES`; el resto de mensajes del almacén llegan **dentro de la respuesta del
      // servidor**, así que en las pruebas se ponen en la respuesta y no hacen falta aquí.
      AL1_una_recepcion_sin_lineas:
        "Un albarán sin decir qué venía no apunta nada. Escribe al menos una cosa: qué producto, cuánto y de qué lote.",
      AL2_la_linea_no_dice_que_es:
        "En esa línea no dices qué ha llegado. Elige el producto o el abono de tu lista, o escribe su nombre tal y como sale en el albarán.",
      AL10_falta_el_motivo:
        "Aquí no hay ningún papel que explique esto, así que lo tiene que explicar quien lo apunta. Escribe en dos palabras qué ha pasado: se rompió, se contó distinto, me lo trajo un vecino…",
      AL11_un_ajuste_necesita_la_diferencia:
        "Un conteo distinto se apunta con lo que sobra o lo que falta. Di cuánto: si hay de más, en positivo, y si hay de menos, en negativo. Si sale cero, es que cuadra y no hay nada que apuntar.",
      AL12_una_merma_necesita_la_cantidad:
        "Para apuntar lo que se ha perdido hace falta saber cuánto. Escribe la cantidad y en qué se mide.",
      AL13_falta_la_unidad:
        "Falta decir en qué se mide esa cantidad. Sin eso no se puede restar de lo que hay en el almacén: pon litros, kilos o unidades.",
      AL17_el_apunte_no_dice_el_total:
        "Ese apunte solo tiene la dosis por hectárea, y eso no es lo que se gastó: la dosis es lo que se echa en cada hectárea. Escribe cuánto has sacado del lote en total, o completa el apunte con la cantidad total.",
      // **El de los días que faltan (T15, 05/10/2026)**: lo usa `app.js` para escribir el «cuándo» de un
      // trabajo previsto («Dentro de…»), y es una frase que ya existía para los días de espera de un
      // tratamiento. Sin ella en la copia, la agenda de las pruebas diría «20/04/2026 · » y nadie lo
      // vería, que es exactamente para lo que está esta copia.
      V8_faltan_dias: "Faltan {cuantos} días.",
      // **Los dos de los trabajos (T15) que `app.js` traduce a frase**: el que dice que un apunte
      // anulado no cuenta (sale en la agenda y en el historial, marcado y con su motivo) y el que dice
      // que **un rodillo detrás de una siembra no borra lo sembrado**, que es lo primero que se pregunta
      // al ver un apero justo después de sembrar.
      TJ3_el_apunte_esta_anulado:
        "Este apunte está anulado: lo que había salido del almacén vuelve a contar.",
      TJ8_un_rodillo_no_cambia_lo_sembrado:
        "Pasar el rodillo o el cultivador no cambia lo que hay sembrado: eso lo cambia sembrar o plantar.",
    },
    etiquetas: {
      // Estas preguntas se piden desde el mapa de campos de `app.js` (`t("etiquetas.<clave>.pregunta")`) y **no estaban** en esta copia: mientras faltaban, las
      // pantallas de alta las pintaban en blanco en los tests y nadie lo veía. Ahora las copia el
      // guardián de `tests/test_interfaz.py` (`test_los_campos_del_mapa_tambien_estan_en_la_copia`).
      // ***Los dos de la riqueza*** (CRM-07, 17/10/2026): **la base** y **la densidad**. La copia tiene que
    // decir lo mismo que sirve el servidor, o la pregunta sale en blanco en este test y **el test no la
    // ve** -es el agujero que cerro `test_los_campos_del_mapa_tambien_estan_en_la_copia`-.
    "abono.base_de_la_riqueza": {
      pregunta: "¿Cómo viene la riqueza en la etiqueta?",
      pista: "En los líquidos puede venir por litro en vez de por ciento en masa",
    },
    "abono.densidad_kg_por_litro": {
      pregunta: "¿Cuánto pesa un litro?",
      pista: "En kilos por litro. Hace falta para los líquidos en % en masa; si no consta, déjalo en blanco",
    },
    "abono.nombre": { pregunta: "¿Cómo se llama el abono?", pista: "Tal y como viene en el saco" },
      "abono.riqueza_k": { pregunta: "Potasio (el tercer número)", pista: "Si el saco no lo trae, dejalo en blanco: quedara como \"no consta\"" },
      "abono.riqueza_n": { pregunta: "Nitrógeno (el primer número)", pista: "Si el saco no lo trae, dejalo en blanco: quedara como \"no consta\"" },
      "abono.riqueza_p": { pregunta: "Fósforo (el segundo número)", pista: "Si el saco no lo trae, dejalo en blanco: quedara como \"no consta\"" },
      "abono.tipo": { pregunta: "¿Es mineral o ecológico?", pista: "Si no lo sabes, déjalo como está" },
      "aplicador.es_empresa": { pregunta: "¿Es una empresa o una persona?", pista: "Si es una empresa, se apunta su número de registro" },
      "aplicador.fecha_caducidad_carne": { pregunta: "¿Cuándo caduca el carné?", pista: "Te aviso un mes antes para que lo renueves" },
      "aplicador.nombre": { pregunta: "¿Quién echa el producto?", pista: "Escribe tu nombre si lo echas tú" },
      "aplicador.numero_carne": { pregunta: "¿Qué número de carné tiene?", pista: "El carné de echar productos. Sin él no se puede aplicar" },
      "aplicador.numero_reganip": { pregunta: "¿Y número del registro de equipos?", pista: "Solo si aplica productos con equipo aéreo o de otro tipo. Si no, déjalo" },
      "aplicador.numero_ropo": { pregunta: "¿Tiene número de registro?", pista: "Si no lo sabes, déjalo en blanco" },
      "aplicador.tipo_carne": { pregunta: "¿Qué carné tiene?", pista: "Básico o cualificado, lo pone el carné" },
      "equipo.fecha_proxima_iteaf": { pregunta: "¿Cuándo le toca la ITV?", pista: "Con la ITV caducada no se puede echar producto. Te aviso antes" },
      "equipo.nombre": { pregunta: "¿Cómo llamas tú a la máquina?", pista: "Por ejemplo: el pulverizador, el atomizador grande" },
      "equipo.numero_roma": { pregunta: "¿Qué número de registro tiene la máquina?", pista: "Si no lo sabes, déjalo en blanco" },
      "instalacion.municipio": { pregunta: "¿En qué pueblo está?", pista: "Si no lo sabes, déjalo en blanco" },
      "instalacion.referencia_catastral": { pregunta: "¿Tiene número del Catastro?", pista: "Sale en el recibo del IBI. Si no lo sabes, déjalo en blanco" },
      "instalacion.superficie_m2": { pregunta: "¿Cuántos metros cuadrados tiene?", pista: "Si no lo sabes, déjalo en blanco" },
      "instalacion.tipo": { pregunta: "¿Qué es?", pista: "Elige lo que más se parezca" },
      "instalacion.uso": { pregunta: "¿Para qué la usas?", pista: "Por ejemplo: guardar el grano, guardar la maquinaria" },
      "labor.animales_propios": { pregunta: "¿Y eran tuyos?", pista: "Si el ganado es de tu explotación. Pueden ser las dos cosas" },
      "labor.animales_terceros": { pregunta: "¿Los animales eran de otra persona?", pista: "Si te han traído ganado a pastar, contesta que sí" },
      "labor.cantidad_semilla_kg": { pregunta: "Semilla que has echado", pista: "En kilos. Si no lo sabes, déjalo en blanco" },
      "labor.densidad_plantacion": { pregunta: "Plantas por hectárea", pista: "Si lo sabes" },
      "labor.dosis_siembra_kg_ha": { pregunta: "Kilos por hectárea", pista: "Si lo sabes. Si no, déjalo" },
      "labor.lote_semilla": { pregunta: "El número de lote", pista: "Viene en el saco. Sirve si hay un problema con esa partida" },
      "labor.marco_plantacion": { pregunta: "A qué marco", pista: "La distancia entre plantas y entre filas, por ejemplo 3 por 1,5 metros" },
      "labor.nitratos_agua": { pregunta: "Los nitratos del agua", pista: "Si tienes el análisis del agua. En miligramos por litro" },
      "labor.numero_contador": { pregunta: "El número del contador", pista: "El que viene en el recibo o en el aparato" },
      "labor.restos_desbroce_depositados": { pregunta: "¿Dejaste los restos del desbroce en el suelo?", pista: "Responde solo si lo sabes" },
      "labor.restos_poda_depositados": { pregunta: "¿Dejaste los restos de la poda en el suelo?", pista: "Responde solo si lo sabes" },
      "labor.siembra_directa": { pregunta: "¿Ha sido siembra directa?", pista: "Sin labrar antes, sobre el rastrojo del año pasado" },
      "labor.sistema_riego": { pregunta: "Cómo riegas", pista: "Aspersión, goteo, a manta…" },
      "labor.tipo_cobertura": { pregunta: "¿Qué tipo de cubierta es?", pista: "Descríbela con tus palabras; falta el catálogo de códigos oficiales" },
      "labor.unidad_agua": { pregunta: "En qué la mides", pista: "Metros cúbicos, metros cúbicos por hectárea o milímetros" },
      "labor.volumen_agua": { pregunta: "Cuánta agua", pista: "Lo que marque el contador, o lo que calcules" },
      "parcela.captacion_consumo_humano": { pregunta: "¿Hay una toma de agua para beber cerca?", pista: "Si la hay, las reglas son más duras. Es importante decirlo bien" },
      "parcela.masa_agua_cerca": { pregunta: "¿Hay río, arroyo o balsa dentro o al lado?", pista: "Se pregunta para no contaminar el agua" },
      "parcela.municipio": { pregunta: "¿En qué pueblo está?", pista: "Junto con la provincia permite consultar la zona de nitratos" },
      "parcela.provincia": { pregunta: "¿En qué provincia está?", pista: "Pon la provincia de esta parcela, que puede ser distinta de la explotación" },
      "parcela.ref_sigpac": { pregunta: "¿Tiene número del SIGPAC?", pista: "Si no lo sabes, déjalo en blanco: se puede poner después" },
      "parcela.uso_sigpac": { pregunta: "¿Qué es esa tierra?", pista: "Como lo llama el SIGPAC. Si no lo sabes, déjalo en blanco" },
      "parcela.zona_vulnerable_nitratos": { pregunta: "¿Está en zona de nitratos?", pista: "Si no lo sabes, elige NO LO SÉ y no pasa nada" },
      "producto.autorizacion_excepcional": { pregunta: "¿Tiene un permiso especial?", pista: "El número del permiso, si te lo han dado para una plaga concreta" },
      "producto.autorizacion_hasta": { pregunta: "¿Hasta cuándo vale ese permiso?", pista: "Después de esa fecha el programa no te dejará apuntarlo" },
      "producto.autorizado": { pregunta: "¿Está autorizado este producto?", pista: "Si lo compraste en una tienda, sí. Se pone en NO cuando la Junta lo ha retirado" },
      "producto.cantidad_comprada": { pregunta: "Cuánto compraste", pista: "Lo que ponga en la factura" },
      "producto.dosis_maxima": { pregunta: "¿Cuánto se puede echar como mucho por hectárea?", pista: "Lo que pone la etiqueta. Con esto te aviso si te pasas" },
      "producto.fecha_caducidad": { pregunta: "¿Cuándo caduca?", pista: "Viene en el envase. Te aviso antes de que se pase" },
      "producto.fecha_compra": { pregunta: "Cuándo lo compraste", pista: "El día de la factura" },
      "producto.lote": { pregunta: "¿Qué número de lote trae?", pista: "Viene en el envase. Sirve si hay un problema con esa partida" },
      "producto.materia_activa": { pregunta: "¿Sabes lo que lleva dentro?", pista: "Si no lo sabes, déjalo en blanco: se rellena con el número de la etiqueta" },
      "producto.numero_registro": { pregunta: "¿Qué número trae la etiqueta?", pista: "Es el número que va junto al nombre. Con él sabré qué lleva y cuánto esperar" },
      "producto.permitido_ecologico": { pregunta: "¿Se puede usar en ecológico?", pista: "Solo importa si tu finca es ecológica. Si no lo sabes, déjalo como está" },
      "producto.plazo_seguridad_dias": { pregunta: "¿Cuántos días de espera trae?", pista: "Los días que hay que esperar antes de poder coger la cosecha" },
      "producto.proveedor": { pregunta: "¿Dónde lo has comprado?", pista: "La tienda o la cooperativa" },
      "producto.tipo_producto": { pregunta: "¿Qué tipo de producto es?", pista: "Escríbelo como aparece en la etiqueta. El código oficial sigue pendiente" },
      "producto.unidad_compra": { pregunta: "En qué lo compras", pista: "Litros, kilos, unidades…" },
      "producto.unidad_dosis": { pregunta: "¿En qué se mide esa dosis?", pista: "Viene en la etiqueta: por hectárea o por cada 100 litros" },
      "comun.parcela_id": { pregunta: "¿Dónde?", pista: "Toca la parcela" },
      "comun.fecha": { pregunta: "¿Cuándo?", pista: "Si es hoy, déjalo" },
      "comun.superficie_ha": { pregunta: "¿Cuántas hectáreas?", pista: "Las de la parcela" },
      "tratamiento.superficie": {
        pregunta: "¿Cuántas hectáreas has tratado?",
        pista: "Viene puesto lo de la parcela",
      },
      "tratamiento.justificacion": { pregunta: "¿Por qué lo has echado?", pista: "El motivo" },
      "tratamiento.producto_id": {
        pregunta: "¿Qué producto has echado?",
        pista: "De los que has comprado",
      },
      "tratamiento.dosis": { pregunta: "¿Cuánto por hectárea?", pista: "La de la etiqueta" },
      "tratamiento.resumen": { pregunta: "Mira si está bien", pista: "Si algo no cuadra, vuelve" },
      "tratamiento.observaciones": { pregunta: "¿Quieres apuntar algo más?", pista: "Opcional" },
      "tratamiento.quien_maquina": { pregunta: "¿Quién lo ha echado y con qué máquina?", pista: "Opcional" },
      "tratamiento.aplicador_id": { pregunta: "¿Quién lo ha echado?", pista: "" },
      "tratamiento.equipo_id": { pregunta: "¿Con qué máquina?", pista: "" },
      "equipo.tipo": { pregunta: "¿Qué máquina es?", pista: "Un pulverizador, un atomizador, una mochila…" },
      "equipo.marca": { pregunta: "¿De qué marca es?", pista: "Si no lo sabes, déjalo" },
      "equipo.modelo": { pregunta: "¿Y el modelo?", pista: "Viene en la chapa de la máquina" },
      "equipo.titularidad": { pregunta: "¿De quién es?", pista: "Si la máquina no va inscrita en el ROMA, dilo aquí" },
      "equipo.fecha_adquisicion": { pregunta: "¿Cuándo la compraste?", pista: "Si no te acuerdas del día, pon el año" },
      "equipo.fecha_iteaf": { pregunta: "¿Cuándo pasó la última inspección?", pista: "La fecha del papel de la ITV" },
      "tratamiento.instalacion_id": { pregunta: "¿En qué nave o almacén?", pista: "Tiene que estar antes" },
      "tratamiento.no_es_parcela": { pregunta: "¿No es en una parcela?", pista: "Si has tratado una nave, dilo aquí" },
      "parcela.alias": { pregunta: "¿Cómo llamas tú a esa tierra?", pista: "El nombre que usas" },
      // El grupo de tierras (ronda 92): un grupo lo junta el programa, así que lo único que se pregunta
      // es cómo lo llama el agricultor. Es el formulario de corregir un grupo, entero. Los otros cuatro
      // campos van aquí igual —hay una prueba que lo exige— porque están en el mapa de campos de
      // `app.js`, aunque no haya ningún paso que los pinte.
      "grupo.nombre": {
        pregunta: "¿Cómo llamas tú a este grupo?",
        pista: "El nombre que usas tú para estas tierras juntas",
      },
      "grupo.parcela_ids": { pregunta: "¿Qué tierras van en este grupo?", pista: "Las junta el programa: las que se llevan igual" },
      "grupo.campana_id": { pregunta: "¿De qué año es el grupo?", pista: "El año que estás llevando" },
      "grupo.cultivo": { pregunta: "¿Qué se lleva en estas tierras?", pista: "El cultivo que tienen en común" },
      "grupo.sistema": { pregunta: "¿Secano o regadío?", pista: "Lo que tienen en común esas tierras" },
      // El año del cuaderno (ronda 93): las cuatro preguntas de su formulario. Faltaban en esta copia y
      // sus pasos salían con la pregunta en blanco (lo caza `test_interfaz.py`).
      "campana.anio": { pregunta: "¿De qué año es?", pista: "El año del cuaderno: 2026, 2027…" },
      "campana.fecha_inicio": { pregunta: "¿Cuándo empieza ese año?", pista: "Muchas cosechas empiezan en septiembre" },
      "campana.fecha_fin": { pregunta: "¿Cuándo termina?", pista: "El día en que se acaba ese año" },
      "campana.cerrada": { pregunta: "¿Has terminado ese año?", pista: "Márcalo cuando no vayas a apuntar nada más" },
      "campana.fechas": {
        pregunta: "¿Cuándo empieza y cuándo termina ese año?",
        pista: "Muchas cosechas empiezan en septiembre, no en enero",
      },
      "instalacion.alias": { pregunta: "¿Cómo llamas tú a esa nave?", pista: "El nombre que usas tú" },
      "parcela.superficie_ha": { pregunta: "¿Cuántas hectáreas tiene?", pista: "Las del SIGPAC" },
      "parcela.sistema": { pregunta: "¿Secano o regadío?", pista: "Importa para el abono" },
      "producto.nombre_comercial": { pregunta: "¿Cómo se llama el producto?", pista: "Como en el envase" },
      "plan.cultivo": { pregunta: "¿Qué vas a abonar?", pista: "El cultivo que hay" },
      "plan.necesidades": { pregunta: "¿Qué necesita el cultivo?", pista: "Kilos de cada cosa" },
      "plan.necesidad_n": { pregunta: "Nitrógeno (N)", pista: "Si no lo sabes, dejalo en blanco" },
      "plan.necesidad_p": { pregunta: "Fósforo (P)", pista: "Si no lo sabes, dejalo en blanco" },
      "plan.necesidad_k": { pregunta: "Potasio (K)", pista: "Si no lo sabes, dejalo en blanco" },
      "plan.produccion_esperada_kg_ha": { pregunta: "¿Cuánto esperas sacar?", pista: "Kilos por hectárea" },
      "plan.aportes_suelo_agua": { pregunta: "¿Qué le aporta la tierra?", pista: "Si no lo sabes, déjalo" },
      "plan.notas": { pregunta: "¿Quieres apuntar algo más?", pista: "Opcional" },
      "analitica.tipo": { pregunta: "¿Qué has mandado analizar?", pista: "Casi siempre es la tierra" },
      "analitica.sitio": { pregunta: "¿De dónde salió?", pista: "Toca la parcela" },
      "analitica.no_es_parcela": { pregunta: "¿No es de una parcela?", pista: "El agua de una balsa, por ejemplo" },
      "analitica.fecha_toma_muestra": { pregunta: "¿Cuándo cogiste la muestra?", pista: "El día que la cogiste" },
      "analitica.parametros": { pregunta: "Copia los números del boletín", pista: "Rellena solo los que vengan" },
      "analitica.laboratorio": { pregunta: "¿Quién ha hecho el análisis?", pista: "El laboratorio que firma" },
      "analitica.numero_informe": { pregunta: "¿Qué número tiene el boletín?", pista: "Viene arriba del papel" },
      "analitica.fecha_resultado": { pregunta: "¿Cuándo te dieron el resultado?", pista: "El día del boletín" },
      "analitica.lote": { pregunta: "¿De qué lote o partida?", pista: "Si era de un lote concreto" },
      "analitica.sustancia_detectada": { pregunta: "¿Qué sustancia han encontrado?", pista: "Lo que diga el boletín" },
      "analitica.observaciones": { pregunta: "¿Quieres apuntar algo más?", pista: "Opcional" },
      "analitica.elegir_para_el_plan": { pregunta: "¿De qué análisis sale este plan?", pista: "De esta parcela" },
      "asesor.nombre": { pregunta: "¿Cómo se llama tu técnico?", pista: "El asesor que te dice qué hacer" },
      "asesor.numero_ropo": { pregunta: "¿Qué número de asesor tiene?", pista: "Su número del registro. Pídeselo" },
      "asesor.ambito": { pregunta: "¿De qué te asesora?", pista: "De plagas, de producción integrada o de ecológico" },
      "asesor.entidad_certificacion": { pregunta: "¿Qué entidad lo certifica?", pista: "Si no lo sabes, déjalo" },
      "asesor.telefono": { pregunta: "¿Su teléfono?", pista: "Opcional" },
      "tratamiento.asesor_id": { pregunta: "¿Te lo ha asesorado un técnico?", pista: "Si lo decides tú solo, pulsa DEJARLO" },
      "tratamiento.asesor_fecha": { pregunta: "¿Cuándo te lo dijo?", pista: "El día que hablaste con él" },
      "tratamiento.asesoramiento_validado": { pregunta: "¿Te dio el visto bueno?", pista: "Si el técnico estuvo de acuerdo" },
      "labor.semilla": { pregunta: "¿Cuánta semilla has echado?", pista: "En kilos" },
      "labor.semilla_detalle": { pregunta: "¿De qué saco era la semilla?", pista: "El número de lote" },
      // Estos tres los usa el paso de los detalles de la semilla, y faltaban en la copia de los
      // textos: por eso nadie comprobaba que la pregunta de la semilla tratada sale en pantalla.
      "labor.material_tratado": { pregunta: "¿La semilla venía tratada?", pista: "Lo suele poner el saco" },
      "labor.material_adquirido": { pregunta: "¿La compraste?", pista: "Si la has comprado, dilo" },
      "labor.fecha_adquisicion": { pregunta: "¿Cuándo la compraste?", pista: "Si no lo sabes, déjalo" },
      "labor.tratamiento_semilla": { pregunta: "¿Qué le habían echado a la semilla?", pista: "Lo que ponga en la etiqueta del saco" },
      "labor.fecha_tratamiento_semilla": { pregunta: "¿Cuándo se trató la semilla?", pista: "Si no lo sabes, déjalo en blanco" },
      "labor.eficacia_tratamiento_semilla": { pregunta: "¿Cómo ha funcionado?", pista: "Lo mismo que de un tratamiento del campo" },
      "labor.plantacion_detalle": { pregunta: "¿Cómo has plantado?", pista: "Cuántas plantas por hectárea" },
      "labor.agua": { pregunta: "¿Cuánta agua has echado?", pista: "Lo que marque el contador" },
      "labor.origen_agua": { pregunta: "¿De dónde ha salido el agua?", pista: "Del pozo, del canal, de la balsa" },
      "labor.agua_detalle": { pregunta: "¿Y los nitratos del agua?", pista: "Si tienes el análisis del agua" },
      "labor.cual": { pregunta: "¿Cuál de estos?", pista: "Si no es ninguno, elige OTRA COSA y lo escribes luego" },
      "labor.equipo_id": { pregunta: "¿Con qué máquina lo has hecho?", pista: "Si lo has hecho a mano, deja el botón DEJARLO y sigue", sin_maquinas: "Añádela primero en Mis cosas." },
      "labor.destino_cosecha": { pregunta: "¿Qué salió de esta cosecha y qué quedó en el suelo?", pista: "Opcional" },
      "labor.semillas_siembra": { pregunta: "¿Sacaste semilla para sembrar?", pista: "" },
      "labor.plantas_cosechadas": { pregunta: "¿Recogiste plantas o partes de ellas?", pista: "" },
      "labor.sin_cosechar_ambiental": { pregunta: "¿Dejaste algo sin cosechar por motivos ambientales?", pista: "" },
      "labor.restos_cosecha_depositados": { pregunta: "¿Dejaste los restos en el suelo?", pista: "" },
      "labor.fecha_establecimiento_cubierta": { pregunta: "¿Cuándo estableciste la cubierta?", pista: "" },
      "labor.anchura_cubierta_m": { pregunta: "¿Qué anchura tiene?", pista: "" },
      "labor.anchura_libre_proyeccion_m": { pregunta: "¿Qué anchura queda libre?", pista: "" },
      // Cómo se echó el producto: la pantalla opcional que se añadió en la ronda 18.
      "tratamiento.como_fue": { pregunta: "¿Quieres apuntar cómo fue?", pista: "Es opcional" },
      "tratamiento.hora_inicio": { pregunta: "¿A qué hora lo echaste?", pista: "Por ejemplo las siete y media" },
      "tratamiento.hora_fin": { pregunta: "¿Y a qué hora acabaste?", pista: "Si no lo sabes, déjalo" },
      "tratamiento.estado_cultivo": { pregunta: "¿Cómo estaba la planta?", pista: "Naciendo, espigando" },
      "tratamiento.como_estaba_el_dia": { pregunta: "¿Cómo estaba el día?", pista: "El viento se pregunta mucho" },
      "tratamiento.temperatura_c": { pregunta: "¿Qué temperatura hacía?", pista: "En grados" },
      "tratamiento.humedad_pct": { pregunta: "¿Había humedad?", pista: "En tanto por ciento" },
      "tratamiento.viento_kmh": { pregunta: "¿Cuánto viento hacía?", pista: "En kilómetros por hora" },
      "tratamiento.viento_direccion": { pregunta: "¿De dónde venía el viento?", pista: "Norte, sur" },
      "tratamiento.volumen_caldo_l_ha": { pregunta: "¿Cuánta mezcla has gastado por hectárea?", pista: "En litros" },
      "tratamiento.franja_seguridad_respetada": { pregunta: "¿Has dejado la orilla sin tratar?", pista: "Junto al río" },
      "tratamiento.aplicado_a_mano": { pregunta: "¿Lo has echado a mano?", pista: "Con mochila o con un apero" },
      "tratamiento.eficacia": { pregunta: "¿Cómo ha funcionado?", pista: "Si no lo sabes, déjalo" },
      "tratamiento.unidad_cantidad_aplicada": { pregunta: "¿En qué unidad se mide la cantidad aplicada?", pista: "" },
      "tratamiento.operadores_expuestos": { pregunta: "¿Cuántos estabais trabajando?", pista: "Contando a ti" },
      "tratamiento.incidencias": { pregunta: "¿Pasó algo raro?", pista: "Si se atascó la boquilla" },
      "venta.tipo": { pregunta: "¿Cómo lo has vendido?", pista: "A un comprador o tú al cliente" },
      "venta.producto": { pregunta: "¿Qué has vendido?", pista: "Lo que ponga en el albarán" },
      "venta.variedad": { pregunta: "¿De qué variedad?", pista: "Si lo sabes" },
      "venta.cantidad": { pregunta: "¿Cuánto has vendido?", pista: "El número del albarán" },
      "venta.unidad": { pregunta: "¿En qué lo mides?", pista: "Kilos o toneladas" },
      "venta.fecha": { pregunta: "¿Cuándo salió?", pista: "El primer día" },
      "venta.fecha_fin": { pregunta: "¿Y el último día?", pista: "Si salió todo el mismo día, déjalo" },
      "venta.lote": { pregunta: "¿De qué partida era?", pista: "El número de lote" },
      "venta.comprador": { pregunta: "¿A quién se lo has vendido?", pista: "La cooperativa o el cliente" },
      "venta.numero_albaran": { pregunta: "¿Qué número tiene el albarán?", pista: "El papel de la venta" },
      "venta.de_donde": { pregunta: "¿De qué parcela salió?", pista: "Si salió de varias, déjalo" },
      "venta.observaciones": { pregunta: "¿Quieres apuntar algo más?", pista: "Opcional" },
      // Estas las usa el asistente y no estaban en esta copia: mientras faltaban, los tests
      // pasaban con la pregunta en blanco y nadie comprobaba que de verdad se preguntara.
      // Ahora hay un test en Python (`test_las_etiquetas_del_asistente_no_se_quedan_fuera_del_test`)
      // que compara esta copia con lo que sirve `/api/interfaz` y avisa si falta alguna.
      "cuaderno.repetir": { pregunta: "¿Lo apuntamos otra vez?", pista: "Puedes cambiar el día antes de apuntarlo" },
      "tratamiento.tipo": { pregunta: "¿Dónde has echado el producto?", pista: "Casi siempre es en una parcela. Elige lo que corresponda" },
      "labor.que_has_hecho": { pregunta: "¿Qué has hecho?", pista: "Elige lo que más se parezca" },
      "labor.detalles": { pregunta: "¿Algo más que apuntar?", pista: "Por ejemplo, cuántos kilos has recogido o de dónde salió el agua" },
      "labor.animales": { pregunta: "¿De quién era el ganado?", pista: "Si te han traído animales a pastar, o si son tuyos. Pueden ser las dos cosas" },
      "labor.cosecha_cantidad": { pregunta: "¿Cuánto has recogido?", pista: "En kilos, si lo sabes. Si no, déjalo en blanco" },
      "labor.datos_propios": { pregunta: "¿Algún dato propio de este trabajo?", pista: "Las preguntas cambian según el trabajo que elegiste" },
      "plan.herramienta": { pregunta: "¿Has usado un programa o una herramienta para hacerlo?", pista: "Si lo has calculado tú de cabeza, contesta que no" },
      "fertilizacion.fertilizante_id": { pregunta: "¿Qué abono has echado?", pista: "El nombre que viene en el saco" },
      "fertilizacion.cantidad_total_kg": { pregunta: "¿Cuántos kilos de abono has echado?", pista: "Los que salen de los sacos. De aquí sale el kg por hectárea." },
      "fertilizacion.kg_ha_producto": { pregunta: "¿Cuántos kilos por hectárea?", pista: "Los kilos de abono que has echado en cada hectárea" },
      "fertilizacion.resumen": { pregunta: "Mira si está bien", pista: "Si algo no cuadra, pulsa VOLVER y lo cambias" },
    },
    justificaciones: ["Vi la plaga o la hierba en el campo", "Aviso de la Junta"],
    unidades: ["L"],
    unidades_dosis: ["L/ha", "kg/ha"],
    certificado: {
      boton: "ENTRAR CON MI CERTIFICADO",
      pista: "Sin teclear nada: usa el certificado que ya tienes",
      no_configurado: "En esta instalación todavía no se puede entrar con certificado.",
    },
    firma: {
      titulo: "Firmar el cuaderno",      explica: "Firmar es lo que hace que el cuaderno valga delante de la administración.",
      sin_firmar: "Todavía no has firmado el cuaderno de este año.",
      no_puede_firmar: "Para firmar hace falta que entres con tu certificado.",
      boton: "FIRMAR EL CUADERNO",
      paso_1: "1. Descarga este fichero",
      paso_2: "2. Fírmalo con AutoFirma",
      paso_3: "3. Sube aquí la firma",
      descargar: "DESCARGAR EL FICHERO",
      subir: "SUBIR LA FIRMA",
      instrucciones: "AutoFirma es el programa que usa la administración.",
      fichero_listo: "Ya tienes el fichero.",
      firmado_ok: "Firmado.",
    },
    plan: {
      titulo: "El plan de abono del año",
      explica: "El plan dice qué abono vas a echar, cuánto y en qué momento.",
      precedente: "El año anterior había",
      herramienta_pregunta: "Lo hice con una herramienta",
      sin_planes: "Todavía no tienes ningún plan de abono apuntado este año.",
      hacer: "HACER EL PLAN DE ABONO",
      guardado: "Plan guardado.",
      guardado_titulo: "Plan guardado",
      se_usa: "Cuando apuntas que has abonado, puedes decir a qué plan responde.",
      previsto: "Tenías previsto",
      aplicado: "Llevas echado",
      queda: "Te queda",
      pasado: "Ojo: llevas más de lo que tenías previsto.",
      sin_necesidades: "A este plan le faltan las necesidades del cultivo.",
      apuntes_uno: "Un abono apuntado contra este plan.",
      apuntes_varios: "{cuantos} abonos apuntados contra este plan.",
      sin_apuntes: "Todavía no has apuntado ningún abono contra este plan.",
      obligatorio: "El plan de abono es obligatorio desde el 1 de septiembre de 2026.",
      kilos_por_hectarea: "kilos por hectárea",
      ver: "VER EL PLAN DE ABONO",
      plan_de: "Plan de {cultivo}",
      tabla_previsto: "Tenías previsto",
      tabla_aplicado: "Llevas",
      tabla_queda: "Te queda",
      tabla_pasado: "Pasado",
      apunta_abonos: "Cuando apuntes un abono, podrás decir que va con este plan.",
      se_basa_en: "Este plan se apoya en un análisis:",
      sin_analisis: "Este plan no se apoya en ningún análisis.",
    },
    analitica: {
      titulo: "Los análisis",
      explica: "Aquí se guardan los análisis que has mandado hacer.",
      sin_analisis: "Todavía no has apuntado ningún análisis.",
      anadir: "APUNTAR UN ANÁLISIS",
      ver: "VER MIS ANÁLISIS",
      guardado: "Análisis apuntado.",
      guardado_titulo: "Análisis apuntado",
      se_usa: "Dónde se aprovecha esto:",
      aprovecha: "Cuando hagas el plan de abono podrás decir que se apoya en él.",
      cuantos_uno: "1 análisis guardado",
      cuantos: "{cuantos} análisis guardados",
      sin_numeros: "Sin números apuntados: solo está guardado el boletín.",
      subir_informe: "SUBIR EL PAPEL DEL LABORATORIO",
      informe_subido: "Boletín guardado.",
      informe_ya_esta: "Ya tienes el boletín guardado.",
      descargar_informe: "DESCARGAR EL BOLETÍN",
      sin_informe: "De este análisis no tienes el papel guardado.",
      el_informe: "El papel del laboratorio",
      de: "Análisis de {que}",
      de_la_parcela: "de {parcela}",
      cogida: "Muestra cogida el {fecha}",
      resultado: "Resultado el {fecha}",
      hace_anios: "Hace {anios} años",
      quien: "Laboratorio",
      informe_numero: "Nº de boletín",
      informe_titulo: "Informe de análisis",
      informe_sin_nada: "Todavía no hay ningún análisis apuntado este año.",
      usar_en_el_plan: "USAR ESTE ANÁLISIS EN EL PLAN",
      apunta_primero: "Primero apunta el análisis.",
      parcela_vacia: "Sin parcela asignada",
      sin_oficial: "De la tierra son los nueve que pide la administración.",
      subir_ahora: "¿Quieres subir el papel del laboratorio?",
      subir_ahora_pista: "Puedes hacerle una foto con el móvil.",
      saltar_informe: "AHORA NO, LO DEJO ASÍ",
      sitio: "De dónde salió",
      sin_analisis_de_la_parcela: "Esta parcela no tiene ningún análisis apuntado. Se puede hacer el plan igual.",
    },
    tipos_analitica: [
      { valor: "suelo", texto: "La tierra" },
      { valor: "agua_riego", texto: "El agua con la que riego" },
      { valor: "cultivo", texto: "La planta" },
      { valor: "producto_cosechado", texto: "Lo que he recogido" },
      { valor: "residuos", texto: "Si lleva restos de lo que eché" },
    ],
    parametros_analitica: {
      suelo: [
        { clave: "materia_organica", pregunta: "Materia orgánica", etiqueta: "Materia orgánica", unidad: "%", oficial: true },
        { clave: "ph", pregunta: "pH", etiqueta: "pH", unidad: "", oficial: true },
        { clave: "fosforo_asimilable", pregunta: "Fósforo", etiqueta: "Fósforo asimilable", unidad: "ppm", oficial: true },
      ],
      agua_riego: [
        { clave: "nitratos", pregunta: "Nitratos", etiqueta: "Nitratos", unidad: "mg/L", oficial: false },
      ],
      cultivo: [
        { clave: "nitrogeno_total", pregunta: "Nitrógeno", etiqueta: "Nitrógeno total", unidad: "%", oficial: false },
      ],
      producto_cosechado: [
        { clave: "humedad", pregunta: "Humedad", etiqueta: "Humedad", unidad: "%", oficial: false },
      ],
      residuos: [
        { clave: "residuo", pregunta: "Cuánto residuo han encontrado", etiqueta: "Residuo encontrado", unidad: "mg/kg", oficial: false },
      ],
    },
    analitica_de_parcela: ["suelo", "cultivo"],
    // El tipo de carné de quien echa el producto: los cuatro del cuaderno de la Junta.
    tipos_carne: [
      { valor: "basico", texto: "Básico" },
      { valor: "cualificado", texto: "Cualificado" },
      { valor: "fumigador", texto: "Fumigador" },
      { valor: "piloto", texto: "Piloto (tratamientos aéreos)" },
    ],
    // De quién es una máquina de echar producto: las tres listas de la app oficial (propia, ajena y
    // equipos sin ROMA).
    titularidades_equipo: [
      { valor: "propia", texto: "Es mía" },
      { valor: "ajena", texto: "Es de otro (me la deja o me la alquila)" },
      { valor: "no_roma", texto: "No va inscrita en el ROMA (mochila, apero…)" },
      // **La cuarta es nueva** (A11, 05/10/2026): de quién es una máquina no se deduce, así que se
      // puede contestar «no lo sé» en vez de quedar como propia sin que nadie lo diga.
      { valor: "nulo", texto: "No lo sé" },
    ],
    ambitos_asesor: [
      { valor: "gip", texto: "Plagas (gestión integrada)" },
      { valor: "produccion_integrada", texto: "Producción integrada" },
      { valor: "ecologico", texto: "Producción ecológica" },
      { valor: "otros", texto: "Otras cosas" },
    ],
    origenes_agua: [
      { valor: "pozo", texto: "Pozo o sondeo" },
      { valor: "canal", texto: "Canal o acequia" },
      { valor: "balsa", texto: "Balsa" },
    ],
    sistemas_riego: [
      { valor: "aspersion", texto: "Aspersión" },
      { valor: "goteo", texto: "Goteo" },
    ],
    unidades_agua: [
      { valor: "m3", texto: "metros cúbicos (m³)" },
      { valor: "m3/ha", texto: "metros cúbicos por hectárea (m³/ha)" },
      { valor: "mm", texto: "milímetros (mm)" },
    ],
    eficacia_del_tratamiento: [
      { valor: "muy_bien", texto: "Muy bien: no ha quedado nada" },
      { valor: "bien", texto: "Bien: ha quedado algo, pero poco" },
      { valor: "regular", texto: "Regular: habría que repetirlo" },
      { valor: "mal", texto: "Mal: no ha servido" },
    ],
    sigpac: {
      titulo: "Traer la parcela del SIGPAC",
      explica: "Si tienes la referencia del trozo, el programa trae solo la superficie.",
      referencia: "La referencia del trozo",
      referencia_pista: "Siete números: provincia, municipio, agregado, zona, polígono, parcela y recinto",
      referencia_como_sea: "La referencia de tu trozo",
      referencia_como_sea_pista: "Pega lo que tengas: la del visor del SIGPAC (37:70:0:0:503:51), los siete números del papel (37-70-0-0-503-51-1) o la referencia catastral (37070A50300051000AQ)",
      referencia_ejemplo: "37-22-0-0-501-427-1",
      poligono: "El polígono",
      parcela: "El número de la parcela",
      o_pega_la_referencia: "Y si tienes la referencia a mano, pégala aquí:",
      buscar: "BUSCAR MIS TROZOS",
      buscar_titulo: "Los trozos que hay en esa parcela",
      buscar_explica: "Marca los que sean tuyos y los traigo.",
      sin_recintos: "En esa parcela el SIGPAC no tiene ningún trozo.",
      recinto_numero: "Trozo {numero}",
      traer_los_marcados: "TRAERME LOS MARCADOS",
      marca_alguno: "Marca al menos un trozo para poder traerlo.",
      busca_antes: "Pulsa BUSCAR MIS TROZOS y marca los que sean tuyos.",
      busqueda_incompleta: "Para buscar tus trozos hacen falta el pueblo y los números del polígono y de la parcela.",
      falta_el_recinto: "A esa referencia le falta el número del trozo.",
      estas_no: "Estas no se han podido traer",
      traer: "TRAERME LOS DATOS",
      comprobar: "COMPROBAR LA REFERENCIA",
      alias: "¿Cómo llamas tú a esa tierra?",
      sistema: "¿Es de secano o de regadío?",
      municipio_parcela: "¿En qué pueblo está esta parcela?",
      provincia_parcela: "¿En qué provincia está esta parcela?",
      ubicacion_pista: "Escribe los dos si los sabes.",
      trayendo: "Preguntando al SIGPAC…",
      traido_titulo: "Parcela traída del SIGPAC",
      traido: "Ya está. La superficie es la oficial.",
      que_ha_venido: "Lo que ha venido solo:",
      no_encontrado: "El SIGPAC no tiene ningún recinto con esa referencia.",
      sin_permiso_red: "No se ha podido preguntar al SIGPAC.",
      a_mano: "APUNTARLA A MANO",
      y_el_dibujo: "Y el dibujo del trozo, que sirve para el mapa",
      superficie_oficial: "Superficie oficial",
      uso: "Qué es",
      pendiente: "Pendiente",
      altitud: "Altitud",
      los_nombres_no_vienen: "El SIGPAC no trae los nombres del pueblo y la provincia.",
      que_hay_descargado: "Los datos oficiales del SIGPAC",
      productos: "Productos del catálogo oficial",
      usos: "Usos del suelo",
      licencia: "De dónde salen estos datos",
      actualizar: "Cómo actualizarlos",
      sin_datos: "Todavía no están descargados los datos oficiales del SIGPAC.",
    },
    venta: {
      titulo: "Lo que he vendido",
      explica: "Aquí se apunta lo que sale de la finca.",
      sin_nada: "Todavía no has apuntado ninguna venta este año.",
      anadir: "APUNTAR UNA VENTA",
      ver: "VER LO QUE HE VENDIDO",
      guardado: "Venta apuntada.",
      guardado_titulo: "Venta apuntada",
      se_usa: "Para qué sirve esto:",
      aprovecha: "Con el lote y las parcelas de origen se puede responder de dónde salió.",
      cuantas_una: "1 venta apuntada",
      cuantas: "{cuantas} ventas apuntadas",
      de_que: "Venta de {producto}",
      informe_titulo: "Cosecha comercializada",
      informe_sin_nada: "Todavía no hay ninguna venta apuntada este año.",
      cuadra: "Llevas vendidos {vendido} kg de los {cosechado} kg que apuntaste que cogiste.",
      no_cuadra: "Ojo: llevas vendidos {vendido} kg y apuntaste {cosechado} kg.",
      sin_cosecha: "Llevas vendidos {vendido} kg y no has apuntado ninguna cosecha.",
      nada_cosechado: "Todavía no has apuntado ninguna cosecha este año.",
      con_unidades: "Hay ventas en unidades, que no se pueden sumar con los kilos.",
      tipo: "Cómo lo vendiste",
      cuando: "¿Cuándo salió?",
      hasta_cuando: "¿Y hasta cuándo?",
      que: "¿Qué has vendido?",
      variedad: "¿De qué variedad?",
      cuanto: "¿Cuánto has vendido?",
      unidad: "¿En qué lo mides?",
      lote: "¿De qué partida?",
      comprador: "¿A quién se lo has vendido?",
      albaran: "¿Qué número tiene el albarán?",
      de_donde: "¿De qué parcelas salió?",
      observaciones: "¿Quieres apuntar algo más?",
      tabla_dia: "Día",
      tabla_que: "Qué",
      tabla_cuanto: "Cuánto",
      tabla_quien: "A quién",
      tabla_lote: "Partida",
      tabla_donde: "De dónde",
      tabla_albaran: "Albarán",
      vendido: "Lo que llevas vendido",
      cosecha_apuntada: "Lo que apuntaste que cogiste",
      queda_por_vender: "Te queda por vender",
      un_viaje: "Un solo día",
      varios_dias: "Salieron en varios días",
      sin_comprador: "No lo has dicho",
      sin_lote: "Sin partida",
      sin_donde: "Sin decir de dónde",
      varias_parcelas: "varias parcelas",
      dinero_fuera: "Aquí no se apunta el precio ni lo que te han pagado.",
    },
    tipos_venta: [
      { valor: "comercializada", texto: "Lo vendí a un comprador o a la cooperativa" },
      { valor: "venta_directa", texto: "Lo vendí yo directamente al cliente" },
    ],
    unidades_venta: [
      { valor: "kg", texto: "kilos", corto: "kg" },
      { valor: "t", texto: "toneladas", corto: "t" },
      { valor: "ud", texto: "unidades", corto: "ud" },
    ],
    sistemas: [
      { valor: "secano", texto: "Secano" },
      { valor: "regadio", texto: "Regadío" },
      // **El tercero es nuevo** (A10, 05/10/2026) y está aquí porque el servidor de verdad lo manda:
      // `catalogos.SISTEMAS_PARA_ELEGIR`. Antes eran dos y el que no tocaba nada quedaba de secano.
      { valor: "nulo", texto: "No lo sé" },
    ],
    tipos_instalacion: [
      { valor: "almacen", texto: "Almacén" },
      { valor: "nave", texto: "Nave" },
    ],
    tipos_tratamiento: [
      { valor: "parcela", texto: "En una parcela" },
      { valor: "semilla_tratada", texto: "La semilla ya venía tratada" },
      { valor: "postcosecha", texto: "Al producto ya recogido" },
      { valor: "instalaciones", texto: "En una nave o un almacén" },
    ],
    maestros: {
      titulo: "Mis parcelas, productos y máquinas",
      intro: "Aquí se da de alta lo que usas.",
      mis_cosas: "MIS PARCELAS, PRODUCTOS Y MÁQUINAS",
      antes_de_empezar: "Antes de empezar",
      falta_parcela: "Hace falta al menos una parcela.",
      anadir_primera_parcela: "AÑADIR MI PRIMERA PARCELA",
      anadir_parcela: "AÑADIR UNA PARCELA",
      anadir_producto: "AÑADIR UN PRODUCTO COMPRADO",
      anadir_abono: "AÑADIR UN ABONO",
      anadir_aplicador: "AÑADIR QUIÉN APLICA",
      anadir_equipo: "AÑADIR UNA MÁQUINA",
      anadir_instalacion: "AÑADIR UNA NAVE O UN ALMACÉN",
      seccion_parcela: "Parcelas",
      seccion_producto: "Productos que he comprado",
      seccion_abono: "Abonos",
      seccion_aplicador: "Quién aplica el producto",
      seccion_asesor: "Quién me asesora",
      seccion_equipo: "Máquinas de echar producto",
      seccion_instalacion: "Naves, almacenes e invernaderos",
      pista_asesor: "El técnico que te dice qué hacer",
      sin_asesor: "Todavía no has apuntado a ningún asesor.",
      anadir_asesor: "AÑADIR QUIÉN ME ASESORA",
      asesor_se_usa: "Cuando apuntas un tratamiento y dices que te lo ha asesorado un técnico.",
      pista_instalacion: "Donde guardas el grano o la maquinaria",
      sin_instalacion: "Todavía no has apuntado ninguna nave ni almacén.",
      instalacion_se_usa: "Cuando tratas una nave o un almacén.",
      pista_parcela: "Los trozos de tierra donde trabajas",
      pista_producto: "Lo que has comprado",
      pista_abono: "Los abonos que usas",
      pista_aplicador: "Tú o un trabajador",
      pista_equipo: "El pulverizador",
      sin_parcela: "Todavía no tienes parcelas.",
      sin_producto: "Todavía no has apuntado ningún producto comprado.",
      sin_abono: "Todavía no has apuntado ningún abono.",
      sin_aplicador: "Todavía no has apuntado quién aplica.",
      sin_equipo: "Todavía no has apuntado ninguna máquina.",
      guardado: "Apuntado. Ya lo tienes disponible.",
      donde_se_usa: "Dónde se usa:",
      parcela_se_usa: "Cuando dices dónde has trabajado.",
      grupo_opcional: "¿Quieres afinar más?",
      grupo_opcional_pista: "Esto es opcional.",
      sin_sitio_titulo: "Esto lo he oído pero no sé dónde ponerlo",
      falta_este_dato: "Falta esto: {pregunta}",
      // El buscador de tierras del paso (ronda 82).
      buscar_tierra: "Buscar entre tus tierras",
      buscar_tierra_ejemplo: "Por ejemplo: 503 51",
      buscar_tierra_pista: "Escribe unas letras del nombre, del pueblo o del número del SIGPAC",
      buscar_boton: "BUSCAR",
      verlas_todas: "VERLAS TODAS",
      buscar_sin_nada: "Con esas letras no encuentro ninguna tierra.",
      buscar_sin_nada_pista: "Prueba con menos letras, o míralo en la lista entera.",
      // Las tarjetas de tierra de esta pantalla (ronda 78): el rótulo de arriba, los datos con su
      // nombre delante, lo que le falta a esa tierra, el pie que dice qué pasa al tocarla y cuántas hay.
      tierra_numero: "Tierra n.º {numero}",
      tierra_sigpac: "Referencia oficial SIGPAC",
      tierra_cultivo: "Cultivo de este año",
      // El pueblo de la tierra, con su nombre delante (ronda 92: sale en la ficha que se enseña al
      // corregir o al borrar una tierra, para poder comprobar que es esa y no la de al lado).
      tierra_pueblo: "Pueblo",
      tierra_sin_cultivo: "Le falta decir qué tiene sembrado este año",
      tierra_ver_cultivo: "VER O CAMBIAR LO QUE HAY SEMBRADO",
      cuantas_tierras: "Tienes {cuantas} tierras apuntadas",
      cuantas_tierras_una: "Tienes 1 tierra apuntada",
    },
    dictado: {
      titulo: "Dímelo con la voz",
      intro: "Cuéntame lo que has hecho.",
      pista_boton: "cuéntamelo con tus palabras",
      boton: "HABLAR",
      escribe: "Escribe lo que has hecho",
      ejemplo: "Por ejemplo: «hoy he echado dos litros»",
      entender: "ENTENDERLO",
      no_se_puede: "Este navegador no sabe escuchar.",
      no_he_oido: "No he oído nada.",
      apuntarlo: "ESTÁ BIEN, APUNTARLO",
      corregir: "CORREGIRLO A MANO",
    },
    medidas_preventivas: [
      { codigo: "rotacion", pregunta: "¿Cambias de cultivo de un año a otro?", etiqueta: "Rotación de cultivos" },
      { codigo: "muestreo", pregunta: "¿Miras el campo antes de decidir echar algo?", etiqueta: "Muestreo y respeto de los umbrales de tratamiento" },
      { codigo: "higiene", pregunta: "¿Limpias la máquina al pasar de una parcela a otra?", etiqueta: "Higiene y limpieza de equipos y maquinaria" },
    ],
    medidas: {
      titulo: "Lo que hago sin echar producto",
      explica: "Antes de echar producto, la ley pide haber probado otras cosas.",
      sin_declarar: "Todavía no has dicho qué haces sin echar producto.",
      declarada_una: "Tienes marcada {cuantas} medida. Se puede cambiar cuando quieras.",
      declarada_varias: "Tienes marcadas {cuantas} medidas. Se pueden cambiar cuando quieras.",
      declarada_ninguna: "Has dicho que no haces ninguna de estas cosas.",
      hacer: "MARCAR LO QUE HAGO",
      ver: "VER LO QUE HAGO SIN PRODUCTO",
      guardado: "Apuntado.",
      guardado_titulo: "Medidas apuntadas",
      se_usa: "Dónde se aprovecha esto:",
      aprovecha: "Al apuntar un producto, lo que hagas aquí ya sale marcado.",
      marcar_titulo: "Marca lo que hagas en tu finca",
      marcar_pista: "Toca las que hagas.",
      guardar: "GUARDAR",
      no_hago_ninguna: "No hago ninguna de estas cosas",
      // Quitar la declaración entera (ronda 93). Sin estos textos, la pantalla que pregunta saldría en
      // blanco y el final del quitado no diría que se ha quitado.
      quitar: "BORRAR LO QUE HE DICHO DE ESTAS MEDIDAS",
      quitar_pista:
        "Esto no es decir que no haces ninguna: es dejar la finca sin contestar, como si no lo hubieras mirado nunca.",
      quitar_explica: "Sirve para volver a empezar: si contestaste por error, o si quieres mirarlo otra vez.",
      quitado_titulo: "Borrado",
      quitado: "Tu finca vuelve a estar sin contestar estas preguntas.",
      informe_titulo: "Medidas preventivas",
      informe_sin_nada: "Todavía no hay ninguna medida preventiva apuntada.",
      observaciones: "Lo que quieras añadir",
      observaciones_pista: "Las diez preguntas no cubren todo.",
      tus_palabras: "Tus palabras",
      sin_observaciones: "Sin nada más apuntado",
      de_la_finca: "En toda la finca",
      en_el_apunte: "Lo que hiciste antes de echarlo",
      del_ano: "Las de este año",
      catalogo_aviso: "El listado oficial no trae los códigos: los de aquí son internos.",
      pregunta_en_el_tratamiento: "¿Qué hiciste antes para no tener que echarlo?",
      pista_en_el_tratamiento: "Ya viene marcado lo que dijiste que haces en tu finca.",
    },
    provincias: ["Salamanca"],
    municipios: {
      elegir: "¿En qué pueblo está?",
      pista: "Escribe las primeras letras y elígelo de la lista",
      buscar: "BUSCAR EL PUEBLO",
      cualquiera: "Todas las provincias",
      codigo_pista: "Código {codigo}",
      no_esta_en_la_lista: "Ese pueblo no está en la lista de Castilla y León.",
      sin_lista: "No se ha podido cargar la lista de pueblos.",
    },
    tipos_abono: [{ valor: "mineral", texto: "Mineral, de fábrica" }],
    modos_aplicacion: [],
    momentos: [],
    plazos_legales: {},
  },
  "/api/campanas/actual": { id: 1, anio: 2026, fecha_inicio: "2026-01-01", fecha_fin: "2026-12-31", cerrada: false },
  // **Los años del cuaderno (ronda 93).** Los tres casos que tiene que saber enseñar la pantalla: el año
  // que se está llevando y **tiene cosas dentro** (no se puede quitar), otro con cosas y ya cerrado, y uno
  // vacío (ese sí se puede quitar). Los tres con lo que tienen dentro contado por el servidor, **y con el
  // desglose** (30/09/2026): los apuntes del cuaderno, las tierras con su cultivo dicho y las demás cosas.
  // Sin el desglose la pantalla decía «42 cosas apuntadas dentro» mientras el cuaderno decía «0 apuntes».
  "/api/campanas": [
    {
      id: 1,
      anio: 2026,
      fecha_inicio: "2025-09-01",
      fecha_fin: "2026-08-31",
      cerrada: false,
      cuantas_cosas: 42,
      apuntes: 5,
      tierras_con_cultivo: 35,
      otras_cosas: 2,
    },
    {
      id: 2,
      anio: 2025,
      fecha_inicio: "2024-09-01",
      fecha_fin: "2025-08-31",
      cerrada: true,
      cuantas_cosas: 38,
      apuntes: 38,
      tierras_con_cultivo: 0,
      otras_cosas: 0,
    },
    {
      id: 3,
      anio: 2024,
      fecha_inicio: "2024-01-01",
      fecha_fin: "2024-12-31",
      cerrada: true,
      cuantas_cosas: 0,
      apuntes: 0,
      tierras_con_cultivo: 0,
      otras_cosas: 0,
    },
  ],
  "/api/parcelas": [
    {
      id: 1,
      alias: "El Prado",
      superficie_ha: 2.43,
      sistema: "secano",
      superficie_oficial: true,
      // El pueblo y la referencia del SIGPAC: son las dos cosas que la tarjeta de una tierra enseña con
      // su nombre delante (ronda 78). Sin ellas no se podría comprobar que se enseñan.
      municipio: "Calvarrasa de Arriba",
      ref_sigpac: "37-70-0-0-503-51-1",
    },
    {
      // **La segunda tierra se añadió el 30/09/2026**, para la tabla del ordenador: con una sola no se
      // puede comprobar que **ordena** (ni el total del pie, que es lo que se viene a mirar en una tabla).
      id: 2,
      alias: "La Vega",
      superficie_ha: 5.0,
      sistema: "regadío",
      superficie_oficial: false,
      municipio: "Peñaranda de Bracamonte",
      ref_sigpac: "37-70-0-0-112-4-2",
    },
  ],
  "/api/productos": [],
  // Las parcelas que se llevan igual: la «unidad homogénea de cultivo» de la app oficial.
  "/api/grupos": [
    {
      id: 1,
      nombre: "Cebada (3 parcelas)",
      cultivo: "Cebada",
      sistema: "secano",
      creado_automaticamente: true,
      parcela_ids: [1, 2, 3],
      superficie_total_ha: 10.0,
    },
  ],
  // Qué hay sembrado en cada parcela. La primera no lo tiene dicho, que es el caso que hay que
  // poder arreglar; la segunda sí, y repite el cultivo del año pasado.
  "/api/cultivos": {
    textos: {},
    campana_id: 1,
    campana_anio: 2026,
    cuantos: 2,
    faltan: 1,
    sistemas: [
      { valor: "secano", texto: "Secano" },
      { valor: "regadío", texto: "Regadío" },
      // Como el de `/api/interfaz`: el de verdad trae tres (A10).
      { valor: "nulo", texto: "No lo sé" },
    ],
    resumen: "A 1 parcelas les falta decir qué tienen este año.",
    parcelas: [
      {
        parcela_id: 1,
        alias: "El Prado",
        superficie_ha: 2.43,
        sistema: "secano",
        uso_sigpac: "Labor secano",
        actual: null,
        anteriores: [],
        falta_decirlo: true,
        repite_el_del_ano_pasado: false,
      },
      {
        parcela_id: 2,
        alias: "La Vega",
        superficie_ha: 5.0,
        sistema: "regadío",
        uso_sigpac: "Labor regadío",
        actual: {
          id: 3,
          campana_id: 1,
          anio: 2026,
          especie: "Maíz",
          variedad: "Pioneer",
          sistema: "regadío",
          fecha_inicio: "2026-04-01",
          fecha_fin: null,
        },
        anteriores: [
          { id: 2, campana_id: 9, anio: 2025, especie: "Maíz", variedad: null, sistema: "regadío" },
        ],
        falta_decirlo: false,
        repite_el_del_ano_pasado: true,
      },
    ],
  },
  // El alta de un cultivo en una parcela. **Faltaba**, y sin ella el POST «fallaba»: la prueba del
  // camino bueno creía estar comprobando el guardado y estaba comprobando el aviso de error.
  "POST /api/parcelas/1/cultivos": {
    id: 1,
    parcela_id: 1,
    especie: "Cebada de dos carreras",
    sistema: "secano",
  },
  // La situación del almacén: lo comprado, lo echado y lo que queda. Así es como lo devuelve el
  // servidor, con el motivo cuando no se puede comparar.
  "/api/productos/cesta/situacion": {
    textos: {},
    campana_id: 1,
    campana_anio: 2026,
    cuantos: 1,
    sin_cantidad: 0,
    sin_poder_comparar: 0,
    resumen: "Tienes 1 producto apuntado.",
    productos: [
      {
        producto_id: 1,
        nombre_comercial: "Ejemplo 25 EC",
        numero_registro: "24.123",
        materia_activa: "Tebuconazol",
        fecha_compra: "2026-03-10",
        proveedor: "Cooperativa de Peñaranda",
        unidad_compra: "L",
        unidad_gastado: "L",
        comprado: 20,
        // De dónde sale el número de lo comprado: el servidor lo manda siempre («facturas», «ficha» o
        // vacío) y desde el 30/09/2026 se enseña en el panel de al lado de la tabla del almacén.
        comprado_de_donde: "ficha",
        gastado: 15,
        apuntes: 1,
        gastado_en_total: 15,
        queda: 5,
        se_puede_comparar: true,
        motivo: "",
      },
    ],
  },
  "/api/fertilizantes": [],
  "/api/aplicadores": [],
  "/api/equipos": [],
  "/api/instalaciones": [
    {
      id: 1,
      alias: "El almacén grande",
      tipo: "almacen",
      municipio: "Peñaranda",
      uso: "Guardar el grano",
      referencia_catastral: null,
      superficie_m2: null,
    },
  ],
  "/api/cuaderno/falta": { campana: 2026, esta_completo: true, pendientes: [], mensaje: null },
  // El cuaderno de la Junta: lo que contesta el servidor al leerlo y al traer sus tierras.
  "/api/cuaderno-cyl/leer": {
    anio: 2026,
    titular: "EXPLOTACIÓN DE EJEMPLO",
    nif: "12345678Z",
    registro_autonomico: "9999999999",
    localidad: "PUEBLO DE EJEMPLO",
    resumen: {
      anio: 2026,
      lineas: 8,
      lineas_leidas: 7,
      lineas_ilegibles: 1,
      tierras: 5,
      tierras_partidas: 1,
      hectareas_declaradas: 14.52,
      hectareas_sigpac: 24.7,
      municipios: ["OTRO PUEBLO DE EJEMPLO", "PUEBLO DE EJEMPLO"],
      cultivos: ["AVENA", "CEBADA", "TRIGO BLANDO"],
      en_zona_nitratos: 1,
      sin_secano_regadio: 1,
      avisos: ["Estas líneas del cuaderno no dicen el polígono, la parcela o el recinto: 8."],
      hojas: 25,
    },
    lineas: [
      {
        orden: 1,
        ref_sigpac: "99-99-0-0-1-1-1",
        municipio: "PUEBLO DE EJEMPLO",
        uso_sigpac: "TA",
        superficie_sigpac_ha: 1.09,
        superficie_cultivada_ha: 1.09,
        especie: "CEBADA",
        variedad: null,
        ecorregimen: "P3",
        sistema: "secano",
        zona_nitratos: true,
      },
    ],
  },
  "/api/cuaderno-cyl/importar": {
    anio: 2026,
    campana_id: 1,
    creadas: 7,
    con_cultivo: 0,
    ya_estaban: 0,
    sin_apuntar: 1,
    lineas_leidas: 8,
    tierras_en_el_cuaderno: 5,
    hectareas_declaradas: 14.52,
    titular_rellenado: ["nº de registro de la explotación", "dirección"],
    avisos: ["Estas líneas del cuaderno no dicen el polígono, la parcela o el recinto: 8."],
  },
  "/api/planes": [],
  "/api/analiticas": [],
  "/api/medidas": declaracionDeMedidas(),
  "/api/ventas": [],
  // Las facturas: la lista (vacía), si se pueden leer las fotos, y lo que contesta al leer una.
  // Lo que le falta al cuaderno de la Junta, para poder decirlo en «mi cuaderno».
  "/api/cuaderno-cyl/que-falta": {
    anio: 2026,
    hojas: 25,
    hojas_con_datos: 9,
    filas: 12,
    cuantas_faltan: 2,
    faltan: [
      { hoja: "1.3. INF. GRAL", que_falta: "las máquinas con las que echas el producto", donde_se_pone: "Mis cosas → máquinas de echar producto" },
      { hoja: "2.2. DATOS IDEN. MEDIAMB. P.", que_falta: "esta hoja todavía no se rellena sola desde el programa", donde_se_pone: "—" },
    ],
  },
  "/api/mi-finca": {
    // El identificador va aquí porque el servidor lo devuelve (`ExplotacionSalida`) y es lo que lleva la
    // dirección para decir **en qué finca** se está (T04): sin él, la dirección no podría distinguir una
    // finca de otra.
    id: 1,
    nombre: "David Pérez Velasco",
    nif: "70922320A",
    provincia: "Salamanca",
    municipio: "Calvarrasa de Arriba",
    registro_autonomico: "0837267320",
    direccion: "C/ Río Segre 6",
    localidad: "Salamanca",
    codigo_postal: "37006",
    telefono: "634597458",
    correo: "david@ejemplo.test",
  },
  "/api/facturas": [],
  "/api/facturas/estado": {
    textos: { titulo: "Mis facturas" },
    lector: {
      hay_lector: true,
      programa: "tesseract",
      idiomas: ["eng", "osd"],
      idioma: "eng",
      lee_el_espanol: false,
      nota: "El lector de fotos está funcionando, pero solo con el idioma inglés: los números los lee bien y las palabras con tilde o con eñe pueden salir cambiadas.",
    },
    tipos_de_fichero: ["jpeg", "jpg", "pdf", "png"],
    unidades: ["kg", "L", "ud"],
  },
  "/api/facturas/leer": {
    proveedor: "COOPERATIVA AGRICOLA DE PEÑARANDA S.C.L.",
    proveedor_nif: "F37012345",
    numero_factura: "2026/00123",
    fecha: "2026-03-15",
    base_imponible: 810.0,
    cuota_iva: 170.1,
    tipo_iva_pct: 21.0,
    total: 980.1,
    como_se_leyo: "foto",
    idioma_del_lector: "eng",
    texto_crudo: "COOPERATIVA ...",
    ya_estaba: null,
    avisos: ["Esto lo he leído de una imagen y el lector solo tiene el idioma inglés."],
    resumen: { lineas: 2, lineas_que_cuadran: 1, cuadra_el_total: true, suman_las_lineas: true },
    lineas: [
      {
        descripcion: "GLIFOSATO 36% SL 20 L",
        cantidad: 2,
        unidad: "ud",
        precio_unitario: 85.0,
        importe: 170.0,
        numero_registro: "24.123",
        cuadra: true,
        confianza: "alta",
        producto_sugerido_id: 1,
        producto_sugerido: "Glifosato 36 SL",
        como_se_sugiere: "por el nombre",
      },
      {
        descripcion: "NITRATO AMONICO 33,5%",
        cantidad: 1000,
        unidad: "kg",
        precio_unitario: 0.45,
        importe: 999.0,
        numero_registro: "",
        cuadra: false,
        confianza: "baja",
        producto_sugerido_id: null,
        producto_sugerido: "",
        como_se_sugiere: "",
      },
    ],
  },
  "POST /api/facturas": {
    id: 5,
    campana_id: 1,
    fecha: "2026-03-15",
    proveedor: "COOPERATIVA AGRICOLA DE PEÑARANDA S.C.L.",
    numero_factura: "2026/00123",
    total: 980.1,
    anulada: false,
    lineas: [{ id: 1, descripcion: "GLIFOSATO 36% SL 20 L", importe: 170.0 }],
  },
  // Las fincas de la cuenta y quién entra en la que se está usando (ronda 89). Dos fincas a propósito: es
  // el caso en el que la pantalla enseña el bloque de cambiar de finca, y sin dos no se podría comprobar
  // que el botón lleva **a la otra** y no a la que ya está puesta.
  "/api/fincas": [
    {
      id: 1,
      nombre: "La finca de David",
      municipio: "Calvarrasa de Arriba",
      papel: "titular",
      activa: true,
    },
    { id: 3, nombre: "Las del río", municipio: "Cabrerizos", papel: "ayudante", activa: false },
  ],
  "/api/fincas/quien-entra": {
    explotacion_id: 1,
    nombre: "La finca de David",
    soy_titular: true,
    personas: [
      {
        usuario_id: 1,
        nombre: "David Pérez Velasco",
        correo: "david@ejemplo.test",
        papel: "titular",
        eres_tu: true,
        se_puede_quitar: false,
      },
      {
        usuario_id: 4,
        nombre: "Ana Pérez",
        correo: "ana@ejemplo.test",
        papel: "ayudante",
        eres_tu: false,
        se_puede_quitar: true,
      },
    ],
  },
  // Al añadir una cuenta, el servidor contesta la lista entera ya con la nueva: lo que se enseña después
  // es la respuesta del servidor, no una lista que se monte el móvil por su cuenta.
  "POST /api/fincas/quien-entra": {
    explotacion_id: 1,
    nombre: "La finca de David",
    soy_titular: true,
    personas: [
      {
        usuario_id: 1,
        nombre: "David Pérez Velasco",
        correo: "david@ejemplo.test",
        papel: "titular",
        eres_tu: true,
        se_puede_quitar: false,
      },
      {
        usuario_id: 4,
        nombre: "Ana Pérez",
        correo: "ana@ejemplo.test",
        papel: "ayudante",
        eres_tu: false,
        se_puede_quitar: true,
      },
      {
        usuario_id: 5,
        nombre: "Juan Pérez",
        correo: "juan@ejemplo.test",
        papel: "ayudante",
        eres_tu: false,
        se_puede_quitar: true,
      },
    ],
  },
  // Cambiar de finca devuelve **un vale nuevo**: el vale dice en qué finca se está trabajando.
  "POST /api/fincas/cambiar": {
    token: "vale-de-la-otra-finca",
    usuario_id: 1,
    explotacion_id: 3,
    nombre: "David Pérez Velasco",
  },
  // Y quitar el acceso, la lista sin esa cuenta.
  "DELETE /api/fincas/quien-entra/4": {
    explotacion_id: 1,
    nombre: "La finca de David",
    soy_titular: true,
    personas: [
      {
        usuario_id: 1,
        nombre: "David Pérez Velasco",
        correo: "david@ejemplo.test",
        papel: "titular",
        eres_tu: true,
        se_puede_quitar: false,
      },
    ],
  },
  "/api/asesores": [],  "/api/cuenta/certificado/estado": {
    configurado: false,
    hay_certificado: false,
    certificado: null,
    si_no_se_puede: "En esta instalación todavía no se puede entrar con certificado.",
    explicacion: "Si vinculas tu certificado, entras sin escribir nada.",
  },
  "/api/firmas/estado": {
    estado: "sin_firmar",
    huella: "0".repeat(64),
    puede_firmar: true,
    nombre_del_fichero: "cuaderno_2026.txt",
    firma: null,
    mensaje: "Todavía no has firmado el cuaderno de este año.",
    explicacion: "Firmar es lo que hace que el cuaderno valga delante de la administración.",
  },
};

function montarServidor(cambios = {}) {
  const llamadas = [];
  // Y las mismas llamadas con su método delante («POST /api/facturas»). Hace falta porque hay rutas
  // que se piden y se mandan: `/api/facturas` es la lista cuando se pide y el alta cuando se manda,
  // y sin el método no se puede comprobar que **no** se ha guardado nada.
  const llamadasConMetodo = [];
  // Y lo que se ha mandado en cada una. Hace falta para las pantallas de formulario: comprobar que
  // la pantalla **se le pide a React** no dice nada de si lo escrito llega bien al servidor, y el
  // fallo que se quiere cazar es justo ese (un campo que se queda sin su `id` se guarda vacío sin
  // que salte ningún error).
  const enviados = [];
  const respuestas = { ...RESPUESTAS, ...cambios };
  const fetchFalso = async (ruta, opciones = {}) => {
    llamadas.push(ruta);
    const metodo = (opciones.method || "GET").toUpperCase();
    llamadasConMetodo.push(`${metodo} ${ruta}`);
    let enviado = null;
    if (typeof opciones.body === "string" && opciones.body) {
      try {
        enviado = JSON.parse(opciones.body);
      } catch (error) {
        enviado = opciones.body;
      }
    } else if (opciones.body && typeof opciones.body.get === "function") {
      // **Un cuerpo de formulario, que también se mira** (CRM-00, 11/10/2026). El alta de una factura de
      // compra manda un `FormData` (los datos **y** el fichero del justificante), y hasta hoy el arnés lo
      // registraba como `null`: ninguna prueba veía lo que salía por ahí —ni la clave de reenvío, que es lo
      // que impide que un reintento apunte la factura dos veces—. Se lee el campo `datos`, que es el JSON
      // que la pantalla construye.
      const datos = opciones.body.get("datos");
      if (datos) {
        try {
          enviado = JSON.parse(datos);
        } catch (error) {
          enviado = datos;
        }
      }
      const fichero = opciones.body.get("fichero");
      if (fichero) enviado = { ...(enviado || {}), __fichero: true };
    }
    enviados.push({ metodo, ruta, cuerpo: enviado });
    const crudo =
      respuestas[`${metodo} ${ruta}`] !== undefined
        ? respuestas[`${metodo} ${ruta}`]
        : respuestas[ruta];
    // **Una respuesta puede pedir que falle** (ver el ayudante `falla()`, aquí debajo): eso no es un
    // dato, es un servidor que dice que no, y hace falta para probar los avisos de error de verdad.
    if (crudo && typeof crudo === "object" && "FALLA" in crudo) {
      return {
        ok: false,
        // 422 y no 500 a propósito: un 5xx se guarda en la cola del móvil para reintentarlo (ver
        // `enviarOApuntar`), y lo que se prueba aquí es el aviso al agricultor, no la cola.
        //
        // **Y se puede pedir otro estado** (`ESTADO`, con el ayudante `falla`): el almacén (T09) contesta
        // **409** en dos casos que se resuelven distinto —que el apunte no diga el total, o que lo que sale
        // deje el envase en negativo— y esa diferencia es lo que la pantalla tiene que saber leer.
        status: crudo.ESTADO || 422,
        headers: { get: () => "application/json" },
        json: async () => crudo.FALLA,
        text: async () => JSON.stringify(crudo.FALLA),
        blob: async () => ({ size: 0 }),
      };
    }
    const cuerpo = crudo;
    return {
      ok: cuerpo !== undefined,
      status: cuerpo !== undefined ? 200 : 404,
      headers: { get: () => "application/json" },
      json: async () => cuerpo,
      text: async () => JSON.stringify(cuerpo),
      blob: async () => ({ size: 0 }),
    };
  };
  return { fetchFalso, llamadas, llamadasConMetodo, enviados };
}

/**
 * Una respuesta que **falla**, con lo que contesta el servidor.
 *
 * Hasta la ronda 71 los avisos de error no tenían ni una prueba, y el motivo era este: el servidor de
 * mentira da por bueno todo lo que esté en su lista, así que no había forma de que una petición fallara.
 * Poniendo `undefined` en una ruta se consigue un 404, pero solo vale para las rutas que **no** existen
 * de verdad (una ruta que se pide con GET y se manda con POST —`/api/medidas`— seguiría dándose por
 * buena al mandarla, porque la lista tiene su GET).
 *
 * Se marca con `FALLA` y no con un guion bajo ni con un `null`, para que al leer la prueba se vea de un
 * vistazo que esa respuesta **no es un dato**: es un fallo.
 */
function falla(cuerpo = { detail: "El servidor no lo ha aceptado." }, estado = 422) {
  return { FALLA: cuerpo, ESTADO: estado };
}

/** Carga app.js con el entorno montado y espera a que termine de arrancar. */
async function cargarAplicacion(cambios = {}, extra = {}) {
  const entorno = montarEntorno();
  // El nombre del titular, tal y como lo deja la aplicación guardado al entrar. Lo lee la
  // pantalla de inicio para el saludo, así que hace falta para poder comprobar que llega.
  if (extra.nombre) {
    entorno.window.localStorage.setItem("cuedigital.nombre", JSON.stringify(extra.nombre));
  }
  // Lo que ya tenga guardado el móvil (la cola de apuntes sin mandar, el último apunte…). Se siembra antes
  // de arrancar la aplicación, que es la única forma de probar los avisos que dependen de eso: sin cola, el
  // aviso de la cabecera no se dibuja y su texto no se puede comprobar.
  for (const [clave, valor] of Object.entries(extra.almacen || {})) {
    entorno.window.localStorage.setItem(clave, JSON.stringify(valor));
  }
  // ***Y lo que va CRUDO*** (21/10/2026): *el vale se guarda **tal cual** -la aplicacion hace
  // `setItem(CLAVE_TOKEN, token)`-, asi que sembrarlo serializado le pone comillas delante y **el lector del
  // vale no lo puede decodificar**: `atob` revienta con la comilla y la sesion sale `null`.*
  for (const [clave, valor] of Object.entries(extra.almacenCrudo || {})) {
    entorno.window.localStorage.setItem(clave, String(valor));
  }
  // La ubicación del móvil, cuando la prueba la necesita. Sin esto, `navigator.geolocation` no
  // existe, que es el caso de un navegador al que no se le ha dado permiso.
  if (extra.ubicacion) {
    entorno.navigator.geolocation = {
      getCurrentPosition: (bien) =>
        bien({ coords: { longitude: extra.ubicacion[0], latitude: extra.ubicacion[1] } }),
    };
  } else if (extra.sinUbicacion) {
    entorno.navigator.geolocation = {
      getCurrentPosition: (_bien, mal) => mal(new Error("sin permiso")),
    };
  }
  const servidor = montarServidor(cambios);
  // **La dirección con la que se abre la aplicación** (T04, 02/10/2026): es lo que permite probar de
  // verdad «abrir una tierra por su enlace» y «recargar y seguir donde estaba», que es abrir la
  // aplicación otra vez con la misma dirección puesta.
  if (extra.direccion) {
    entorno.window.location.hash = extra.direccion;
  }
  // Con `defineProperty` y no con `globalThis.x = ...`: en Node 22 y siguientes
  // algunos de estos globales (navigator, localStorage) son de solo lectura, y
  // asignarlos directamente revienta.
  const definir = (nombre, valor) =>
    Object.defineProperty(globalThis, nombre, {
      value: valor,
      configurable: true,
      writable: true,
    });

  definir("document", entorno.document);
  definir("window", entorno.window);
  definir("navigator", entorno.navigator);
  definir("URL", entorno.URL);
  definir("fetch", servidor.fetchFalso);
  definir("localStorage", entorno.window.localStorage);

  // Se importa con marca en la URL para que Node no reutilice el módulo entre tests:
  // cada test tiene que arrancar de cero.
  const app = await import(`../web/app.js?prueba=${Math.random()}`);
  await new Promise((resolver) => setTimeout(resolver, 60));

  return { app, entorno, servidor };
}

// ---------------------------------------------------------------------------

test("app.js se carga y arranca sin reventar", async () => {
  await cargarAplicacion();
  assert.ok(true);
});

test("pide el vocabulario de la interfaz al servidor", async () => {
  const { servidor } = await cargarAplicacion();
  assert.ok(
    servidor.llamadas.includes("/api/interfaz"),
    `no ha pedido la interfaz; ha pedido: ${servidor.llamadas.join(", ")}`,
  );
});

test("carga los datos que necesita para funcionar", async () => {
  const { servidor } = await cargarAplicacion();
  for (const ruta of [
    "/api/campanas/actual",
    "/api/parcelas",
    "/api/cuaderno/falta",
    // Los dos últimos se añadieron cuando se descubrió que `estado.tratamientos` no lo rellenaba
    // nadie (la pantalla «mi cuaderno» decía «0 apuntes de producto» con el año lleno) y que la
    // pantalla de inicio decidía si había apuntes mirando solo lo que recordaba el móvil.
    "/api/tratamientos",
    "/api/cuaderno/resumen",
  ]) {
    assert.ok(servidor.llamadas.includes(ruta), `no ha pedido ${ruta}`);
  }
});

// ---------------------------------------------------------------------------
// La pantalla de inicio, que ya está en React
//
// Aquí había ocho pruebas que miraban el HTML de la pantalla de inicio en el contenedor de
// mentira: los seis botones con su texto y su icono, el botón grande, los destinos
// (`data-ir`), el botón de repetir, los de dictado y «mis cosas» y el aviso de que falta la
// primera parcela. **Se han movido a `tests_js/react.test.js`**, reescritas contra el
// componente, porque en el DOM de mentira de este fichero React no se puede montar: no tiene
// `ownerNode`, ni un `appendChild` de verdad, ni un `innerHTML` que se pueda leer. Allí se
// comprueba lo mismo, botón por botón y frase por frase, y además que ninguna frase está
// escrita a mano dentro del componente. No se ha perdido ninguna comprobación.
//
// Lo que se comprueba aquí es lo que solo se puede ver desde `app.js`: que la pantalla de
// inicio **se le pide a React** con los datos que tiene la aplicación, y que el resto de la
// interfaz sigue arrancando sin reventar por el camino.
// ---------------------------------------------------------------------------

test("la pantalla de inicio se le pide a React, con los datos de la aplicación", async () => {
  const antes = montajes.length;
  const { entorno } = await cargarAplicacion({}, { nombre: "Juan" });
  const pedidos = montajes.slice(antes);

  assert.equal(pedidos.length, 1, `se han pedido ${pedidos.length} montajes: solo la pantalla de inicio`);
  assert.equal(pedidos[0].contenedor, entorno.nodos.get("pantalla"), "no se monta en la pantalla");

  const elemento = pedidos[0].elemento;
  assert.ok(elemento, "no se le ha pedido nada a React: la pantalla se está pintando a mano otra vez");
  assert.ok(elemento.props, "lo que se le pasa a React no es un elemento de React");
  assert.equal(elemento.type.name, "PantallaInicio", "lo que se le pide a React no es la pantalla de inicio");

  // Los textos que recibe son los del servidor, los mismos que sirve `/api/interfaz`. `panel_de_mando` entra
  // con la fase 4 (30/09/2026): es **la misma pantalla** mirada de otra forma, así que sus textos van con
  // los suyos y no en un módulo aparte.
  assert.deepEqual(Object.keys(elemento.props.textos).sort(), [
    "dictado",
    "inicio",
    "maestros",
    "panel_de_mando",
  ]);
  assert.equal(elemento.props.textos.inicio.saludo, "Hola");
  assert.equal(elemento.props.textos.inicio.botones.length, 6);
  assert.equal(elemento.props.textos.maestros.mis_cosas, "MIS PARCELAS, PRODUCTOS Y MÁQUINAS");
  assert.equal(elemento.props.textos.dictado.titulo, "Dímelo con la voz");

  // Y el estado de la aplicación va con ellos: el titular, la campaña, si hay parcelas y si
  // hay algo que repetir. Con estos cuatro datos se decide TODO lo que sale en la pantalla.
  assert.equal(elemento.props.nombre, "Juan");
  assert.equal(elemento.props.campana.anio, 2026);
  assert.equal(elemento.props.hayParcelas, true, "hay parcelas cargadas y no se le ha dicho");
  assert.equal(elemento.props.hayUltimo, false);

  // La interfaz vieja sigue arrancando: nada ha pintado el HTML de la pantalla de inicio a
  // mano, que es lo que se hacía antes de esto.
  assert.equal(
    entorno.nodos.get("pantalla").innerHTML,
    "",
    "la pantalla de inicio se ha pintado además con `pintar()`",
  );

  // Sin ninguna parcela, se le pide el aviso que desbloquea al agricultor nuevo: es lo que
  // dibuja `BloqueAntesDeEmpezar` (ver `react.test.js`).
  const antesDelSegundo = montajes.length;
  await cargarAplicacion({ "/api/parcelas": [] });
  const nuevos = montajes.slice(antesDelSegundo);
  assert.equal(nuevos.length, 1, "el arranque sin parcelas no ha pedido su pantalla de inicio");
  assert.equal(
    nuevos[0].elemento.props.hayParcelas,
    false,
    "con cero parcelas no se avisa al agricultor nuevo de que le falta la primera",
  );
});

// ---------------------------------------------------------------------------
// «Lo mismo que la última vez», y la verdad sobre si hay algo apuntado
//
// El atajo se decidía con `localStorage`: en un móvil nuevo, en el ordenador de casa o después
// de que el navegador borrase sus datos, el agricultor leía «todavía no has apuntado nada» **con
// el cuaderno lleno** y se quedaba sin el atajo. Los apuntes no viven en el móvil, viven en el
// servidor, y es de ahí de donde se sacan ahora. Y el mismo error estaba en «mi cuaderno»: la
// lista de tratamientos de la pantalla no la rellenaba nadie, así que decía «0 apuntes de
// producto» con el año lleno. Las dos cosas se comprueban aquí, contra `app.js`.
// ---------------------------------------------------------------------------

/** Un tratamiento del año, tal y como lo devuelve `/api/tratamientos`. */
function unTratamiento(extra = {}) {
  return {
    id: 7,
    campana_id: 1,
    fecha: "2026-04-10",
    tipo: "parcela",
    parcela_id: 1,
    grupo_id: null,
    instalacion_id: null,
    producto_cosechado: null,
    lote_cosecha: null,
    superficie_tratada_ha: 4.9,
    justificacion: "Vi la hierba en el campo",
    plaga: "Hierbas adventicias",
    producto_id: 5,
    producto_nombre: "Glifosato 36 SL",
    numero_registro: "ES-00849",
    dosis: 3,
    unidad_dosis: "L/ha",
    aplicador_id: null,
    equipo_id: null,
    medidas: [],
    anulado: false,
    ...extra,
  };
}

test("con un tratamiento en la finca se ofrece repetirlo, aunque este móvil no lo recuerde", async () => {
  const antes = montajes.length;
  await cargarAplicacion({
    "/api/tratamientos": [unTratamiento(DENTRO_DE_LA_TIERRA)],
    "/api/cuaderno/resumen": { apuntes_de_producto: 1, apuntes_de_abono: 0, apuntes_de_trabajo: 0 },
  });
  const elemento = montajes[montajes.length - 1].elemento;
  assert.equal(
    elemento.props.hayUltimo,
    true,
    "hay un tratamiento apuntado en la finca y no se ofrece repetirlo: el atajo sigue mirando solo el móvil",
  );
});

test("un tratamiento anulado o de otro año no es «la última vez»", async () => {
  const antes = montajes.length;
  await cargarAplicacion({
    "/api/tratamientos": [unTratamiento({ anulado: true }), unTratamiento({ id: 8, campana_id: 2025 })],
    "/api/cuaderno/resumen": { apuntes_de_producto: 0, apuntes_de_abono: 0, apuntes_de_trabajo: 0 },
  });
  const elemento = montajes[montajes.length - 1].elemento;
  assert.equal(
    elemento.props.hayUltimo,
    false,
    "se ofrece repetir un tratamiento anulado o de una campaña que no es la que se está llevando",
  );
});

test("el atajo abre el asistente con el producto y la dosis de la última vez", async () => {
  const { entorno } = await cargarAplicacion({
    "/api/tratamientos": [unTratamiento(DENTRO_DE_LA_TIERRA)],
    "/api/cuaderno/resumen": { apuntes_de_producto: 1, apuntes_de_abono: 0, apuntes_de_trabajo: 0 },
    // El producto tiene que estar en los maestros: el asistente enseña su nombre y su unidad de
    // dosis, y sin él la pantalla sale a medias (que es lo que pasó al escribir esta prueba).
    "/api/productos": [
      { id: 5, nombre_comercial: "Glifosato 36 SL", unidad_dosis: "L/ha", numero_registro: "ES-00849" },
    ],
  });
  await pulsar(entorno, "repetir");
  const html = pantallaPedida(entorno);
  // Se abre en la pantalla de repetición («¿Lo apuntamos otra vez?»), no en el alta de cero.
  assert.ok(
    html.includes("¿Lo apuntamos otra vez?"),
    `el atajo no ha abierto el asistente de repetir: ${html.slice(0, 200)}`,
  );
  // Va directo al resumen, con lo del último día puesto: el agricultor solo cambia el día.
  const resumen = resumenPedido();
  assert.ok(
    resumen.includes("Glifosato 36 SL"),
    `el asistente se ha abierto sin el producto de la última vez: ${resumen}`,
  );
  assert.ok(resumen.includes("3"), `el resumen no dice la dosis: ${resumen}`);
});

test("sin nada apuntado se dice, y con apuntes no se dice que no haya nada", async () => {
  // Una finca recién hecha: ni un apunte. Aquí «todavía no has apuntado nada» es verdad.
  const antes = montajes.length;
  await cargarAplicacion({
    "/api/tratamientos": [],
    "/api/cuaderno/resumen": { apuntes_de_producto: 0, apuntes_de_abono: 0, apuntes_de_trabajo: 0 },
  });
  const vacia = montajes[montajes.length - 1].elemento;
  assert.equal(vacia.props.hayUltimo, false);
  assert.equal(vacia.props.sinUltimo, "Nada apuntado todavía.");

  // Y una finca con un abono apuntado: hay apuntes, pero ninguno se puede repetir con dos toques
  // (el atajo es de tratamientos). Decirle que no ha apuntado nada sería mentirle.
  const antesConAbono = montajes.length;
  await cargarAplicacion({
    "/api/tratamientos": [],
    "/api/cuaderno/resumen": { apuntes_de_producto: 0, apuntes_de_abono: 3, apuntes_de_trabajo: 0 },
  });
  const conAbono = montajes[montajes.length - 1].elemento;
  assert.equal(conAbono.props.hayUltimo, false);
  assert.equal(
    conAbono.props.sinUltimo,
    "Ya has apuntado cosas, pero ningún tratamiento.",
    "con apuntes en el cuaderno se sigue diciendo que no hay nada apuntado",
  );
  assert.ok(antesConAbono > antes);
});

/**
 * Lo último que se le ha pedido a React como «mi cuaderno», con sus datos ya preparados.
 *
 * Desde la ronda 70 esta pantalla está **entera en React** (sus nueve bloques), así que su HTML ya no
 * se puede leer del contenedor de mentira de este fichero: aquí se comprueba **lo que `app.js` le
 * pasa al componente** —los apuntes contados, lo que falta, las ventas, las medidas, los análisis, el
 * plan, la firma, el cuaderno de la Junta y el registro electrónico—, y el dibujo de cada bloque está
 * en `tests_js/react.test.js`, contra el componente.
 */
function ultimoCuadernoPedido() {
  const pedidos = montajes.filter((montaje) => montaje.elemento?.type?.name === "PantallaMiCuaderno");
  assert.ok(pedidos.length, "no se le ha pedido la pantalla de «mi cuaderno» a React");
  return pedidos[pedidos.length - 1].elemento.props;
}

test("«mi cuaderno» enseña los tratamientos del año, y no cero", async () => {
  // Este era el fallo de verdad: `estado.tratamientos` no lo rellenaba nadie, así que la pantalla
  // decía «0 apuntes de producto» y una lista vacía aunque el agricultor tuviera el año lleno.
  //
  // **Y desde la ronda 91 el título cuenta los cuatro tipos de apunte** —producto, abono, trabajo y
  // cosecha— porque la lista enseña los cuatro y cada uno se puede corregir y borrar: se cambió «1
  // apunte de producto» por «1 apunte en el cuaderno». El resto de la prueba es la misma.
  const { entorno } = await cargarAplicacion({
    "/api/tratamientos": [unTratamiento()],
    "/api/cuaderno/resumen": { apuntes_de_producto: 1, apuntes_de_abono: 0, apuntes_de_trabajo: 0 },
  });
  await pulsar(entorno, "inicio", { ir: "mi_cuaderno" });
  const apuntes = ultimoCuadernoPedido().apuntes;
  assert.equal(apuntes.titulo, "1 apunte en el cuaderno", "no cuenta el tratamiento apuntado, ni lo dice en singular");
  assert.ok(apuntes.hay, "con un tratamiento apuntado dice que no hay nada");
  assert.equal(apuntes.filas.length, 1, "no le llega el tratamiento apuntado");
  // Desde el rediseño (ronda 79) cada apunte es una **tarjeta**: su número, su fecha y **cada dato con su
  // nombre delante**. El producto es el nombre de la tarjeta y el resto son sus filas.
  const apunte = apuntes.filas[0];
  assert.equal(apunte.etiqueta, "Glifosato 36 SL", "no le llega el producto del tratamiento");
  assert.equal(apunte.rotulo, "Apunte 1", "la tarjeta del apunte no lleva su número");
  // La fecha y **de qué clase es el apunte** (ronda 91): en la misma lista hay productos, abonos,
  // trabajos y cosechas, y sin decirlo un abono y una labor se leen igual.
  assert.deepEqual(apunte.lineas, ["10/04/2026", "Producto"], "no le llega la fecha del tratamiento");
  const filas = Object.fromEntries(apunte.filas.map((fila) => [fila.etiqueta, fila.valor]));
  // **La tierra, que no salía en ninguna parte**: el apunte guardaba a qué tierra se echó desde el primer
  // día y la pantalla no lo decía. Es lo primero que se pregunta en una inspección.
  assert.equal(filas["Tierra y parcela"], "El Prado", "el apunte no dice en qué tierra se hizo");
  assert.equal(filas["Hectáreas tratadas"], "4,90 ha", "no le llegan las hectáreas tratadas");
  assert.equal(filas["Cuánto por hectárea"], "3,00 L/ha", "no le llega cuánto se echó por hectárea");
  // Y el botón de apuntar otro tratamiento, dentro del bloque: sin volver al inicio a buscarlo.
  assert.equal(apuntes.acciones[0].accion, "inicio", "no se puede apuntar otro desde aquí");
  assert.equal(apuntes.acciones[0].datos.ir, "echar_producto", "el botón no lleva al asistente");
});

test("la frase de un vistazo cuenta lo que falta, en singular y en plural", async () => {
  // **Esto se añadió en la ronda 80.** Es lo primero que se lee al abrir «mi cuaderno» —la pantalla que
  // más se mira— y contesta a la única pregunta que se hace el agricultor antes de mirar nada: «¿tengo el
  // cuaderno al día?». Se comprueba aquí porque quien la escribe es `app.js`: el componente solo la pinta.
  const { entorno } = await cargarAplicacion({
    "/api/cuaderno/falta": {
      pendientes: [
        { tipo: "parcela_sin_cultivo", parcela_id: 1, mensaje: "A El Prado le falta decir qué cultivo tiene este año." },
      ],
      cuantos: 1,
    },
  });
  await pulsar(entorno, "inicio", { ir: "mi_cuaderno" });
  assert.equal(
    ultimoCuadernoPedido().faltantes.resumen,
    "Te falta 1 cosa por apuntar",
    "con una cosa pendiente no lo dice en singular",
  );

  const tres = await cargarAplicacion({
    "/api/cuaderno/falta": {
      pendientes: [
        { tipo: "a", mensaje: "Una cosa." },
        { tipo: "b", mensaje: "Otra cosa." },
        { tipo: "c", mensaje: "Y otra." },
      ],
      cuantos: 3,
    },
  });
  await pulsar(tres.entorno, "inicio", { ir: "mi_cuaderno" });
  assert.equal(ultimoCuadernoPedido().faltantes.resumen, "Te faltan 3 cosas por apuntar");

  // Sin nada pendiente se dice, que es lo que tranquiliza.
  const nada = await cargarAplicacion(); // el de por defecto: no falta nada
  await pulsar(nada.entorno, "inicio", { ir: "mi_cuaderno" });
  assert.equal(ultimoCuadernoPedido().faltantes.resumen, "No te falta nada por apuntar");
});

test("si el servidor no contesta lo que falta, no se afirma que no falte nada", async () => {
  // **Es el caso que importa.** «No te falta nada por apuntar» con la lista sin llegar sería afirmar lo
  // que no se sabe, y eso es justo lo que este programa no hace: si no hay dato, no hay frase.
  const { entorno } = await cargarAplicacion({
    "/api/cuaderno/falta": falla({ detail: "El servidor no ha podido mirarlo." }),
  });
  await pulsar(entorno, "inicio", { ir: "mi_cuaderno" });
  assert.equal(
    ultimoCuadernoPedido().faltantes.resumen,
    "",
    "dice que no falta nada cuando en realidad no lo sabe",
  );
});

test("con el año sin empezar, el cuaderno dice que no hay nada que revisar (y no que esté al día)", async () => {
  // **01/10/2026, hallazgo de la auditoría de valores por defecto (T02).** Con cero tierras y cero apuntes,
  // las comprobaciones del servidor no tienen nada que mirar, la lista de pendientes sale vacía y la pantalla
  // decía «No te falta nada por apuntar»: **el silencio se leía como un visto bueno**, y delante de una
  // inspección eso es lo peor que puede decir este programa. Un cuaderno sin empezar no está al día. Ahora el
  // servidor contesta `esta_completo: null` con un mensaje suyo, y las dos pantallas lo enseñan tal cual.
  const mensaje = "Todavía no hay nada apuntado este año, así que no hay nada que revisar.";
  const { entorno } = await cargarAplicacion({
    "/api/cuaderno/falta": {
      campana: 2026,
      esta_completo: null,
      pendientes: [],
      mensaje,
    },
  });
  await pulsar(entorno, "inicio", { ir: "mi_cuaderno" });
  assert.equal(ultimoCuadernoPedido().faltantes.resumen, mensaje);

  // **Y la sección de abajo tampoco puede decir que está todo** (07/10/2026). Se corrigió la frase de
  // arriba el 01/10 y **el texto de la sección se quedó fijo**: la pantalla decía «Todavía no has apuntado
  // nada este año» y, justo debajo, «Lo tienes todo apuntado». Lo encontró David mirando la pantalla, no
  // una suite, y esta comprobación es para que no vuelva: con el año sin empezar, la sección vacía **no**
  // puede ser la de «lo tienes todo».
  const cuaderno = ultimoCuadernoPedido();
  assert.equal(
    cuaderno.faltantes.vacio,
    "Aqui saldra lo que te falte cuando apuntes algo.",
    "la sección vacía no dice que el cuaderno no ha empezado",
  );
  assert.notEqual(
    cuaderno.faltantes.vacio,
    "Todo apuntado.",
    "la sección vacía afirma que está todo mientras el servidor no ha mirado nada",
  );

  // Y el panel de mando del ordenador, con el mismo caso: su frase de «no falta nada» es la del servidor.
  await pulsar(entorno, "ir-inicio");
  const mando = montajes[montajes.length - 1].elemento.props.mando;
  assert.equal(mando.faltantes.vacio, mensaje);
});

test("los números de cada bloque se dicen con su palabra, y en singular cuando son uno", async () => {
  // **Esto se añadió en la ronda 81.** Los resúmenes eran «2 · 44.000 Kilos» (que ni dice qué se cuenta
  // —entregas, ventas— ni se lee bien: la unidad larga es un rótulo de campo y va en mayúscula) y
  // «1 · Dónde se aprovecha esto:» (la explicación de para qué sirve un análisis puesta donde va el
  // número: no decía cuántos había). Ahora cada uno dice qué cuenta y cuánto, y en singular si es uno.
  const dos = await cargarAplicacion({
    "/api/ventas": [unaVenta(), unaVenta({ id: 2, kilos: 2000.0, cantidad: 2000.0, producto: "Cebada" })],
    "/api/analiticas": [unAnalisis()],
  });
  await pulsar(dos.entorno, "inicio", { ir: "mi_cuaderno" });
  const props = ultimoCuadernoPedido();
  assert.equal(
    props.ventas.resumen,
    "2 ventas apuntadas · 44.000 kg",
    `el resumen de las ventas no dice qué cuenta: «${props.ventas.resumen}»`,
  );
  assert.equal(
    props.analiticas.resumen,
    "1 análisis guardado",
    `el resumen de los análisis no dice cuántos hay: «${props.analiticas.resumen}»`,
  );

  // Con una sola venta, en singular: «1 ventas apuntadas» es lo primero que hace desconfiar.
  const una = await cargarAplicacion({ "/api/ventas": [unaVenta()] });
  await pulsar(una.entorno, "inicio", { ir: "mi_cuaderno" });
  assert.equal(ultimoCuadernoPedido().ventas.resumen, "1 venta apuntada · 42.000 kg");

  // Y sin nada, no hay línea de resumen: la lista vacía ya lo dice con su frase.
  const ninguna = await cargarAplicacion();
  await pulsar(ninguna.entorno, "inicio", { ir: "mi_cuaderno" });
  const sinNada = ultimoCuadernoPedido();
  assert.equal(sinNada.ventas.resumen, "", "con la lista vacía sigue diciendo un número");
  assert.equal(sinNada.analiticas.resumen, "", "sin análisis sigue diciendo un número");
});

test("el aviso de apuntes sin mandar se dice en singular cuando solo hay uno", async () => {
  // **Esto se añadió en la ronda 84.** El aviso decía «{cuantos} cosas apuntadas esperando a que haya
  // cobertura» y con un apunte se leía «1 cosas apuntadas». Y este aviso sale en la cabecera justo cuando
  // el agricultor está en el campo sin cobertura, que es cuando más lo mira.
  const unApunte = [
    {
      id_local: "p1",
      ruta: "/api/tratamientos",
      metodo: "POST",
      cuerpo: { fecha: "2026-04-10" },
      apuntado_en: "2026-04-10T09:00:00.000Z",
    },
  ];
  const uno = await cargarAplicacion({}, { almacen: { "cuedigital.pendientes": unApunte } });
  assert.equal(
    uno.entorno.nodos.get("aviso-pendientes").textContent,
    "1 pendiente",
    "con un solo apunte sin mandar, el aviso no se dice en singular",
  );

  const tres = await cargarAplicacion(
    {},
    {
      almacen: {
        "cuedigital.pendientes": [
          ...unApunte,
          { ...unApunte, id_local: "p2" },
          { ...unApunte, id_local: "p3" },
        ],
      },
    },
  );
  assert.equal(tres.entorno.nodos.get("aviso-pendientes").textContent, "3 pendientes");
});

test("el título de la cabecera se rellena en castellano", async () => {
  const { entorno } = await cargarAplicacion();
  assert.equal(entorno.nodos.get("cabecera-texto").textContent, "Mi cuaderno");
});

test("el pie de la página viene del servidor, y además dice la versión", async () => {
  // **La versión se añadió el 30/09/2026, a petición de David**: con la aplicación en el móvil y en el
  // ordenador y con la caché por medio, no había forma de saber si lo que se veía era lo nuevo o lo viejo.
  // El texto sigue viniendo del servidor (nada escrito a mano); lo único que se añade aquí es el número,
  // que es el mismo que el de la caché (lo comprueba `tests/test_la_version_visible.py`).
  const { entorno } = await cargarAplicacion();
  const pie = entorno.nodos.get("pie").textContent;
  assert.match(pie, /^Pie · versión \d{4}-\d{2}-\d{2}-\d+$/, `el pie dice: «${pie}»`);
});

// ---------------------------------------------------------------------------
// EL ARMAZÓN DEL ORDENADOR: el menú lateral y la barra de arriba (30/09/2026)
//
// Es lo que pidió David: *«debe ser responsive para usarse en pc y móvil, no solo móvil… no es una app
// usable de gestión»*. Hasta hoy, para llegar a sus 64 tierras había que saber que estaban detrás de un
// botón de la pantalla de inicio: **no había menú**.
//
// Lo que se comprueba aquí es el cableado, que es lo que solo se ve desde `app.js`: que el armazón se monte
// con la finca, el año y la cuenta, que lleve **todos** los módulos con su acción, y que **el módulo en el
// que se está vaya marcado**. Lo que se ve dentro del armazón está en `tests_js/react.test.js`, contra el
// componente; y que en el ordenador se vea de verdad, en la comprobación de navegador.
// ---------------------------------------------------------------------------

test("el armazón se monta con la finca, el año, la cuenta y todos los módulos", async () => {
  // La lista de lo que se ha pedido montar es del módulo y **se acumula entre pruebas**: se cuenta desde
  // donde estaba, como se hace con `montajes`.
  const antesDeCargar = montajesDelMarco.length;
  const { entorno } = await cargarAplicacion();
  assert.equal(
    montajesDelMarco.length,
    antesDeCargar + 1,
    `se ha pedido el armazón ${montajesDelMarco.length - antesDeCargar} veces al arrancar`,
  );
  const armazon = montajesDelMarco[montajesDelMarco.length - 1];
  assert.equal(armazon.contenedor, entorno.nodos.get("marco"), "el armazón no se monta en su contenedor");
  const props = armazon.elemento.props;
  // El nombre del titular sirve de cuenta: en este programa la finca no tiene nombre propio (ver
  // `textos.MENU`), así que la barra dice la cuenta y el año, que son los dos datos que sí existen.
  assert.equal(props.cuenta, "David Pérez Velasco", "el armazón no dice quién está apuntando");
  assert.equal(props.campana, "2026", "el armazón no dice en qué año se está apuntando");
  // Todos los módulos, cada uno con su acción: si uno se quedara sin acción, su renglón no haría nada.
  const claves = props.modulos.map((uno) => uno.clave);
  // **El orden cambió el 07/10/2026, y es el encargo del rediseño**: los mismos 21 renglones, agrupados por
  // donde el agricultor los busca (Inicio · El campo · La gestión · El cuaderno · Ajustes). La agrupación es
  // **visual**: no hay pantallas nuevas ni pasos de más. Esta lista es la que vigila que el menú lleve
  // **todos** los módulos: el que falte no lo ve el agricultor.
  assert.deepEqual(claves, [
    "panel",
    // **La búsqueda global** (07/10/2026, del encargo del rediseño): va la segunda, en el grupo de
    // Inicio, porque sirve para todo. Se apunta aquí por el mismo motivo que los demás: esta lista
    // es la que vigila que el menú lleve **todos** los módulos.
    "buscar",
    // **La normativa** (07/10/2026): con su pantalla, su ruta y su puerta ya hechas. Se apunta aquí
    // por el mismo motivo que la búsqueda: esta lista vigila que el menú lleve **todos** los módulos.
    "normativa",
    "tierras",
    "trabajos",
    "cultivos",
    "grupos",
    "almacen",
    "semillas",
    "analisis",
    "plan",
    "medidas",
    "contactos",
    "maquinaria",
    "cuentas",
    "ventas",
    "facturas",
    "papeles",
    "cuaderno",
    "anos",
    "junta",
    "datos",
    "ayuda",
  ]);
  // **Y cada grupo con sus renglones**, del mismo sitio del que salen los de arriba: si un grupo se queda
  // vacío o un renglón se queda sin grupo, aquí se ve. (El grupo «Normativa» del encargo **no está**, y es
  // a propósito: **la normativa es un renglón del grupo de Inicio, no un grupo**, y su pantalla existe
  // desde el 07/10/2026 -con su ruta, su puerta y sus pruebas-, así que ya no es un renglón sin sitio.)
  assert.deepEqual(
    props.grupos.map((grupo) => [grupo.clave, grupo.modulos.length]),
    [
      ["inicio", 3],
      ["campo", 9],
      ["gestion", 6],
      ["cuaderno", 3],
      ["ajustes", 2],
    ],
  );
  for (const modulo of props.modulos) {
    assert.ok(modulo.accion, `el módulo ${modulo.clave} no lleva acción`);
    assert.ok(modulo.etiqueta, `el módulo ${modulo.clave} no lleva su nombre`);
  }
  // Y las acciones son las que existen de verdad: las de las pantallas, no nombres nuevos.
  const porClave = Object.fromEntries(props.modulos.map((uno) => [uno.clave, uno]));
  assert.equal(porClave.panel.accion, "ir-inicio");
  assert.deepEqual(porClave.tierras.datos, { ir: "mis_cosas" });
  assert.deepEqual(porClave.almacen.accion, "cesta-ver");
  assert.deepEqual(porClave.anos.accion, "campanas-abrir");
  assert.deepEqual(porClave.facturas.accion, "facturas-abrir");
  assert.deepEqual(porClave.datos.accion, "mis-datos-abrir");
});

test("el módulo en el que se está va marcado, y cambia al cambiar de pantalla", async () => {
  // **Sin esto, un menú no sirve para nada**: el agricultor no sabría dónde está. Y el módulo lo dice **la
  // pantalla que está puesta**, no el botón que se ha pulsado: «Mi cuaderno» se abre desde el menú, desde
  // la pantalla de inicio y desde el aviso de lo que falta, y en los tres sitios tiene que marcar lo mismo.
  const { entorno } = await cargarAplicacion();
  const primero = montajesDelMarco[montajesDelMarco.length - 1];
  assert.equal(primero.elemento.props.modulos.find((uno) => uno.activo).clave, "panel");

  // Se va a las tierras: el armazón se vuelve a montar con «tierras» marcado.
  const antes = montajesDelMarco.length;
  await pulsar(entorno, "mis-cosas");
  assert.equal(montajesDelMarco.length, antes + 1, "no ha puesto al día el armazón al cambiar de módulo");
  const tierras = montajesDelMarco[montajesDelMarco.length - 1].elemento.props.modulos;
  assert.equal(tierras.find((uno) => uno.activo).clave, "tierras");
  assert.equal(tierras.filter((uno) => uno.activo).length, 1, "hay más de un módulo marcado");

  // Y al almacén (que tiene su propia acción, `cesta-ver`).
  await pulsar(entorno, "cesta-ver");
  const almacen = montajesDelMarco[montajesDelMarco.length - 1].elemento.props.modulos;
  assert.equal(almacen.find((uno) => uno.activo).clave, "almacen");

  // **Y no se vuelve a montar si el módulo no cambia**: el menú no puede parpadear cada vez que se toca
  // algo dentro de la misma pantalla.
  const antesDeRepetir = montajesDelMarco.length;
  await pulsar(entorno, "cesta-ver");
  assert.equal(montajesDelMarco.length, antesDeRepetir, "ha vuelto a montar el armazón sin cambiar de módulo");
});

// ---------------------------------------------------------------------------
// Pulsar botones de verdad
//
// Los tests de arriba comprueban lo que se pinta al arrancar. Estos pulsan botones
// como lo haría un agricultor, y son los que demuestran que la aplicación se puede
// usar de punta a punta en vez de quedarse en la primera pantalla.
// ---------------------------------------------------------------------------

async function pulsar(entorno, accion, datos = {}) {
  const elemento = { dataset: { accion, ...datos } };
  elemento.closest = () => elemento;
  await entorno.manejadores.click({ target: { closest: () => elemento } });
  await new Promise((resolver) => setTimeout(resolver, 30));
}

/**
 * Avanza por el asistente hasta encontrar una pantalla concreta, o se para en el resumen.
 *
 * Los asistentes tienen pasos opcionales y pasos que solo salen en algunos casos, así que contar
 * las pulsaciones es frágil: el test se rompe al añadir un paso, y eso no es un fallo de la
 * aplicación. Se avanza hasta que aparezca lo que se busca, y si se llega al resumen sin verlo, se
 * dice claramente que no ha salido.
 *
 * **Y lo que se busca puede estar en dos sitios**, desde que el asistente se está migrando a React:
 * en la pregunta del paso (que la pinta la interfaz vieja, y se lee con `pantallaDe`) o **dentro de lo
 * que se le ha pedido a React** (las etiquetas y las opciones de un grupo de campos, por ejemplo). Se
 * miran los dos, porque si no, un paso migrado «desaparece» para esta búsqueda y el test se va al
 * resumen sin darse cuenta. Pasó al migrar los campos del maestro.
 */
async function avanzarHasta(entorno, textoBuscado, intentos = 8) {
  for (let paso = 0; paso < intentos; paso += 1) {
    const html = pantallaPedida(entorno);
    if (html.includes(textoBuscado)) return html;
    if (html.includes("APUNTARLO")) {
      assert.fail(`no ha salido «${textoBuscado}»: el asistente ha llegado al resumen`);
    }
    await pulsar(entorno, "asistente-seguir");
  }
  assert.fail(`no ha salido «${textoBuscado}» en ${intentos} pantallas`);
}

/** Todos los textos de una estructura anidada, sean diccionarios o listas. */
function todosLosTextos(valor) {
  if (typeof valor === "string") return [valor];
  if (Array.isArray(valor)) return valor.flatMap(todosLosTextos);
  if (valor && typeof valor === "object") return Object.values(valor).flatMap(todosLosTextos);
  return [];
}

/**
 * Todos los textos de **lo último que se le ha pedido a React**.
 *
 * Sirve para buscar una pregunta que ya no está en el HTML del contenedor: cuando una pantalla o un paso
 * se migra, sus textos viajan dentro del elemento que se le pide a React, no en el HTML que pintaba la
 * interfaz vieja.
 *
 * **Y hay pasos que montan varias piezas a la vez** (el sitio de la muestra pide la lista de tierras, la
 * de naves y el lote): en esos casos lo que se le pide es una **lista de elementos**, y hay que mirar
 * dentro de todos. Se descubrió porque esta función devolvía nada y la prueba decía que el paso no
 * listaba las tierras, con la aplicación perfectamente bien.
 */
function textosDeLoPedido() {
  const montado = montajes[montajes.length - 1];
  if (!montado || !montado.elemento) return "";
  return todosLosTextos(Array.isArray(montado.elemento) ? montado.elemento : [montado.elemento]).join(
    " | ",
  );
}

/**
 * Los elementos que forman **el formulario del paso** del asistente.
 *
 * El asistente está entero en React desde la ronda 72: lo que se le pide a React ya no es solo la pieza
 * del paso, sino **la pantalla entera** (`PantallaAsistente`), con el formulario dentro de sus
 * propiedades (`formulario`). Esta función devuelve el formulario —uno o varios elementos, según el
 * paso—, que es lo que miran las pruebas de las piezas (`campoPedido`, `listaPedida`,
 * `bloquesDelMaestroPedidos`, `resumenPedido`, `sigpacPedido`).
 */
function piezasPedidas() {
  const montado = montajes[montajes.length - 1];
  if (!montado || !montado.elemento) return [];
  const elemento = montado.elemento;
  // Lo que se le ha pedido a React puede ser la pantalla del asistente (con el formulario dentro), una
  // lista de elementos (los pasos que montan dos piezas) o una pieza suelta.
  const dentro =
    elemento && elemento.type && elemento.type.name === "PantallaAsistente"
      ? elemento.props.formulario
      : elemento;
  if (!dentro) return [];
  return Array.isArray(dentro) ? dentro.filter(Boolean) : [dentro];
}

/**
 * La pieza que el paso está montando como formulario, por su nombre («ListaParaElegir», «Campo»…).
 *
 * Cuando lo que se le pide a React es la pantalla entera del asistente, buscar la pieza por su nombre es
 * lo que deja comprobar **cuál** de ellas se está usando en ese paso.
 */
function piezaDelPaso(nombre) {
  const pieza = piezasPedidas().find((uno) => uno && uno.type && uno.type.name === nombre);
  assert.ok(
    pieza,
    `el formulario del paso no trae ${nombre}: trae ` +
      `${piezasPedidas().map((uno) => uno && uno.type && uno.type.name).join(", ") || "nada"}`,
  );
  return pieza;
}

/**
 * El error que el asistente está enseñando en el paso actual.
 *
 * Es lo que sale en rojo debajo de la pregunta (por ejemplo, «dinos en qué parcela»). Se mira la
 * propiedad del componente, que es donde vive ahora: en el HTML del contenedor ya no hay nada, porque el
 * asistente está entero en React.
 */
function errorDelAsistente() {
  const elemento = montajes[montajes.length - 1].elemento;
  assert.equal(
    elemento && elemento.type && elemento.type.name,
    "PantallaAsistente",
    "el último montaje no es el asistente",
  );
  return elemento.props.error || "";
}

/**
 * Lo que la aplicación ha pedido pintar, como texto: el contenedor **y** lo que se le ha pedido a React.
 *
 * Antes esto era `pantallaDe(entorno)` a secas, porque todas las pantallas del asistente se pintaban con
 * `innerHTML` en el contenedor. Desde que el asistente está entero en React el contenedor se queda
 * vacío, así que se miran los dos sitios: lo que pinta la interfaz vieja (la cabecera, el aviso de
 * apuntes pendientes) y lo que se le pide a React.
 *
 * **Cuidado con lo que esto no comprueba:** que un texto salga aquí quiere decir que la aplicación lo ha
 * mandado pintar, no que esté en su sitio. Para eso están las pruebas de cada pieza
 * (`campoPedido()`, `listaPedida()`…) y la comprobación en un navegador de verdad.
 */
function pantallaPedida(entorno) {
  return `${pantallaDe(entorno)} ${textosDeLoPedido()}`;
}

/**
 * Tocar el mapa con el dedo, en un punto concreto de la imagen.
 *
 * Hace falta porque el toque no es un botón cualquiera: lo que importa es **dónde** se ha tocado.
 * El navegador le dice al manejador dónde ha sido (`offsetX`, `offsetY`), y eso es lo que se
 * reproduce aquí; sin esto no se podría probar que tocar un sitio pregunta por ese sitio.
 */
async function tocarElMapa(entorno, x, y) {
  const elemento = { dataset: { accion: "mapa-tocar" } };
  elemento.closest = () => elemento;
  await entorno.manejadores.click({
    target: { closest: () => elemento },
    offsetX: x,
    offsetY: y,
  });
  await new Promise((resolver) => setTimeout(resolver, 30));
}

function pantallaDe(entorno) {
  return entorno.nodos.get("pantalla").innerHTML;
}

// ---------------------------------------------------------------------------
// El almacén («lo que tengo en el almacén») se pasó a React en la ronda 34
//
// Lo que comprobaban estas dos pruebas —lo comprado, lo echado, lo que queda, dónde se compró y **que
// no se invente la cuenta cuando no se puede restar**— está ahora en `tests_js/react.test.js`,
// reescrito contra el componente. Y se añade lo que solo se ve desde `app.js`: que la pantalla **se
// le pide a React** con los números ya contados y las filas ya preparadas.
// ---------------------------------------------------------------------------

test("el almacén se le pide a React, con las cuentas ya hechas", async () => {
  const { entorno } = await cargarAplicacion();
  const antes = montajes.length;
  await pulsar(entorno, "cesta-ver");
  const pedidos = montajes.slice(antes);

  assert.equal(pedidos.length, 1, `se han pedido ${pedidos.length} montajes: solo el almacén`);
  const elemento = pedidos[0].elemento;
  assert.ok(elemento, "no se le pide nada a React: el almacén se está pintando a mano otra vez");
  assert.equal(elemento.type.name, "PantallaCesta");

  // Las filas llegan **ya contadas** desde `app.js`: la pantalla no calcula nada.
  const producto = elemento.props.productos[0];
  assert.equal(producto.nombre_comercial, "Ejemplo 25 EC");
  const etiquetas = producto.filas.map((fila) => fila.etiqueta);
  assert.ok(etiquetas.includes("Compraste"), `no lleva lo comprado: ${etiquetas.join(", ")}`);
  assert.ok(etiquetas.includes("Llevas echado"), "no lleva lo echado");
  // **Los dos «te queda», cada uno con su nombre** (T21, 06/10/2026). Esta prueba pedía la etiqueta
  // «Te queda» a secas, y esa etiqueta ya no existe a propósito: desde el T21 la fila destacada es el
  // saldo **del almacén** cuando se sabe, y la cuenta de los papeles va con su nombre, porque no son lo
  // mismo (lo comprado no está dentro hasta que llega el albarán). Este producto de mentira no trae
  // `saldo_fisico`, así que aquí manda la de los papeles; el caso con almacén está en la prueba de abajo.
  assert.ok(
    etiquetas.includes("Según los papeles (lo comprado menos lo echado)"),
    `no lleva lo que queda: ${etiquetas.join(", ")}`,
  );
  const donde = producto.filas.find((fila) => fila.etiqueta === "Dónde lo compraste");
  assert.ok(donde && donde.valor.includes("Cooperativa de Peñaranda"), "no dice dónde se compró");

  // Y dos cosas del diseño de Stitch de esta pantalla (ronda 90): «Te queda» **cierra la tarjeta y va
  // destacada**, y cada producto lleva su etiqueta de estado, que es lo que dice de un vistazo cuál hay
  // que mirar. Se comprueba aquí porque lo prepara `app.js`: la pantalla solo lo pinta.
  const ultima = producto.filas[producto.filas.length - 1];
  assert.equal(
    ultima.etiqueta,
    "Según los papeles (lo comprado menos lo echado)",
    "el número de lo que queda ya no cierra la tarjeta",
  );
  assert.equal(ultima.destacada, true, "«Te queda» no va destacada");
  assert.equal(producto.estado.texto, "Las cuentas cuadran", "no le llega la etiqueta de estado");
  assert.equal(producto.estado.tipo, "bien");

  // Y la cuenta del almacén, que el servidor ya mandaba y no enseñaba nadie (ronda 84). Se comprueba con la
  // frase del servidor, que es la que decide el singular y el plural (`con_cuenta`, en `textos.py`).
  assert.equal(
    elemento.props.resumen,
    "Tienes 1 producto apuntado.",
    "no le llega la cuenta de productos que manda el servidor",
  );

  assert.equal(entorno.nodos.get("pantalla").innerHTML, "");
});

/** La tabla del almacén que se le ha pedido a React (la última pantalla montada). */
function tablaDeLaCestaPedida() {
  const pantalla = montajes[montajes.length - 1].elemento;
  assert.ok(pantalla.props.tabla, "el almacén no lleva tabla");
  return pantalla.props.tabla;
}

/** El almacén con un producto al que se le pueden cambiar los números del saldo físico. */
async function conElSaldoFisico(cambios) {
  const base = RESPUESTAS["/api/productos/cesta/situacion"];
  const producto = { ...base.productos[0], ...cambios };
  const { entorno, servidor } = await cargarAplicacion({
    "/api/productos/cesta/situacion": { ...base, productos: [producto] },
  });
  await pulsar(entorno, "cesta-ver");
  return { entorno, servidor, producto: ultimoMontaje().props.productos[0] };
}

test("cuando el almacén sabe lo que hay, «te queda» es lo del almacén y los papeles van aparte", async () => {
  // **Lo que el T21 viene a arreglar** (06/10/2026): el mismo producto tenía dos números —lo comprado
  // menos lo echado (papeles) y lo que hay dentro del almacén (movimientos)— en dos pantallas distintas,
  // y el agricultor sin saber cuál creerse. Ahora manda **el del almacén** y la cuenta de los papeles se
  // enseña al lado, con su nombre. **No se suman ni se mezclan**: son dos hechos distintos.
  const { producto } = await conElSaldoFisico({
    saldo_fisico: 4,
    saldo_fisico_conocido: true,
    saldo_fisico_unidad: "L",
    // Y los papeles dicen otra cosa, a propósito: es el caso normal (comprado sin albarán todavía).
    queda: 5,
  });

  const etiquetas = producto.filas.map((fila) => fila.etiqueta);
  assert.ok(
    etiquetas.includes("Te queda (lo que hay en el almacén)"),
    `no dice lo que hay en el almacén: ${etiquetas.join(", ")}`,
  );
  assert.ok(
    etiquetas.includes("Según los papeles (lo comprado menos lo echado)"),
    "no se enseña la cuenta de los papeles, que es otro hecho distinto",
  );

  const delAlmacen = producto.filas.find((fila) => fila.etiqueta === "Te queda (lo que hay en el almacén)");
  assert.equal(delAlmacen.valor, "4,00 L", "el número de lo que hay no es el del almacén");
  assert.equal(delAlmacen.destacada, true, "lo que hay en el almacén no va destacado");
  const deLosPapeles = producto.filas.find(
    (fila) => fila.etiqueta === "Según los papeles (lo comprado menos lo echado)",
  );
  assert.equal(deLosPapeles.valor, "5,00 L");
  assert.notEqual(deLosPapeles.destacada, true, "los papeles no pueden ir destacados: manda el almacén");

  // Y **la tabla del ordenador lleva el mismo número que el titular de la tarjeta**, no otro.
  assert.equal(tablaDeLaCestaPedida().filas[0].celdas[3].texto, "4,00 L");
});

test("cuando el almacén no sabe lo que hay, se dice por qué y manda el número de los papeles", async () => {
  // Un producto que no está enlazado con nada del almacén: su saldo físico es **desconocido**, y eso se
  // dice con su motivo. Lo que **no** se hace es poner un cero (diría que no queda nada) ni esconder la
  // fila (el agricultor se quedaría buscando el número que viene a ver).
  const { producto } = await conElSaldoFisico({
    saldo_fisico: null,
    saldo_fisico_conocido: false,
    motivo_fisico:
      "Este producto no está enlazado con nada del almacén, así que de lo que te queda no se puede decir nada aquí.",
    queda: 5,
  });

  const etiquetas = producto.filas.map((fila) => fila.etiqueta);
  assert.ok(
    etiquetas.includes("Según los papeles (lo comprado menos lo echado)"),
    `no queda ningún número: ${etiquetas.join(", ")}`,
  );
  const destacada = producto.filas.find((fila) => fila.destacada);
  assert.equal(
    destacada.etiqueta,
    "Según los papeles (lo comprado menos lo echado)",
    "sin saldo físico, lo que manda es lo que dicen los papeles",
  );
  assert.ok(
    /no está enlazado con nada del almacén/.test(producto.motivo),
    `no se dice por qué no hay número del almacén: «${producto.motivo}»`,
  );
  assert.ok(!etiquetas.includes("Te queda (lo que hay en el almacén)"), "enseña un saldo físico que no tiene");
});

test("la tabla del almacén llega con sus columnas, sus números y el pie", async () => {
  // **30/09/2026.** El libro de entradas y salidas, de arriba abajo, como en el diseño de escritorio que
  // pidió Stitch (`docs/stitch/escritorio/almacen.png`): en el móvil esta misma lista va en tarjetas.
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "cesta-ver");
  const tabla = tablaDeLaCestaPedida();

  assert.deepEqual(
    tabla.columnas.map((columna) => columna.texto),
    ["Producto", "Comprado", "Echado", "Te queda", "Estado", "Acciones"],
  );
  assert.deepEqual(
    tabla.columnas.map((columna) => columna.campo || null),
    ["nombre_comercial", "comprado", "gastado", "queda", null, null],
  );
  assert.equal(tabla.filas.length, 1, "no sale el producto que hay en el almacén");
  // Los números **con su unidad**, que la pone el servidor: sin ella, «20,00» no dice de qué.
  assert.equal(tabla.filas[0].celdas[1].texto, "20,00 L");
  assert.equal(tabla.filas[0].celdas[2].texto, "15,00 L");
  assert.equal(tabla.filas[0].celdas[3].texto, "5,00 L");
  // El estado va en su etiqueta, **en corto**: la frase entera ponía la fila altísima (se vio en la captura
  // de la versión de ordenador). El número de registro, que estaba aquí como columna, está en el panel.
  assert.equal(tabla.filas[0].celdas[4].estado.texto, "Cuadra");
  assert.equal(
    tabla.filas[0].celdas.some((celda) => celda.texto === "24.123"),
    false,
    "el número de registro sigue en la tabla: es lo que la ensancha hasta apilar los botones",
  );
  // **El nombre del producto es un botón** (se toca y su ficha sale en el panel de al lado): la fila entera
  // no, que en una tabla es lo que menos se espera.
  assert.equal(tabla.filas[0].celdas[0].accion, "elegir-fila");
  assert.equal(tabla.filas[0].celdas[0].datos.tabla, "cesta");
  assert.equal(tabla.filas[0].celdas[0].datos.id, 1);
  // **Y se puede corregir y borrar desde la tabla**, con los mismos dos botones que lleva su renglón en «mis
  // parcelas, productos y máquinas»: el almacén también se equivoca.
  assert.deepEqual(
    tabla.filas[0].acciones.map((una) => una.accion),
    ["cosa-corregir", "cosa-borrar"],
  );
  assert.equal(tabla.filas[0].acciones[0].datos.tipo, "producto");
  // El pie: cuántos hay y **cuántos hay que mirar**. Con las cuentas bien, solo el número.
  assert.equal(tabla.resumen, "1 producto en el almacén");
  // Y de entrada **sin nada elegido**: el panel dice qué hacer en vez de quedarse en blanco.
  assert.equal(tabla.panel.elegida, false);
  assert.equal(tabla.panel.titulo, "El producto que has elegido");
  assert.equal(
    tabla.panel.vacio,
    "Toca el nombre de un producto de la lista y lo verás aquí, con sus cuentas.",
  );
});

test("el pie del almacén dice cuántos productos hay que mirar", async () => {
  // Es la cuenta que se viene a hacer aquí, como las hectáreas en la tabla de tierras: con el almacén lleno,
  // lo que se busca es **cuál hay que arreglar**. Y el singular se escribe bien («1 hay que mirarlo»).
  const { entorno } = await cargarAplicacion({
    "/api/productos/cesta/situacion": {
      textos: {},
      campana_id: 1,
      campana_anio: 2026,
      cuantos: 2,
      sin_cantidad: 0,
      sin_poder_comparar: 1,
      resumen: "Tienes 2 productos apuntados.",
      productos: [
        {
          producto_id: 1,
          nombre_comercial: "Ejemplo 25 EC",
          numero_registro: "24.123",
          materia_activa: "Tebuconazol",
          fecha_compra: "2026-03-10",
          proveedor: "Cooperativa de Peñaranda",
          unidad_compra: "L",
          unidad_gastado: "L",
          comprado: 20,
          comprado_de_donde: "facturas",
          gastado: 15,
          apuntes: 2,
          gastado_en_total: 15,
          queda: 5,
          se_puede_comparar: true,
          motivo: "",
        },
        {
          producto_id: 2,
          nombre_comercial: "Otro 50 WG",
          numero_registro: "25.999",
          materia_activa: "Cipermetrina",
          fecha_compra: null,
          proveedor: "",
          unidad_compra: "kg",
          unidad_gastado: "L",
          comprado: 10,
          comprado_de_donde: "ficha",
          gastado: 3,
          apuntes: 1,
          gastado_en_total: 3,
          queda: null,
          se_puede_comparar: false,
          motivo: "Un litro y un kilo no son lo mismo y no se pueden restar.",
        },
      ],
    },
  });
  await pulsar(entorno, "cesta-ver");
  const tabla = tablaDeLaCestaPedida();
  assert.equal(tabla.filas.length, 2);
  // Uno cuadra y el otro no: el pie lo dice, en singular.
  assert.equal(tabla.resumen, "2 productos en el almacén · 1 hay que mirarlo");
  // Y el que no se puede comparar lo dice **en su celda**, con palabras y en corto (la frase entera pone la
  // fila altísima: se vio en la captura de la versión de ordenador).
  assert.equal(tabla.filas[1].celdas[4].estado.texto, "No se compara");
  assert.equal(tabla.filas[1].celdas[4].estado.tipo, "mirar");
  // Un dato que no se sabe sale con un guion, nunca con un cero.
  assert.equal(tabla.filas[1].celdas[3].texto, "—");
});

test("elegir un producto lo enseña en el panel, con de dónde sale lo comprado", async () => {
  // **Fase 3, 30/09/2026.** El panel es la mitad de lo que hace que una tabla sirva: se toca el nombre y la
  // ficha sale al lado, sin cambiar de pantalla. Y lleva lo que en una celda no cabe: **de dónde sale el
  // número de lo comprado** —el servidor lo mandaba desde siempre (`comprado_de_donde`) y no lo enseñaba
  // ninguna pantalla—, la fecha y el proveedor, y el motivo cuando no hay cuenta posible.
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "cesta-ver");
  await pulsar(entorno, "elegir-fila", { tabla: "cesta", id: 1 });

  const tabla = tablaDeLaCestaPedida();
  assert.equal(tabla.panel.elegida, true, "el panel no enseña el producto elegido");
  assert.equal(tabla.filas[0].elegida, true, "la fila elegida no queda marcada");
  const panel = tabla.panel;
  assert.equal(panel.detalle, "Tebuconazol", "el panel no dice de qué es el producto");
  const etiquetas = panel.filas.map((fila) => fila.etiqueta);
  assert.deepEqual(etiquetas, [
    "Nº de registro",
    "Comprado",
    "Echado",
    "Te queda",
    "De dónde sale",
    "Cuándo",
    "Dónde lo compraste",
  ]);
  const valores = Object.fromEntries(panel.filas.map((fila) => [fila.etiqueta, fila.valor]));
  assert.equal(valores["Comprado"], "20,00 L");
  // Lo echado va con sus apuntes: un número sin de dónde sale no se puede comprobar.
  assert.equal(valores["Echado"], "15,00 L · En 1 apuntes");
  assert.equal(valores["Te queda"], "5,00 L");
  // En la copia de prueba, lo comprado sale de la ficha del producto.
  assert.equal(valores["De dónde sale"], "Lo escribiste en la ficha del producto");
  assert.equal(valores["Cuándo"], "10/03/2026");
  assert.equal(valores["Dónde lo compraste"], "Cooperativa de Peñaranda");
  // Y sus dos botones, en el panel: corregir y borrar.
  assert.deepEqual(
    panel.acciones.map((una) => una.accion),
    ["cosa-corregir", "cosa-borrar"],
  );
  // Volver a tocar el mismo producto cierra el panel: es como se cierra sin buscar un botón de cerrar.
  await pulsar(entorno, "elegir-fila", { tabla: "cesta", id: 1 });
  assert.equal(tablaDeLaCestaPedida().panel.elegida, false, "volver a tocar el producto no cierra el panel");
});

test("el panel del producto dice por qué no hay cuenta, cuando no la hay", async () => {
  // El motivo va en su franja de aviso, como en la tarjeta del móvil: es «algo que hay que mirar», y en esta
  // aplicación eso va con su señal (y con palabras, no solo con el color).
  const { entorno } = await cargarAplicacion({
    "/api/productos/cesta/situacion": {
      textos: {},
      campana_id: 1,
      campana_anio: 2026,
      cuantos: 1,
      sin_cantidad: 0,
      sin_poder_comparar: 1,
      resumen: "Tienes 1 producto apuntado.",
      productos: [
        {
          producto_id: 3,
          nombre_comercial: "Otro 50 WG",
          numero_registro: "25.999",
          materia_activa: "Cipermetrina",
          fecha_compra: null,
          proveedor: "",
          unidad_compra: "kg",
          unidad_gastado: "L",
          comprado: 10,
          comprado_de_donde: "",
          gastado: 3,
          apuntes: 0,
          gastado_en_total: 3,
          queda: null,
          se_puede_comparar: false,
          motivo: "Un litro y un kilo no son lo mismo y no se pueden restar.",
        },
      ],
    },
  });
  await pulsar(entorno, "cesta-ver");
  await pulsar(entorno, "elegir-fila", { tabla: "cesta", id: 3 });
  const panel = tablaDeLaCestaPedida().panel;
  assert.deepEqual(panel.avisos, ["Un litro y un kilo no son lo mismo y no se pueden restar."]);
  // Y **sin origen no se pone la fila**: un origen inventado es peor que no tenerlo.
  assert.ok(
    !panel.filas.some((fila) => fila.etiqueta === "De dónde sale"),
    "el panel se inventa de dónde sale lo comprado",
  );
  // Sin proveedor ni fecha tampoco se ponen esas filas.
  assert.ok(!panel.filas.some((fila) => fila.etiqueta === "Dónde lo compraste"));
  assert.ok(!panel.filas.some((fila) => fila.etiqueta === "Cuándo"));
});

test("ordenar la tabla de facturas ordena las facturas, y no las tierras", async () => {
  // **Esto estaba roto** (30/09/2026): el manejador de «ordenar-tabla» solo miraba si la tabla era la del
  // cuaderno, así que pulsar una cabecera de la tabla de facturas ordenaba **la lista de tierras** y llevaba
  // al agricultor a otra pantalla sin decirle nada. Es lo peor que puede hacer un programa de gestión.
  const laFactura = {
    id: 9,
    proveedor: "Cooperativa Agrícola",
    numero_factura: "2026/00123",
    fecha: "2026-03-02",
    base_imponible: 620.0,
    cuota_iva: 130.2,
    total: 750.2,
    tiene_fichero: true,
    lineas: [],
  };
  const otra = { ...laFactura, id: 10, numero_factura: "2026/00999", fecha: "2026-05-20", total: 100 };
  const { entorno } = await cargarAplicacion({ "/api/facturas": [laFactura, otra] });
  await pulsar(entorno, "facturas-abrir");
  let tabla = montajes[montajes.length - 1].elemento.props.tabla;
  // De entrada, por fecha y **de lo más nuevo a lo más viejo**, que es como lo cuenta el agricultor.
  assert.deepEqual(
    tabla.filas.map((fila) => fila.celdas[2].texto),
    ["2026/00999", "2026/00123"],
  );
  const ordenada = tabla.columnas.find((columna) => columna.ordenada);
  assert.equal(ordenada.campo, "fecha_iso", "la tabla no dice por dónde va ordenada");
  assert.equal(ordenada.descendente, true);

  // Se pulsa la cabecera del total: la tabla se ordena por el total y **se sigue viendo la lista de
  // facturas** (la factura más barata primero, que es un orden nuevo).
  await pulsar(entorno, "ordenar-tabla", { tabla: "facturas", campo: "total_numero" });
  const pantalla = montajes[montajes.length - 1].elemento;
  assert.equal(pantalla.type.name, "PantallaFacturas", "ordenar las facturas ha llevado a otra pantalla");
  tabla = pantalla.props.tabla;
  assert.deepEqual(
    tabla.filas.map((fila) => fila.celdas[5].texto),
    ["100,00 €", "750,20 €"],
  );
  assert.equal(tabla.columnas.find((columna) => columna.ordenada).campo, "total_numero");

  // Y el orden de las tierras **no se ha tocado**: cada tabla se acuerda del suyo.
  await pulsar(entorno, "mis-cosas");
  assert.equal(
    tablaDeTierrasPedida().columnas.find((columna) => columna.ordenada).campo,
    "numero",
    "ordenar las facturas ha cambiado el orden de las tierras",
  );
});

test("ordenar la tabla de los años ordena los años, y se queda en su pantalla", async () => {
  // El mismo fallo, en la otra tabla: los años se pueden ordenar por lo llenos que estén, que es lo que se
  // mira al empezar el año o al arreglar uno mal puesto.
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "campanas-abrir");
  let tabla = montajes[montajes.length - 1].elemento.props.tabla;
  // De entrada, del año más nuevo al más viejo.
  assert.deepEqual(
    tabla.filas.map((fila) => fila.celdas[0].texto),
    ["2026", "2025", "2024"],
  );
  const ordenada = tabla.columnas.find((columna) => columna.ordenada);
  assert.equal(ordenada.campo, "anio_numero");
  assert.equal(ordenada.descendente, true);

  await pulsar(entorno, "ordenar-tabla", { tabla: "anos", campo: "apuntes" });
  const pantalla = montajes[montajes.length - 1].elemento;
  assert.equal(pantalla.type.name, "PantallaCampanas", "ordenar los años ha llevado a otra pantalla");
  tabla = pantalla.props.tabla;
  assert.equal(tabla.columnas.find((columna) => columna.ordenada).campo, "apuntes");
  // Ordenado por los apuntes, de menos a más: el vacío primero. Se ordena por **los apuntes**, que es lo que
  // enseña la celda, y no por el total de cosas (que decide si el año se puede quitar y no es una columna).
  assert.equal(tabla.filas[0].celdas[0].texto, "2024");
});

test("en todas las tablas, las celdas cuadran con las columnas", async () => {
  // **Esto estaba mal en las cinco tablas** y se vio en una captura de la versión de ordenador: la pieza
  // (`react/piezas/tabla.js`) **siempre** pinta al final la celda de las acciones, así que cada `tablaDe…`
  // añadía además una celda vacía de más. Con una celda de más, los botones de la fila caían en una columna
  // **sin cabecera**: la tabla se ensanchaba sola, el encabezado no estaba encima de sus botones y, con el
  // panel abierto, la última columna quedaba fuera de la vista. Nadie lo veía porque las dos columnas de más
  // estaban casi vacías.
  //
  // Lo que se comprueba aquí vale para la tabla que se añada mañana: **celdas = columnas − 1** (la última la
  // pone la pieza) y **la última columna es la de las acciones** (sin campo, no se ordena).
  const { entorno } = await cargarAplicacion({
    // Con las listas vacías no habría ni una fila que mirar y esta prueba pasaría sin comprobar nada: se le
    // dan los dos apuntes del cuaderno (para la tabla de los apuntes) y una factura.
    ...DOS_APUNTES,
    "/api/facturas": [
      {
        id: 9,
        proveedor: "Cooperativa Agrícola",
        numero_factura: "2026/00123",
        fecha: "2026-03-02",
        base_imponible: 620.0,
        cuota_iva: 130.2,
        total: 750.2,
        tiene_fichero: true,
        lineas: [],
      },
    ],
  });
  const tablas = [];
  await pulsar(entorno, "mis-cosas");
  tablas.push(["las tierras", tablaDeTierrasPedida()]);
  await pulsar(entorno, "cesta-ver");
  tablas.push(["el almacén", tablaDeLaCestaPedida()]);
  await pulsar(entorno, "facturas-abrir");
  tablas.push(["las facturas", montajes[montajes.length - 1].elemento.props.tabla]);
  await pulsar(entorno, "campanas-abrir");
  tablas.push(["los años del cuaderno", montajes[montajes.length - 1].elemento.props.tabla]);
  await pulsar(entorno, "cultivo-ver-todos");
  tablas.push(["qué hay sembrado", montajes[montajes.length - 1].elemento.props.tabla]);
  await pulsar(entorno, "inicio", { ir: "mi_cuaderno" });
  tablas.push(["el cuaderno", tablaDeApuntesPedida()]);

  assert.equal(tablas.length, 6, "no se han mirado las seis tablas");
  for (const [nombre, tabla] of tablas) {
    assert.ok(tabla, `la tabla de ${nombre} no llega`);
    assert.ok(tabla.filas.length, `la tabla de ${nombre} no tiene filas que mirar`);
    for (const fila of tabla.filas) {
      assert.equal(
        fila.celdas.length,
        tabla.columnas.length - 1,
        `en ${nombre} hay ${fila.celdas.length} celdas para ${tabla.columnas.length} columnas: ` +
          "la última columna (Acciones) la pone la pieza, no `app.js`",
      );
    }
    const ultima = tabla.columnas[tabla.columnas.length - 1];
    assert.equal(ultima.campo, undefined, `en ${nombre} la última columna no es la de las acciones`);
  }
});

test("la tabla de qué hay sembrado llega con sus columnas, sus celdas y el pie", async () => {
  // **30/09/2026.** Es la lista más larga del programa después de las tierras (una fila por tierra) y se
  // había quedado sin tabla: en el ordenador se veían tres tarjetas enormes por pantalla. Se vio en la
  // revisión de la interfaz, mirando la aplicación con las 64 tierras de verdad.
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "cultivo-ver-todos");
  const tabla = montajes[montajes.length - 1].elemento.props.tabla;
  assert.ok(tabla, "la pantalla de qué hay sembrado no lleva tabla");
  assert.deepEqual(
    tabla.columnas.map((columna) => columna.texto),
    ["Tierra", "Hectáreas", "Este año hay", "Rotación", "Otros años", "Estado", "Acciones"],
  );
  assert.deepEqual(
    tabla.columnas.map((columna) => columna.campo || null),
    ["alias", "superficie_ha", "especie", null, "anteriores", null, null],
  );
  // Las tierras, por nombre: la que no tiene dicho qué tiene y la que sí (y repite lo del año pasado).
  assert.deepEqual(
    tabla.filas.map((fila) => fila.celdas[0].texto),
    ["El Prado", "La Vega"],
  );
  assert.deepEqual(
    tabla.filas.map((fila) => fila.celdas[1].texto),
    ["2,43 ha", "5,00 ha"],
  );
  // **Lo que hay este año**: la que no lo tiene dicho deja la celda vacía (y lo dice en su estado), y la que
  // sí lo trae con su variedad.
  assert.equal(tabla.filas[0].celdas[2].texto, "");
  assert.equal(tabla.filas[1].celdas[2].texto, "Maíz · Pioneer");
  // **La alerta de rotación, en su propia columna** (30/09/2026): con 64 tierras el aviso se busca
  // recorriendo la lista, y como letra pequeña debajo del cultivo no se veía. Va con palabras y en ámbar.
  assert.equal(tabla.filas[0].celdas[3].estado, null, "una tierra que no repite no lleva alerta");
  assert.equal(tabla.filas[1].celdas[3].estado.texto, "Repite lo del año pasado");
  assert.equal(tabla.filas[1].celdas[3].estado.tipo, "mirar");
  // Lo de años anteriores, con su año delante.
  assert.match(tabla.filas[1].celdas[4].texto, /2025: Maíz/);
  // Y el estado, que es lo que se viene a buscar aquí: **a cuáles les falta decirlo**.
  assert.equal(tabla.filas[0].celdas[5].estado.texto, "Falta rellenar");
  assert.equal(tabla.filas[0].celdas[5].estado.tipo, "falta");
  assert.equal(tabla.filas[1].celdas[5].estado.texto, "Al día");
  // El botón de la fila, con la etiqueta corta: «DECIRLO» en la que falta y «CAMBIARLO» en la que ya está.
  assert.deepEqual(
    tabla.filas.map((fila) => fila.acciones.map((una) => una.accion)),
    [["cultivo-decir"], ["cultivo-decir"]],
  );
  assert.deepEqual(
    tabla.filas.map((fila) => fila.acciones[0].etiqueta),
    ["DECIRLO", "CAMBIARLO"],
  );
  assert.equal(tabla.filas[0].acciones[0].datos.id, 1, "el botón de la fila no dice de qué tierra es");
  // Y el pie: cuántas tierras hay y cuántas tienen dicho su cultivo.
  assert.equal(tabla.resumen, "2 tierras · 1 con su cultivo dicho");
});

test("el panel de mando del ordenador llega con sus números, lo que falta y los últimos apuntes", async () => {
  // **Fase 4, 30/09/2026.** Es la pantalla que se abre al entrar desde un pc, y antes era la del móvil
  // estirada: ocho botones de ancho completo en un monitor. Lo que se comprueba aquí es el **cableado**: que
  // los cuatro números salgan de los datos que la pantalla ya tiene, que lo que falta sea **la misma lista
  // del cuaderno** (con su botón) y que los últimos apuntes sean los mismos de la tabla del cuaderno.
  const { entorno } = await cargarAplicacion({
    "/api/tratamientos": [unTratamiento({ fecha: "2026-05-02", superficie_tratada_ha: 4.9 })],
    "/api/ventas": [unaVenta({ kilos: 42000.0, cantidad: 42000.0 })],
    "/api/cuaderno/falta": {
      campana: 2026,
      esta_completo: false,
      pendientes: [
        {
          tipo: "parcela_sin_cultivo",
          mensaje: "A El Prado le falta decir qué tiene este año.",
        },
      ],
      mensaje: null,
    },
  });
  const pantalla = montajes[montajes.length - 1].elemento;
  assert.equal(pantalla.type.name, "PantallaInicio");
  const mando = pantalla.props.mando;
  assert.ok(mando, "la pantalla de inicio no lleva el panel de mando del ordenador");

  // 1. Los cuatro números, contados de los datos que ya están cargados (ni una petición más).
  assert.deepEqual(
    mando.numeros.map((numero) => numero.etiqueta),
    ["Apuntes este año", "Hectáreas tratadas", "Lo que has vendido", "Tus tierras"],
  );
  assert.equal(mando.numeros[0].valor, "1");
  assert.equal(mando.numeros[0].detalle, "1 apunte en el cuaderno");
  assert.equal(mando.numeros[1].valor, "4,90 ha");
  assert.equal(
    mando.numeros[1].detalle,
    "de 7,43 ha de tus tierras",
    "las hectáreas tratadas se cuentan sobre las de todas las tierras",
  );
  assert.equal(mando.numeros[2].valor, "42.000 kg");
  assert.equal(mando.numeros[2].detalle, "1 venta apuntada");
  assert.equal(mando.numeros[3].valor, "2");
  // La tarjeta de las tierras dice **lo que hay que hacer**, que es lo que la hace útil.
  assert.equal(mando.numeros[3].detalle, "1 sin decir qué tiene este año");

  // 2. Lo que falta: la misma lista del cuaderno, con su cuenta y **su botón**.
  assert.equal(mando.faltantes.titulo, "Lo que falta por completar");
  assert.equal(mando.faltantes.cuantas, "1 cosa por completar");
  assert.equal(mando.faltantes.pendientes.length, 1);
  assert.equal(mando.faltantes.pendientes[0].accion, "cultivo-ver-todos");
  assert.equal(mando.faltantes.pendientes[0].etiqueta, "Qué hay sembrado");

  // 3. Los últimos apuntes: los mismos cinco que la tabla del cuaderno, con el enlace a la lista entera.
  assert.deepEqual(mando.ultimos.columnas, ["Fecha", "Qué", "Tierra", "Hectáreas"]);
  assert.equal(mando.ultimos.filas.length, 1);
  assert.equal(mando.ultimos.filas[0][0], "02/05/2026");
  assert.equal(mando.ultimos.filas[0][2], "El Prado");
  assert.equal(mando.ultimos.filas[0][3], "4,90 ha");
  assert.equal(mando.ultimos.ver_todos.etiqueta, "Ver el apunte del año");
  assert.equal(mando.ultimos.ver_todos.datos.ir, "mi_cuaderno");

  // 4. Y el cierre: el cuaderno en papel, los datos en un fichero y la firma.
  assert.deepEqual(
    mando.cierre.botones.map((boton) => boton.accion),
    ["inicio", "sacar-datos", "firmar-abrir"],
  );
  assert.equal(mando.cierre.botones[0].datos.ir, "papel");
  // Los tres botones de apuntar, con los textos y los iconos del servidor (los mismos del móvil).
  assert.deepEqual(
    mando.apuntar.map((boton) => boton.datos.ir),
    ["echar_producto", "abonar", "trabajo"],
  );
  assert.ok(mando.apuntar[0].icono, "los botones de apuntar pierden su icono");

  // Y el móvil **no se queda sin nada**: los seis botones de siempre siguen ahí, en su bloque.
  assert.equal(pantalla.props.textos.inicio.botones.length, 6);
});

test("con el servidor sin contestar lo que falta, el panel de mando no dice que no falte nada", async () => {
  // La regla de la casa: **lo que no se sabe no se afirma**. Si la lista de lo que falta no ha llegado, el
  // panel de mando no puede decir «no te falta nada» (sería una buena noticia inventada).
  const { entorno } = await cargarAplicacion({
    "/api/cuaderno/falta": falla({ detail: "El servidor no ha podido mirarlo." }),
  });
  const mando = montajes[montajes.length - 1].elemento.props.mando;
  assert.equal(mando.faltantes.cuantas, "");
  assert.deepEqual(mando.faltantes.pendientes, []);
  // Y la tarjeta de las tierras tampoco se inventa el número de las que faltan.
  const tierras = mando.numeros[3];
  assert.equal(tierras.valor, "2", "las tierras sí se saben: lo que no se sabe es el cultivo");
});

test("la ficha del producto pregunta cuánto se compró", async () => {
  // Sin pedir el dato, la pantalla del almacén no tendría nada que enseñar.
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "mis-cosas");
  await pulsar(entorno, "anadir-maestro", { tipo: "producto" });
  escribir(entorno, "nombre_comercial", "Ejemplo 25 EC");
  await pulsar(entorno, "asistente-seguir"); // el nombre
  escribir(entorno, "numero_registro", "24.123");
  await pulsar(entorno, "asistente-seguir"); // el número de registro
  escribir(entorno, "dosis_maxima", "0,8");
  await pulsar(entorno, "asistente-seguir"); // la dosis máxima
  await pulsar(entorno, "elegir", { campo: "unidad_dosis", valor: "L/ha" }); // la unidad
  escribir(entorno, "plazo_seguridad_dias", "21");
  await pulsar(entorno, "asistente-seguir"); // los días de espera
  await pulsar(entorno, "asistente-saltar"); // los datos de la etiqueta
  // Los tres datos de la compra los pide ahora React (la pieza `CamposDelMaestro`): lo que se mira es
  // lo que se le pide —el `id` de cada campo, que es lo único que tiene `app.js` para leerlo— y que la
  // unidad sea una **lista** y no una casilla de escribir.
  const ids = idsDeLosBloques();
  assert.ok(ids.includes("cantidad_comprada"), `no pregunta cuánto: ${ids.join(", ")}`);
  assert.ok(ids.includes("fecha_compra"), "no pregunta cuándo");
  // La unidad se elige de una lista, no se escribe: si el agricultor escribiera a mano saldrían
  // diez formas de decir «litros» y no se podrían sumar.
  const unidades = opcionesDelBloque("unidad_compra");
  assert.ok(unidades.length > 1, `no ofrece la lista de unidades: ${unidades.join(", ")}`);
});

// ---------------------------------------------------------------------------
// «Qué hay sembrado» se pasó a React en la ronda 38
//
// Lo que comprobaba esta prueba —lo que falta, el cultivo de cada tierra, el historial de otros
// años y el botón para decirlo— está ahora en `tests_js/react.test.js`, contra el componente. Aquí
// se comprueba lo que solo se ve desde `app.js`: que la pantalla **se le pide a React** con las
// tierras ya preparadas.
// ---------------------------------------------------------------------------

test("qué hay sembrado se le pide a React, con las tierras ya preparadas", async () => {
  const { entorno } = await cargarAplicacion();
  const antes = montajes.length;
  await pulsar(entorno, "cultivo-ver-todos");
  const pedidos = montajes.slice(antes);

  assert.equal(pedidos.length, 1, `se han pedido ${pedidos.length} montajes: solo «qué hay sembrado»`);
  const elemento = pedidos[0].elemento;
  assert.ok(elemento, "no se le pide nada a React: la pantalla se está pintando a mano otra vez");
  assert.equal(elemento.type.name, "PantallaCultivos");

  const tierras = elemento.props.parcelas;
  assert.ok(tierras.length, "no le llega ninguna tierra");
  for (const tierra of tierras) {
    assert.ok(tierra.alias, "una tierra sin nombre");
    assert.equal(typeof tierra.tiene_cultivo, "boolean", "no se sabe si tiene cultivo declarado");
    assert.ok(Array.isArray(tierra.filas), "las filas de la ficha no llegan preparadas");
  }
  // La franja de lo que falta: el texto del servidor («A 1 parcela le falta decir qué tiene este año.») y
  // **el botón que enseña solo esas** (30/09/2026, del diseño de escritorio de esta pantalla).
  assert.equal(typeof elemento.props.aviso.texto, "string", "no le llega el resumen del servidor");
  assert.equal(elemento.props.aviso.boton.accion, "cultivo-solo-las-que-faltan");
  assert.equal(elemento.props.aviso.boton.etiqueta, "VER SOLO LAS QUE FALTAN");

  assert.equal(entorno.nodos.get("pantalla").innerHTML, "");
});

test("el filtro de las que faltan enseña solo esas, y siempre hay salida", async () => {
  // **30/09/2026, y lo pide el diseño de escritorio de esta pantalla** (`docs/stitch/escritorio/cultivos.png`):
  // el aviso dice a cuántas tierras les falta decir qué tienen y el botón enseña esas y solo esas, para
  // irlas diciendo una detrás de otra. Un filtro del que no se puede salir es una lista de tierras que ha
  // desaparecido, así que el mismo botón las devuelve todas.
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "cultivo-ver-todos");
  const todasAntes = montajes[montajes.length - 1].elemento.props.parcelas.length;
  assert.equal(todasAntes, 2, "la copia de prueba tiene dos tierras");

  await pulsar(entorno, "cultivo-solo-las-que-faltan");
  const filtrada = montajes[montajes.length - 1].elemento.props;
  assert.equal(filtrada.parcelas.length, 1, "el filtro no ha dejado solo la que falta");
  assert.equal(filtrada.parcelas[0].alias, "El Prado");
  assert.equal(filtrada.tabla.filas.length, 1, "la tabla no se ha filtrado con las tarjetas");
  // Y el pie dice que se está viendo una de dos: un filtro sin decirlo parece una pérdida de tierras.
  assert.match(filtrada.tabla.resumen, /^1 de 2 tierras/);
  assert.doesNotMatch(filtrada.tabla.resumen, /0 con su cultivo dicho/,
    "el filtro de las pendientes no añade una cifra cero que no ayuda a resolverlas");
  // Y el botón pasa a ser el de volver a verlas todas.
  assert.equal(filtrada.aviso.boton.accion, "cultivo-ver-todas");
  assert.equal(filtrada.aviso.boton.etiqueta, "VERLAS TODAS");

  await pulsar(entorno, "cultivo-ver-todas");
  const todas = montajes[montajes.length - 1].elemento.props;
  assert.equal(todas.parcelas.length, 2, "no se vuelven a ver todas las tierras");
  assert.equal(todas.aviso.boton.accion, "cultivo-solo-las-que-faltan");
});

test("el aviso de «le falta el cultivo» lleva al sitio donde se arregla", async () => {
  // La regla del proyecto: si le dices al agricultor que le falta algo, le das el botón que lo
  // arregla. Antes esto era solo un texto en una lista.
  const { entorno } = await cargarAplicacion({
    "/api/cuaderno/falta": {
      pendientes: [
        { tipo: "parcela_sin_cultivo", parcela_id: 1, mensaje: "A El Prado le falta decir qué cultivo tiene este año." },
      ],
      cuantos: 1,
    },
  });
  await pulsar(entorno, "inicio", { ir: "mi_cuaderno" });
  const faltantes = ultimoCuadernoPedido().faltantes;
  const pendiente = faltantes.pendientes[0];
  assert.ok(
    pendiente.mensaje.includes("A El Prado le falta decir"),
    `no le llega el aviso: ${JSON.stringify(pendiente)}`,
  );
  assert.equal(
    pendiente.accion,
    "cultivo-ver-todos",
    `el aviso no lleva a donde se arregla: ${JSON.stringify(pendiente)}`,
  );
  assert.equal(pendiente.etiqueta, "Qué hay sembrado", "el botón del aviso sale sin texto");
});

test("decir qué hay sembrado se puede hacer de punta a punta", async () => {
  // El formulario **se le pide a React** con la tierra, lo que ya estaba declarado y las opciones de
  // sistema; que los cinco campos tengan su `id` se comprueba en `tests_js/react.test.js`. Aquí lo que
  // importa es el camino entero: abrirlo, escribir y guardar de verdad.
  const { entorno, servidor } = await cargarAplicacion();
  await pulsar(entorno, "cultivo-ver-todos");
  const antes = montajes.length;
  await pulsar(entorno, "cultivo-decir", { id: "1" });

  const elemento = montajes[montajes.length - 1].elemento;
  assert.equal(elemento.type.name, "PantallaDecirCultivo");
  assert.equal(elemento.props.parcela.id, 1, "no le llega de qué tierra es");
  assert.ok(elemento.props.parcela.detalle.includes("El Prado"), "no dice de qué tierra habla");
  assert.ok(
    elemento.props.sistemas.some((opcion) => opcion.elegido),
    "no viene elegido el secano o el regadío",
  );
  assert.ok(antes >= 0);

  escribir(entorno, "cultivo-especie", "Cebada de dos carreras");
  await pulsar(entorno, "cultivo-guardar", { id: "1" });

  // Se ha guardado **lo que estaba escrito** y ha vuelto a la lista.
  const guardado = servidor.enviados.find(
    (envio) => envio.metodo === "POST" && envio.ruta.includes("/api/parcelas/1/cultivos"),
  );
  assert.ok(guardado, `no ha guardado el cultivo: ${servidor.llamadasConMetodo.join(", ")}`);
  assert.equal(guardado.cuerpo.especie, "Cebada de dos carreras", "no ha mandado lo escrito");

  // Al guardar, `app.js` recarga **todos** los datos antes de volver a la lista (`cargarDatos`): son
  // veinte peticiones, así que hay que dejarle un momento más que el que espera `pulsar`.
  await new Promise((resolver) => setTimeout(resolver, 200));
  const despues = montajes[montajes.length - 1].elemento;
  assert.equal(
    despues.type.name,
    "PantallaCultivos",
    `no vuelve a la lista de lo sembrado: monta ${despues.type.name} y se ha pedido ${servidor.llamadasConMetodo.join(", ")}`,
  );
});

// ---------------------------------------------------------------------------
// CAMBIAR Y QUITAR lo que hay sembrado en una tierra (ronda 93)
//
// Las dos cosas se podían por la API desde la ronda anterior —el `POST` corrige en el sitio cuando esa
// tierra ya tiene cultivo declarado ese año, y el `DELETE` lo quita— y **ninguna pantalla las pedía**: al
// agricultor que se equivocaba de tierra al decir el cultivo solo le quedaba escribir otro encima, que es
// dejar un dato falso en el cuaderno. Lo pidió David así: «recuerda también dejar borrar las cosas que
// introduzca porque puede que me equivoque, o modificar también».
//
// Lo que se comprueba aquí es el cableado: que la pantalla diga que está **cambiando** (y no diciendo),
// que guardar no cree un segundo cultivo, que el final diga «Corregido» y no «Apuntado», y que quitar
// pregunte antes y no mande nada hasta que se confirme.
// ---------------------------------------------------------------------------

test("cambiar lo que hay sembrado dice que está cambiando y no crea un cultivo nuevo", async () => {
  const { entorno, servidor } = await cargarAplicacion({
    // La tierra 2 ya tiene dicho qué tiene este año (maíz): a esa se va a cambiar.
    "POST /api/parcelas/2/cultivos": { id: 3, especie: "Maíz tardío", corregido: true },
  });
  await pulsar(entorno, "cultivo-ver-todos");
  await pulsar(entorno, "cultivo-decir", { id: "2" });

  const pantalla = montajes[montajes.length - 1].elemento;
  assert.equal(pantalla.type.name, "PantallaDecirCultivo");
  assert.equal(pantalla.props.ya_dicho, true, "no dice que esa tierra ya tenía cultivo");
  // Y lo que ya estaba dicho llega dentro de sus campos, para no escribirlo entero otra vez.
  assert.equal(pantalla.props.valores.especie, "Maíz", "no llega lo que ya estaba dicho");
  assert.equal(pantalla.props.valores.variedad, "Pioneer");
  assert.equal(
    pantalla.props.textos.corregir.boton_guardar,
    "GUARDAR LOS CAMBIOS",
    "el botón de guardar no dice que se están guardando cambios",
  );

  // Una tierra **sin** nada dicho no dice que está cambiando nada: enseña la pantalla de siempre.
  await pulsar(entorno, "cultivo-ver-todos");
  await pulsar(entorno, "cultivo-decir", { id: "1" });
  assert.equal(
    montajes[montajes.length - 1].elemento.props.ya_dicho,
    false,
    "una tierra sin cultivo dice que está cambiando lo que ya estaba",
  );

  // Y se cambia de verdad: la especie nueva va al mismo cultivo, con un `POST` a la misma puerta.
  await pulsar(entorno, "cultivo-ver-todos");
  await pulsar(entorno, "cultivo-decir", { id: "2" });
  escribir(entorno, "cultivo-especie", "Maíz tardío");
  await pulsar(entorno, "cultivo-guardar", { id: "2" });
  const enviado = servidor.enviados.find(
    (envio) => envio.metodo === "POST" && envio.ruta.includes("/api/parcelas/2/cultivos"),
  );
  assert.ok(enviado, `no ha mandado el cambio: ${servidor.llamadasConMetodo.join(", ")}`);
  assert.equal(enviado.cuerpo.especie, "Maíz tardío");
  assert.equal(enviado.cuerpo.campana_id, 1, "no dice de qué campaña es el cultivo");

  // El final dice **«Corregido»**, no «Apuntado»: quien acaba de cambiar un dato no ha apuntado nada.
  await new Promise((resolver) => setTimeout(resolver, 200));
  const despues = montajes[montajes.length - 1].elemento;
  assert.equal(despues.props.titulo, "Corregido", "el final del cambio no dice que se ha corregido");
  // Y su botón lleva **a la lista de lo sembrado**, que es a donde dice que lleva: el nombre de esa
  // pantalla (`cultivos`) tiene que estar en `irAInicio`, o el botón cae en el `default` y lleva al
  // inicio sin que ninguna prueba que mire el `data-ir` se entere (pasó en la ronda 93 con `mis_cosas`).
  const ver = despues.props.acciones.find((una) => una.accion === "inicio");
  assert.equal(ver.datos.ir, "cultivos");
  await pulsar(entorno, "inicio", { ir: "cultivos" });
  assert.equal(
    montajes[montajes.length - 1].elemento.type.name,
    "PantallaCultivos",
    "el botón de ver lo sembrado no acaba en la lista de lo sembrado",
  );
});

test("quitar el cultivo de una tierra pregunta antes, y solo entonces lo manda", async () => {
  const { entorno, servidor } = await cargarAplicacion({
    "DELETE /api/parcelas/2/cultivos/1": { borrado: true, parcela_id: 2, campana_id: 1 },
  });
  await pulsar(entorno, "cultivo-ver-todos");
  await pulsar(entorno, "cultivo-decir", { id: "2" });

  // El botón de quitar está, con su explicación, y **solo en la tierra que tiene algo que quitar**.
  await pulsar(entorno, "cultivo-quitar", { id: "2" });
  const pregunta = montajes[montajes.length - 1].elemento;
  assert.equal(pregunta.props.pregunta, "¿Seguro que quieres borrarlo?");
  assert.ok(
    JSON.stringify(pregunta.props.contenido).includes("Maíz"),
    "la pregunta no enseña lo que va a desaparecer",
  );
  assert.deepEqual(
    pregunta.props.acciones.map((una) => una.accion),
    ["cultivo-quitar-si", "cultivo-decir", "cultivo-ver-todos"],
    "la pregunta no ofrece sus salidas (quitarlo, cambiarlo y volver)",
  );
  // Abrir la pregunta **no quita nada**: eso es lo que hace que se pueda mirar sin miedo.
  assert.equal(
    servidor.enviados.filter((envio) => envio.metodo === "DELETE").length,
    0,
    "se ha quitado el cultivo solo con abrir la pantalla que pregunta",
  );

  await pulsar(entorno, "cultivo-quitar-si", { id: "2" });
  const quitado = servidor.enviados.find((envio) => envio.metodo === "DELETE");
  assert.ok(quitado, `no ha mandado el quitado: ${servidor.llamadasConMetodo.join(", ")}`);
  // **A la campaña que está diciendo la lista**, que es la de este año: quitarla de otro año dejaría
  // dicho el de este, que es el error que hay que poder deshacer.
  assert.equal(quitado.ruta, "/api/parcelas/2/cultivos/1");
  await new Promise((resolver) => setTimeout(resolver, 200));
  const despues = montajes[montajes.length - 1].elemento;
  assert.equal(despues.props.titulo, "Quitado", "el final del quitado no dice que se ha quitado");
});

// ---------------------------------------------------------------------------
// La pregunta de dónde se ha echado es una PIEZA de React desde la ronda 62
//
// La mitad de los pasos del asistente son la misma pantalla —una lista de botones— y estaban escritos
// siete veces a mano en `app.js`. Ahora hay una pieza (`react/piezas/lista_para_elegir.js`) y lo que
// comprueba **aquí** es solo el cableado: que el paso se le pide a React y que le llegan los botones
// ya preparados, con su acción y sus `data-*`, que son lo que lee el manejador de clics. Lo que se ve
// dentro está en `tests_js/react.test.js`, contra la pieza.
// ---------------------------------------------------------------------------

test("la pregunta de dónde se ha echado se le pide a React, con las tierras preparadas", async () => {
  const { entorno } = await cargarAplicacion({ "/api/productos": UN_PRODUCTO });
  const antes = montajes.length;
  await pulsar(entorno, "inicio", { ir: "echar_producto" });
  const pedidos = montajes.slice(antes);

  assert.equal(pedidos.length, 1, `se han pedido ${pedidos.length} montajes: solo el paso`);
  const elemento = pedidos[0].elemento;
  assert.ok(elemento, "no se le pide nada a React: el paso se está pintando a mano otra vez");
  // Se le pide **la pantalla del asistente**, con la pieza del paso dentro (ver `piezasPedidas`).
  assert.equal(elemento.type.name, "PantallaAsistente");
  assert.equal(elemento.props.titulo, "¿Dónde?", "la pregunta del paso no llega al componente");
  const lista = piezaDelPaso("ListaParaElegir");

  const tierras = lista.props.bloques[0].botones;
  assert.ok(tierras.length, "no le llega ninguna tierra");
  assert.equal(tierras[0].accion, "elegir", "la tierra no lleva la acción de elegir");
  assert.equal(tierras[0].datos.campo, "parcela_id", "la tierra no dice a qué campo contesta");
  assert.equal(tierras[0].datos.superficie, 2.43, "la tierra no lleva su superficie");
  // Desde el rediseño (ronda 77) la tierra llega como **tarjeta**: con su forma dibujada, su superficie,
  // su pueblo y sus avisos (y el dibujo del trozo, que es como el agricultor reconoce cuál es cuál).
  assert.equal(tierras[0].tarjeta, true, "la tierra no llega como tarjeta");
  assert.ok(
    tierras[0].lineas[0].includes("hectáreas"),
    `la tarjeta no lleva la superficie: ${JSON.stringify(tierras[0].lineas)}`,
  );
  assert.ok(Array.isArray(tierras[0].avisos), "la tarjeta no lleva sus avisos");
  assert.equal(tierras[0].elegida, false, "una tierra sin elegir sale como elegida");
  assert.ok(tierras[0].textos.elegida, "la etiqueta de «ELEGIDA» no le llega");

  // Y la salida de «no es una parcela» va en **su propio bloque y al final**: nueve de cada diez veces
  // el producto se echa en la tierra, así que esa pregunta no puede estar delante.
  const bloques = lista.props.bloques;
  const ultimo = bloques[bloques.length - 1];
  assert.ok(
    ultimo.botones.some((boton) => boton.accion === "tipo-tratamiento"),
    "no le llega la salida de «no es una parcela»",
  );
  assert.ok(
    bloques.slice(0, -1).every((bloque) => bloque.botones.every((b) => b.accion === "elegir")),
    "la salida de «no es una parcela» no está la última",
  );
});

// ---------------------------------------------------------------------------
// El buscador de tierras del paso (rediseño de la ronda 82)
//
// David tiene 51 tierras: sin buscador, apuntar dónde ha echado el producto es recorrer cincuenta y una
// tarjetas con el pulgar. El diseño lo pide («Buscar entre tus fincas», `mis_tierras.png`) y aquí se
// comprueba el cableado: que lo escrito se lee **por el `id` del campo**, que la lista se filtra, que lo
// escrito no se borra al volver a pintar y que de un filtro se puede salir. La búsqueda en sí (las
// tildes, el pueblo, los trozos del SIGPAC) se prueba en `nucleo.test.js`, que es donde vive.
// ---------------------------------------------------------------------------

/** Las tierras que el paso está enseñando ahora mismo, ya preparadas. */
function tierrasDelPaso() {
  const lista = piezaDelPaso("ListaParaElegir");
  const bloque = lista.props.bloques[0];
  return bloque ? bloque.botones : [];
}

/** Tres tierras con nombre, pueblo y número del SIGPAC, para poder buscar entre ellas. */
const TRES_TIERRAS = [
  {
    id: 1,
    alias: "El Prado",
    superficie_ha: 4.9,
    sistema: "secano",
    municipio: "Calvarrasa de Arriba",
    ref_sigpac: "37-70-0-0-503-51-1",
  },
  {
    id: 2,
    alias: "Las Suertes de Arriba",
    superficie_ha: 3.2,
    sistema: "secano",
    municipio: "Peñaranda de Bracamonte",
    ref_sigpac: "37-70-0-0-112-4-2",
  },
  {
    id: 3,
    alias: "El Vallejo Llano",
    superficie_ha: 6.1,
    sistema: "regadío",
    municipio: "Macotera",
    ref_sigpac: "37-70-0-0-88-9-1",
  },
];

test("el buscador de tierras filtra la lista, y se puede volver a verlas todas", async () => {
  const { entorno } = await cargarAplicacion({
    "/api/productos": UN_PRODUCTO,
    "/api/parcelas": TRES_TIERRAS,
  });
  await pulsar(entorno, "inicio", { ir: "echar_producto" });
  assert.equal(tierrasDelPaso().length, 3, "antes de buscar no salen las tres tierras");

  escribir(entorno, "buscar_tierra", "prado");
  await pulsar(entorno, "buscar-tierra");
  assert.deepEqual(
    tierrasDelPaso().map((tierra) => tierra.etiqueta),
    ["El Prado"],
    "la búsqueda no ha filtrado la lista",
  );
  // **Lo escrito no se puede borrar al buscar**: la pantalla se vuelve a montar entera, así que el texto
  // tiene que volver al campo. Si no, el agricultor escribe, busca y se queda sin saber qué buscó.
  assert.equal(piezaDelPaso("Campo").props.valor, "prado", "el buscador ha perdido lo escrito");
  // Y con una búsqueda puesta, el botón de verlas todas está a mano.
  assert.ok(
    piezaDelPaso("Campo").props.botones.some((boton) => boton.accion === "buscar-tierra-limpiar"),
    "con una búsqueda puesta no hay forma de volver a verlas todas",
  );

  await pulsar(entorno, "buscar-tierra-limpiar");
  assert.equal(tierrasDelPaso().length, 3, "«VERLAS TODAS» no devuelve la lista entera");
  assert.equal(piezaDelPaso("Campo").props.valor, "", "al limpiar sigue escrito lo de antes");
});

test("si el buscador no encuentra nada, se dice y se puede volver a la lista entera", async () => {
  // Una lista vacía sin salida deja al agricultor creyendo que ha perdido sus tierras.
  const { entorno } = await cargarAplicacion({
    "/api/productos": UN_PRODUCTO,
    "/api/parcelas": TRES_TIERRAS,
  });
  await pulsar(entorno, "inicio", { ir: "echar_producto" });
  escribir(entorno, "buscar_tierra", "cebada");
  await pulsar(entorno, "buscar-tierra");

  const lista = piezaDelPaso("ListaParaElegir");
  // Los bloques no llegan (`undefined` en las propiedades): lo que se le pide es el aviso, y con el aviso
  // la pieza no pinta ninguna lista (ver `ListaParaElegir`).
  assert.equal((lista.props.bloques || []).length, 0, "sigue enseñando tierras que no casan");
  assert.ok(lista.props.aviso, "no dice que no ha encontrado nada");
  assert.match(lista.props.aviso.texto, /no encuentro ninguna tierra/, `dice: ${lista.props.aviso.texto}`);
  assert.equal(
    lista.props.aviso.boton.accion,
    "buscar-tierra-limpiar",
    "el aviso no lleva el botón que lo arregla",
  );

  await pulsar(entorno, "buscar-tierra-limpiar");
  assert.equal(tierrasDelPaso().length, 3, "el botón del aviso no devuelve la lista entera");
});

test("el buscador se vacía al empezar un apunte nuevo", async () => {
  // Un filtro que sobrevive sin que se vea es la forma más fácil de que alguien crea que ha perdido sus
  // tierras: se busca en un apunte, se sale, y en el siguiente solo sale una.
  const { entorno } = await cargarAplicacion({
    "/api/productos": UN_PRODUCTO,
    "/api/parcelas": TRES_TIERRAS,
  });
  await pulsar(entorno, "inicio", { ir: "echar_producto" });
  escribir(entorno, "buscar_tierra", "prado");
  await pulsar(entorno, "buscar-tierra");
  assert.equal(tierrasDelPaso().length, 1);

  await pulsar(entorno, "ir-inicio");
  await pulsar(entorno, "inicio", { ir: "echar_producto" });
  assert.equal(tierrasDelPaso().length, 3, "el apunte nuevo empieza con la búsqueda del anterior puesta");
  assert.equal(piezaDelPaso("Campo").props.valor, "", "el campo sale con lo que se buscó antes");
});

// ---------------------------------------------------------------------------
// El envoltorio del asistente se pasó a React en la ronda 72
//
// El asistente era lo último que se pintaba con `innerHTML`: las barras de progreso, la pregunta, la pista,
// el aviso de error, el hueco del formulario y los botones. Ahora eso es `PantallaAsistente`, y lo que se
// comprueba aquí es **el cableado**: que el paso se le pide a React con su pregunta, su sitio, sus botones
// y su error. El dibujo (las barras, el orden, las clases) está en `tests_js/react.test.js`, contra el
// componente.
// ---------------------------------------------------------------------------

test("el asistente se le pide a React con la pregunta, el formulario y sus botones", async () => {
  const { entorno } = await cargarAplicacion({ "/api/productos": UN_PRODUCTO });
  await pulsar(entorno, "inicio", { ir: "echar_producto" });

  const elemento = montajes[montajes.length - 1].elemento;
  assert.equal(elemento.type.name, "PantallaAsistente");
  assert.equal(elemento.props.titulo, "¿Dónde?", "no le llega la pregunta del paso");
  assert.ok(elemento.props.pista, "no le llega la explicación del paso");
  // El formulario del paso son **dos piezas** desde la ronda 82: el buscador de tierras y la lista de
  // tierras. Antes era una sola (`ListaParaElegir`), y por eso este paso se comprobaba sin buscador.
  assert.equal(piezaDelPaso("ListaParaElegir").type.name, "ListaParaElegir", "no le llega la lista");
  const buscador = piezaDelPaso("Campo");
  assert.equal(buscador.props.id, "buscar_tierra", "el buscador no lleva su campo con su `id`");
  assert.ok(buscador.props.etiqueta, "el buscador no lleva su etiqueta del servidor");
  assert.ok(
    buscador.props.botones.some((boton) => boton.accion === "buscar-tierra"),
    `el buscador no tiene su botón de buscar: ${JSON.stringify(buscador.props.botones)}`,
  );
  assert.equal(elemento.props.error, "", "el primer paso sale con un error");
  assert.equal(elemento.props.indice, 0);
  assert.ok(elemento.props.total > 1, `el paso no sabe cuántos hay: ${elemento.props.total}`);
  // En el primer paso solo hay SEGUIR: no se puede volver atrás ni saltar (no es opcional).
  assert.deepEqual(
    elemento.props.botones.map((boton) => [boton.accion, boton.etiqueta]),
    [["asistente-seguir", "SEGUIR"]],
  );
  assert.equal(elemento.props.botones[0].principal, true, "SEGUIR no es el botón principal");
  // Y el contenedor se queda vacío: lo pinta React entero.
  assert.equal(pantallaDe(entorno), "");
});

test("en un paso opcional sale DEJARLO, y en el resumen el botón dice APUNTARLO", async () => {
  // Los dos botones que cambian según el paso: el de saltar (solo en los opcionales) y el de apuntar
  // (solo en el último, que es el resumen). Si se equivocaran, el agricultor no podría saltarse lo que no
  // sabe o no podría acabar el apunte.
  const { entorno } = await cargarAplicacion({ "/api/productos": UN_PRODUCTO });
  await pulsar(entorno, "inicio", { ir: "echar_producto" });

  // Se contesta lo obligatorio para poder llegar a las observaciones, que son **opcionales**: es el paso
  // donde tiene que salir DEJARLO.
  await pulsar(entorno, "elegir", { campo: "parcela_id", valor: "1", superficie: "2.43" });
  await pulsar(entorno, "asistente-seguir"); // la fecha
  await pulsar(entorno, "asistente-seguir"); // las hectáreas
  await pulsar(entorno, "elegir", {
    campo: "justificacion",
    valor: "Vi la plaga o la hierba en el campo",
  });
  await pulsar(entorno, "elegir", { campo: "producto_id", valor: "5" });
  await pulsar(entorno, "asistente-seguir"); // la dosis
  await pulsar(entorno, "asistente-saltar"); // quién y con qué máquina
  await pulsar(entorno, "asistente-saltar"); // las medidas preventivas

  const opcional = montajes[montajes.length - 1].elemento;
  assert.equal(opcional.type.name, "PantallaAsistente");
  assert.equal(opcional.props.titulo, "¿Quieres apuntar algo más?", "no es el paso de las observaciones");
  const acciones = opcional.props.botones.map((boton) => boton.accion);
  assert.ok(acciones.includes("asistente-saltar"), `no se puede saltar: ${acciones.join(", ")}`);
  assert.ok(acciones.includes("asistente-atras"), "no se puede volver atrás en mitad del apunte");

  // Y en el último paso (el resumen) el botón de seguir dice APUNTARLO.
  await pulsar(entorno, "asistente-saltar"); // las observaciones
  await pulsar(entorno, "asistente-saltar"); // cómo se echó
  const resumen = montajes[montajes.length - 1].elemento;
  assert.equal(resumen.type.name, "PantallaAsistente");
  assert.equal(resumen.props.indice, resumen.props.total - 1, "no es el último paso");
  const seguir = resumen.props.botones.find((boton) => boton.accion === "asistente-seguir");
  assert.equal(seguir.etiqueta, "APUNTARLO", "el último paso no invita a apuntar");
  assert.equal(seguir.principal, true);
});

test("cuando el paso no deja seguir, el motivo se le pasa a React", async () => {
  // El motivo lo dice `recoger()` del paso, y tiene que llegar a la pantalla: es lo que sale en rojo
  // debajo de la pregunta. Antes se pintaba con `innerHTML` y ahora viaja como propiedad.
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "ventas-nueva");
  await pulsar(entorno, "elegir", { campo: "tipo", valor: "comercializada" });
  // Se pulsa SEGUIR sin decir qué se ha vendido: el paso no puede pasar.
  await pulsar(entorno, "asistente-seguir");
  assert.ok(errorDelAsistente(), "el paso no ha dicho qué falta");
  assert.ok(
    pantallaPedida(entorno).includes("¿Qué has vendido?"),
    "el asistente se ha ido del paso en vez de avisar",
  );

  // Y al contestarlo, el aviso desaparece.
  escribir(entorno, "producto", "Lechuga romana");
  await pulsar(entorno, "asistente-seguir");
  assert.equal(errorDelAsistente(), "", "sigue el aviso después de contestar");
});

test("la pregunta del abono se le pide a React, con la riqueza de cada uno", async () => {
  // El paso del abono era el único de esta clase que no tenía prueba: se pintaba a mano en medio de la
  // lista de pasos de la fertilización, y al pasarlo a la pieza se le pone la que le faltaba.
  const { entorno } = await cargarAplicacion({
    "/api/fertilizantes": [
      { id: 3, nombre: "Nitrato amónico 33,5", riqueza_n: 33.5, riqueza_p: 0, riqueza_k: 0 },
    ],
  });
  await pulsar(entorno, "inicio", { ir: "abonar" });
  await pulsar(entorno, "elegir", { campo: "parcela_id", valor: "1", superficie: "2.43" });
  await pulsar(entorno, "asistente-seguir"); // la fecha

  const abonos = botonesDeLaLista();
  assert.ok(abonos.length, "no le llega ningún abono");
  assert.equal(abonos[0].etiqueta, "Nitrato amónico 33,5", "el abono no lleva su nombre");
  assert.equal(abonos[0].accion, "elegir", "el abono no lleva la acción de elegir");
  assert.equal(abonos[0].datos.campo, "fertilizante_id", "el abono no dice a qué campo contesta");
  // La riqueza (nitrógeno-fósforo-potasio) es lo que distingue un abono de otro de un vistazo.
  assert.match(
    abonos[0].pista,
    /\d+-\d+-\d+/,
    `el abono no lleva su riqueza: ${abonos[0].pista}`,
  );
});

test("sin abonos dados de alta, el asistente ofrece añadir uno", async () => {
  const { entorno } = await cargarAplicacion({ "/api/fertilizantes": [] });
  await pulsar(entorno, "inicio", { ir: "abonar" });
  await pulsar(entorno, "elegir", { campo: "parcela_id", valor: "1", superficie: "2.43" });
  await pulsar(entorno, "asistente-seguir"); // la fecha

  const aviso = avisoDeLaLista();
  assert.ok(aviso.includes("Todavía no has apuntado ningún abono"), `no explica qué pasa: ${aviso}`);
  assert.ok(aviso.includes("AÑADIR UN ABONO"), `explica qué pasa pero no deja arreglarlo: ${aviso}`);
});

/**
 * El campo que el asistente ha pedido a React, tal y como se le ha pedido.
 *
 * Como el resumen y la lista, el campo ya no es HTML: es una **pieza** (`react/piezas/campo.js`) que se
 * monta en el hueco del formulario. Lo que hay que mirar es lo que se le pide. Devuelve las propiedades
 * del componente `Campo`.
 */
function campoPedido() {
  const campo = piezasPedidas().find((uno) => uno && uno.type && uno.type.name === "Campo");
  assert.ok(
    campo,
    `el último montaje no trae un campo: ${piezasPedidas().map((uno) => uno && uno.type && uno.type.name).join(", ")}`,
  );
  return campo.props;
}

/**
 * La fecha en corto, como la escribe la aplicación: de `2026-04-10` a `10/04/2026`.
 *
 * Se escribe aquí, en la prueba, en vez de llamar a la función de `app.js`: es lo que se lee en la
 * etiqueta del campo, y si la aplicación la escribiera de otra forma esto tiene que notarlo.
 */
function fechaEnCorto(iso) {
  const [ano, mes, dia] = iso.split("-");
  return `${dia}/${mes}/${ano}`;
}

/**
 * Los bloques del maestro que se le han pedido a React (la pieza `CamposDelMaestro`).
 *
 * Los datos de una ficha (un producto, una máquina, un asesor) y los números de un plan se piden con
 * esta pieza. Lo que hay que mirar es **lo que se le pide**: el `id` de cada campo de escribir (es lo
 * único que tiene `app.js` para leerlo) y las opciones de cada bloque de elegir.
 */
function bloquesDelMaestroPedidos() {
  const grupo = piezasPedidas().find((uno) => uno && uno.type && uno.type.name === "CamposDelMaestro");
  assert.ok(
    grupo,
    `el último montaje no trae un grupo de campos: ${piezasPedidas().map((uno) => uno && uno.type && uno.type.name).join(", ")}`,
  );
  return grupo.props.bloques;
}

/** Los `id` de los campos de escribir de un grupo de bloques (lo que `app.js` lee). */
function idsDeLosBloques(bloques = bloquesDelMaestroPedidos()) {
  return bloques.filter((bloque) => bloque.tipo !== "opciones").map((bloque) => bloque.id);
}

/** Las etiquetas que se ven en un grupo de bloques: la pregunta y la pista de cada uno, y sus opciones. */
function textosDeLosBloques(bloques = bloquesDelMaestroPedidos()) {
  return bloques
    .flatMap((bloque) => [
      bloque.etiqueta,
      bloque.pista,
      ...(bloque.opciones || []).map((opcion) => opcion.etiqueta),
    ])
    .filter(Boolean)
    .join(" | ");
}

/**
 * Las opciones de un bloque de elegir, buscándolo por el campo al que contesta.
 *
 * Se busca por el campo y no por su posición a propósito: si un día se cambia el orden de los datos de
 * la ficha, una prueba que mirara «el bloque segundo» seguiría pasando y estaría comprobando otra cosa.
 */
function opcionesDelBloque(campo, bloques = bloquesDelMaestroPedidos()) {
  const bloque = bloques.find((uno) => uno.tipo === "opciones" && uno.campo === campo);
  assert.ok(
    bloque,
    `no se le ha pedido a React ningún bloque de elegir para «${campo}»: se ha pedido ` +
      bloques.map((uno) => uno.campo || uno.id).join(", "),
  );
  return bloque.opciones.map((opcion) => opcion.etiqueta);
}

test("la pregunta de la fecha se le pide a React, con su día por defecto y sus atajos", async () => {
  // El paso de la fecha es el que más se ve en todo el programa: apuntar lo de hoy son dos toques, y
  // eso depende de que el campo venga **con la fecha de hoy puesta** y de los dos atajos de debajo.
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "inicio", { ir: "echar_producto" });
  // Se elige la primera tierra y **ya se está en la fecha** (el paso de la nave se salta solo cuando lo
  // que se apunta es en la tierra): lo que se mira es el campo que se le pide para ese paso.
  await pulsar(entorno, "elegir", { campo: "parcela_id", valor: "1", superficie: "2.43" });

  const fecha = campoPedido();
  assert.equal(fecha.id, "fecha", "el campo no lleva el id de siempre: app.js no podría leerlo");
  assert.equal(fecha.tipo, "fecha");
  assert.match(fecha.valor, /^\d{4}-\d{2}-\d{2}$/, `la fecha no viene puesta: ${fecha.valor}`);
  // La etiqueta la compone `app.js` con la fecha: no puede venir escrita del componente.
  assert.ok(
    fecha.etiqueta.includes(fechaEnCorto(fecha.valor)),
    `la etiqueta no lleva la fecha puesta: ${fecha.etiqueta}`,
  );

  // Los dos atajos, con el campo dentro: un análisis tiene DOS fechas y «HOY» tiene que saber cuál es.
  const atajos = fecha.botones.map((boton) => boton.accion);
  assert.deepEqual(atajos, ["fecha-rapida", "fecha-rapida"], `los atajos no son los de siempre: ${atajos}`);
  assert.equal(fecha.botones[0].datos.campo, "fecha");
  assert.match(fecha.botones[0].datos.valor, /^\d{4}-\d{2}-\d{2}$/);
  assert.notEqual(
    fecha.botones[0].datos.valor,
    fecha.botones[1].datos.valor,
    "«HOY» y «AYER» llevan la misma fecha",
  );
});

test("la pregunta de las hectáreas se le pide a React, con su id y su unidad", async () => {
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "inicio", { ir: "echar_producto" });
  await pulsar(entorno, "elegir", { campo: "parcela_id", valor: "1", superficie: "2.43" });
  await pulsar(entorno, "asistente-seguir"); // de la fecha a las hectáreas

  const superficie = campoPedido();
  assert.equal(superficie.id, "superficie_tratada_ha", "el id del campo ha cambiado");
  assert.equal(superficie.tipo, "numero", "las hectáreas no piden el teclado de números");
  // El id no es decoración: es lo único que tiene `app.js` para leer lo escrito.
  assert.equal(superficie.valor, "2.43", "las hectáreas no vienen puestas con lo que tiene la tierra");
  // Y la pregunta es la del servidor, no una escrita en el componente.
  assert.equal(superficie.etiqueta, "¿Cuántas hectáreas has tratado?");
  // El sufijo (la unidad) también viene del servidor: en esta copia de los textos está vacío, y lo que
  // se comprueba es que el campo **acepte** el sufijo para que quepa el que mande el servidor.
  assert.equal(typeof superficie.sufijo, "string");
  // Y la ayuda, con sus cuatro rótulos del servidor, viaja con el campo.
  assert.ok(superficie.ayuda && superficie.ayuda.datos, "el campo se pide sin su ayuda");
  assert.ok(superficie.ayuda.rotulos.que_es, "la ayuda se pide sin sus rótulos");
});

test("la pregunta del motivo se le pide a React, con su ayuda", async () => {
  // «¿Por qué lo has echado?» es la pregunta que sostiene el cuaderno entero (y la que pide la norma):
  // se contesta eligiendo de una lista y lleva su explicación debajo.
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "inicio", { ir: "echar_producto" });
  await pulsar(entorno, "elegir", { campo: "parcela_id", valor: "1", superficie: "2.43" });
  await pulsar(entorno, "asistente-seguir"); // la fecha
  await pulsar(entorno, "asistente-seguir"); // las hectáreas

  const motivos = botonesDeLaLista();
  assert.ok(motivos.length, "no le llega ningún motivo");
  assert.equal(motivos[0].accion, "elegir");
  assert.equal(motivos[0].datos.campo, "justificacion", "el motivo no dice a qué campo contesta");
  assert.ok(
    motivos[0].datos.valor,
    "el motivo no lleva su valor: es lo que se guarda, no lo que se lee",
  );
  const props = listaPedida();
  assert.ok(props.ayuda && props.ayuda.datos, "el motivo se pide sin su ayuda");
  assert.ok(props.ayuda.rotulos.que_es, "la ayuda se pide sin sus rótulos");
});

test("un grupo de parcelas se ofrece al apuntar, y pone la superficie de todas", async () => {
  // **Esto es nuevo de la ronda 17.** `GrupoParcelas` (la «unidad homogénea de cultivo» de la app
  // oficial) tenía tres endpoints y **ninguna pantalla los llamaba**: `grupo_id` no aparecía ni
  // una vez en el JavaScript. Y lo que ahorra es lo que dice el documento oficial: con seis
  // parcelas de cebada, un tratamiento es **un apunte**, no seis.
  const { entorno } = await cargarAplicacion({ "/api/productos": UN_PRODUCTO });
  await pulsar(entorno, "inicio", { ir: "echar_producto" });
  // La pregunta de dónde se ha echado es una **pieza** de React desde la ronda 62: lo que se mira es
  // lo que se le ha pedido a la pieza, no el HTML del contenedor.
  const lista = textoDeLaLista();
  assert.ok(lista.includes("En varias parcelas a la vez"), `no ofrece los grupos: ${lista}`);
  assert.ok(lista.includes("Cebada (3 parcelas)"), "no lista el grupo");

  await pulsar(entorno, "elegir", { campo: "grupo_id", valor: "1", superficie: "10" });
  // **Y no puede salir el aviso de que falta la tierra.** Al elegir el grupo se borra la parcela (un
  // apunte es de una o del otro), y el paso seguía exigiendo la parcela: el agricultor se quedaba
  // encerrado con un aviso de que le faltaba justo lo que acababa de sustituir. Lo tapaba esta misma
  // prueba, que leía el «10,00 ha» del botón del grupo y creía estar leyendo el resumen (ver
  // `exigeSitio` en `app.js`).
  assert.equal(
    errorDelAsistente(),
    "",
    "al elegir el grupo dice que le falta la tierra",
  );
  // Hasta el resumen, contestando lo que hace falta: es donde el agricultor ve la superficie que se va
  // a apuntar. Se contesta lo obligatorio y se saltan los pasos opcionales.
  await pulsar(entorno, "asistente-seguir"); // la fecha
  await pulsar(entorno, "asistente-seguir"); // la superficie
  await pulsar(entorno, "elegir", {
    campo: "justificacion",
    valor: "Vi la plaga o la hierba en el campo",
  });
  await pulsar(entorno, "elegir", { campo: "producto_id", valor: "5" });
  await pulsar(entorno, "asistente-seguir"); // la dosis
  await pulsar(entorno, "asistente-saltar"); // quién y con qué máquina
  await pulsar(entorno, "asistente-saltar"); // las medidas preventivas
  await pulsar(entorno, "asistente-saltar"); // las observaciones
  await pulsar(entorno, "asistente-saltar"); // cómo se echó
  const resumen = resumenPedido();
  // La superficie es la de todas las parcelas del grupo (2 + 3 + 5), no la de una.
  assert.ok(resumen.includes("10,00"), `no pone la superficie del grupo: ${resumen}`);
});

test("elegir una parcela quita el grupo, y al revés", async () => {
  // Un apunte es de una parcela o de un grupo, nunca de los dos: mandar los dos dejaría el
  // cuaderno sin saber de qué tierra se está hablando.
  //
  // **Ojo con cómo se comprueba.** Antes esto contaba los `boton-elegido` del HTML del contenedor, y
  // al pasar la lista a React esa cuenta se quedó en cero y la prueba **pasaba sin comprobar nada**
  // (el DOM de mentira no monta React). Ahora se mira lo que se le pide a la pieza: qué botones van
  // marcados y de qué campo. Se vuelve atrás (`asistente-atras`) para que la lista se vuelva a pedir,
  // que es lo que hace el agricultor cuando se equivoca.
  const { entorno } = await cargarAplicacion({ "/api/productos": UN_PRODUCTO });
  await pulsar(entorno, "inicio", { ir: "echar_producto" });
  await pulsar(entorno, "elegir", { campo: "grupo_id", valor: "1", superficie: "10" });
  await pulsar(entorno, "asistente-atras");
  let marcados = botonesMarcados();
  assert.equal(marcados.length, 1, `el grupo no queda marcado (${marcados.length} marcados)`);
  assert.equal(marcados[0].datos.campo, "grupo_id", "el que queda marcado no es el grupo");

  await pulsar(entorno, "elegir", { campo: "parcela_id", valor: "1", superficie: "2.43" });
  await pulsar(entorno, "asistente-atras");
  marcados = botonesMarcados();
  assert.equal(
    marcados.length,
    1,
    `elegir la parcela no ha quitado el grupo (${marcados.length} marcados)`,
  );
  assert.equal(marcados[0].datos.campo, "parcela_id", "el que queda marcado no es la parcela");
});

// ---------------------------------------------------------------------------
// Los grupos de parcelas se pasaron a React en la ronda 44
//
// Aquí se comprueba el cableado: que la pantalla se le pide a React con los grupos **ya preparados**
// (su nombre, sus cuentas y los nombres de sus parcelas). Lo que se ve dentro está en
// `tests_js/react.test.js`, contra el componente.
// ---------------------------------------------------------------------------

test("la pantalla de los grupos se le pide a React, con los grupos preparados", async () => {
  const { entorno } = await cargarAplicacion();
  const antes = montajes.length;
  await pulsar(entorno, "grupo-ver");
  const pedidos = montajes.slice(antes);

  assert.equal(pedidos.length, 1, `se han pedido ${pedidos.length} montajes: solo los grupos`);
  const elemento = pedidos[0].elemento;
  assert.ok(elemento, "no se le pide nada a React: la pantalla se está pintando a mano otra vez");
  assert.equal(elemento.type.name, "PantallaGrupos");

  const grupos = elemento.props.grupos;
  assert.ok(grupos.length, "no le llega ningún grupo");
  const grupo = grupos[0];
  assert.ok(grupo.nombre, "el grupo no lleva su nombre");
  assert.ok(grupo.detalle.includes("ha"), `el detalle no lleva la superficie: ${grupo.detalle}`);
  assert.ok(grupo.parcelas, "el grupo no lleva los nombres de sus parcelas");
  assert.equal(typeof elemento.props.faltanCultivos, "number", "no le llega cuántas tierras faltan");
});

test("la ficha del producto pregunta si está autorizado y si vale para ecológico", async () => {
  // **Esto es nuevo de la ronda 19, y cierra tres comprobaciones de golpe.** El programa ya tenía
  // escrito y probado que un producto retirado no se puede usar, que uno que no vale para
  // ecológico no se puede echar en una finca ecológica, y que una autorización excepcional
  // caducada bloquea. Las tres dependían de datos que **no se podían meter desde ninguna
  // pantalla**, así que no podían saltar nunca: el programa decía «adelante» en los tres casos.
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "mis-cosas");
  await pulsar(entorno, "anadir-maestro", { tipo: "producto" });
  escribir(entorno, "nombre_comercial", "Ejemplo 25 EC");
  await pulsar(entorno, "asistente-seguir"); // el nombre
  escribir(entorno, "numero_registro", "24.123");
  await pulsar(entorno, "asistente-seguir"); // el número de registro
  escribir(entorno, "dosis_maxima", "0,8");
  await pulsar(entorno, "asistente-seguir"); // la dosis máxima
  await pulsar(entorno, "elegir", { campo: "unidad_dosis", valor: "L/ha" }); // la unidad
  escribir(entorno, "plazo_seguridad_dias", "21");
  await pulsar(entorno, "asistente-seguir"); // los días de espera
  await pulsar(entorno, "asistente-saltar"); // los datos de la etiqueta
  await pulsar(entorno, "asistente-saltar"); // cuánto se compró
  // La autorización del producto se pide con la misma pieza que el resto de los datos de la ficha: los
  // dos «sí o no» son bloques de elegir y los dos campos con fecha son de escribir.
  const bloques = bloquesDelMaestroPedidos();
  assert.ok(
    bloques.some((uno) => uno.tipo === "opciones" && uno.campo === "autorizado"),
    `no pregunta si está autorizado: ${bloques.map((uno) => uno.campo || uno.id).join(", ")}`,
  );
  assert.ok(
    opcionesDelBloque("permitido_ecologico").length === 3,
    "no pregunta lo de ecológico con sus tres respuestas (sí, no y no lo sé)",
  );
  // **Tres respuestas, no dos** (02/10/2026). Con un «sí o no» a secas, dejar el bloque plegado
  // —que pone «opcional» y es lo que hace todo el mundo— dejaba el producto como autorizado y como
  // permitido en ecológico sin que nadie lo hubiera dicho: es el defecto A1 de
  // `docs/T02_VALORES_POR_DEFECTO.md`, y hacía que las dos comprobaciones de esta ficha **no
  // pudieran saltar nunca**. La tercera respuesta es «No lo sé», y el servidor la guarda como
  // «no comprobado» en vez de dar permiso.
  assert.ok(
    opcionesDelBloque("permitido_ecologico").includes("No lo sé"),
    `falta la respuesta «No lo sé»: ${opcionesDelBloque("permitido_ecologico").join(", ")}`,
  );
  const ids = idsDeLosBloques(bloques);
  assert.ok(ids.includes("autorizacion_excepcional"), "no pregunta el permiso especial");
  assert.ok(ids.includes("autorizacion_hasta"), "no pregunta hasta cuándo vale el permiso");
});

test("la ficha del aplicador pregunta el tipo de carné", async () => {
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "mis-cosas");
  await pulsar(entorno, "anadir-maestro", { tipo: "aplicador" });
  escribir(entorno, "nombre", "David Pérez");
  await pulsar(entorno, "asistente-seguir"); // el nombre
  await pulsar(entorno, "elegir", { campo: "es_empresa", valor: "bool:false" });
  escribir(entorno, "numero_carne", "C-123456");
  // Se avanza **hasta encontrar la pregunta**, en vez de contar pulsaciones: al cambiar los pasos del
  // asistente el test se rompía sin que la aplicación estuviera mal (es lo que explica `avanzarHasta`).
  await avanzarHasta(entorno, "¿Qué carné tiene?");
  // El tipo de carné es una **lista cerrada**, no una casilla de texto: son los cuatro que distingue
  // el cuaderno de la Junta en su hoja 1.2, y así la cruz se pone siempre en la columna que toca.
  // (Uno de ellos se llama «Piloto (tratamientos aéreos)» entero, así que se busca dentro del texto.)
  const carnets = opcionesDelBloque("tipo_carne").join(" | ");
  for (const nombre of ["Básico", "Cualificado", "Fumigador", "Piloto"]) {
    assert.ok(carnets.includes(nombre), `no ofrece el carné ${nombre}: ${carnets}`);
  }
  assert.ok(
    idsDeLosBloques().includes("numero_reganip"),
    "no pregunta el número de registro de equipos",
  );
});

// ---------------------------------------------------------------------------
// «Mis cosas» se pasó a React en la ronda 32
//
// Lo que comprobaban estas pruebas —las siete secciones, sus botones de añadir, lo que ya hay
// dado de alta, el número de asesor y **el dibujo de la parcela**— **se ha movido** a
// `tests_js/react.test.js`, reescrito contra el componente. Aquí se puede leer su HTML tan poco
// como el de la pantalla de inicio (el DOM de mentira no monta React), así que lo que queda aquí
// es lo que solo se ve desde `app.js`: que la pantalla **se le pide a React** con los datos que
// tiene la aplicación, ya preparados (secciones, textos y atajos).
// ---------------------------------------------------------------------------

test("mis cosas se le pide a React, con las secciones ya preparadas", async () => {
  const { entorno } = await cargarAplicacion();
  const antes = montajes.length;
  await pulsar(entorno, "mis-cosas");
  const pedidos = montajes.slice(antes);

  assert.equal(pedidos.length, 1, `se han pedido ${pedidos.length} montajes: solo «mis cosas»`);
  assert.equal(pedidos[0].contenedor, entorno.nodos.get("pantalla"), "no se monta en la pantalla");

  const elemento = pedidos[0].elemento;
  assert.ok(elemento, "no se le pide nada a React: «mis cosas» se está pintando a mano otra vez");
  assert.equal(elemento.type.name, "PantallaMisCosas");

  // Las siete secciones, con su texto del servidor y sus elementos ya preparados.
  const tipos = elemento.props.secciones.map((seccion) => seccion.tipo);
  assert.deepEqual(tipos, [
    "parcela",
    "producto",
    "abono",
    "aplicador",
    "asesor",
    "equipo",
    "instalacion",
  ]);
  // La sección de las tierras ya no es una lista de renglones: son tarjetas (ver el test de aquí abajo).
  const parcelas = elemento.props.secciones[0];
  assert.equal(parcelas.titulo, "Parcelas");
  assert.equal(parcelas.anadir, "AÑADIR UNA PARCELA");
  assert.equal(parcelas.elementos[0].etiqueta, "El Prado");
  assert.ok(parcelas.elementos[0].lineas[0].includes("hectáreas"), "la parcela no lleva su superficie");

  // Y los cuatro atajos de abajo, con su acción.
  assert.deepEqual(
    elemento.props.atajos.map((atajo) => atajo.accion),
    ["papel-ver-todos", "cesta-ver", "cultivo-ver-todos", "grupo-ver"],
  );

  // Nada se ha pintado además con `pintar()`, que es lo que se hacía antes de esto.
  assert.equal(entorno.nodos.get("pantalla").innerHTML, "");
});

// ---------------------------------------------------------------------------
// Las tierras de «mis cosas» van como TARJETAS desde la ronda 78
//
// La sección era un muro de renglones iguales —«El Prado · 2,43 ha · secano»— y con 51 tierras no había
// forma de distinguir una de otra, ni nada que hacer con ellas desde esa pantalla. Ahora cada tierra
// llega como tarjeta: con la forma que tiene en el SIGPAC, su pueblo, sus datos con el nombre delante
// («una referencia del SIGPAC suelta no dice qué es») y **lo que le falta a esa tierra con el camino para
// arreglarlo dentro de la misma tarjeta**.
//
// Se comprueba aquí el cableado —qué le llega a React desde `app.js`—, que es lo que solo se puede ver
// desde este lado. El dibujo de la tarjeta está en `tests_js/react.test.js`, contra la pieza.
// ---------------------------------------------------------------------------

test("las tierras de «mis cosas» llegan como tarjetas, con lo que le falta a cada una", async () => {
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "mis-cosas");
  const seccion = montajes[montajes.length - 1].elemento.props.secciones[0];

  assert.equal(seccion.tarjetas, true, "las tierras de «mis cosas» siguen siendo una lista de renglones");
  // La frase se elige por el número de tierras que hay (singular o plural). Con dos tierras en la finca de
  // la prueba, la frase es la del plural: es lo que evita que salga «Tienes 1 tierras apuntadas», que fue
  // un fallo de verdad (ronda 84).
  assert.match(seccion.cuantas, /2 tierras apuntadas/, `no dice cuántas tierras hay: «${seccion.cuantas}»`);

  const tierra = seccion.elementos[0];
  assert.equal(tierra.etiqueta, "El Prado", "la tarjeta no lleva el nombre de la tierra");
  assert.equal(tierra.rotulo, "Tierra n.º 1", `la tarjeta no lleva su número: «${tierra.rotulo}»`);

  // Los datos, con su nombre delante: el pueblo y la referencia oficial del SIGPAC.
  const etiquetas = tierra.filas.map((fila) => fila.etiqueta);
  assert.ok(etiquetas.includes("Referencia oficial SIGPAC"), `sin la referencia: ${etiquetas.join(", ")}`);
  const referencia = tierra.filas.find((fila) => fila.etiqueta === "Referencia oficial SIGPAC");
  assert.equal(referencia.valor, "37-70-0-0-503-51-1", "la referencia no es la de esa tierra");
  assert.ok(
    tierra.lineas.includes("Calvarrasa de Arriba"),
    `la tarjeta no dice en qué pueblo está: ${JSON.stringify(tierra.lineas)}`,
  );

  // A esta tierra le falta decir qué tiene sembrado este año (`falta_decirlo` lo calcula el servidor).
  // **La tarjeta ya no abre «lo que hay sembrado»: abre la ficha de la tierra** (07/10/2026). Antes la
  // misma tierra llevaba a dos pantallas distintas según el aparato —en el móvil al cultivo y en el
  // ordenador al panel con su historia—, que es lo contrario de la ficha única que pide el encargo; y el
  // cultivo ya se ve dentro de la ficha («Qué hay hoy»), así que no se pierde nada de lo que se miraba.
  // El aviso de lo que le falta sigue saliendo **en ámbar, dentro de la tarjeta**.
  assert.equal(tierra.pendiente, "Le falta decir qué tiene sembrado este año");
  assert.equal(tierra.accionTexto, "LO QUE HA PASADO EN ESTA TIERRA");

  // Y la tarjeta **no elige: abre** la ficha de esa tierra. Por eso no lleva el círculo de elegir (una
  // lista que no se elige no puede prometer un círculo) y sí la acción con su tierra.
  assert.equal(tierra.marca, false, "la tarjeta promete una elección que en esta pantalla no existe");
  assert.equal(tierra.accion, "tierra-historia");
  assert.equal(tierra.datos.id, 1, "la tarjeta no dice de qué tierra habla");
});

// ---------------------------------------------------------------------------
// El buscador de tierras de «mis cosas» (rediseño de la ronda 87)
//
// El diseño lo pide en esta pantalla («Buscar entre tus fincas»): con 51 tierras, mirar una concreta era
// recorrerlas todas. Se comprueba aquí el cableado —el campo, el filtro, la vuelta a la lista entera y que
// **los dos buscadores no se pisen**—, y el dibujo en `react.test.js`.
// ---------------------------------------------------------------------------

/** Las tierras que la sección de «mis cosas» está enseñando ahora mismo. */
function tierrasDeMisCosas() {
  return montajes[montajes.length - 1].elemento.props.secciones[0].elementos;
}

test("el buscador de «mis cosas» filtra las tierras, y con un número que no cambia", async () => {
  const { entorno } = await cargarAplicacion({ "/api/parcelas": TRES_TIERRAS });
  await pulsar(entorno, "mis-cosas");
  const seccion = montajes[montajes.length - 1].elemento.props.secciones[0];
  assert.ok(seccion.buscar, "la sección de las tierras no lleva buscador");
  assert.equal(
    seccion.buscar.props.id,
    "buscar_tierra_mis_cosas",
    "el buscador no lleva su campo con su `id`",
  );
  assert.equal(seccion.sinResultados, null, "avisa de que no hay resultados antes de buscar");
  assert.equal(tierrasDeMisCosas().length, 3, "antes de buscar no salen las tres tierras");

  escribir(entorno, "buscar_tierra_mis_cosas", "vallejo");
  await pulsar(entorno, "buscar-tierra-mis-cosas");
  const encontradas = tierrasDeMisCosas();
  assert.deepEqual(
    encontradas.map((tierra) => tierra.etiqueta),
    ["El Vallejo Llano"],
    "la búsqueda no ha filtrado las tierras",
  );
  // El número es el que tiene en la lista entera (es la tercera): renumerar al buscar sería mentirle.
  assert.equal(encontradas[0].rotulo, "Tierra n.º 3", `la numeración cambió: ${encontradas[0].rotulo}`);
  // Lo escrito no se pierde al volver a pintar, y se puede volver a verlas todas.
  assert.equal(
    montajes[montajes.length - 1].elemento.props.secciones[0].buscar.props.valor,
    "vallejo",
    "el buscador ha perdido lo escrito",
  );

  await pulsar(entorno, "buscar-tierra-limpiar-mis-cosas");
  assert.equal(tierrasDeMisCosas().length, 3, "«VERLAS TODAS» no devuelve la lista entera");
});

test("si el buscador de «mis cosas» no encuentra nada, lo dice y deja volver", async () => {
  // El aviso de «todavía no tienes parcelas» sería mentira aquí: las tiene. Y sin salida, un filtro del que
  // no se puede salir es una lista de tierras que ha desaparecido.
  const { entorno } = await cargarAplicacion({ "/api/parcelas": TRES_TIERRAS });
  await pulsar(entorno, "mis-cosas");
  escribir(entorno, "buscar_tierra_mis_cosas", "cebada");
  await pulsar(entorno, "buscar-tierra-mis-cosas");

  const seccion = montajes[montajes.length - 1].elemento.props.secciones[0];
  assert.equal(seccion.elementos.length, 0, "sigue enseñando tierras que no casan");
  assert.ok(seccion.sinResultados, "no dice que no ha encontrado nada");
  assert.match(seccion.sinResultados.texto, /no encuentro ninguna tierra/);
  assert.equal(seccion.sinResultados.boton.accion, "buscar-tierra-limpiar-mis-cosas");

  await pulsar(entorno, "buscar-tierra-limpiar-mis-cosas");
  assert.equal(tierrasDeMisCosas().length, 3, "el botón del aviso no devuelve la lista entera");
});

test("los dos buscadores de tierras no se pisan", async () => {
  // **Por qué son dos.** Con uno solo, buscar «prado» al apuntar un tratamiento dejaría «mis cosas»
  // enseñando una tierra de las tres, y su cuenta seguiría diciendo que hay tres: nadie lo habría pedido.
  const { entorno } = await cargarAplicacion({
    "/api/productos": UN_PRODUCTO,
    "/api/parcelas": TRES_TIERRAS,
  });
  await pulsar(entorno, "inicio", { ir: "echar_producto" });
  escribir(entorno, "buscar_tierra", "prado");
  await pulsar(entorno, "buscar-tierra");
  assert.equal(piezaDelPaso("ListaParaElegir").props.bloques[0].botones.length, 1, "el asistente no filtró");

  await pulsar(entorno, "mis-cosas");
  assert.equal(tierrasDeMisCosas().length, 3, "el filtro del asistente ha escondido tierras en «mis cosas»");
  assert.equal(
    montajes[montajes.length - 1].elemento.props.secciones[0].buscar.props.valor,
    "",
    "el buscador de «mis cosas» sale con lo que se buscó en el asistente",
  );
});

test("añadir una parcela ofrece el SIGPAC y, si se dice que no, abre el asistente", async () => {
  // **Este test cambió en la ronda 10, y por qué.** Antes `anadir-maestro` de una parcela
  // llevaba directo al asistente de siempre. Ahora pasa antes por la pantalla que ofrece
  // traerla del SIGPAC, porque con cuarenta parcelas teclear ocho datos en cada una es el
  // momento en el que más gente abandona. El asistente de siempre sigue ahí, detrás de
  // «APUNTARLA A MANO», y este test comprueba las dos cosas.
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "anadir-maestro", { tipo: "parcela" });
  assert.equal(
    confirmacionPedida().titulo,
    "Traer la parcela del SIGPAC",
    "no ofrece traerla del SIGPAC",
  );
  await pulsar(entorno, "sigpac-no");
  const html = pantallaPedida(entorno);
  assert.ok(html.includes("¿Cómo llamas tú a esa tierra?"), `no llega al asistente: ${html.slice(0, 200)}`);
  // El nombre se escribe en un campo que pinta React: lo que importa es que se le pida con su `id`,
  // que es lo único que tiene `app.js` para leer lo escrito.
  assert.ok(idsDeLosBloques().includes("alias"), "no hay dónde escribir el nombre");
});

test("el asistente de alta pregunta una cosa por pantalla", async () => {
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "anadir-maestro", { tipo: "parcela" });
  await pulsar(entorno, "sigpac-no");
  const html = pantallaPedida(entorno);
  assert.ok(!html.includes("¿Cuántas hectáreas tiene?"), "pregunta dos cosas a la vez");
});

// ---------------------------------------------------------------------------
// «Dímelo con la voz» se pasó a React
//
// Aquí había dos pruebas que miraban su HTML en el contenedor de mentira («se abre desde el
// inicio» y «sin dicción en el navegador, se puede escribir igual»). **Se han reescrito contra el
// componente**, en `tests_js/react.test.js`. Aquí queda lo que solo se ve desde `app.js`: que la
// pantalla **se le pide a React** y que lo único que sabe `window` —si este navegador trae
// reconocimiento de voz— le llega como propiedad.
// ---------------------------------------------------------------------------

test("el dictado se le pide a React, con lo que sabe el navegador", async () => {
  const { entorno } = await cargarAplicacion();
  const antes = montajes.length;
  await pulsar(entorno, "dictado");

  const pedidos = montajes.slice(antes);
  assert.equal(pedidos.length, 1, `se han pedido ${pedidos.length} montajes: solo la pantalla`);
  const elemento = pedidos[0].elemento;
  assert.ok(elemento, "no se le ha pedido nada a React: la pantalla se pinta a mano otra vez");
  assert.equal(elemento.type.name, "PantallaDictado");
  assert.equal(pedidos[0].contenedor, entorno.nodos.get("pantalla"));

  // Los textos, del servidor.
  assert.equal(elemento.props.textos.dictado.titulo, "Dímelo con la voz");
  assert.equal(elemento.props.textos.acciones.volver, "VOLVER");
  // Y el estado: lo que ya se había dictado y el error, si lo hubo.
  assert.equal(elemento.props.escrito, "");
  assert.equal(elemento.props.error, "");
  // El entorno de las pruebas no trae reconocimiento de voz, así que `puedeHablar` tiene que
  // llegar en falso: es lo que hace que salga el aviso en vez del micrófono.
  assert.equal(elemento.props.puedeHablar, false);

  // Y no se ha pintado además con `pintar()`.
  assert.equal(pantallaDe(entorno), "", "el dictado se ha pintado además con `pintar()`");
});

// ---------------------------------------------------------------------------
// El camino del dictado, de punta a punta desde `app.js`
//
// Lo que se comprueba aquí no se puede ver en un componente suelto: que el texto que se escribe en
// el campo **lo lee `app.js` por su `id`**, que se manda al servidor y que lo que contesta se
// enseña en la pantalla de revisión, que también es de React. (En un navegador de verdad esto se
// comprueba además con `scripts/comprobar_en_un_navegador.py`, que teclea en el campo de verdad.)
// ---------------------------------------------------------------------------

test("lo dictado se manda al servidor y su revisión se le pide a React", async () => {
  const { entorno, servidor } = await cargarAplicacion({
    "POST /api/borradores/desde-texto": {
      tipo: "tratamiento",
      datos: { parcela_id: 1 },
      entendido: [{ pregunta: "¿Dónde?", valor: "El Prado", campo: "parcela_id" }],
      falta: [{ pregunta: "¿Cuándo?" }],
      fuente: "reglas",
      titulo: "Lo que he entendido",
      intro: "Mira si está bien. Completa lo que falte y apúntalo.",
      falta_intro: "Para poder apuntarlo me falta esto:",
      nada_entendido: null,
    },
  });
  await pulsar(entorno, "dictado");
  // Se escribe en el campo, como lo haría el agricultor con el teclado. En el DOM de mentira no hay
  // campos de verdad, así que se le mete uno con su valor; es el mismo truco que usan las pruebas de
  // los asistentes para poder pasar de pantalla.
  escribir(entorno, "dictado-texto", "he echado glifosato en el prado");

  const antes = montajes.length;
  await pulsar(entorno, "dictado-entender");

  assert.ok(
    servidor.llamadasConMetodo.includes("POST /api/borradores/desde-texto"),
    `no se ha mandado lo dictado al servidor: ${servidor.llamadasConMetodo.join(", ")}`,
  );

  const pedidos = montajes.slice(antes);
  assert.equal(pedidos.length, 1, `se han pedido ${pedidos.length} montajes: solo la revisión`);
  const elemento = pedidos[0].elemento;
  assert.ok(elemento, "la revisión de lo dictado no se le ha pedido a React");
  assert.equal(elemento.type.name, "PantallaBorrador");
  // Lo que se enseña es **lo que ha contestado el servidor**, sin tocar: sus frases y su contenido.
  assert.equal(elemento.props.borrador.titulo, "Lo que he entendido");
  assert.equal(elemento.props.borrador.entendido[0].valor, "El Prado");
  assert.equal(elemento.props.borrador.falta[0].pregunta, "¿Cuándo?");
  assert.equal(elemento.props.textos.dictado.apuntarlo, "ESTÁ BIEN, APUNTARLO");
});

test("con lo dictado en blanco no se molesta al servidor", async () => {
  // Menos de tres letras no es una frase: se dice y no se manda nada.
  const { entorno, servidor } = await cargarAplicacion();
  await pulsar(entorno, "dictado");
  escribir(entorno, "dictado-texto", "ab");
  await pulsar(entorno, "dictado-entender");
  assert.ok(
    !servidor.llamadasConMetodo.includes("POST /api/borradores/desde-texto"),
    "ha mandado al servidor un texto que no dice nada",
  );
});

// ---------------------------------------------------------------------------
// Sin parcelas: el bloqueo que tenía la aplicación
//
// El aviso de la pantalla de inicio —el que desbloquea al agricultor nuevo— se comprueba ahora
// en `tests_js/react.test.js` («sin parcelas, avisa y ofrece el botón que lo arregla» y «con
// parcelas, el aviso de antes de empezar no aparece»), y desde `app.js` en la prueba de arriba,
// que mira que se le pase `hayParcelas: false` a React. Aquí se queda lo que no pinta React: el
// asistente de apuntar, que es el otro sitio donde se topa con que no hay parcelas.
// ---------------------------------------------------------------------------

test("sin parcelas, el asistente de echar producto no deja al agricultor sin salida", async () => {
  const { entorno } = await cargarAplicacion({ "/api/parcelas": [] });
  await pulsar(entorno, "inicio", { ir: "echar_producto" });
  // La pregunta y su aviso los dibuja la pieza `ListaParaElegir`: lo que se le pide es el aviso **con
  // el botón que lo arregla**, que es lo que impide que el agricultor se quede sin salida.
  const aviso = avisoDeLaLista();
  assert.ok(aviso.includes("Todavía no tienes parcelas"), `no explica qué pasa: ${aviso}`);
  assert.ok(
    aviso.includes("AÑADIR MI PRIMERA PARCELA"),
    "explica qué pasa pero no ofrece hacerlo",
  );
});

test("sin productos comprados, el asistente ofrece añadir uno", async () => {
  const { entorno } = await cargarAplicacion();
  // Se recorre el asistente hasta la pregunta del producto, como lo haría el
  // agricultor: parcela, fecha, hectáreas, motivo… y ahí se topa con que no tiene
  // ningún producto dado de alta.
  await pulsar(entorno, "inicio", { ir: "echar_producto" });
  await pulsar(entorno, "elegir", { campo: "parcela_id", valor: "1", superficie: "2.43" });
  await pulsar(entorno, "asistente-seguir"); // la fecha
  await pulsar(entorno, "asistente-seguir"); // las hectáreas
  await pulsar(entorno, "elegir", {
    campo: "justificacion",
    valor: "Vi la plaga o la hierba en el campo",
  });
  const html = pantallaPedida(entorno);
  assert.ok(html.includes("¿Qué producto has echado?"), `no llegó al producto: ${html.slice(0, 200)}`);
  const aviso = avisoDeLaLista();
  assert.ok(aviso.includes("Todavía no has apuntado ningún producto comprado"), aviso);
  assert.ok(aviso.includes("AÑADIR UN PRODUCTO COMPRADO"), aviso);
});

test("el asistente de echar producto llega hasta la pregunta del producto", async () => {
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "inicio", { ir: "echar_producto" });
  await pulsar(entorno, "elegir", { campo: "parcela_id", valor: "1", superficie: "2.43" });
  const html = pantallaPedida(entorno);
  assert.ok(html.includes("¿Cuándo?"), "no ha avanzado a la fecha");
});

// ---------------------------------------------------------------------------
// Entrar con el certificado digital
// ---------------------------------------------------------------------------

/** Carga la aplicación sin sesión, que es cuando sale la pantalla de entrar. */
async function cargarSinSesion(cambios = {}) {
  const entorno = montarEntorno();
  const servidor = montarServidor(cambios);

  // Se borra el token para que arranque en la pantalla de entrada.
  entorno.window.localStorage.removeItem("cuedigital.token");

  const definir = (nombre, valor) =>
    Object.defineProperty(globalThis, nombre, { value: valor, configurable: true, writable: true });
  definir("document", entorno.document);
  definir("window", entorno.window);
  definir("navigator", entorno.navigator);
  definir("URL", entorno.URL);
  definir("fetch", servidor.fetchFalso);
  definir("localStorage", entorno.window.localStorage);

  await import(`../web/app.js?prueba=${Math.random()}`);
  await new Promise((resolver) => setTimeout(resolver, 60));
  return { entorno, servidor };
}

// ---------------------------------------------------------------------------
// La pantalla de entrar se pasó a React (ronda 55)
//
// Es la primera que ve cualquiera, y hasta ahora era de la interfaz vieja: lo primero que se
// encontraba el agricultor era la mitad antigua. Aquí había tres pruebas que miraban su HTML en el
// contenedor de mentira (el botón del certificado con y sin configurar, y que no tape el entrar con
// correo y clave). **Se han reescrito contra el componente**, en `tests_js/react.test.js`, y aquí
// queda lo que solo se ve desde `app.js`: que la pantalla **se le pide a React** con el modo, las
// provincias y el estado del certificado.
// ---------------------------------------------------------------------------

test("la pantalla de entrar se le pide a React, con el estado del certificado", async () => {
  const antes = montajes.length;
  const { entorno } = await cargarSinSesion({
    "/api/cuenta/certificado/estado": {
      configurado: true,
      hay_certificado: true,
      certificado: { nif: "70922320A", nombre: "PEREZ VELASCO DAVID" },
      si_no_se_puede: "",
      explicacion: "",
    },
  });

  const pedidos = montajes.slice(antes);
  assert.ok(pedidos.length >= 1, "la pantalla de entrar no se le ha pedido a React");
  const elemento = pedidos[pedidos.length - 1].elemento;
  assert.equal(elemento.type.name, "PantallaEntrar");
  assert.equal(elemento.props.modo, "entrar", "no empieza en el modo de entrar");
  assert.ok(
    elemento.props.certificado && elemento.props.certificado.configurado,
    "no le llega que el certificado está configurado",
  );
  assert.ok(Array.isArray(elemento.props.provincias), "no le llegan las provincias del servidor");
  assert.ok(
    elemento.props.ayudaDelNif && elemento.props.ayudaDelNif.rotulos,
    "no le llega la ayuda del NIF con sus rótulos",
  );
  assert.equal(entorno.nodos.get("pantalla").innerHTML, "");
});

test("sin certificado configurado, se le dice a React que no lo hay", async () => {
  // Enseñar un botón que lleva a un error es peor que no enseñarlo, así que la decisión se toma con
  // lo que contesta el servidor y se le pasa al componente.
  const antes = montajes.length;
  await cargarSinSesion();
  const elemento = montajes[montajes.length - 1].elemento;
  assert.equal(elemento.type.name, "PantallaEntrar");
  assert.ok(
    !elemento.props.certificado || !elemento.props.certificado.configurado,
    "le llega un certificado configurado que no existe",
  );
  assert.ok(antes >= 0);
});

// ---------------------------------------------------------------------------
// La firma del cuaderno
// ---------------------------------------------------------------------------

function estadoDeFirma(cambios = {}) {
  return {
    estado: "sin_firmar",
    huella: "a".repeat(64),
    puede_firmar: true,
    nombre_del_fichero: "cuaderno_2026.txt",
    firma: null,
    mensaje: "Todavía no has firmado el cuaderno de este año.",
    explicacion: "Firmar es lo que hace que el cuaderno valga delante de la administración.",
    ...cambios,
  };
}

test("mi cuaderno deja guardar los datos en un fichero, además de sacarlo en papel", async () => {
  // El registro en un formato que se puede guardar, abrir con Excel y entregar si lo piden. La ley
  // pide **llevar** el registro y poder enseñarlo, y mandarlo a la Junta es voluntario, así que
  // este botón es el que de verdad hace falta tener: no puede quedarse sin puerta.
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "inicio", { ir: "mi_cuaderno" });
  const acciones = ultimoCuadernoPedido().acciones;
  const sacarDatos = acciones.find((accion) => accion.accion === "sacar-datos");
  assert.ok(sacarDatos, `no se pueden guardar los datos: ${JSON.stringify(acciones)}`);
  assert.ok(
    sacarDatos.etiqueta.includes("GUARDAR LOS DATOS EN UN FICHERO"),
    `el botón sale sin texto: ${sacarDatos.etiqueta}`,
  );
  assert.ok(
    acciones.some((accion) => accion.accion === "sacar-papel"),
    "no se puede sacar el papel",
  );
});

test("mi cuaderno dice que llevar el registro es obligatorio y mandarlo no", async () => {
  // Es lo que la gente cree al revés: que está obligada a enviar los datos a la Junta. La ley dice
  // justo lo contrario —llevar el registro y poder enseñarlo sí, enviarlo no (artículo 10.2 del
  // Real Decreto 1054/2022)— y este programa no puede callárselo para empujar a nadie a usar la
  // ventanilla de la Junta. Va con el artículo delante, para que se pueda comprobar.
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "inicio", { ir: "mi_cuaderno" });
  const ley = ultimoCuadernoPedido().textos.cuaderno.ley_pista;
  assert.ok(ley.includes("es obligatorio"), `no dice qué es obligatorio: ${ley}`);
  assert.ok(ley.includes("voluntario"), "no dice que mandarlo es voluntario");
  assert.ok(ley.includes("artículo 10.2"), "sin el artículo no se puede comprobar");
});

// ---------------------------------------------------------------------------
// La ayuda se pasó a React en la ronda 39
//
// Lo que comprobaba esta prueba —que explique lo que obliga la ley, con el artículo delante, y que
// diga lo que todavía no está aclarado en vez de prometer de más— está ahora en
// `tests_js/react.test.js`, contra el componente. Aquí se comprueba lo que solo se ve desde
// `app.js`: que la pantalla **se le pide a React** con todas sus partes ya preparadas.
// ---------------------------------------------------------------------------

test("la ayuda se le pide a React, con sus partes preparadas", async () => {
  const { entorno } = await cargarAplicacion();
  const antes = montajes.length;
  await pulsar(entorno, "inicio", { ir: "ayuda" });
  const pedidos = montajes.slice(antes);

  assert.equal(pedidos.length, 1, `se han pedido ${pedidos.length} montajes: solo la ayuda`);
  const elemento = pedidos[0].elemento;
  assert.ok(elemento, "no se le pide nada a React: la ayuda se está pintando a mano otra vez");
  assert.equal(elemento.type.name, "PantallaAyuda");

  // Las seis frases de la ley, con su título (cada una con el suyo, no el rótulo del apartado: ronda 83).
  assert.equal(elemento.props.ley.length, 6, "no le llegan las seis frases de la ley");
  assert.equal(
    elemento.props.ley[0].titulo,
    "Llevar el cuaderno al día",
    `la primera frase de la ley no lleva su título: «${elemento.props.ley[0].titulo}»`,
  );
  assert.equal(
    elemento.props.ley[1].titulo,
    "Mandar los datos a la Junta",
    "las frases de la ley repiten el rótulo del apartado en vez de tener el suyo",
  );
  assert.ok(elemento.props.ley[0].texto.includes("10.2") || elemento.props.ley[1].texto.includes("10.2"));

  // Los porqués llegan como **lista**, no como diccionario: el orden de lo que se lee importa. Su
  // contenido (que estén todos, y el de cuánto tiempo se guardan los papeles) se comprueba en
  // `react.test.js` contra los textos de verdad. Aquí se comprueba el cableado: que cada porqué llegue
  // **con su título**, que es lo que hace que en la pantalla tenga nombre (ronda 83). El título y el texto
  // van en dos diccionarios distintos del servidor (`PORQUE` y `PORQUE_TITULOS`) y los junta `app.js`.
  assert.ok(Array.isArray(elemento.props.porques), "los porqués no llegan como lista");
  assert.deepEqual(
    elemento.props.porques.map((porque) => porque.titulo),
    ["Para qué sirve el cuaderno", "En papel o en el móvil"],
    "los porqués no llegan con su título",
  );
  assert.ok(
    elemento.props.porques[0].texto.startsWith("Desde 2013"),
    "el porqué no lleva su texto",
  );

  // Y los cuatro bloques de abajo, también como listas.
  assert.ok(Array.isArray(elemento.props.reglas), "no le llegan las reglas de los nitratos");
  assert.ok(Array.isArray(elemento.props.aportes), "no le llegan los aportes máximos");
  assert.ok(Array.isArray(elemento.props.periodos), "no le llegan los periodos prohibidos");
  assert.ok(Array.isArray(elemento.props.limites), "no le llega lo que falta por confirmar");

  assert.equal(entorno.nodos.get("pantalla").innerHTML, "");
});

test("mi cuaderno dice si está firmado", async () => {
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "inicio", { ir: "mi_cuaderno" });
  const firma = ultimoCuadernoPedido().firma;
  assert.ok(firma.hay, "no le llega el apartado de firma");
  assert.equal(firma.titulo, "Firmar el cuaderno");
  assert.equal(firma.mensaje, "Todavía no has firmado el cuaderno de este año.");
  assert.equal(firma.puede, true, "con certificado no se le ofrece firmar");
  assert.deepEqual(
    firma.botones.map((boton) => boton.accion),
    ["firmar-abrir"],
    "no le llega el botón de firmar",
  );
});

test("sin certificado no sale el botón de firmar, y se explica por qué", async () => {
  // Un botón que lleva a un error es peor que no enseñarlo.
  const { entorno } = await cargarAplicacion({
    "/api/firmas/estado": estadoDeFirma({ puede_firmar: false }),
  });
  await pulsar(entorno, "inicio", { ir: "mi_cuaderno" });
  const firma = ultimoCuadernoPedido().firma;
  assert.equal(firma.puede, false);
  assert.deepEqual(firma.botones, [], "sale el botón sin poder firmar");
  assert.ok(
    firma.no_puede_firmar.includes("hace falta que entres con tu certificado"),
    `no dice por qué: ${firma.no_puede_firmar}`,
  );
});

// ---------------------------------------------------------------------------
// «Firmar el cuaderno» se pasó a React
//
// Aquí había dos pruebas que miraban su HTML en el contenedor de mentira («abre los tres pasos» y
// «los tres pasos dicen el nombre del fichero»). **Se han reescrito contra el componente**, en
// `tests_js/react.test.js`, junto con el aviso de firmado y el error. Aquí queda lo que solo se ve
// desde `app.js`: que la pantalla **se le pide a React** con el nombre del fichero y con el campo del
// fichero en su sitio, y que el botón de firmar sale solo cuando se puede firmar.
// ---------------------------------------------------------------------------

test("los tres pasos se le piden a React, con el nombre del fichero", async () => {
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "inicio", { ir: "mi_cuaderno" });
  assert.deepEqual(
    ultimoCuadernoPedido().firma.botones.map((boton) => boton.accion),
    ["firmar-abrir"],
    "el bloque de la firma no lleva al sitio donde se firma",
  );

  const antes = montajes.length;
  await pulsar(entorno, "firmar-abrir");
  const pedidos = montajes.slice(antes);

  assert.equal(pedidos.length, 1, `se han pedido ${pedidos.length} montajes: solo la pantalla`);
  const elemento = pedidos[0].elemento;
  assert.ok(elemento, "no se le ha pedido nada a React: la pantalla se pinta a mano otra vez");
  assert.equal(elemento.type.name, "PantallaFirmar");
  assert.equal(elemento.props.textos.firma.paso_1, "1. Descarga este fichero");

  // El nombre del fichero llega desde el estado de la firma, que es lo que el agricultor tiene que
  // reconocer en su carpeta de descargas.
  assert.equal(elemento.props.nombreDelFichero, "cuaderno_2026.txt");
  // Y sin acabar de firmar, no se enseña el aviso de firmado.
  assert.equal(elemento.props.firmado, "");
  assert.equal(elemento.props.error, "");

  // Y la pantalla no se ha pintado a mano: el contenedor está **vacío** (lo pinta React entero).
  assert.equal(
    pantallaDe(entorno),
    "",
    "la pantalla de firmar se ha pintado además con `pintar()`",
  );
});

test("si el cuaderno se cambió después de firmar, se avisa en rojo", async () => {
  // Una firma que ya no cuadra es peor que no tener firma: parece que el cuaderno
  // está respaldado y no lo está.
  const { entorno } = await cargarAplicacion({
    "/api/firmas/estado": estadoDeFirma({
      estado: "cambiado_despues_de_firmar",
      mensaje: "Ojo: este cuaderno se firmó, pero después se ha cambiado algo.",
      firma: { id: 1, firmante_nombre: "PEREZ VELASCO DAVID" },
    }),
  });
  await pulsar(entorno, "inicio", { ir: "mi_cuaderno" });
  const firma = ultimoCuadernoPedido().firma;
  assert.equal(firma.cambiado, true, "no se marca como algo que hay que mirar");
  assert.ok(firma.mensaje.includes("Ojo"));
});

test("si está firmado y sin cambios, se dice con el nombre de quien firmó", async () => {
  const { entorno } = await cargarAplicacion({
    "/api/firmas/estado": estadoDeFirma({
      estado: "firmado",
      mensaje: "Firmado el 22/09/2026 por PEREZ VELASCO DAVID. Nadie lo ha cambiado.",
      firma: { id: 1, firmante_nombre: "PEREZ VELASCO DAVID" },
    }),
  });
  await pulsar(entorno, "inicio", { ir: "mi_cuaderno" });
  const firma = ultimoCuadernoPedido().firma;
  assert.ok(firma.mensaje.includes("PEREZ VELASCO DAVID"));
  assert.equal(firma.cambiado, false, "un cuaderno firmado y sin cambios no es un problema");
});

// ---------------------------------------------------------------------------
// Naves y almacenes
// ---------------------------------------------------------------------------

// La sección de naves y almacenes dentro de «mis cosas» se comprueba ahora en
// `tests_js/react.test.js` («las siete secciones»): la pantalla se pinta con React y su HTML ya no
// se puede leer desde aquí. Lo que sí se sigue comprobando aquí es que **añadir una nave** abra su
// asistente, que es cosa del manejador de clics.

test("añadir una nave abre su asistente con su primera pregunta", async () => {
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "anadir-maestro", { tipo: "instalacion" });
  const html = pantallaPedida(entorno);
  assert.ok(html.includes("¿Cómo llamas tú a esa nave?"));
  assert.ok(idsDeLosBloques().includes("alias"), "no hay dónde escribir el nombre de la nave");
});

test("al apuntar un producto, se ofrece la salida para naves y postcosecha", async () => {
  // Nueve de cada diez veces es una parcela, así que la salida va al final de la lista
  // y no como una pantalla previa que todo el mundo tiene que pasar.
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "inicio", { ir: "echar_producto" });
  const html = pantallaPedida(entorno);
  assert.ok(html.includes("¿Dónde?"), "no sale la primera pregunta");
  // Y la lista —que ahora la dibuja React— trae las dos salidas y **al final**, después de las tierras.
  const lista = textoDeLaLista();
  assert.ok(lista.includes("¿No es en una parcela?"), `no ofrece la salida: ${lista}`);
  assert.ok(lista.includes("En una nave o un almacén"), lista);
  assert.ok(lista.includes("Al producto ya recogido"), lista);
});

test("eligiendo una nave, el asistente pregunta en cuál", async () => {
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "inicio", { ir: "echar_producto" });
  await pulsar(entorno, "tipo-tratamiento", { tipo: "instalaciones" });
  const html = pantallaPedida(entorno);
  assert.ok(html.includes("¿En qué nave o almacén?"), `no pregunta la nave: ${html.slice(0, 300)}`);
  assert.ok(textoDeLaLista().includes("El almacén grande"), "no lista las naves que hay");
  assert.ok(!html.includes("¿Cuándo?"), "se ha saltado a la fecha sin saber dónde");
});

test("en el caso normal, el asistente sigue preguntando la fecha directamente", async () => {
  // Este paso intermedio no puede aparecerle a quien echa producto en la tierra.
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "inicio", { ir: "echar_producto" });
  await pulsar(entorno, "elegir", { campo: "parcela_id", valor: "1", superficie: "2.43" });
  const html = pantallaPedida(entorno);
  assert.ok(html.includes("¿Cuándo?"), "no pregunta la fecha");
  assert.ok(!html.includes("¿En qué nave o almacén?"), "pregunta la nave sin venir a cuento");
});

test("sin naves apuntadas, se ofrece añadir una en vez de dejar sin salida", async () => {
  const { entorno } = await cargarAplicacion({ "/api/instalaciones": [] });
  await pulsar(entorno, "inicio", { ir: "echar_producto" });
  await pulsar(entorno, "tipo-tratamiento", { tipo: "instalaciones" });
  const aviso = avisoDeLaLista();
  assert.ok(aviso.includes("Todavía no tienes ninguna nave ni almacén"), aviso);
  assert.ok(aviso.includes("AÑADIR UNA NAVE O UN ALMACÉN"), `avisa pero no deja arreglarlo: ${aviso}`);
});

// ---------------------------------------------------------------------------
// El plan de abono del año
// ---------------------------------------------------------------------------

function unPlan(cambios = {}) {
  return {
    id: 1,
    campana_id: 1,
    parcela_id: 1,
    grupo_id: null,
    cultivo: "Trigo blando",
    superficie_ha: 2.43,
    produccion_esperada_kg_ha: null,
    necesidad_n: 100,
    necesidad_p: 40,
    necesidad_k: 60,
    aportes_suelo_agua: null,
    detalle: [],
    notas: null,
    aplicado_n: 0,
    aplicado_p: 0,
    aplicado_k: 0,
    queda_n: 100,
    queda_p: 40,
    queda_k: 60,
    se_ha_pasado: false,
    apuntes: 0,
    mensaje: "Todavía no has apuntado ningún abono contra este plan.",
    ...cambios,
  };
}

test("sin plan de abono, mi cuaderno lo dice y ofrece hacerlo", async () => {
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "inicio", { ir: "mi_cuaderno" });
  const plan = ultimoCuadernoPedido().plan;
  assert.ok(plan.titulo.includes("El plan de abono del año"), `no hay apartado de plan: ${plan.titulo}`);
  assert.equal(plan.hay, false);
  assert.ok(plan.sin_planes.includes("Todavía no tienes ningún plan de abono"));
  // El aviso, cuando no hay plan, lleva **su botón suelto** (no en barra) y con su icono: es lo único
  // que se puede hacer en ese bloque, y por eso es el que empuja a hacerlo.
  const hacer = plan.botones.find((boton) => boton.accion === "plan-hacer");
  assert.ok(hacer, `avisa pero no ofrece arreglarlo: ${JSON.stringify(plan.botones)}`);
  assert.equal(hacer.icono, "🧪");
});

test("con plan, mi cuaderno enseña si vas bien", async () => {
  const { entorno } = await cargarAplicacion({ "/api/planes": [unPlan()] });
  await pulsar(entorno, "inicio", { ir: "mi_cuaderno" });
  const plan = ultimoCuadernoPedido().plan;
  assert.equal(plan.hay, true);
  assert.ok(plan.mensaje.includes("Todavía no has apuntado ningún abono contra este plan"));
  assert.equal(plan.se_ha_pasado, false, "ir bien no puede pintarse como un problema");
  assert.deepEqual(
    plan.acciones.map((accion) => accion.accion),
    ["plan-ver", "plan-hacer"],
    "no le llegan los dos botones del plan",
  );
});

test("si te has pasado del plan, se avisa en rojo", async () => {
  const { entorno } = await cargarAplicacion({
    "/api/planes": [
      unPlan({ aplicado_n: 120, queda_n: -20, se_ha_pasado: true, mensaje: "Ojo: llevas más" }),
    ],
  });
  await pulsar(entorno, "inicio", { ir: "mi_cuaderno" });
  const plan = ultimoCuadernoPedido().plan;
  assert.equal(plan.se_ha_pasado, true, "pasarse del plan tiene que verse");
  assert.ok(plan.mensaje.includes("más de lo que tenías previsto"), `no lo dice: ${plan.mensaje}`);
});

// ---------------------------------------------------------------------------
// «El plan de abono del año» se pasó a React
//
// Aquí había dos pruebas que miraban su HTML en el contenedor de mentira («enseña previsto, aplicado
// y lo que queda» y «dice qué había el año anterior y si se usó una herramienta»). **Se han
// reescrito contra el componente**, en `tests_js/react.test.js`, que es donde se puede comprobar
// frase por frase. Aquí queda lo que solo se ve desde `app.js`: que la pantalla **se le pide a
// React** con las filas y los textos ya preparados.
// ---------------------------------------------------------------------------

test("el plan de abono se le pide a React, con las filas ya contadas", async () => {
  const { entorno, servidor } = await cargarAplicacion({
    "/api/planes": [
      unPlan({ aplicado_n: 60, queda_n: 40, cultivo_precedente: "Cebada", herramienta: true }),
    ],
  });
  const antes = montajes.length;
  await pulsar(entorno, "plan-ver");

  assert.ok(servidor.llamadas.includes("/api/planes"), "no ha pedido los planes");

  const pedidos = montajes.slice(antes);
  assert.equal(pedidos.length, 1, `se han pedido ${pedidos.length} montajes: solo la pantalla`);
  const elemento = pedidos[0].elemento;
  assert.ok(elemento, "no se le ha pedido nada a React: la pantalla se pinta a mano otra vez");
  assert.equal(elemento.type.name, "PantallaPlanes");
  assert.equal(elemento.props.textos.plan.titulo, "El plan de abono del año");

  const plan = elemento.props.planes[0];
  assert.equal(plan.titulo, "Plan de Trigo blando", "el título no viene con el cultivo");
  assert.ok(
    plan.detalle.includes("100,0") === false && plan.detalle.includes("El Prado"),
    `la línea del plan no dice la parcela y su superficie: ${plan.detalle}`,
  );
  assert.equal(plan.precedente, "El año anterior había: Cebada");
  assert.equal(plan.herramienta, "Lo hice con una herramienta: Sí");
  // Las filas llegan **contadas y escritas**: el componente no formatea números.
  const fila = plan.filas.find((f) => f.nombre === "N");
  assert.ok(fila, "no vienen las filas de los nutrientes");
  assert.ok(/100,0 · 60,0 · 40,0/.test(fila.texto), `la fila no viene contada: ${fila.texto}`);
  // Y la cabecera nombra **los tres** números (ronda 85): el tercero salía sin rótulo y había que
  // adivinar de qué era.
  assert.equal(
    plan.cabecera,
    "Tenías previsto · Llevas · Te queda",
    `la cabecera no nombra las tres columnas: ${plan.cabecera}`,
  );

  assert.ok(
    !pantallaDe(entorno).includes("Plan de Trigo blando"),
    "la pantalla se ha pintado además con `pintar()`",
  );
});

test("cuando en el plan se ha pasado, el tercer número se cambia por la palabra", async () => {
  // Antes en su sitio iba un ⚠️ suelto: un dato sin nombre no se puede leer, y el aviso de arriba ya lo dice
  // en rojo. Ahora dice «Pasado», que es un texto del servidor que existía y no usaba nadie (ronda 85).
  const { entorno } = await cargarAplicacion({
    "/api/planes": [unPlan({ aplicado_n: 130, queda_n: -30, se_ha_pasado: true })],
  });
  await pulsar(entorno, "plan-ver");
  const plan = montajes[montajes.length - 1].elemento.props.planes[0];
  const fila = plan.filas.find((f) => f.nombre === "N");
  assert.equal(fila.texto, "100,0 · 130,0 · Pasado", `la fila del pasado no se lee: ${fila.texto}`);
});

test("hacer un plan empieza preguntando dónde", async () => {
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "plan-hacer");
  const html = pantallaPedida(entorno);
  assert.ok(html.includes("¿Dónde?"), "no empieza por la parcela");
  assert.ok(html.includes('data-accion="plan-hacer"') === false, "sigue en el inicio");
});

test("tras elegir la parcela, el plan ofrece apoyarse en un análisis de esa parcela", async () => {
  // Antes de tener analíticas, este paso no existía y después de la parcela se preguntaba
  // el cultivo. Ahora hay uno en medio, y es OPCIONAL: el agricultor que no tiene análisis
  // pulsa DEJARLO y sigue. Se prueba aquí porque es justo el sitio donde un paso de más
  // podría dejar a alguien atascado.
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "plan-hacer");
  await pulsar(entorno, "elegir", { campo: "parcela_id", valor: "1", superficie: "2.43" });
  const html = pantallaPedida(entorno);
  assert.ok(
    html.includes("¿De qué análisis sale este plan?"),
    `no ofrece el análisis: ${html.slice(0, 200)}`,
  );
  assert.ok(html.includes("DEJARLO"), "un paso opcional tiene que poder saltarse");
});

test("saltando el análisis, el plan sigue preguntando el cultivo", async () => {
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "plan-hacer");
  await pulsar(entorno, "elegir", { campo: "parcela_id", valor: "1", superficie: "2.43" });
  await pulsar(entorno, "asistente-saltar");
  const html = pantallaPedida(entorno);
  assert.ok(html.includes("¿Qué vas a abonar?"), `no pregunta el cultivo: ${html.slice(0, 200)}`);
  assert.ok(idsDeLosBloques().includes("cultivo"), "no hay dónde escribir el cultivo");
});

test("con análisis de la parcela, el plan los enseña para elegir uno", async () => {
  const { entorno } = await cargarAplicacion({ "/api/analiticas": [unAnalisis()] });
  await pulsar(entorno, "plan-hacer");
  await pulsar(entorno, "elegir", { campo: "parcela_id", valor: "1", superficie: "2.43" });
  // La lista la pinta React: se mira lo que se le pide, con su acción y su `data-campo`.
  const analisis = botonesDeLaLista();
  assert.ok(
    analisis.some((boton) => boton.etiqueta === "Análisis de La tierra de El Prado"),
    `no lista el análisis: ${analisis.map((b) => b.etiqueta).join(", ")}`,
  );
  assert.equal(analisis[0].datos.campo, "analitica_id", "el análisis no dice a qué campo contesta");
  assert.equal(analisis[0].accion, "elegir");
});

test("sin análisis de la parcela, el plan lo dice y no deja un hueco", async () => {
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "plan-hacer");
  await pulsar(entorno, "elegir", { campo: "parcela_id", valor: "1", superficie: "2.43" });
  const aviso = avisoDeLaLista();
  assert.ok(aviso.includes("Esta parcela no tiene ningún análisis apuntado."), aviso);
  // Y con él, el botón que lo arregla: sin eso, el aviso deja al agricultor sin salida.
  assert.ok(aviso.includes("APUNTAR UN ANÁLISIS"), `el aviso no dice dónde se añade: ${aviso}`);
});

// ---------------------------------------------------------------------------
// El conector del SIGPAC
// ---------------------------------------------------------------------------

test("al añadir una parcela se ofrece traerla del SIGPAC", async () => {
  // Es lo que ahorra teclear ocho datos por cada una: con cuarenta parcelas es la diferencia
  // entre empezar y abandonar.
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "anadir-maestro", { tipo: "parcela" });
  const { titulo, acciones } = confirmacionPedida();
  assert.equal(titulo, "Traer la parcela del SIGPAC", `no lo ofrece: ${titulo}`);
  const codigos = acciones.map((accion) => accion.accion);
  assert.ok(codigos.includes("sigpac-si"), "no ofrece traerla del SIGPAC");
  assert.ok(codigos.includes("sigpac-no"), "y sin cerrar la puerta a hacerlo a mano");
});

/**
 * La pantalla de traer la tierra del SIGPAC, tal y como se le ha pedido a React.
 *
 * Se migró como **pantalla** (no con las piezas del asistente) porque tiene cosas que no tiene ningún otro
 * paso: un desplegable, listas de `li` y el detalle de cada recinto. Lo que hay que mirar es lo que se le
 * pide: los `id` de los campos, los pueblos buscados y los recintos con su detalle ya montado.
 */
function sigpacPedido() {
  const pantalla = piezasPedidas().find(
    (uno) => uno && uno.type && uno.type.name === "PantallaTraerDelSigpac",
  );
  assert.ok(
    pantalla,
    `el último montaje no trae la pantalla del SIGPAC: ${piezasPedidas().map((uno) => uno && uno.type && uno.type.name).join(", ")}`,
  );
  return pantalla.props;
}

test("traer del SIGPAC no pide ocho datos: se busca la parcela y se marcan los trozos", async () => {
  // Montado como lo hacen las aplicaciones oficiales del FEGA («Añadir recintos de SigPac»):
  // provincia, municipio, polígono y parcela, un botón de buscar y la lista de trozos para
  // marcar. Y además se puede pegar la referencia tal cual sale del visor o del Catastro.
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "sigpac-si");

  // **Un solo paso, sin barra y sin «Paso 1 de 1», y sin la explicación repetida** (ronda 88): la pantalla
  // explica ella misma lo que hace y la casilla de la referencia lleva debajo su propia explicación, que era
  // la misma que la pista del paso y salía dos veces.
  const paso = montajes[montajes.length - 1].elemento.props;
  assert.equal(paso.total, 1, "la pantalla del SIGPAC tiene más de un paso");
  assert.equal(paso.paso, "", "dice «Paso 1 de 1» en un asistente de un solo paso");
  assert.equal(paso.pista, "", `la pista del paso repite lo que ya dice la pantalla: «${paso.pista}»`);

  const { textos, datos } = sigpacPedido();
  // El ejemplo de la referencia (la del visor) sale del servidor, no escrito aquí.
  assert.ok(
    textos.sigpac.referencia_ejemplo,
    "no le llega el ejemplo de la referencia: el agricultor no sabría qué pegar",
  );
  assert.ok(textos.sigpac.referencia_ejemplo.length > 6, textos.sigpac.referencia_ejemplo);
  assert.ok(!("superficie_ha" in datos), "sigue pidiendo la superficie a mano");
  // Las provincias del desplegable, con su «cualquiera» para quien no la sepa.
  assert.ok(datos.provincias.length >= 1, "no le llegan las provincias");
  assert.equal(datos.provincias[0].etiqueta, "Salamanca", "la provincia no llega con su nombre");
  assert.ok(textos.municipios.cualquiera, "no le llega la opción de «cualquiera»");
  // **Los tres sistemas, y ninguno dado por hecho** (A10, 05/10/2026). Esta prueba pedía antes dos
  // —«secano» y «regadío»— con el secano ya elegido «porque es lo normal en estas tierras». Eso era el
  // defecto: quien no tocaba el botón declaraba de secano una tierra de regadío, y el sistema decide
  // **contra qué columna del anexo III de la Orden MAV/398/2022 se compara el abonado**. Ahora se
  // ofrecen tres y sale marcado «no lo sé», que es lo que el agricultor puede afirmar sin saberlo.
  assert.deepEqual(
    datos.sistemas.map((sistema) => sistema.valor),
    ["secano", "regadio", "nulo"],
    "no le llegan los tres sistemas",
  );
  assert.ok(
    datos.sistemas[2].elegido,
    "no sale marcado «no lo sé»: parecería que el agricultor ya ha declarado el sistema",
  );
  assert.ok(
    datos.sistemas.every((sistema) => !sistema.elegido || sistema.valor === "nulo"),
    "viene un sistema dado por elegido sin que nadie lo haya dicho",
  );
  // Los cuatro campos que sí se piden, con su `id` de siempre: es lo que lee `app.js`.
  assert.equal(datos.poligono, "", "el polígono no llega vacío");
  assert.equal(datos.parcela, "");
  assert.equal(datos.alias, "");
});

test("sin decir qué parcela es, no se llama al SIGPAC y se dice qué falta", async () => {
  // Una llamada que se sabe que va a fallar solo hace esperar al agricultor delante de una
  // pantalla parada. Se comprueba lo que falta **antes** de salir a la red.
  const { entorno, servidor } = await cargarAplicacion();
  await pulsar(entorno, "sigpac-si");
  await pulsar(entorno, "buscar-trozos");
  const html = pantallaPedida(entorno);
  assert.ok(html.includes("hacen falta el pueblo"), "no dice qué falta");
  assert.ok(
    !servidor.llamadas.some((r) => r.includes("sigpac/buscar")),
    "ha llamado al SIGPAC sin decir qué parcela es",
  );
});

test("para poner el pueblo no hay que saberse el código: se busca y se elige de la lista", async () => {
  // Es lo que hace que no haya que saberse nada: el agricultor escribe las primeras letras de su
  // pueblo, lo elige, y el programa se queda con el nombre y con el código oficial (el del INE,
  // que es el mismo que sale en el visor del SIGPAC y en la referencia catastral).
  const { entorno } = await cargarAplicacion({
    "/api/municipios?buscar=Calvarrasa&provincia=Salamanca": {
      municipios: [
        {
          nombre: "Calvarrasa de Arriba",
          provincia: "Salamanca",
          codigo_ine: "37070",
          codigo_municipio: "070",
          codigo_provincia: "37",
        },
      ],
      cuantos: 1,
      total: 2248,
    },
  });
  await pulsar(entorno, "sigpac-si");
  escribir(entorno, "municipio_sigpac", "Calvarrasa");
  escribir(entorno, "provincia_sigpac", "Salamanca");
  await pulsar(entorno, "buscar-pueblo");

  // La lista de pueblos la pinta React, con el nombre, su provincia entre paréntesis (hay pueblos que se
  // llaman igual en dos provincias) y el código oficial, que es el que usa el SIGPAC.
  const conLista = sigpacPedido().datos.pueblos;
  assert.equal(conLista.length, 1, `esperaba un pueblo y hay ${conLista.length}`);
  assert.equal(
    conLista[0].etiqueta,
    "Calvarrasa de Arriba (Salamanca)",
    "el pueblo no lleva su provincia",
  );
  assert.ok(conLista[0].pista.includes("37070"), `no enseña el código oficial: ${conLista[0].pista}`);
  assert.equal(conLista[0].nombre, "Calvarrasa de Arriba", "el nombre no va aparte: no se podría elegir");
  assert.equal(conLista[0].provincia, "Salamanca");

  await pulsar(entorno, "elegir-pueblo", {
    nombre: "Calvarrasa de Arriba",
    provincia: "Salamanca",
  });
  // Al elegirlo, el pueblo se queda escrito en el campo (que es lo que el agricultor tiene que ver).
  assert.equal(
    sigpacPedido().datos.municipio,
    "Calvarrasa de Arriba",
    "al elegirlo no se queda escrito el pueblo",
  );
});

test("se buscan los trozos de la parcela y se traen los marcados", async () => {
  // El recorrido entero, tal y como lo hace el agricultor: elige el pueblo, escribe el polígono y
  // la parcela, busca, y trae el trozo. Y todo eso sin saberse ningún código de memoria.
  const { entorno, servidor } = await cargarAplicacion({
    "/api/municipios?buscar=Calvarrasa&provincia=Salamanca": {
      municipios: [
        {
          nombre: "Calvarrasa de Arriba",
          provincia: "Salamanca",
          codigo_ine: "37070",
          codigo_municipio: "070",
          codigo_provincia: "37",
        },
      ],
      cuantos: 1,
      total: 2248,
    },
    "/api/sigpac/buscar": {
      recintos: [
        {
          recinto: 1,
          referencia: "37-70-0-0-503-51-1",
          superficie_ha: 4.9016,
          uso_sigpac: "TA",
          uso: "TIERRAS ARABLES",
          pendiente_pct: 1,
          altitud: 837,
          tiene_dibujo: true,
        },
      ],
      municipio: { nombre: "Calvarrasa de Arriba", provincia: "Salamanca", codigo_ine: "37070" },
      encontrados: 1,
    },
    "/api/parcelas/desde-sigpac/varias": {
      creadas: [{ id: 1, alias: "El llano", ref_sigpac: "37-70-0-0-503-51-1" }],
      cuantas: 1,
      fallos: [],
      mensaje: "Ya está: una parcela traída del SIGPAC.",
    },
  });

  await pulsar(entorno, "sigpac-si");
  escribir(entorno, "municipio_sigpac", "Calvarrasa");
  escribir(entorno, "provincia_sigpac", "Salamanca");
  await pulsar(entorno, "buscar-pueblo");
  await pulsar(entorno, "elegir-pueblo", {
    nombre: "Calvarrasa de Arriba",
    provincia: "Salamanca",
  });
  escribir(entorno, "poligono_sigpac", "503");
  escribir(entorno, "parcela_sigpac", "51");
  escribir(entorno, "alias_sigpac", "El llano");
  await pulsar(entorno, "buscar-trozos");

  const conTrozos = sigpacPedido().datos.trozos;
  assert.ok(servidor.llamadas.includes("/api/sigpac/buscar"), "no ha buscado los trozos");
  assert.equal(conTrozos.length, 1, `esperaba un trozo y hay ${conTrozos.length}`);
  // El detalle del recinto lo monta `app.js` (es quien conoce los números): la superficie con cuatro
  // decimales, el uso con su código delante como lo enseña el visor del SIGPAC, la pendiente y la altitud.
  assert.equal(conTrozos[0].etiqueta, "Trozo 1", `no sale el trozo: ${conTrozos[0].etiqueta}`);
  assert.ok(conTrozos[0].pista.includes("4,9016 ha"), `no dice la superficie: ${conTrozos[0].pista}`);
  assert.ok(
    conTrozos[0].pista.includes("TA — TIERRAS ARABLES"),
    `no dice el uso como lo dice el SIGPAC: ${conTrozos[0].pista}`,
  );
  assert.equal(conTrozos[0].referencia, "37-70-0-0-503-51-1", "el recinto no lleva su referencia");

  // Se marca y se desmarca pulsando. **Con un solo recinto, ya viene marcado**: si la parcela tiene uno
  // solo no hay duda de cuál es (con cinco, marcarlos todos daría de alta parcelas que no son suyas).
  assert.ok(
    sigpacPedido().datos.trozos[0].marcado,
    "con un solo recinto tiene que venir ya marcado",
  );
  await pulsar(entorno, "marcar-trozo", { referencia: "37-70-0-0-503-51-1" });
  assert.ok(!sigpacPedido().datos.trozos[0].marcado, "al desmarcarlo sigue marcado");
  await pulsar(entorno, "marcar-trozo", { referencia: "37-70-0-0-503-51-1" });
  assert.ok(sigpacPedido().datos.trozos[0].marcado, "al volver a marcarlo no queda marcado");

  await pulsar(entorno, "traer-marcados");
  assert.ok(
    servidor.llamadas.includes("/api/parcelas/desde-sigpac/varias"),
    "no ha traído el trozo marcado",
  );
  // Y se dice lo que se ha traído, para que el agricultor lo vea antes de fiarse.
  const confirmacion = confirmacionPedida();
  const listas = (confirmacion.listas || []).flatMap((lista) => lista.elementos);
  assert.ok(
    listas.some((elemento) => elemento.cabecera === "El llano"),
    `no enseña la parcela traída: ${listas.map((el) => el.cabecera).join(", ")}`,
  );
});

test("la referencia del visor también sirve para buscar, sin elegir pueblo", async () => {
  const { entorno, servidor } = await cargarAplicacion({
    "/api/sigpac/buscar": {
      recintos: [
        {
          recinto: 1,
          referencia: "37-70-0-0-503-51-1",
          superficie_ha: 4.9016,
          uso_sigpac: "TA",
          uso: "TIERRAS ARABLES",
        },
      ],
      encontrados: 1,
    },
  });
  await pulsar(entorno, "sigpac-si");
  escribir(entorno, "ref_sigpac", "37:70:0:0:503:51");
  await pulsar(entorno, "buscar-trozos");

  assert.ok(servidor.llamadas.includes("/api/sigpac/buscar"), "no ha buscado con la referencia");
  const trozos = sigpacPedido().datos.trozos;
  assert.equal(trozos.length, 1, `no sale el trozo: ${trozos.length}`);
  assert.equal(trozos[0].etiqueta, "Trozo 1");
});

test("elegir apuntarla a mano lleva al alta de siempre", async () => {
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "anadir-maestro", { tipo: "parcela" });
  await pulsar(entorno, "sigpac-no");
  const html = pantallaPedida(entorno);
  assert.ok(html.includes("¿Cómo llamas tú a esa tierra?"), `no es el alta a mano: ${html.slice(0, 200)}`);
});

// ---------------------------------------------------------------------------
// El mapa: elegir la tierra tocándola
// ---------------------------------------------------------------------------

/** Lo que contesta el servidor cuando se toca un punto del mapa. */
function unaParcelaDelMapa(cambios = {}) {
  return {
    encontrado: true,
    referencia: "37-70-0-0-503-51-1",
    recinto: 1,
    superficie_ha: 4.9016,
    uso_sigpac: "TA",
    uso: "TIERRAS ARABLES",
    pendiente_pct: 1,
    altitud: 837,
    puntos: [
      [-5.5546, 40.9073],
      [-5.5563, 40.9050],
      [-5.5545, 40.9051],
    ],
    municipio: { nombre: "Calvarrasa de Arriba", provincia: "Salamanca", codigo_ine: "37070" },
    referencia_catastral: "37070A503000510000AQ",
    en_zona_de_nitratos: false,
    zona_de_nitratos_porcentaje: 0,
    ...cambios,
  };
}

/** Una parcela ya apuntada, con su centro, para que el mapa sepa por dónde abrirse. */
function misParcelas(cambios = {}) {
  return [
    {
      id: 1,
      alias: "El Prado",
      ref_sigpac: "37-70-0-0-503-51-1",
      provincia: "Salamanca",
      municipio: "Calvarrasa de Arriba",
      superficie_ha: 4.9016,
      superficie_oficial: true,
      sistema: "secano",
      masa_agua_cerca: false,
      captacion_consumo_humano: false,
      zona_vulnerable_nitratos: null,
      pendiente_pct: 1,
      uso_sigpac: "TA",
      centro: [-5.5559, 40.9058],
      ...cambios,
    },
  ];
}

/**
 * La pantalla de confirmación (o de ofrecer un camino) que se le ha pedido a React.
 *
 * Las cinco confirmaciones (venta guardada, análisis guardado, plan guardado, medidas guardadas y ficha
 * de un maestro guardada) y las pantallas que ofrecen un camino (traer la tierra del SIGPAC, el listado de
 * papeles y las tierras traídas) son la **misma pieza**. Lo que hay que mirar es lo que se le pide: el
 * título, la explicación, los avisos y los botones.
 */
function confirmacionPedida() {
  const pantalla = piezasPedidas().find((uno) => uno && uno.type && uno.type.name === "Confirmacion");
  assert.ok(
    pantalla,
    `el último montaje no trae una confirmación: ${piezasPedidas().map((uno) => uno && uno.type && uno.type.name).join(", ")}`,
  );
  return pantalla.props;
}

/** Las acciones de una confirmación pedida, en un solo texto, para poder buscar dentro. */
function accionesDeLoPedido() {
  return confirmacionPedida()
    .acciones.map((accion) => `${accion.accion}: ${accion.etiqueta}`)
    .join(" | ");
}

test("el alta de parcela ofrece el mapa como primer camino", async () => {
  // Quien no se sabe sus códigos tiene que ver el mapa sin buscarlo: es la primera opción, y la
  // referencia y el apunte a mano siguen estando para quien no tenga cobertura.
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "anadir-maestro", { tipo: "parcela" });
  const { acciones } = confirmacionPedida();
  assert.equal(acciones[0].accion, "mapa-abrir", "el mapa no es el primer camino");
  assert.equal(acciones[0].etiqueta, "VER EL MAPA Y ELEGIRLA AHÍ", "el botón del mapa no dice qué hace");
  const codigos = acciones.map((accion) => accion.accion);
  assert.ok(codigos.includes("sigpac-si"), "se ha perdido el camino de la referencia");
  assert.ok(codigos.includes("sigpac-no"), "se ha perdido el apunte a mano");
  // Y se dice que el mapa necesita conexión, que es lo que avisa en el campo.
  const textos = todosLosTextos(confirmacionPedida().contenido && confirmacionPedida().contenido.props);
  assert.ok(
    textos.join(" ").includes("necesita conexión"),
    `no se dice que el mapa necesita conexión: ${textos.join(" ")}`,
  );
});

test("el plan de abono no enseña nada que no se haya dicho", async () => {
  // Ni un «no» de relleno ni un dato inventado: lo que el anexo II pide se enseña **cuando se sabe**.
  // (Lo que se ve en pantalla con esos datos se comprueba en `tests_js/react.test.js`, contra el
  // componente; aquí se comprueba que `app.js` **no se lo invente** al prepararlos.)
  const { entorno } = await cargarAplicacion({
    "/api/planes": [unPlan({ cultivo_precedente: null, herramienta: null })],
  });
  const antes = montajes.length;
  await pulsar(entorno, "plan-ver");
  const plan = montajes[montajes.length - 1].elemento.props.planes[0];
  assert.ok(antes >= 0);
  assert.equal(plan.precedente, "", "dice el cultivo del año anterior sin saberlo");
  assert.equal(plan.herramienta, "", "dice si se usó herramienta sin saberlo");
});

test("al hacer el plan se pregunta si se ha usado una herramienta", async () => {
  const { entorno } = await cargarAplicacion({
    "/api/planes": { id: 3, cultivo: "Trigo blando", herramienta: true },
  });
  await pulsar(entorno, "plan-hacer");
  // El primer paso del plan pide la parcela, y el siguiente (el análisis) es opcional.
  await pulsar(entorno, "elegir", { campo: "parcela_id", valor: 1, superficie: 2.43 });
  await pulsar(entorno, "asistente-saltar");
  escribir(entorno, "cultivo", "Trigo blando");
  await pulsar(entorno, "asistente-seguir");
  const conPregunta = await avanzarHasta(entorno, "¿Has usado un programa o una herramienta para hacerlo?");
  assert.ok(conPregunta, "no pregunta si se usó una herramienta");
  await pulsar(entorno, "elegir", { campo: "herramienta", valor: "bool:true" });
  await avanzarHasta(entorno, "APUNTARLO");
  await pulsar(entorno, "asistente-seguir");
  assert.ok(
    entorno && pantallaPedida(entorno).length > 0,
    "el plan no se ha podido guardar",
  );
});

// ---------------------------------------------------------------------------
// El mapa del SIGPAC se pasó a React (ronda 58)
//
// Es la primera pantalla migrada **que se toca con el dedo**: el toque lo sigue atendiendo el
// manejador delegado de `document` (necesita saber **dónde** se ha tocado), así que lo que se
// comprueba aquí es que el mapa se le pide a React con las imágenes, la caja que se está mirando y lo
// que ha contestado el SIGPAC. Lo que se ve dentro está en `tests_js/react.test.js`.
// ---------------------------------------------------------------------------

/** Lo que se le ha pedido a React en el último montaje. */
function loPedido() {
  return montajes[montajes.length - 1].elemento;
}

test("el mapa se le pide a React, centrado en la tierra del agricultor", async () => {
  // Se abre centrado en su primera parcela: si tiene parcelas, ya se sabe por dónde empezar.
  const { entorno } = await cargarAplicacion({ "/api/parcelas": misParcelas() });
  await pulsar(entorno, "anadir-maestro", { tipo: "parcela" });
  await pulsar(entorno, "mapa-abrir");

  const elemento = loPedido();
  assert.equal(elemento.type.name, "PantallaMapa");
  assert.equal(elemento.props.centrado, true, "no se sabe por dónde empezar");
  assert.ok(
    elemento.props.imagenes.foto.includes("/api/mapa/imagen?capa=foto"),
    "no pide la foto del campo",
  );
  assert.ok(
    elemento.props.imagenes.linderos.includes("/api/mapa/imagen?capa=linderos"),
    "no pide los linderos",
  );
  // El dibujo lleva el tamaño de la imagen: los puntos del trozo vienen en esos píxeles.
  assert.equal(elemento.props.imagenes.vista, "0 0 900 600");
  // Los números van en castellano (con coma): los lee un agricultor, no un ordenador.
  assert.ok(
    elemento.props.centro.includes("40,90580"),
    `no se centra en su parcela: ${elemento.props.centro}`,
  );
  assert.equal(elemento.props.cargando, false, "se queda en «cargando»");
});

test("tocar el mapa pregunta por ese punto, no por otro", async () => {
  // La cuenta: la caja que se enseña va de -5.5759 a -5.5359 de longitud y de 40.9018 a 40.9098
  // de latitud (4,9016 ha no, la caja del mapa). Tocar en el centro tiene que preguntar por el
  // centro, y tocar a la izquierda por un punto más al oeste.
  const { entorno, servidor } = await cargarAplicacion({
    "/api/parcelas": misParcelas(),
    "/api/mapa/punto": unaParcelaDelMapa(),
  });
  await pulsar(entorno, "anadir-maestro", { tipo: "parcela" });
  await pulsar(entorno, "mapa-abrir");
  await tocarElMapa(entorno, 450, 300); // el centro de la imagen de 900×600

  const llamada = servidor.llamadas.find((r) => r.includes("/api/mapa/punto"));
  assert.ok(llamada, `no ha preguntado por el punto: ${servidor.llamadas.join(", ")}`);

  // Y lo que ha contestado el SIGPAC llega preparado al componente: sus filas, el trozo dibujado y
  // los botones de apuntarla o decir que no es esa.
  const elemento = loPedido();
  assert.equal(elemento.type.name, "PantallaMapa");
  const elegido = elemento.props.elegido;
  assert.ok(elegido, "no le llega lo que ha contestado el SIGPAC");
  const filas = JSON.stringify(elegido.filas);
  assert.ok(filas.includes("37-70-0-0-503-51-1"), "no viene la referencia");
  assert.ok(filas.includes("4,9016"), "no viene la superficie");
  assert.ok(filas.includes("TA — TIERRAS ARABLES"), "no viene el uso como lo dice el SIGPAC");
  assert.ok(filas.includes("Calvarrasa de Arriba"), "no viene el pueblo");
  assert.ok(filas.includes("37070A503000510000AQ"), "no viene la referencia catastral");
  assert.ok(elemento.props.poligono.includes(","), "no viene el trozo para dibujarlo");
  // **En el mapa sale marcado «no lo sé» y ningún sistema** (A10, 05/10/2026): esta prueba pedía antes
  // el secano «por defecto». El mapa no puede declarar de secano una tierra que el agricultor no ha
  // mirado: lo que sale marcado es «no lo sé», y sigue habiendo los tres botones para cambiarlo.
  assert.equal(elegido.sistemas.length, 3, "el mapa no ofrece «no lo sé»");
  assert.ok(
    elegido.sistemas.some((sistema) => sistema.elegido && sistema.valor === "nulo"),
    "no viene marcado «no lo sé» en el mapa: el sistema no se adivina",
  );
  assert.ok(
    elegido.sistemas.every((sistema) => !sistema.elegido || sistema.valor === "nulo"),
    "el mapa da por elegido un sistema que nadie ha dicho",
  );
});

test("el botón del centro pregunta por lo que está debajo de la cruz", async () => {
  const { entorno, servidor } = await cargarAplicacion({
    "/api/parcelas": misParcelas(),
    "/api/mapa/punto": unaParcelaDelMapa(),
  });
  await pulsar(entorno, "anadir-maestro", { tipo: "parcela" });
  await pulsar(entorno, "mapa-abrir");
  await pulsar(entorno, "mapa-preguntar");
  assert.ok(
    servidor.llamadas.some((r) => r.includes("/api/mapa/punto")),
    "el botón del centro no pregunta nada",
  );
});

test("acercar y alejar cambian la zona que se enseña", async () => {
  const { entorno } = await cargarAplicacion({ "/api/parcelas": misParcelas() });
  await pulsar(entorno, "anadir-maestro", { tipo: "parcela" });
  await pulsar(entorno, "mapa-abrir");
  const ancha = loPedido().props.imagenes.foto;
  await pulsar(entorno, "mapa-acercar");
  const cerca = loPedido().props.imagenes.foto;

  const caja = (url) => {
    const encontrado = url.match(
      /oeste=(-?[\d.]+)&(?:amp;)?sur=(-?[\d.]+)&(?:amp;)?este=(-?[\d.]+)&(?:amp;)?norte=(-?[\d.]+)/,
    );
    return encontrado ? encontrado.slice(1).map(Number) : null;
  };
  const antes = caja(ancha);
  const despues = caja(cerca);
  assert.ok(antes && despues, "no se puede leer la zona del mapa");
  assert.ok(
    despues[2] - despues[0] < antes[2] - antes[0],
    `acercar no ha acercado: ${antes} -> ${despues}`,
  );
  await pulsar(entorno, "mapa-alejar");
  await pulsar(entorno, "mapa-alejar");
  const lejos = caja(loPedido().props.imagenes.foto);
  assert.ok(lejos[2] - lejos[0] > antes[2] - antes[0], "alejar no ha alejado");
});

test("«ESTOY AQUÍ» pone el mapa donde está el agricultor y dice qué parcela es", async () => {
  const { entorno, servidor } = await cargarAplicacion(
    { "/api/parcelas": [], "/api/mapa/punto": unaParcelaDelMapa() },
    { ubicacion: [-5.5547, 40.9073] },
  );
  await pulsar(entorno, "anadir-maestro", { tipo: "parcela" });
  await pulsar(entorno, "mapa-abrir");
  await pulsar(entorno, "mapa-estoy-aqui");
  const elemento = loPedido();
  assert.ok(
    elemento.props.centro.includes("40,90730"),
    `no se ha centrado donde está: ${elemento.props.centro}`,
  );
  assert.ok(
    servidor.llamadas.some((r) => r.includes("/api/mapa/punto")),
    "no ha preguntado qué parcela es la suya",
  );
  assert.ok(
    JSON.stringify(elemento.props.elegido.filas).includes("37-70-0-0-503-51-1"),
    "no dice qué parcela ha encontrado",
  );
});

test("sin ubicación y sin parcelas, el mapa lo dice en vez de enseñar otro sitio", async () => {
  const { entorno } = await cargarAplicacion({ "/api/parcelas": [] }, { sinUbicacion: true });
  await pulsar(entorno, "anadir-maestro", { tipo: "parcela" });
  await pulsar(entorno, "mapa-abrir");
  const elemento = loPedido();
  // Ni se pinta el mapa (`centrado` en falso) y se dice por qué, con el botón de pedir la ubicación:
  // es lo único que puede hacer el agricultor en ese caso.
  assert.equal(elemento.props.centrado, false, "pinta un mapa de un sitio que no es el suyo");
  assert.ok(
    elemento.props.error.includes("No se puede saber por dónde empezar"),
    `no explica por qué no hay mapa: ${elemento.props.error}`,
  );
});

test("apuntar la parcela del mapa manda la referencia y lo que trajo el SIGPAC", async () => {
  const { entorno, servidor } = await cargarAplicacion({
    "/api/parcelas": misParcelas(),
    "/api/mapa/punto": unaParcelaDelMapa(),
    "/api/parcelas/desde-sigpac": {
      id: 2,
      alias: "Parcela 51, recinto 1",
      ref_sigpac: "37-70-0-0-503-51-1",
      superficie_ha: 4.9016,
      uso_sigpac: "TA",
      pendiente_pct: 1,
      provincia: "Salamanca",
      municipio: "Calvarrasa de Arriba",
    },
  });
  await pulsar(entorno, "anadir-maestro", { tipo: "parcela" });
  await pulsar(entorno, "mapa-abrir");
  await pulsar(entorno, "mapa-preguntar");
  escribir(entorno, "alias_mapa", "El llano");
  await pulsar(entorno, "mapa-apuntar");

  assert.ok(
    servidor.llamadas.includes("/api/parcelas/desde-sigpac"),
    `no ha apuntado la parcela: ${servidor.llamadas.join(", ")}`,
  );
  // La confirmación de lo traído se le pide a React, con los cuatro datos de la tierra.
  const confirmacion = confirmacionPedida();
  assert.equal(
    confirmacion.titulo,
    "Parcela traída del SIGPAC",
    `no va a la pantalla de traída: ${confirmacion.titulo}`,
  );
});

test("«NO ES ESA» quita la parcela y deja seguir buscando", async () => {
  const { entorno } = await cargarAplicacion({
    "/api/parcelas": misParcelas(),
    "/api/mapa/punto": unaParcelaDelMapa(),
  });
  await pulsar(entorno, "anadir-maestro", { tipo: "parcela" });
  await pulsar(entorno, "mapa-abrir");
  await pulsar(entorno, "mapa-preguntar");
  await pulsar(entorno, "mapa-no-es-esa");
  const elemento = loPedido();
  assert.ok(!elemento.props.elegido, "sigue preguntando por la que no es");
  assert.equal(elemento.props.centrado, true, "no deja volver a buscar");
});

test("si el punto no tiene parcela, se dice con palabras", async () => {
  const { entorno } = await cargarAplicacion({
    "/api/parcelas": misParcelas(),
    "/api/mapa/punto": { encontrado: false, mensaje: "Ahí no hay ninguna parcela del SIGPAC." },
  });
  await pulsar(entorno, "anadir-maestro", { tipo: "parcela" });
  await pulsar(entorno, "mapa-abrir");
  await pulsar(entorno, "mapa-preguntar");
  const elemento = loPedido();
  assert.ok(elemento.props.error.includes("no hay ninguna parcela"), "no dice que ahí no hay nada");
  assert.ok(!elemento.props.elegido, "pregunta por una parcela que no existe");
});

test("la zona de nitratos se cuenta como es: sí, una parte, no, o no se sabe", async () => {
  const casos = [
    [{ en_zona_de_nitratos: true, zona_de_nitratos_porcentaje: 100 }, "está en zona de nitratos"],
    [
      { en_zona_de_nitratos: true, zona_de_nitratos_porcentaje: 32.5 },
      "el 33 % de tu tierra está en zona de nitratos",
    ],
    [{ en_zona_de_nitratos: false, zona_de_nitratos_porcentaje: 0 }, "No está en zona de nitratos"],
    [
      { en_zona_de_nitratos: null, zona_de_nitratos_porcentaje: null },
      "No se ha podido comprobar",
    ],
  ];
  for (const [cambios, esperado] of casos) {
    const { entorno } = await cargarAplicacion({
      "/api/parcelas": misParcelas(),
      "/api/mapa/punto": unaParcelaDelMapa(cambios),
    });
    await pulsar(entorno, "anadir-maestro", { tipo: "parcela" });
    await pulsar(entorno, "mapa-abrir");
    await pulsar(entorno, "mapa-preguntar");
    const filas = JSON.stringify(loPedido().props.elegido.filas);
    assert.ok(filas.includes(esperado), `${JSON.stringify(cambios)} no dice «${esperado}»`);
  }
});

test("volver desde el mapa deja el alta de parcela como estaba", async () => {
  const { entorno } = await cargarAplicacion({ "/api/parcelas": misParcelas() });
  await pulsar(entorno, "anadir-maestro", { tipo: "parcela" });
  await pulsar(entorno, "mapa-abrir");
  await pulsar(entorno, "mapa-volver");
  const codigos = confirmacionPedida().acciones.map((accion) => accion.accion);
  assert.ok(codigos.includes("mapa-abrir"), "no ha vuelto a la elección");
  assert.ok(codigos.includes("sigpac-si"), "se ha perdido el camino de la referencia");
});

test("una labor pregunta con qué máquina se hizo", async () => {
  // El contenido mínimo del CUE pide la maquinaria en los bloques de labores y de siembra, y solo
  // la preguntaban los tratamientos: se podía apuntar que se labró y no con qué.
  const { entorno, servidor } = await cargarAplicacion({
    "/api/labores": { id: 9, tipo: "laboreo", fecha: "2026-04-10", equipo_id: 3, anulado: false },
    "/api/equipos": [
      {
        id: 3,
        nombre: "Pulverizador grande",
        tipo: "Atomizador",
        numero_roma: "ROMA-9876",
        numero_serie: null,
        fecha_iteaf: "2024-03-01",
        fecha_proxima_iteaf: "2029-03-01",
      },
    ],
  });
  await pulsar(entorno, "trabajo", { tipo: "laboreo" });
  await pulsar(entorno, "elegir", { campo: "parcela_id", valor: 1, superficie: 2.43 });
  escribir(entorno, "fecha", "2026-04-10");
  await pulsar(entorno, "asistente-seguir"); // la fecha
  escribir(entorno, "superficie_ha", "2,43");
  await pulsar(entorno, "asistente-seguir"); // la superficie

  // Los pasos opcionales hasta llegar a la máquina (se saltan con DEJARLO).
  for (let intentos = 0; intentos < 4; intentos += 1) {
    const html = pantallaPedida(entorno);
    if (html.includes("¿Con qué máquina lo has hecho?")) break;
    await pulsar(entorno, "asistente-saltar");
  }
  const conMaquina = pantallaPedida(entorno);
  assert.ok(
    conMaquina.includes("¿Con qué máquina lo has hecho?"),
    `no pregunta por la máquina: ${conMaquina.slice(0, 300)}`,
  );
  // Las máquinas las dibuja React (la pieza `ListaParaElegir`): lo que se mira es lo que se le pide,
  // con su acción y su `data-campo`, que es lo que lee el manejador de clics.
  const maquinas = botonesDeLaLista();
  assert.ok(
    maquinas.some((boton) => boton.etiqueta === "Pulverizador grande"),
    `no ofrece las máquinas apuntadas: ${maquinas.map((b) => b.etiqueta).join(", ")}`,
  );
  assert.equal(maquinas[0].datos.campo, "equipo_id", "la máquina no dice a qué campo contesta");

  await pulsar(entorno, "elegir", { campo: "equipo_id", valor: 3 });
  await pulsar(entorno, "asistente-seguir"); // es el último paso: aquí se apunta la labor
  assert.ok(
    servidor.llamadas.includes("/api/labores"),
    `no ha apuntado la labor: ${servidor.llamadas.join(", ")}`,
  );
});

test("al elegir la máquina de un trabajo se avisa de lo que hay que mirar", async () => {
  // **Los «avisos al planificar un trabajo» del contrato (T14, 03/10/2026).** El sitio donde de verdad
  // hacen falta es el paso en el que se elige con qué se hace el trabajo: de nada sirve decirlo en la
  // ficha de la máquina si el agricultor ya ha enganchado el remolque. El aviso es el mismo que calcula el
  // servidor (`/api/maquinaria/avisos`) y que enseña su ficha, así que las dos pantallas no pueden decir
  // cosas distintas de la misma máquina.
  const { entorno } = await cargarAplicacion({
    "/api/labores": { id: 9, tipo: "laboreo", fecha: "2026-04-10", equipo_id: 3, anulado: false },
    "/api/equipos": [
      {
        id: 3,
        nombre: "Pulverizador grande",
        tipo: "Atomizador",
        numero_roma: "ROMA-9876",
        numero_serie: null,
        fecha_iteaf: "2024-03-01",
        fecha_proxima_iteaf: "2029-03-01",
      },
    ],
    // Un aviso vencido y otro de disponibilidad, los dos de la máquina que **es** ese equipo del cuaderno
    // (así se pasa de la hoja 1.3 a la lista de maquinaria). Y un tercero de otra máquina, que no se tiene
    // que colar aquí.
    "/api/maquinaria/avisos": [
      {
        codigo: "M4_una_inspeccion_esta_vencida",
        mensaje: "La ITEAF de «Pulverizador grande» venció el 12/05/2026. Pide cita antes de usarla.",
        tipo: "iteaf",
        urgente: true,
        maquina_id: 1,
        maquina: "Pulverizador grande",
        equipo_aplicacion_id: 3,
      },
      {
        codigo: "M1_la_maquina_no_esta_disponible",
        mensaje: "«El Landini» está apuntada como que no puedes contar con ella.",
        tipo: "disponibilidad",
        urgente: true,
        maquina_id: 2,
        maquina: "El Landini",
        equipo_aplicacion_id: 9,
      },
    ],
  });
  await pulsar(entorno, "trabajo", { tipo: "laboreo" });
  await pulsar(entorno, "elegir", { campo: "parcela_id", valor: 1, superficie: 2.43 });
  escribir(entorno, "fecha", "2026-04-10");
  await pulsar(entorno, "asistente-seguir");
  escribir(entorno, "superficie_ha", "2,43");
  await pulsar(entorno, "asistente-seguir");
  for (let intentos = 0; intentos < 4; intentos += 1) {
    const html = pantallaPedida(entorno);
    if (html.includes("¿Con qué máquina lo has hecho?")) break;
    await pulsar(entorno, "asistente-saltar");
  }
  const maquinas = botonesDeLaLista();
  const suya = maquinas.find((boton) => boton.etiqueta === "Pulverizador grande");
  assert.ok(suya, "no ofrece la máquina del cuaderno");
  assert.match(
    suya.pista,
    /La ITEAF de «Pulverizador grande» venció el 12\/05\/2026/,
    `no avisa de la inspección vencida al planificar: «${suya.pista}»`,
  );
  // Y la fecha de la ITEAF que ya se enseñaba sigue estando: el aviso se **añade**, no sustituye.
  assert.match(suya.pista, /ITV hasta 01\/03\/2029/);
  // Y el aviso de otra máquina no se cuela en esta lista.
  assert.doesNotMatch(suya.pista, /El Landini/);
});

test("lo escrito en el formulario de una máquina no se pierde al elegir una opción", async () => {
  // **La trampa que ya costó una ronda en este programa**: pintar la pantalla borra la casilla. En este
  // formulario se elige con botones (la clase, la propiedad, la disponibilidad) y se escribe con el
  // teclado, así que elegir una opción **repinta** el formulario entero: si lo escrito viviera solo en las
  // casillas, el agricultor escribiría la matrícula, tocaría «Es mía» y la matrícula desaparecería.
  const { entorno } = await cargarAplicacion({
    "/api/maquinaria": {
      maquinas: [],
      total: 0,
      con_avisos: 0,
      con_avisos_urgentes: 0,
      equipos_sin_ficha: [],
      que_falta: [],
    },
  });
  await pulsar(entorno, "maquinaria-ver");
  await pulsar(entorno, "maquina-nueva");
  escribir(entorno, "maquina-nombre", "El Landini");
  escribir(entorno, "maquina-clasificacion", "Pulverizador arrastrado");
  escribir(entorno, "maquina-horas", "2400");
  await pulsar(entorno, "maquina-elegir", { campo: "clase", valor: "tractor" });
  const html = pantallaPedida(entorno);
  assert.ok(html.includes("El Landini"), "al elegir la clase se ha borrado el nombre");
  assert.ok(
    html.includes("Pulverizador arrastrado"),
    "al elegir la clase se ha borrado la clasificación técnica",
  );
  assert.ok(html.includes("2400"), "al elegir la clase se han borrado las horas");
});

test("si la semilla viene tratada, la siembra pregunta qué le echaron", async () => {
  // Es el bloque «uso de semilla tratada» del anexo II: hasta la ronda 5 solo se apuntaba «semilla
  // tratada: sí», que dice que sí pero no qué. Y se pregunta **solo si** venía tratada: preguntar
  // por el tratamiento de una semilla sin tratar sería preguntar por algo que no existe.
  const { entorno, servidor } = await cargarAplicacion({
    "/api/labores": { id: 11, tipo: "siembra", fecha: "2026-03-01", anulado: false },
  });
  await pulsar(entorno, "trabajo", { tipo: "siembra" });
  await pulsar(entorno, "elegir", { campo: "parcela_id", valor: 1, superficie: 2.43 });

  // Hasta el paso donde se dice si la semilla venía tratada.
  const conTratada = await avanzarHasta(entorno, "¿La semilla venía tratada?");
  assert.ok(conTratada, "no pregunta si la semilla venía tratada");
  await pulsar(entorno, "elegir", { campo: "material_tratado", valor: "bool:true" });

  // Y ahora sí: el paso del tratamiento que recibió.
  const conTratamiento = await avanzarHasta(entorno, "¿Qué le habían echado a la semilla?");
  escribir(entorno, "tratamiento_semilla", "Imidacloprid + tiram");
  escribir(entorno, "fecha_tratamiento_semilla", "2026-02-01");
  await pulsar(entorno, "elegir", { campo: "eficacia_tratamiento_semilla", valor: "bien" });
  await avanzarHasta(entorno, "APUNTARLO");
  await pulsar(entorno, "asistente-seguir"); // es el último paso: aquí se apunta la siembra

  assert.ok(
    servidor.llamadas.includes("/api/labores"),
    `no ha apuntado la siembra: ${servidor.llamadas.join(", ")}`,
  );
});

test("si la semilla NO viene tratada, no se pregunta por su tratamiento", async () => {
  const { entorno } = await cargarAplicacion({
    "/api/labores": { id: 12, tipo: "siembra", fecha: "2026-03-01", anulado: false },
  });
  await pulsar(entorno, "trabajo", { tipo: "siembra" });
  await pulsar(entorno, "elegir", { campo: "parcela_id", valor: 1, superficie: 2.43 });
  await avanzarHasta(entorno, "¿La semilla venía tratada?");
  await pulsar(entorno, "elegir", { campo: "material_tratado", valor: "bool:false" });
  await pulsar(entorno, "asistente-seguir");

  const html = pantallaPedida(entorno);
  assert.ok(
    !html.includes("¿Qué le habían echado a la semilla?"),
    `pregunta por el tratamiento de una semilla sin tratar: ${html.slice(0, 300)}`,
  );
});

test("otras altas no pasan por el SIGPAC", async () => {
  // La pregunta del SIGPAC es solo para parcelas: un abono o una máquina no tiene recinto.
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "anadir-maestro", { tipo: "abono" });
  const html = pantallaPedida(entorno);
  assert.ok(idsDeLosBloques().includes("nombre"), `no es el alta de abono: ${html.slice(0, 200)}`);
  assert.ok(!html.includes("Traer la parcela del SIGPAC"));
});
// ---------------------------------------------------------------------------
// El asesor, la semilla y el agua
// ---------------------------------------------------------------------------

// La sección del asesor y su número (ROPO) dentro de «mis cosas» se comprueban ahora en
// `tests_js/react.test.js`, contra el componente. Aquí se sigue comprobando **el alta**, que es
// cosa del asistente y del manejador de clics.

test("añadir un asesor empieza pidiendo el número, no el nombre", async () => {
  // El número es lo que bloquea: sin él la Junta rechaza el tratamiento entero, así que se
  // pregunta antes de que el agricultor se confíe.
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "anadir-maestro", { tipo: "asesor" });
  const html = pantallaPedida(entorno);
  assert.ok(html.includes("¿Cómo se llama tu técnico?"), `no empieza por el nombre: ${html.slice(0, 200)}`);
  assert.ok(html.includes("¿De qué te asesora?") === false, "pregunta todo de golpe");
});

test("las listas del agua salen en la pantalla, no un cuadro de texto", async () => {
  // Para que el agricultor elija en vez de escribir: si escribe a mano salen diez formas de
  // decir «pozo» y después no se pueden sumar ni comparar.
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "inicio", { ir: "trabajo" });
  await pulsar(entorno, "trabajo", { tipo: "riego" });
  await pulsar(entorno, "elegir", { campo: "parcela_id", valor: "1", superficie: "2.43" });
  await pulsar(entorno, "asistente-seguir"); // la fecha
  await pulsar(entorno, "asistente-seguir"); // las hectáreas
  const html = pantallaPedida(entorno);
  assert.ok(html.includes("¿Cuánta agua has echado?"), `no pregunta el agua: ${html.slice(0, 250)}`);
  // El agua se pide con la pieza de los grupos de campos, y dos de sus datos son listas.
  const textos = textosDeLosBloques();
  assert.ok(textos.includes("Aspersión"), `no ofrece la lista de sistemas de riego: ${textos}`);
  assert.ok(textos.includes("metros cúbicos"), `no ofrece las unidades del agua: ${textos}`);
});

test("el riego pregunta de dónde sale el agua y sus nitratos", async () => {
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "inicio", { ir: "trabajo" });
  await pulsar(entorno, "trabajo", { tipo: "riego" });
  await pulsar(entorno, "elegir", { campo: "parcela_id", valor: "1", superficie: "2.43" });
  await pulsar(entorno, "asistente-seguir"); // la fecha
  await pulsar(entorno, "asistente-seguir"); // las hectáreas
  await pulsar(entorno, "asistente-saltar"); // el agua
  const html = pantallaPedida(entorno);
  assert.ok(html.includes("¿De dónde ha salido el agua?"), "no pregunta el origen");
  const origenes = opcionesDelBloque("origen_agua").join(" | ");
  assert.ok(origenes.includes("Pozo o sondeo"), `no ofrece la lista de orígenes: ${origenes}`);
});

test("«otro trabajo» pregunta cuál, y ofrece el pastoreo y la cubierta", async () => {
  // **Este test es nuevo de la ronda 14, y el fallo que cierra era de fondo.** Antes, pulsar
  // «OTRO TRABAJO» guardaba la palabra «otra» y ahí se acababa: el agricultor no podía decir si
  // había labrado, podado o pastado, y en el cuaderno todo eso quedaba igual. El documento
  // oficial de la Junta nombra tres prácticas para ese apartado —«Laboreo, mantenimiento de
  // cubierta, pastoreo»— y dos de ellas no existían ni como opción.
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "inicio", { ir: "trabajo" });
  await pulsar(entorno, "trabajo", { tipo: "otra" });
  await pulsar(entorno, "elegir", { campo: "parcela_id", valor: "1", superficie: "2.43" });
  await pulsar(entorno, "asistente-seguir"); // la fecha
  const html = pantallaPedida(entorno);
  assert.ok(html.includes("¿Cuál de estos?"), `no pregunta cuál: ${html.slice(0, 250)}`);
  // Las prácticas las dibuja la lista de React (la pieza `ListaParaElegir`): lo que se mira es lo que
  // se le ha pedido a la pieza.
  const lista = textoDeLaLista();
  assert.ok(lista.includes("HE MANTENIDO LA CUBIERTA"), `no ofrece el mantenimiento de cubierta: ${lista}`);
  assert.ok(lista.includes("HA PASTADO EL GANADO"), "no ofrece el pastoreo");
  assert.ok(lista.includes("HE LABRADO LA TIERRA"), "no ofrece el laboreo");
  assert.ok(lista.includes("OTRA COSA"), "no deja salir por la puerta de atrás");
});

/**
 * El resumen del asistente, tal y como se le ha pedido a React.
 *
 * **El resumen ya no es HTML**: es una **pieza** de React (`react/piezas/resumen_del_apunte.js`) que se
 * monta en el hueco del formulario, así que lo que hay que mirar es lo que se le ha pedido, no el HTML
 * del contenedor. Devuelve las filas en un solo texto, para poder buscar dentro.
 */
function resumenPedido() {
  const resumen = piezasPedidas().find((uno) => uno && uno.type && uno.type.name === "ResumenDelApunte");
  assert.ok(
    resumen,
    `el último montaje no trae el resumen: ${piezasPedidas().map((uno) => uno && uno.type && uno.type.name).join(", ")}`,
  );
  const filas = resumen.props.filas.map(([etiqueta, valor]) => `${etiqueta}: ${valor}`);
  const espera = resumen.props.espera;
  return [...filas, espera ? espera.texto : "", espera ? espera.dias : ""].join(" | ");
}

/**
 * La lista de botones del asistente, tal y como se le ha pedido a React.
 *
 * **La lista ya no es HTML**: es la **pieza** `react/piezas/lista_para_elegir.js`, que se monta en el
 * hueco del formulario. Lo que hay que mirar es lo que se le ha pedido, no el HTML del contenedor (el
 * DOM de mentira no monta React, así que ahí no hay nada). Es la misma lección que trajo el resumen.
 */
function listaPedida() {
  const lista = piezasPedidas().find((uno) => uno && uno.type && uno.type.name === "ListaParaElegir");
  assert.ok(
    lista,
    `el último montaje no trae una lista de elegir: ${piezasPedidas().map((uno) => uno && uno.type && uno.type.name).join(", ")}`,
  );
  return lista.props;
}

/** Todos los botones de la lista pedida, en un solo arreglo, en su orden. */
function botonesDeLaLista() {
  const lista = listaPedida();
  return (lista.bloques || []).flatMap((bloque) => bloque.botones || []);
}

/**
 * Los botones que van marcados (los que el agricultor ya había elegido).
 *
 * Son dos formas de decir lo mismo, y las dos cuentan, porque las dos existen: los botones normales se
 * marcan con la clase `boton-elegido` y **las tarjetas de tierra** con `elegida: true` (que además saca
 * la palabra «ELEGIDA» y el círculo marcado). Se mira lo que dice cada uno, no cómo se pinta.
 */
function botonesMarcados() {
  return botonesDeLaLista().filter(
    (boton) => boton.clase === "boton-elegido" || boton.elegida === true,
  );
}

/** Todo el texto de la lista pedida —avisos, títulos, pistas y botones—, para poder buscar dentro. */
function textoDeLaLista() {
  const lista = listaPedida();
  const trozos = [];
  if (lista.aviso) {
    trozos.push(lista.aviso.texto);
    if (lista.aviso.boton) trozos.push(lista.aviso.boton.etiqueta);
  }
  for (const bloque of lista.bloques || []) {
    trozos.push(bloque.titulo, bloque.pista);
    for (const boton of bloque.botones || []) {
      // Los botones normales llevan su pista; las tarjetas de tierra llevan sus líneas y sus avisos.
      trozos.push(boton.etiqueta, boton.pista, ...(boton.lineas || []), ...(boton.avisos || []));
    }
  }
  return trozos.filter(Boolean).join(" | ");
}

/**
 * El aviso de la lista pedida (lo que se le dice al agricultor cuando no puede elegir nada), con su
 * botón y su pista. Se devuelve como texto, para buscar dentro igual que en `textoDeLaLista`.
 *
 * **Se busca la lista que trae el aviso**, no «la última»: hay pasos que montan dos listas (la de las
 * diez medidas y, debajo, el aviso de que la finca no ha declarado nada), y el aviso está en la segunda.
 */
function avisoDeLaLista() {
  const conAviso = piezasPedidas()
    .filter((uno) => uno && uno.type && uno.type.name === "ListaParaElegir")
    .map((uno) => uno.props)
    .find((props) => props.aviso);
  assert.ok(conAviso, "no se le ha pedido ningún aviso a la lista");
  const aviso = conAviso.aviso;
  return [aviso.texto, aviso.pista, aviso.boton ? aviso.boton.etiqueta : ""].filter(Boolean).join(" | ");
}

test("lo que se apunta es la práctica elegida, no la palabra «otra»", async () => {
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "inicio", { ir: "trabajo" });
  await pulsar(entorno, "trabajo", { tipo: "otra" });
  await pulsar(entorno, "elegir", { campo: "parcela_id", valor: "1", superficie: "2.43" });
  await pulsar(entorno, "asistente-seguir"); // la fecha
  await pulsar(entorno, "elegir", { campo: "tipo", valor: "pastoreo" });
  await pulsar(entorno, "asistente-seguir"); // la superficie
  await pulsar(entorno, "asistente-saltar"); // los detalles
  await pulsar(entorno, "asistente-saltar"); // las preguntas propias del pastoreo
  // El resumen es lo último que ve el agricultor antes de apuntarlo: tiene que decir «Pastoreo»,
  // no «otra», y no un código en minúsculas.
  const resumen = resumenPedido();
  assert.ok(resumen.includes("Pastoreo"), `el resumen no dice la práctica: ${resumen}`);
});

test("la cubierta pregunta establecimiento y anchuras por separado", async () => {
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "inicio", { ir: "trabajo" });
  await pulsar(entorno, "trabajo", { tipo: "otra" });
  await pulsar(entorno, "elegir", { campo: "parcela_id", valor: "1", superficie: "2.43" });
  await pulsar(entorno, "asistente-seguir");
  await pulsar(entorno, "elegir", { campo: "tipo", valor: "cubierta" });
  await pulsar(entorno, "asistente-seguir");
  await pulsar(entorno, "asistente-saltar");
  // Las cuatro preguntas de la cubierta las pide React con la pieza de los grupos de campos: lo que
  // importa es que se le pidan con el `id` de siempre, que es lo único que tiene `app.js` para leerlas.
  const ids = idsDeLosBloques();
  for (const id of ["fecha_establecimiento_cubierta", "anchura_cubierta_m", "anchura_libre_proyeccion_m"]) {
    assert.ok(ids.includes(id), `no se pregunta «${id}»: ${ids.join(", ")}`);
  }
});

test("la cosecha pregunta las cuatro decisiones sin suponer que sean no", async () => {
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "inicio", { ir: "trabajo" });
  await pulsar(entorno, "trabajo", { tipo: "cosecha" });
  await pulsar(entorno, "elegir", { campo: "parcela_id", valor: "1", superficie: "2.43" });
  await pulsar(entorno, "asistente-seguir");
  await pulsar(entorno, "asistente-saltar");
  // Las cuatro decisiones se piden como cuatro bloques de elegir («sí», «no»), no como un cuadro de
  // texto: son preguntas que hay que poder contestar sin escribir nada.
  const pedidas = textosDeLosBloques();
  for (const pregunta of ["¿Sacaste semilla", "¿Recogiste plantas", "¿Dejaste algo sin cosechar", "¿Dejaste los restos"]) {
    assert.ok(pedidas.includes(pregunta), `${pregunta} · se ha pedido: ${pedidas.slice(0, 300)}`);
  }
});

test("las prácticas que ya tienen su botón no se vuelven a preguntar", async () => {
  // Sembrar, plantar, regar y coger la cosecha tienen su botón en la pantalla de inicio. Si
  // aparecieran otra vez aquí, el agricultor tendría dos caminos para apuntar lo mismo y no
  // sabría cuál es el bueno.
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "inicio", { ir: "trabajo" });
  await pulsar(entorno, "trabajo", { tipo: "otra" });
  await pulsar(entorno, "elegir", { campo: "parcela_id", valor: "1", superficie: "2.43" });
  await pulsar(entorno, "asistente-seguir"); // la fecha
  const html = pantallaPedida(entorno);
  assert.ok(!html.includes("HE SEMBRADO"), "vuelve a ofrecer sembrar");
  assert.ok(!html.includes("HE REGADO"), "vuelve a ofrecer regar");
});

test("la siembra pregunta la semilla y su número de lote", async () => {
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "inicio", { ir: "trabajo" });
  await pulsar(entorno, "trabajo", { tipo: "siembra" });
  await pulsar(entorno, "elegir", { campo: "parcela_id", valor: "1", superficie: "2.43" });
  await pulsar(entorno, "asistente-seguir"); // la fecha
  await pulsar(entorno, "asistente-seguir"); // las hectáreas
  const html = pantallaPedida(entorno);
  assert.ok(html.includes("¿Cuánta semilla has echado?"), `no pregunta la semilla: ${html.slice(0, 250)}`);
  const ids = idsDeLosBloques();
  assert.ok(ids.includes("cantidad_semilla_kg"), `no pregunta cuánta semilla: ${ids.join(", ")}`);
  assert.ok(ids.includes("dosis_siembra_kg_ha"), "no pregunta la dosis de siembra");
});

test("el lote de la semilla se pregunta aparte, porque es lo que salva una partida", async () => {
  // Si un día hay un problema con un saco de semilla, el que tiene apuntado el lote es el
  // único que puede decir de dónde salió.
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "inicio", { ir: "trabajo" });
  await pulsar(entorno, "trabajo", { tipo: "siembra" });
  await pulsar(entorno, "elegir", { campo: "parcela_id", valor: "1", superficie: "2.43" });
  await pulsar(entorno, "asistente-seguir"); // la fecha
  await pulsar(entorno, "asistente-seguir"); // las hectáreas
  await pulsar(entorno, "asistente-saltar"); // la semilla
  const html = pantallaPedida(entorno);
  assert.ok(html.includes("¿De qué saco era la semilla?"), `no pregunta el lote: ${html.slice(0, 250)}`);
  assert.ok(idsDeLosBloques().includes("lote_semilla"), "no hay dónde escribir el lote");
});

// ---------------------------------------------------------------------------
// Lo que se vende
// ---------------------------------------------------------------------------

/** Una venta como la devuelve el servidor. */
function unaVenta(cambios = {}) {
  return {
    id: 1,
    campana_id: 1,
    tipo: "comercializada",
    etiqueta_tipo: "Venta a comprador",
    fecha: "2026-07-10",
    fecha_fin: null,
    producto: "Trigo blando",
    variedad: "Craklin",
    cantidad: 42000.0,
    unidad: "kg",
    etiqueta_unidad: "kilos",
    texto_cantidad: "42.000,00 kg",
    kilos: 42000.0,
    lote: "L-2026-07",
    comprador: "Cooperativa Agrícola de Peñaranda",
    numero_albaran: "ALB-2026-118",
    parcela_id: 1,
    grupo_id: null,
    donde: "El Prado",
    observaciones: null,
    anulado: false,
    ...cambios,
  };
}

/**
 * La tabla de lo que se ha vendido, como la devuelve `/api/ventas/tabla` (T12, 03/10/2026).
 *
 * Las columnas, las celdas y el pie **los compone el servidor** (el pie es la cuenta del conjunto
 * filtrado, y el dinero no se suma en el navegador: allí todo número es de coma flotante). Aquí se copia
 * lo que sirve, para poder comprobar que `app.js` se lo pasa a React sin recalcularlo.
 */
function unaTablaDeVentas(cambios = {}) {
  return {
    columnas: [
      { clave: "cliente", texto: "Cliente", ordenable: true },
      { clave: "producto", texto: "Producto", ordenable: true },
      { clave: "fecha", texto: "Fecha", ordenable: true },
      { clave: "cantidad", texto: "Cantidad", ordenable: true },
      { clave: "importe", texto: "Importe", ordenable: true },
      { clave: "vencimiento", texto: "Vencimiento", ordenable: true },
      { clave: "cobrado", texto: "Cobrado", ordenable: true },
      { clave: "pendiente", texto: "Pendiente", ordenable: true },
    ],
    filas: [
      {
        id: 1,
        cliente: "Cooperativa Agrícola de Peñaranda",
        producto: "Trigo blando",
        fecha: "10/07/2026",
        fecha_valor: "2026-07-10",
        cantidad: "42.000,00 kg",
        cantidad_valor: 42000.0,
        importe: "9.870,00 €",
        importe_valor: "9870.00",
        importe_conocido: true,
        vencimiento: "",
        vencimiento_valor: "",
        cobrado: "",
        cobrado_valor: "",
        pendiente: "",
        pendiente_valor: "",
        estado: "Sin facturar",
        clave_estado: "sin_facturar",
        estado_vencida: false,
        partida: "L-2026-07",
        albaran: "ALB-2026-118",
        donde: "El Prado",
        factura_emitida_id: null,
        factura_numero: "",
        facturada: false,
        aviso_facturada: "",
        ajustes: 0,
        de_que_cosecha: "",
      },
    ],
    pie: "1 entrega · 9.870,00 € · pendiente 0,00 €",
    avisos: [],
    totales: { importe: "9870.00", facturado: "0.00", cobrado: "0.00", pendiente: "0.00", entregas: 1, sin_importe: 0, por_cobrar: 0 },
    filtradas: 1,
    total: 1,
    ...cambios,
  };
}

test("sin ventas, mi cuaderno lo dice y ofrece apuntar una", async () => {
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "inicio", { ir: "mi_cuaderno" });
  const ventas = ultimoCuadernoPedido().ventas;
  assert.equal(ventas.titulo, "Lo que he vendido", "no hay apartado de ventas");
  assert.equal(ventas.hay, false);
  assert.ok(ventas.sin_nada.includes("Todavía no has apuntado ninguna venta este año."));
  assert.deepEqual(
    ventas.acciones.map((accion) => accion.accion),
    ["ventas-nueva"],
    "avisa pero no ofrece arreglarlo",
  );
});

test("con ventas, mi cuaderno las enseña con su cantidad y su comprador", async () => {
  const { entorno } = await cargarAplicacion({ "/api/ventas": [unaVenta()] });
  await pulsar(entorno, "inicio", { ir: "mi_cuaderno" });
  const ventas = ultimoCuadernoPedido().ventas;
  assert.equal(ventas.hay, true);
  // La venta llega a medias de preparar: la fecha escrita (y unida con su raya si salió en varios
  // viajes), el producto y la línea de detalle.
  const fila = ventas.filas[0];
  assert.equal(fila.producto, "Trigo blando", "no dice qué se vendió");
  assert.match(fila.fecha, /^\d{2}\/\d{2}\/\d{4}$/, `la fecha no viene escrita: ${fila.fecha}`);
  assert.ok(fila.detalle.includes("42.000,00 kg"), `no dice cuánto: ${fila.detalle}`);
  assert.ok(fila.detalle.includes("Cooperativa Agrícola de Peñaranda"), "no dice a quién");
  assert.ok(fila.detalle.includes("El Prado"), "no dice de dónde salió");
  // Y el resumen de arriba: cuántas y cuántos kilos, que es lo que se mira de un vistazo.
  assert.ok(ventas.resumen.includes("42.000"), `el resumen no lleva los kilos: ${ventas.resumen}`);
  assert.deepEqual(
    ventas.acciones.map((accion) => accion.accion),
    ["ventas-ver", "ventas-nueva"],
    "con ventas no se ofrece verlas todas",
  );
});

// ---------------------------------------------------------------------------
// «Lo que he vendido» se pasó a React en la ronda 43
//
// Aquí se comprueba el cableado: que la pantalla se le pide a React con las ventas **ya preparadas**
// (con su fecha escrita, su producto y su línea de detalle). Lo que se ve dentro —el albarán, el
// comprador, el aviso de que aquí no se apunta el precio y que sin ventas se dice— está en
// `tests_js/react.test.js`, contra el componente.
// ---------------------------------------------------------------------------

test("la pantalla de ventas se le pide a React, con la tabla y su pie", async () => {
  // CAMBIA CON EL T12 (03/10/2026), y con el motivo: la pantalla dejó de ser una lista de tarjetas y es
  // una **tabla** con las ocho columnas del contrato (§4, S12) y con el pie del conjunto filtrado. Lo que
  // se comprueba aquí sigue siendo lo mismo de siempre: que lo que `app.js` le pide a React lleva **los
  // datos ya preparados** —las columnas con su rótulo del servidor, las celdas escritas, el pie— y que la
  // pantalla no calcula nada de dinero.
  const { entorno } = await cargarAplicacion({
    "/api/ventas": [unaVenta()],
    "/api/ventas/tabla": unaTablaDeVentas(),
  });
  await pulsar(entorno, "inicio", { ir: "mi_cuaderno" });
  const antes = montajes.length;
  await pulsar(entorno, "ventas-ver");
  const pedidos = montajes.slice(antes);

  assert.equal(pedidos.length, 1, `se han pedido ${pedidos.length} montajes: solo las ventas`);
  const elemento = pedidos[0].elemento;
  assert.ok(elemento, "no se le pide nada a React: la pantalla se está pintando a mano otra vez");
  assert.equal(elemento.type.name, "PantallaVentas");

  const tabla = elemento.props.tabla;
  assert.ok(tabla, "no le llega la tabla de lo que se ha vendido");
  // **Las ocho columnas del contrato**, con su rótulo: las sirve el servidor y aquí solo se colocan.
  const rotulos = tabla.columnas.map((columna) => columna.texto);
  for (const esperado of [
    "Cliente",
    "Producto",
    "Fecha",
    "Cantidad",
    "Importe",
    "Vencimiento",
    "Cobrado",
    "Pendiente",
  ]) {
    assert.ok(rotulos.includes(esperado), `falta la columna «${esperado}»: ${rotulos.join(", ")}`);
  }
  // Y la fila, con sus celdas **una menos que columnas** (la última, «Acciones», la pinta la pieza).
  assert.ok(tabla.filas.length, "la tabla no lleva ninguna fila");
  assert.equal(
    tabla.filas[0].celdas.length + 1,
    tabla.columnas.length,
    "las celdas de la fila no cuadran con las columnas",
  );
  // El pie es la cuenta del conjunto filtrado, **ya compuesta por el servidor**: la pantalla no suma.
  assert.match(tabla.pie, /pendiente/, `el pie no dice lo que falta por cobrar: ${tabla.pie}`);
  // Y cada fila lleva sus acciones, que son el recorrido del dinero (poner el importe, facturar, ajustar)
  // más las de siempre.
  const acciones = tabla.filas[0].acciones.map((accion) => accion.accion);
  assert.ok(acciones.includes("venta-ajuste"), `la fila no deja apuntar una devolución: ${acciones}`);
  assert.ok(acciones.includes("cosa-corregir"));
  assert.ok(acciones.includes("cosa-borrar"));
  // Y el filtro con el que se ha pedido, para que la barra sepa qué está puesto.
  assert.deepEqual(elemento.props.filtros, { q: "", solo: "", orden: "", sentido: -1 });
});

test("apuntar una venta empieza preguntando cómo se vendió", async () => {
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "ventas-nueva");
  const html = pantallaPedida(entorno);
  assert.ok(html.includes("¿Cómo lo has vendido?"), `no pregunta el tipo: ${html.slice(0, 200)}`);
  // Las dos clases de venta se eligen de una lista (un bloque de elegir de la pieza), no se escriben.
  const valores = bloquesDelMaestroPedidos()
    .find((bloque) => bloque.campo === "tipo")
    .opciones.map((opcion) => opcion.valor);
  assert.deepEqual(valores, ["comercializada", "venta_directa"], `las clases no son las de la norma: ${valores}`);
});

test("elegido el tipo, pregunta qué se ha vendido y en qué variedad", async () => {
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "ventas-nueva");
  await pulsar(entorno, "elegir", { campo: "tipo", valor: "comercializada" });
  const html = pantallaPedida(entorno);
  assert.ok(html.includes("¿Qué has vendido?"), `no pregunta el producto: ${html.slice(0, 200)}`);
  const ids = idsDeLosBloques();
  assert.ok(ids.includes("producto"), `no hay dónde escribir el producto: ${ids.join(", ")}`);
  assert.ok(ids.includes("variedad"), "no hay dónde escribir la variedad");
});

/**
 * Escribe en una casilla del formulario, como lo haría el agricultor con el teclado.
 *
 * El DOM de mentira no tiene casillas: se le mete una con su valor. Hace falta para poder
 * recorrer un asistente en el que algo es obligatorio, porque si no, no se puede pasar de
 * la pantalla y el recorrido no se puede probar.
 */
function escribir(entorno, id, valor) {
  const nodo = entorno.nodos.get(id) || { id, value: "" };
  nodo.value = valor;
  entorno.nodos.set(id, nodo);
}

test("la cantidad y la unidad se preguntan juntas", async () => {
  // Son una sola idea: separarlas obligaría a pasar dos pantallas para decir «42 toneladas».
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "ventas-nueva");
  await pulsar(entorno, "elegir", { campo: "tipo", valor: "comercializada" });
  escribir(entorno, "producto", "Trigo blando");
  await pulsar(entorno, "asistente-seguir"); // el producto
  const html = pantallaPedida(entorno);
  assert.ok(html.includes("¿Cuánto has vendido?"), `no pregunta la cantidad: ${html.slice(0, 200)}`);
  // La unidad se elige de una lista: si el agricultor la escribiera a mano, «42 toneladas» y «42.000 kg»
  // no se podrían sumar.
  const unidades = opcionesDelBloque("unidad").join(" | ");
  assert.ok(unidades.includes("kilos"), `no ofrece las unidades: ${unidades}`);
});

test("el recorrido de una venta llega hasta el resumen", async () => {
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "ventas-nueva");
  await pulsar(entorno, "elegir", { campo: "tipo", valor: "comercializada" });
  // El producto y la cantidad se rellenan a mano y se comprueba que son obligatorios: sin
  // ellos la norma no se cumple, y el asistente no deja seguir.
  await pulsar(entorno, "asistente-seguir");
  assert.ok(pantallaPedida(entorno).includes("¿Qué has vendido?"), "ha dejado seguir sin producto");
});

test("las dos clases de venta se ofrecen con sus palabras", async () => {
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "ventas-nueva");
  // Se mira el texto de las opciones que se le piden a React: es lo que va a leer el agricultor.
  const clases = opcionesDelBloque("tipo").join(" | ");
  assert.ok(
    clases.includes("Lo vendí a un comprador o a la cooperativa"),
    `no se lee como se lo diría el agricultor: ${clases}`,
  );
  assert.ok(clases.includes("Lo vendí yo directamente al cliente"), clases);
  assert.ok(!clases.includes("cosecha comercializada"), "está saliendo el nombre oficial");
});

test("una venta se puede apuntar de punta a punta y el resumen lo enseña", async () => {
  // Este test recorre el asistente entero, paso a paso, como lo haría el agricultor. Es el
  // que caza el fallo más tonto y más difícil de ver: una pantalla de más o de menos en el
  // recorrido, que deja al agricultor mirando una pantalla vacía.
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "ventas-nueva");
  await pulsar(entorno, "elegir", { campo: "tipo", valor: "venta_directa" });
  escribir(entorno, "producto", "Lechuga romana");
  escribir(entorno, "variedad", "Batavia");
  await pulsar(entorno, "asistente-seguir"); // el producto
  escribir(entorno, "cantidad", "3000");
  await pulsar(entorno, "elegir", { campo: "unidad", valor: "ud" });
  await pulsar(entorno, "asistente-seguir"); // la fecha
  await pulsar(entorno, "asistente-saltar"); // el último día y la partida
  await pulsar(entorno, "elegir", { campo: "parcela_id", valor: "1", superficie: "2.43" });
  await pulsar(entorno, "asistente-saltar"); // a quién y el albarán
  // Y los dos pasos del dinero (T12, 03/10/2026): el importe y el precio, y luego el vencimiento y de qué
  // cosecha salió. Son **opcionales los dos** —una entrega de 8.000 kg sin precio se apunta igual, que es
  // el caso A08 del contrato—, así que se saltan como se saltaría el agricultor con prisa.
  await pulsar(entorno, "asistente-saltar"); // el importe y el precio
  await pulsar(entorno, "asistente-saltar"); // el vencimiento y la cosecha
  await pulsar(entorno, "asistente-saltar"); // lo que quiera apuntar
  const html = pantallaPedida(entorno);
  assert.ok(html.includes("APUNTARLO"), `no llega al resumen: ${html.slice(0, 300)}`);
  // El resumen lo pinta React (la misma pieza que el de echar producto): lo que se mira es lo que se le
  // pide, con las filas ya montadas.
  const resumen = resumenPedido();
  assert.ok(resumen.includes("Lechuga romana"), `el resumen no dice qué se vendió: ${resumen}`);
  assert.ok(resumen.includes("Batavia"), "el resumen no dice la variedad");
  assert.ok(resumen.includes("3.000,00 ud"), `el resumen no dice bien la cantidad: ${resumen}`);
  assert.ok(resumen.includes("El Prado"), "el resumen no dice de dónde salió");
});

// ---------------------------------------------------------------------------
// LAS TREINTA ACCIONES DEL DINERO SE PULSAN DE VERDAD (revisión del T12, 03/10/2026)
//
// **Por qué existe este bloque.** `react.test.js` comprueba que los botones del T12 están pintados
// (`data-accion="…"`), y eso solo demuestra que existen: **quién los atiende no lo probaba nadie**. Medido
// en la revisión: de las 30 acciones del dinero que el manejador de clics de `app.js` sabe atender, solo
// dos se pulsaban en alguna prueba (`ventas-nueva` y `ventas-ver`); las otras 28 no se ejecutaban ni una
// vez. Es el hueco que en el T10 escondió un botón roto y en el T11 dejó las cuatro pantallas de contactos
// sin probar.
//
// Lo que se comprueba aquí, acción por acción: **que al pulsarla pase lo que tiene que pasar** (que se
// abra la pantalla, que se pida lo que hace falta y que lo que se manda llegue al servidor con su método).
// Lo que se ve dentro de cada pantalla se sigue comprobando en `react.test.js`, contra el componente.
// ---------------------------------------------------------------------------

/** Una entrega con su dinero, como la devuelve `GET /api/ventas/{id}` (T12). */
function unaEntregaConDinero(cambios = {}) {
  return unaVenta({
    importe: "121.00",
    texto_importe: "121,00 €",
    importe_total: "121.00",
    texto_importe_total: "121,00 €",
    precio_unitario: null,
    vencimiento: "2026-08-20",
    texto_vencimiento: "20/08/2026",
    cobrado: "40.00",
    texto_cobrado: "40,00 €",
    pendiente: "81.00",
    texto_pendiente: "81,00 €",
    estado: "cobrada_en_parte",
    etiqueta_estado: "Cobrada en parte",
    facturada: true,
    contacto_id: 3,
    cosecha_id: null,
    kilos_netos: 42000.0,
    ajustes: [],
    ...cambios,
  });
}

/** Una factura nuestra, como la devuelve el servidor (T12). */
function unaFacturaEmitida(cambios = {}) {
  return {
    id: 7,
    campana_id: 1,
    numero: "F-1",
    fecha: "2026-07-20",
    fecha_linea: "Fecha: 20/07/2026",
    vencimiento: "2026-08-20",
    titulo: "Factura F-1 · Cooperativa Agrícola de Peñaranda",
    titulo_con_pendiente: "Factura F-1 · Cooperativa Agrícola de Peñaranda · Pendiente: 81,00 €",
    cliente: "Cooperativa Agrícola de Peñaranda",
    cliente_nif: null,
    contacto_id: 3,
    importe_total: "121.00",
    texto_total: "121,00 €",
    cobrado: "40.00",
    texto_cobrado: "40,00 €",
    pendiente: "81.00",
    texto_pendiente: "81,00 €",
    estado: "cobrada_en_parte",
    etiqueta_estado: "Cobrada en parte",
    anulada: false,
    motivo_anulacion: null,
    lineas: [
      {
        id: 1,
        venta_id: 1,
        descripcion: "Trigo blando · 10/07/2026",
        fecha: "10/07/2026",
        cantidad: 42000.0,
        unidad: "kg",
        importe: "121.00",
        texto_importe: "121,00 €",
        anulada: false,
        entrega_existe: true,
        diferencia: false,
      },
    ],
    cobros: [],
    entregas: 1,
    ...cambios,
  };
}

/** Un cobro, como lo devuelve el servidor (T12). */
function unCobro(cambios = {}) {
  return {
    id: 11,
    fecha: "2026-08-01",
    fecha_linea: "Fecha: 01/08/2026",
    importe: "40.00",
    texto_importe: "40,00 €",
    importe_imputado: "40.00",
    texto_imputado: "40,00 €",
    texto_sin_asignar: "",
    factura_emitida_id: 7,
    factura_numero: "F-1",
    forma: "transferencia",
    etiqueta_forma: "Transferencia",
    cliente: "Cooperativa Agrícola de Peñaranda",
    contacto_id: 3,
    referencia: "TRF-1",
    anulado: false,
    ...cambios,
  };
}

/** Un ajuste de una entrega, como lo devuelve el servidor (T12). */
function unAjuste(cambios = {}) {
  return {
    id: 5,
    tipo: "devolucion",
    etiqueta_tipo: "Devolución",
    fecha: "2026-07-12",
    cantidad: -3000.0,
    unidad: "kg",
    importe: "-40.50",
    texto_importe: "-40,50 €",
    origen: "cliente",
    etiqueta_origen: "Lo dice el cliente",
    motivo: "volvió un camión con el género húmedo",
    evidencia_descripcion: "boletín del laboratorio",
    tiene_papel: false,
    nombre_del_papel: null,
    anulado: false,
    motivo_anulacion: null,
    ...cambios,
  };
}

/** Las respuestas del dinero de las cuatro pantallas, para el recorrido de estas pruebas. */
function elDineroDeLaRevision() {
  return {
    "/api/ventas": [unaVenta()],
    "/api/ventas/tabla": unaTablaDeVentas(),
    "/api/ventas/1": unaEntregaConDinero(),
    "PUT /api/ventas/1": unaEntregaConDinero(),
    "POST /api/ventas/1/ajustes": unAjuste(),
    "POST /api/ventas/1/ajustes/5/anular": unAjuste({ anulado: true, motivo_anulacion: "me equivoqué" }),
    "/api/facturas-emitidas": [unaFacturaEmitida()],
    "/api/facturas-emitidas/7": unaFacturaEmitida(),
    "POST /api/facturas-emitidas": unaFacturaEmitida(),
    "POST /api/facturas-emitidas/7/anular": unaFacturaEmitida({ anulada: true }),
    "/api/cobros": [unCobro()],
    "POST /api/cobros": { cobro: unCobro(), factura: unaFacturaEmitida(), avisos: [] },
    "/api/cobros/11": unCobro(),
    "POST /api/cobros/11/conciliar": { cobro: unCobro(), factura: unaFacturaEmitida(), avisos: [] },
    "POST /api/cobros/11/anular": unCobro({ anulado: true }),
    "/api/contactos": [
      { id: 3, nombre: "Cooperativa Agrícola de Peñaranda", nif: "B47000000", papeles: ["comprador"] },
    ],
  };
}

/** Las palabras del dinero que este recorrido necesita del servidor. */
//
// El resto de `/api/interfaz` ya está en `RESPUESTAS`; estas son las del T12 que estas pruebas miran: el
// motivo con el que se quita un ajuste —que **viaja al servidor**, y sin él el apunte se quedaría sin
// decir por qué se quitó— y los rótulos de la puerta del contacto. Se copian de `textos.py`, que es de
// donde los sirve el servidor de verdad.
RESPUESTAS["/api/interfaz"].venta = {
  ...(RESPUESTAS["/api/interfaz"].venta || {}),
  ajuste_motivo_al_quitar: "Me he equivocado al apuntarlo",
  ajuste_guardado: "Apunte añadido. El importe de la entrega ya lo tiene en cuenta.",
  ajuste_anulado: "Apunte quitado. El importe de la entrega ya no lo tiene en cuenta.",
  sin_contacto: "Sin enlazar con ninguna ficha",
  cliente_ficha: "¿Es uno de tus contactos?",
  cliente_ficha_pista: "Si lo eliges, sus datos ya no hay que volver a escribirlos.",
};

test("las seis acciones de la lista de lo vendido se pulsan de verdad (T12)", async () => {
  const { entorno, servidor } = await cargarAplicacion(elDineroDeLaRevision());
  await pulsar(entorno, "ventas-ver");
  assert.equal(ultimoMontaje().type.name, "PantallaVentas", "«ver lo vendido» no abre la lista");

  // Buscar: el filtro lo hace **el servidor** (el pie es la cuenta del conjunto filtrado y el dinero no se
  // suma en el navegador), así que lo que se comprueba es que la búsqueda viaja en la petición.
  escribir(entorno, "buscar_venta", "coop");
  await pulsar(entorno, "ventas-buscar");
  assert.ok(
    servidor.llamadas.some((ruta) => ruta.includes("/api/ventas/tabla?") && ruta.includes("q=coop")),
    `la búsqueda no se le pide al servidor: ${servidor.llamadas.filter((r) => r.includes("tabla")).join(", ")}`,
  );

  // Y los dos filtros, que son la pregunta que se viene a hacer aquí («¿quién me debe?» y «¿a qué le falta
  // el importe?»).
  await pulsar(entorno, "ventas-solo-pendientes");
  assert.ok(
    servidor.llamadas.some((ruta) => ruta.includes("solo=pendientes")),
    "el filtro de lo que falta por cobrar no se le pide al servidor",
  );
  await pulsar(entorno, "ventas-solo-sin-importe");
  assert.ok(
    servidor.llamadas.some((ruta) => ruta.includes("solo=sin_importe")),
    "el filtro de lo que no tiene importe no se le pide al servidor",
  );
  const antes = servidor.llamadas.length;
  await pulsar(entorno, "ventas-ver-todas");
  const sinFiltro = servidor.llamadas.slice(antes).filter((ruta) => ruta.startsWith("/api/ventas/tabla"));
  assert.ok(sinFiltro.length, "«verlo todo» no vuelve a pedir la tabla");
  assert.ok(
    sinFiltro.some((ruta) => !ruta.includes("q=") && !ruta.includes("solo=")),
    `«verlo todo» no quita los filtros: ${sinFiltro.join(", ")}`,
  );

  // Y apuntar una venta nueva: el asistente, que es la misma puerta de siempre.
  await pulsar(entorno, "ventas-nueva");
  assert.equal(ultimoMontaje().type.name, "PantallaAsistente", "«apuntar una venta» no abre el asistente");
});

test("las ocho acciones de la entrega (el importe y el ajuste) se pulsan de verdad (T12)", async () => {
  const { entorno, servidor } = await cargarAplicacion(elDineroDeLaRevision());

  // Poner el importe de una entrega: es la puerta del A08. Se pide la entrega entera (el `PUT` es el
  // mismo para el alta y para la corrección: mandar media entrega le borraría el producto y los kilos).
  await pulsar(entorno, "venta-importe", { id: 1 });
  assert.equal(ultimoMontaje().type.name, "PantallaImporte", "«poner el importe» no abre su pantalla");
  assert.ok(
    servidor.llamadas.includes("/api/ventas/1"),
    `no se pide la entrega entera: ${servidor.llamadas.join(", ")}`,
  );
  // Y se guarda: el `PUT` lleva el importe escrito, como texto decimal.
  escribir(entorno, "venta-importe", "121,00");
  escribir(entorno, "venta-precio", "0,00288");
  escribir(entorno, "venta-vencimiento", "2026-08-20");
  escribir(entorno, "venta-contacto", "3");
  await pulsar(entorno, "venta-importe-guardar");
  const guardado = loMandado(servidor, "/api/ventas/1", "PUT").slice(-1)[0];
  assert.ok(guardado, `no se ha guardado el importe: ${servidor.llamadasConMetodo.join(", ")}`);
  assert.equal(guardado.cuerpo.importe, "121,00", "el importe no viaja como texto decimal");
  assert.equal(guardado.cuerpo.producto, "Trigo blando", "el `PUT` no lleva la entrega entera");
  assert.equal(guardado.cuerpo.contacto_id, 3, "la ficha del cliente no llega al servidor");

  // Apuntar un ajuste, que es el otro camino del dinero (una devolución, un peso, una humedad).
  await pulsar(entorno, "venta-ajuste", { id: 1 });
  assert.equal(ultimoMontaje().type.name, "PantallaAjuste", "«apuntar un ajuste» no abre su pantalla");
  await pulsar(entorno, "ajuste-elegir-tipo", { campo: "tipo", valor: "devolucion" });
  await pulsar(entorno, "ajuste-elegir-origen", { campo: "origen", valor: "cliente" });
  escribir(entorno, "ajuste-cantidad", "-3000");
  escribir(entorno, "ajuste-importe", "-40,50");
  escribir(entorno, "ajuste-motivo", "volvió un camión con el género húmedo");
  await pulsar(entorno, "ajuste-guardar");
  const ajuste = loMandado(servidor, "/api/ventas/1/ajustes", "POST").slice(-1)[0];
  assert.ok(ajuste, `no se ha apuntado el ajuste: ${servidor.llamadasConMetodo.join(", ")}`);
  assert.equal(ajuste.cuerpo.tipo, "devolucion", "el ajuste no dice qué pasó");
  assert.equal(ajuste.cuerpo.origen, "cliente", "el ajuste no dice de dónde sale el número");
  assert.equal(ajuste.cuerpo.importe, "-40,50", "el importe del ajuste no viaja como texto");

  // Y quitarlo: primero se pregunta (**no se toca nada hasta que se contesta**) y luego se anula, que no
  // borra el apunte.
  await pulsar(entorno, "venta-ajuste", { id: 1 });
  await pulsar(entorno, "ajuste-anular", { venta: 1, id: 5 });
  assert.equal(
    cuantasVeces(servidor, "POST /api/ventas/1/ajustes/5/anular"),
    0,
    "se ha quitado el ajuste sin preguntar",
  );
  await pulsar(entorno, "ajuste-anular-si", { venta: 1, id: 5 });
  assert.equal(
    cuantasVeces(servidor, "POST /api/ventas/1/ajustes/5/anular"),
    1,
    `la confirmación no anula el ajuste: ${servidor.llamadasConMetodo.join(", ")}`,
  );
  assert.ok(
    loMandado(servidor, "/api/ventas/1/ajustes/5/anular", "POST")[0].cuerpo.motivo,
    "el ajuste se quita sin motivo apuntado",
  );
});

test("las siete acciones de la factura nuestra se pulsan de verdad (T12)", async () => {
  const { entorno, servidor } = await cargarAplicacion(elDineroDeLaRevision());

  await pulsar(entorno, "facturas-emitidas-ver");
  assert.equal(ultimoMontaje().type.name, "PantallaFacturasEmitidas", "no abre la lista de facturas");

  // Juntar entregas: se entra por el botón de la lista y por el de una entrega concreta, y en el segundo
  // caso la entrega viene marcada.
  await pulsar(entorno, "factura-emitida-nueva");
  assert.equal(ultimoMontaje().type.name, "PantallaFacturarEntregas", "no abre el «qué entregas van»");
  await pulsar(entorno, "ventas-facturar", { id: 1 });
  assert.equal(ultimoMontaje().type.name, "PantallaFacturarEntregas", "«facturar esto» no abre la pantalla");
  await pulsar(entorno, "facturar-marcar", { id: 1 });
  await pulsar(entorno, "facturar-marcar", { id: 1 });
  assert.equal(ultimoMontaje().type.name, "PantallaFacturarEntregas", "marcar una entrega se sale de la pantalla");

  // Y guardarla: el `POST` lleva las entregas marcadas, el cliente y **la ficha** con la que va. La entrega
  // vuelve a estar marcada (los dos toques de arriba la han marcado y desmarcado).
  assert.ok(
    ultimoMontaje().props.entregas[0].elegida,
    "la entrega ha quedado sin marcar después de pulsar su casilla dos veces",
  );
  escribir(entorno, "factura-emitida-numero", "F-1");
  escribir(entorno, "factura-emitida-cliente", "Cooperativa Agrícola de Peñaranda");
  escribir(entorno, "factura-emitida-contacto", "3");
  await pulsar(entorno, "factura-emitida-guardar");
  const factura = loMandado(servidor, "/api/facturas-emitidas", "POST").slice(-1)[0];
  assert.ok(factura, `no se ha hecho la factura: ${servidor.llamadasConMetodo.join(", ")}`);
  assert.deepEqual(factura.cuerpo.entregas, [1], "la factura no lleva la entrega marcada");
  assert.equal(factura.cuerpo.contacto_id, 3, "la ficha del cliente no llega al servidor");
  assert.ok(factura.cuerpo.clave_de_reenvio, "la factura viaja sin clave de reenvío");

  // Abrir su ficha, preguntar si se quita y quitarla. Quitarla **no borra nada**: sus entregas vuelven a
  // estar libres, y eso lo comprueba la suite entera del servidor.
  await pulsar(entorno, "factura-emitida-abrir", { id: 7 });
  assert.ok(
    servidor.llamadas.includes("/api/facturas-emitidas/7"),
    `no se pide la ficha de la factura: ${servidor.llamadas.join(", ")}`,
  );
  assert.equal(ultimoMontaje().type.name, "PantallaFacturaEmitida", "no abre la ficha de la factura");
  await pulsar(entorno, "factura-emitida-anular", { id: 7 });
  assert.equal(
    cuantasVeces(servidor, "POST /api/facturas-emitidas/7/anular"),
    0,
    "se ha quitado la factura sin preguntar",
  );
  await pulsar(entorno, "factura-emitida-anular-si", { id: 7 });
  assert.equal(
    cuantasVeces(servidor, "POST /api/facturas-emitidas/7/anular"),
    1,
    `la confirmación no quita la factura: ${servidor.llamadasConMetodo.join(", ")}`,
  );
  assert.equal(ultimoMontaje().type.name, "PantallaFacturasEmitidas", "quitar una factura no vuelve a la lista");
});

/**
 * Marca una casilla, como el agricultor con el dedo.
 *
 * El DOM de mentira no tiene casillas —solo `entorno.nodos`, que es un `Map`—, así que se le mete una con
 * `checked`, igual que `escribir` le mete un `value`.
 */
function marcar(entorno, id) {
  const nodo = entorno.nodos.get(id) || { id };
  nodo.checked = true;
  entorno.nodos.set(id, nodo);
}

test("un cobro se reparte entre dos facturas desde la pantalla (CRM-01)", async () => {
  // **La cifra del encargo, por la puerta por la que entra el agricultor**: 350 que entran de una vez y
  // saldan una deuda de 100 y otra de 250. Se marcan las dos, no se escribe ningún importe —se aplica lo
  // que le queda a cada una, que es lo que se quiere casi siempre— y lo que tiene que llegar al servidor es
  // **una aplicación por factura**, no una factura suelta.
  const conDosDeudas = {
    ...elDineroDeLaRevision(),
    "/api/facturas-emitidas": [
      unaFacturaEmitida({ id: 7, pendiente: "100.00" }),
      unaFacturaEmitida({ id: 8, pendiente: "250.00" }),
    ],
  };
  const { entorno, servidor } = await cargarAplicacion(conDosDeudas);
  await pulsar(entorno, "cobros-ver");
  await pulsar(entorno, "cobro-nuevo");
  escribir(entorno, "cobro-importe", "350,00");
  marcar(entorno, "cobro-reparto-7");
  marcar(entorno, "cobro-reparto-8");
  await pulsar(entorno, "cobro-guardar");

  const enviado = loMandado(servidor, "/api/cobros", "POST").slice(-1)[0];
  assert.ok(enviado, `no se ha apuntado el cobro: ${servidor.llamadasConMetodo.join(", ")}`);
  assert.deepEqual(
    (enviado.cuerpo.aplicaciones || []).map((fila) => [fila.factura_emitida_id, fila.importe]),
    [
      [7, "100.00"],
      [8, "250.00"],
    ],
    `el reparto no viaja con una fila por factura y lo que le queda a cada una: ${JSON.stringify(enviado.cuerpo)}`,
  );
  assert.equal(
    enviado.cuerpo.factura_emitida_id,
    undefined,
    "y no viaja **también** una factura suelta: el servidor contesta 422 a las dos cosas a la vez, con razón",
  );
  assert.ok(enviado.cuerpo.clave_de_reenvio, "el reparto viaja sin clave de reenvío");
});

test("las nueve acciones del cobro se pulsan de verdad (T12)", async () => {
  const { entorno, servidor } = await cargarAplicacion(elDineroDeLaRevision());

  await pulsar(entorno, "cobros-ver");
  assert.equal(ultimoMontaje().type.name, "PantallaCobros", "«lo que me han pagado» no abre su lista");

  // Apuntar un cobro: puede ser una parte de lo que se deben (A06) y puede no saberse de qué factura es.
  await pulsar(entorno, "cobro-nuevo");
  assert.equal(ultimoMontaje().type.name, "PantallaCobroNuevo", "«apuntar un cobro» no abre su pantalla");
  escribir(entorno, "cobro-importe", "40,00");
  escribir(entorno, "cobro-cliente", "Cooperativa Agrícola de Peñaranda");
  escribir(entorno, "cobro-contacto", "3");
  escribir(entorno, "cobro-referencia", "TRF-1");
  await pulsar(entorno, "cobro-guardar");
  const cobro = loMandado(servidor, "/api/cobros", "POST").slice(-1)[0];
  assert.ok(cobro, `no se ha apuntado el cobro: ${servidor.llamadasConMetodo.join(", ")}`);
  assert.equal(cobro.cuerpo.importe, "40,00", "el cobro no viaja como texto decimal");
  assert.equal(cobro.cuerpo.contacto_id, 3, "la ficha del cliente no llega al servidor");
  assert.ok(cobro.cuerpo.clave_de_reenvio, "el cobro viaja sin clave de reenvío");
  // **Y no se ha creado ninguna factura**: es la segunda mitad del A06.
  assert.equal(cuantasVeces(servidor, "POST /api/facturas-emitidas"), 0, "apuntar un cobro ha creado una factura");

  // Decir de qué factura es un cobro que no lo sabía, y deshacerlo. Lo segundo no borra el dinero.
  await pulsar(entorno, "cobro-conciliar", { id: 11 });
  assert.equal(
    cuantasVeces(servidor, "POST /api/cobros/11/conciliar"),
    1,
    `«decir de qué factura es» no concilia cuando solo hay una factura pendiente: ${servidor.llamadasConMetodo.join(", ")}`,
  );
  await pulsar(entorno, "cobro-desconciliar", { id: 11 });
  const deshecho = loMandado(servidor, "/api/cobros/11/conciliar", "POST").slice(-1)[0];
  assert.equal(deshecho.cuerpo.factura_emitida_id, null, "deshacer la asignación la deja puesta");

  // Quitar un cobro: se pregunta antes y luego se anula (no se borra).
  await pulsar(entorno, "cobros-ver");
  await pulsar(entorno, "cobro-anular", { id: 11 });
  assert.equal(cuantasVeces(servidor, "POST /api/cobros/11/anular"), 0, "se ha quitado el cobro sin preguntar");
  await pulsar(entorno, "cobro-anular-si", { id: 11 });
  assert.equal(
    cuantasVeces(servidor, "POST /api/cobros/11/anular"),
    1,
    `la confirmación no quita el cobro: ${servidor.llamadasConMetodo.join(", ")}`,
  );
});

test("con más de una factura pendiente, «decir de qué factura es» pregunta cuál (T12)", async () => {
  // La otra mitad de `cobro-conciliar`: cuando hay más de una factura con algo pendiente **no se elige por
  // el agricultor**: se le pregunta, y la respuesta se manda con `cobro-conciliar-con`. Sin esto, el botón
  // de conciliar tendría un camino (el de una sola factura) probado y el otro no.
  const { entorno, servidor } = await cargarAplicacion({
    ...elDineroDeLaRevision(),
    "/api/facturas-emitidas": [
      unaFacturaEmitida(),
      unaFacturaEmitida({ id: 8, numero: "F-2", titulo: "Factura F-2 · Cooperativa Agrícola de Peñaranda" }),
    ],
  });
  await pulsar(entorno, "cobros-ver");
  await pulsar(entorno, "cobro-conciliar", { id: 11 });
  assert.equal(ultimoMontaje().type.name, "Confirmacion", "no se pregunta con qué factura va el cobro");
  await pulsar(entorno, "cobro-conciliar-con", { cobro: 11, factura: 8 });
  const conciliado = loMandado(servidor, "/api/cobros/11/conciliar", "POST").slice(-1)[0];
  assert.ok(conciliado, `no se ha conciliado con la factura elegida: ${servidor.llamadasConMetodo.join(", ")}`);
  assert.equal(conciliado.cuerpo.factura_emitida_id, 8, "el cobro no va a la factura que se ha elegido");
});

// ---------------------------------------------------------------------------
// Las medidas preventivas de la finca
// ---------------------------------------------------------------------------

test("sin declarar, mi cuaderno lo dice y ofrece marcarlas", async () => {
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "inicio", { ir: "mi_cuaderno" });
  const medidas = ultimoCuadernoPedido().medidas;
  assert.ok(medidas.titulo.includes("Lo que hago sin echar producto"), `no hay apartado: ${medidas.titulo}`);
  assert.equal(medidas.declarada, false);
  assert.ok(medidas.sin_declarar.includes("Todavía no has dicho qué haces sin echar producto."));
  assert.deepEqual(
    medidas.acciones.map((accion) => accion.accion),
    ["medidas-ver"],
    "avisa pero no ofrece arreglarlo",
  );
  assert.equal(medidas.acciones[0].etiqueta, "MARCAR LO QUE HAGO", "el botón no dice qué hace");
});

test("con medidas declaradas, mi cuaderno las enseña con su nombre", async () => {
  const { entorno } = await cargarAplicacion({
    "/api/medidas": declaracionDeMedidas(["rotacion", "higiene"]),
  });
  await pulsar(entorno, "inicio", { ir: "mi_cuaderno" });
  const medidas = ultimoCuadernoPedido().medidas;
  assert.equal(medidas.declarada, true);
  // Los nombres llegan **ya resueltos** (el código `rotacion` es «Rotación de cultivos»): el
  // componente no tiene por qué saber el catálogo.
  assert.deepEqual(
    medidas.aplicadas,
    ["Rotación de cultivos", "Higiene y limpieza de equipos y maquinaria"],
    `no le llegan las medidas aplicadas: ${JSON.stringify(medidas.aplicadas)}`,
  );
});

test("haber dicho que no haces ninguna llega como declarado y sin ninguna medida", async () => {
  // El agricultor puede declarar que no hace ninguna. Eso **no es lo mismo** que no haberlo declarado
  // nunca (lo segundo es un hueco del cuaderno), y la pantalla lo pinta en rojo para que se vea. Que
  // ese rojo salga lo comprueba `tests_js/react.test.js` contra el componente; aquí se comprueba el
  // dato del que sale: declarada sí, medidas ninguna.
  const { entorno } = await cargarAplicacion({
    "/api/medidas": declaracionDeMedidas([], { rotacion: "nota para que cuente como declarada" }),
  });
  await pulsar(entorno, "inicio", { ir: "mi_cuaderno" });
  const medidas = ultimoCuadernoPedido().medidas;
  assert.equal(medidas.declarada, true);
  assert.deepEqual(medidas.aplicadas, [], "dice que hace medidas que no ha declarado");
});

// ---------------------------------------------------------------------------
// «Las medidas preventivas» se pasaron a React en la ronda 41
//
// Aquí ya no se puede leer su HTML (React no se monta en el DOM de mentira de este fichero), así que
// lo que comprueban estas pruebas es **el cableado y el estado**: que la pantalla se le pida a React
// con las diez medidas, y que al marcar, desmarcar o pulsar «no hago ninguna» lo que se le vuelve a
// pedir lleva las marcas que toca. El dibujo de cada medida (la pregunta en cristiano, el icono ✅ o
// ⬜, el campo de la nota) se comprueba en `react.test.js` contra el componente.
// ---------------------------------------------------------------------------

/** Lo último que se le ha pedido a React: la pantalla de medidas con sus diez medidas. */
function ultimasMedidasPedidas() {
  const pedidos = montajes.filter((montaje) => montaje.elemento?.type?.name === "PantallaMedidas");
  assert.ok(pedidos.length, "no se le ha pedido la pantalla de medidas a React");
  return pedidos[pedidos.length - 1].elemento.props.medidas;
}

/** Los códigos que van marcados en esa petición. */
function codigosMarcados(medidas) {
  return medidas.filter((medida) => medida.marcada).map((medida) => medida.codigo);
}

test("la pantalla de medidas se le pide a React, con las diez medidas", async () => {
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "inicio", { ir: "mi_cuaderno" });
  await pulsar(entorno, "medidas-ver");

  const medidas = ultimasMedidasPedidas();
  // El número se saca de la copia del vocabulario que hay en este fichero (que trae tres, no las
  // diez del catálogo de verdad): así la prueba no se queda vieja si esa copia cambia.
  const delCatalogo = RESPUESTAS["/api/interfaz"].medidas_preventivas;
  assert.equal(medidas.length, delCatalogo.length, "no le llegan todas las medidas del catálogo");
  for (const medida of medidas) {
    assert.ok(medida.codigo, "una medida sin código");
    assert.ok(medida.pregunta, `la medida ${medida.codigo} llega sin su pregunta`);
    assert.equal(typeof medida.marcada, "boolean", "no se sabe si está marcada");
    assert.ok(!medida.pregunta.includes("_"), `la pregunta parece un código: ${medida.pregunta}`);
  }
});

test("marcar una medida la deja marcada", async () => {
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "medidas-ver");
  await pulsar(entorno, "medidas-marcar", { codigo: "rotacion" });
  assert.deepEqual(codigosMarcados(ultimasMedidasPedidas()), ["rotacion"]);
});

test("volver a tocarla la desmarca", async () => {
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "medidas-ver");
  await pulsar(entorno, "medidas-marcar", { codigo: "rotacion" });
  await pulsar(entorno, "medidas-marcar", { codigo: "rotacion" });
  assert.deepEqual(codigosMarcados(ultimasMedidasPedidas()), [], "sigue marcada después de quitarla");
});

test("marcar una no desmarca las demás", async () => {
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "medidas-ver");
  await pulsar(entorno, "medidas-marcar", { codigo: "rotacion" });
  await pulsar(entorno, "medidas-marcar", { codigo: "higiene" });
  assert.deepEqual(codigosMarcados(ultimasMedidasPedidas()).sort(), ["higiene", "rotacion"]);
});

test("el botón de no hago ninguna las quita todas", async () => {
  const { entorno } = await cargarAplicacion({
    "/api/medidas": declaracionDeMedidas(["rotacion", "higiene"]),
  });
  await pulsar(entorno, "medidas-ver");
  assert.deepEqual(codigosMarcados(ultimasMedidasPedidas()).sort(), ["higiene", "rotacion"]);
  await pulsar(entorno, "medidas-ninguna");
  assert.deepEqual(codigosMarcados(ultimasMedidasPedidas()), [], "siguen marcadas");
});

test("la pantalla avisa de dónde salen las diez preguntas", async () => {
  // Honestidad: los códigos del catálogo de la Junta no son públicos, así que los de aquí son
  // internos. Que quede dicho en pantalla y no solo en el código.
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "medidas-ver");
  const pedidos = montajes.filter((montaje) => montaje.elemento?.type?.name === "PantallaMedidas");
  const textos = pedidos[pedidos.length - 1].elemento.props.textos.medidas;
  assert.ok(
    textos.catalogo_aviso.includes("los de aquí son internos"),
    "no avisa de dónde salen las diez preguntas",
  );
});

// ---------------------------------------------------------------------------
// Las medidas dentro del apunte de un producto
// ---------------------------------------------------------------------------

/**
 * Recorre el asistente de «echar producto» hasta la pantalla de las medidas preventivas.
 *
 * Se recorre como lo haría el agricultor, pulsando de verdad: parcela, fecha, hectáreas,
 * motivo, producto, dosis, quién y con qué máquina (que se salta) y medidas.
 *
 * Hace falta un producto dado de alta: sin él, el asistente se para en la pantalla que
 * ofrece añadir uno, que es lo correcto pero no es lo que este test quiere comprobar.
 */
async function hastaLasMedidas(entorno) {
  await pulsar(entorno, "inicio", { ir: "echar_producto" });
  await pulsar(entorno, "elegir", { campo: "parcela_id", valor: "1", superficie: "2.43" });
  await pulsar(entorno, "asistente-seguir"); // la fecha
  await pulsar(entorno, "asistente-seguir"); // las hectáreas
  await pulsar(entorno, "elegir", {
    campo: "justificacion",
    valor: "Vi la plaga o la hierba en el campo",
  });
  await pulsar(entorno, "elegir", { campo: "producto_id", valor: "1" });
  await pulsar(entorno, "asistente-seguir"); // la dosis
  await pulsar(entorno, "asistente-saltar"); // quién y con qué máquina
  // Y aquí ya se está en las medidas preventivas: el paso del sitio solo sale en naves y
  // postcosecha, así que se salta él solo. Antes había una línea de más que pasaba de
  // largo esta pantalla y el test no la veía; por eso el recorrido se pulsa de verdad.
}

const UN_PRODUCTO = [
  {
    id: 1,
    nombre_comercial: "Ejemplo 25 EC",
    numero_registro: "24.123",
    dosis_maxima: 1.0,
    unidad_dosis: "L/ha",
    plazo_seguridad_dias: 21,
  },
];

test("al apuntar un producto se pregunta qué se hizo antes de echarlo", async () => {
  const { entorno } = await cargarAplicacion({ "/api/productos": UN_PRODUCTO });
  await hastaLasMedidas(entorno);
  const html = pantallaPedida(entorno);
  assert.ok(
    html.includes("¿Qué hiciste antes para no tener que echarlo?"),
    `no pregunta las medidas: ${html.slice(0, 300)}`,
  );
});

test("lo declarado en la finca ya sale marcado en el apunte", async () => {
  // Esto es lo que hace que la sección sirva de algo en vez de ser un formulario que se
  // rellena una vez y no se vuelve a mirar.
  const { entorno } = await cargarAplicacion({
    "/api/productos": UN_PRODUCTO,
    "/api/medidas": declaracionDeMedidas(["rotacion", "higiene"]),
  });
  await hastaLasMedidas(entorno);
  // Las medidas las pinta React (la pieza `ListaParaElegir`): lo que se mira es cuáles se le piden
  // marcadas, no el HTML del contenedor.
  const marcadas = botonesMarcados();
  assert.equal(marcadas.length, 2, `esperaba dos medidas ya marcadas y hay ${marcadas.length}`);
  assert.deepEqual(
    marcadas.map((boton) => boton.datos.codigo).sort(),
    ["higiene", "rotacion"],
    "las marcadas no son las que declaró la finca",
  );
});

test("en el apunte se puede quitar la que esta vez no se hizo", async () => {
  const { entorno } = await cargarAplicacion({
    "/api/productos": UN_PRODUCTO,
    "/api/medidas": declaracionDeMedidas(["rotacion", "higiene"]),
  });
  await hastaLasMedidas(entorno);
  await pulsar(entorno, "medidas-marcar-apunte", { codigo: "higiene" });
  const marcadas = botonesMarcados();
  assert.equal(marcadas.length, 1, `esperaba una marcada y hay ${marcadas.length}`);
  assert.equal(marcadas[0].datos.codigo, "rotacion", "la que queda marcada no es la que se hizo");
});

test("el resumen del apunte enseña las medidas con su nombre", async () => {
  const { entorno } = await cargarAplicacion({
    "/api/productos": UN_PRODUCTO,
    "/api/medidas": declaracionDeMedidas(["rotacion"]),
  });
  await hastaLasMedidas(entorno);
  await pulsar(entorno, "asistente-saltar"); // las observaciones
  // **Este salto es nuevo de la ronda 18, y por qué.** Entre las observaciones y el resumen se
  // añadió la pantalla opcional de «cómo se echó» (la hora, el estado de la planta y las
  // condiciones del día). El test tiene que saltarla igual que la saltaría el agricultor.
  await pulsar(entorno, "asistente-saltar"); // cómo se echó
  await pulsar(entorno, "asistente-seguir"); // y el resumen
  const resumen = resumenPedido();
  assert.ok(resumen.includes("Lo que hiciste antes de echarlo"), `el resumen no lo dice: ${resumen}`);
  assert.ok(resumen.includes("Rotación de cultivos"), "no enseña el nombre de la medida");
});

test("la pantalla de «cómo se echó» pregunta la hora y cómo estaba el día", async () => {
  // Lo que cierra esto: once campos del registro de tratamientos **no llegaban a ninguna
  // pantalla**. Dos de ellos los pide el contenido mínimo del CUE por su número (la hora,
  // campo 3, y el estado de la planta, campo 8), y el aviso «¿has dejado la orilla sin tratar?»
  // saltaba siempre porque la pregunta no existía en ninguna pantalla.
  const { entorno } = await cargarAplicacion({ "/api/productos": UN_PRODUCTO });
  await hastaLasMedidas(entorno);
  await pulsar(entorno, "asistente-saltar"); // las observaciones
  await pulsar(entorno, "asistente-saltar"); // las observaciones
  const html = pantallaPedida(entorno);
  assert.ok(html.includes("¿Quieres apuntar cómo fue?"), `no ofrece la pantalla: ${html.slice(0, 250)}`);
  // La pantalla entera la pide React, con secciones: lo que se mira son los `id` de los campos que se
  // le piden, que son los únicos que tiene `app.js` para leer lo escrito.
  const ids = idsDeLosBloques();
  for (const id of ["hora_inicio", "estado_cultivo", "viento_kmh", "unidad_cantidad_aplicada", "operadores_expuestos", "incidencias"]) {
    assert.ok(ids.includes(id), `no se pregunta «${id}»: ${ids.join(", ")}`);
  }
  const textos = textosDeLosBloques();
  assert.ok(textos.includes("¿Has dejado la orilla sin tratar?"), "no pregunta la orilla");
  // Estas dos se añadieron al mapear el cuaderno al formato de la Junta: el interfaz las exige
  // como obligatorias (el aplicador a mano y la eficacia del tratamiento) y el cuaderno no las
  // preguntaba en ninguna pantalla. Es el mismo fallo de siempre: el dato escrito y sin puerta.
  assert.ok(textos.includes("¿Lo has echado a mano?"), "no pregunta si se aplicó a mano");
  assert.ok(textos.includes("¿Cómo ha funcionado?"), "no pregunta cómo funcionó el tratamiento");
  // Y la lista de respuestas tiene que venir del vocabulario, no estar escrita en el JavaScript:
  // si no viniera, la pregunta saldría sin opciones y nadie lo notaría.
  assert.ok(
    textos.includes("Regular: habría que repetirlo"),
    "la pregunta de la eficacia se queda sin opciones",
  );
});

// ---------------------------------------------------------------------------
// Traer las tierras del cuaderno de la Junta (el Cuecyl)
// ---------------------------------------------------------------------------

/**
 * Elige un fichero en la pantalla, como lo haría el agricultor en su móvil.
 *
 * El DOM de mentira no tiene casillas de fichero: se le mete una con su fichero dentro. Sin esto
 * no se podría probar nada de esta pantalla, porque sin fichero no hay nada que leer.
 */
function elegirFichero(entorno, nombre = "CuadernoExplotacion_12345678Z.xlsx") {
  entorno.nodos.set("cuaderno-fichero", { id: "cuaderno-fichero", files: [{ name: nombre }] });
}

test("al añadir una parcela se ofrece traer las tierras del cuaderno de la Junta", async () => {
  // Es la opción que ahorra teclear 54 parcelas, así que tiene que estar donde se busca: en la
  // pantalla que sale al pulsar «añadir parcela».
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "anadir-maestro", { tipo: "parcela" });
  const acciones = accionesDeLoPedido();
  assert.ok(acciones.includes("TRAER MIS TIERRAS"), `no ofrece traer el cuaderno: ${acciones}`);
  assert.ok(acciones.includes("cuaderno-abrir"), "el botón no lleva su acción");
});

// ---------------------------------------------------------------------------
// «Traer tus tierras del cuaderno de la Junta» se pasó a React (ronda 61)
//
// Lo que se ve dentro (el título, el resumen del fichero con sus cuentas, el resultado y el campo del
// fichero) está en `tests_js/react.test.js`, contra el componente. Aquí queda lo que solo se ve desde
// `app.js`: que la pantalla **se le pide a React** en sus tres estados, y la regla que no se toca:
// **leer el fichero no apunta nada.**
// ---------------------------------------------------------------------------

test("la pantalla del cuaderno se le pide a React, con el campo del fichero", async () => {
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "anadir-maestro", { tipo: "parcela" });
  const antes = montajes.length;
  await pulsar(entorno, "cuaderno-abrir");
  const pedidos = montajes.slice(antes);
  assert.equal(pedidos.length, 1, `se han pedido ${pedidos.length} montajes: solo la pantalla`);
  const elemento = pedidos[0].elemento;
  assert.equal(elemento.type.name, "PantallaCuadernoDeLaJunta");
  assert.equal(elemento.props.resultado, null, "enseña un resultado sin haber traído nada");
  assert.equal(elemento.props.resumen, null, "enseña un resumen sin haber leído nada");
  assert.equal(elemento.props.leyendo, false);
  assert.equal(elemento.props.error, "");
  // Y no se ha pintado a mano: en el contenedor (**que ya no pinta nada**, porque toda la aplicación es
  // React) no aparece ni un campo de esta pantalla. Se mira el contenedor a propósito: es la comprobación
  // de que no ha vuelto el `pintar()`.
  assert.ok(
    !pantallaDe(entorno).includes("cuaderno-fichero"),
    "la pantalla del cuaderno se ha pintado además con `pintar()`",
  );
});

test("sin elegir fichero lo dice en vez de no hacer nada", async () => {
  const { entorno, servidor } = await cargarAplicacion();
  await pulsar(entorno, "anadir-maestro", { tipo: "parcela" });
  await pulsar(entorno, "cuaderno-abrir");
  await pulsar(entorno, "cuaderno-leer");
  const elemento = montajes[montajes.length - 1].elemento;
  assert.ok(elemento.props.error.includes("CuadernoExplotacion"), `no avisa: ${elemento.props.error}`);
  assert.ok(
    !servidor.llamadas.includes("/api/cuaderno-cyl/leer"),
    "ha llamado al servidor sin fichero",
  );
});

test("al leer el cuaderno se enseña lo que trae antes de apuntar nada", async () => {
  // Este es el paso que evita la sorpresa de encontrarse 51 parcelas sin saber de dónde salen.
  const { entorno, servidor } = await cargarAplicacion();
  await pulsar(entorno, "anadir-maestro", { tipo: "parcela" });
  await pulsar(entorno, "cuaderno-abrir");
  elegirFichero(entorno);
  await pulsar(entorno, "cuaderno-leer");
  assert.ok(servidor.llamadas.includes("/api/cuaderno-cyl/leer"), "no ha leído el cuaderno");

  const elemento = montajes[montajes.length - 1].elemento;
  assert.equal(elemento.type.name, "PantallaCuadernoDeLaJunta");
  const resumen = elemento.props.resumen;
  assert.ok(resumen, "no le llega el resumen del fichero");
  const filas = JSON.stringify(resumen.filas);
  assert.ok(filas.includes("Campaña"), "el resumen no dice la campaña");
  assert.ok(filas.includes("2026"), "el resumen no dice el año");
  assert.ok(filas.includes("EXPLOTACIÓN DE EJEMPLO"), "el resumen no dice el titular");
  assert.ok(filas.includes("Tierras distintas"), "el resumen no cuenta las tierras");
  assert.ok(filas.includes("Hectáreas que declaras"), "el resumen no suma las hectáreas");
  assert.ok(filas.includes("PUEBLO DE EJEMPLO"), "el resumen no dice los pueblos");
  // Las tierras, ya en texto: la referencia y su cultivo con las hectáreas.
  const lineas = JSON.stringify(resumen.lineas);
  assert.ok(lineas.includes("99-99-0-0-1-1-1"), "no enseña la referencia de las tierras");
  // Y el aviso de las líneas que no se pueden leer también sale aquí, antes de apuntar.
  assert.ok(JSON.stringify(resumen.avisos).includes("no dicen el polígono"), "no avisa de la línea");
  // Lo más importante: leer **no** apunta.
  assert.ok(
    !servidor.llamadas.includes("/api/cuaderno-cyl/importar"),
    "ha apuntado las tierras sin preguntar",
  );
});

test("confirmar apunta las tierras y dice qué ha pasado", async () => {
  const { entorno, servidor } = await cargarAplicacion();
  await pulsar(entorno, "anadir-maestro", { tipo: "parcela" });
  await pulsar(entorno, "cuaderno-abrir");
  elegirFichero(entorno);
  await pulsar(entorno, "cuaderno-leer");
  await pulsar(entorno, "cuaderno-traer");
  assert.ok(servidor.llamadas.includes("/api/cuaderno-cyl/importar"), "no ha traído las tierras");

  const resultado = montajes[montajes.length - 1].elemento.props.resultado;
  assert.ok(resultado, "no le llega lo que se ha apuntado");
  const cuentas = JSON.stringify(resultado.cuentas);
  assert.ok(cuentas.includes("Tierras nuevas: 7"), `no dice cuántas: ${cuentas}`);
  // Y lo que no ha entrado se dice: un cuaderno con una línea menos sin avisar es un descuadre.
  assert.ok(
    resultado.sin_apuntar.includes("Líneas que no se han podido apuntar: 1"),
    `no dice lo que ha faltado: ${resultado.sin_apuntar}`,
  );
  // Y el resumen deja de estar: ya no hay nada que confirmar.
  assert.equal(montajes[montajes.length - 1].elemento.props.resumen, null);
});

test("si el fichero no es el cuaderno, se dice lo que ha pasado", async () => {
  // El servidor contesta con su mensaje y la pantalla lo enseña tal cual: en castellano y
  // explicando qué fichero hay que subir.
  const { entorno } = await cargarAplicacion({
    "/api/cuaderno-cyl/leer": undefined,
  });
  await pulsar(entorno, "anadir-maestro", { tipo: "parcela" });
  await pulsar(entorno, "cuaderno-abrir");
  elegirFichero(entorno, "una-factura.xlsx");
  await pulsar(entorno, "cuaderno-leer");
  const elemento = montajes[montajes.length - 1].elemento;
  assert.ok(
    elemento.props.error.includes("No se ha podido abrir el cuaderno"),
    `no avisa: ${elemento.props.error}`,
  );
  assert.equal(elemento.props.resumen, null, "enseña un resumen de un fichero que no se pudo leer");
});

test("se puede volver sin traer nada", async () => {
  const { entorno, servidor } = await cargarAplicacion();
  await pulsar(entorno, "anadir-maestro", { tipo: "parcela" });
  await pulsar(entorno, "cuaderno-abrir");
  await pulsar(entorno, "cuaderno-volver");
  const acciones = accionesDeLoPedido();
  assert.ok(acciones.includes("VER EL MAPA Y ELEGIRLA AHÍ"), "no vuelve a la pantalla de elegir");
  assert.ok(
    !servidor.llamadas.includes("/api/cuaderno-cyl/importar"),
    "ha apuntado algo al volver",
  );
});

test("sin conexión no se intenta subir el cuaderno y se dice por qué", async () => {
  // Subir un fichero no se puede hacer «a medias»: o va entero o no va. Es mejor decirlo que
  // dejar al agricultor delante de una barra que no avanza.
  const { entorno, servidor } = await cargarAplicacion();
  entorno.navigator.onLine = false;
  globalThis.navigator = entorno.navigator;
  await pulsar(entorno, "anadir-maestro", { tipo: "parcela" });
  await pulsar(entorno, "cuaderno-abrir");
  elegirFichero(entorno);
  await pulsar(entorno, "cuaderno-leer");
  const elemento = montajes[montajes.length - 1].elemento;
  assert.ok(elemento.props.error, "no avisa de que sin conexión no se puede subir");
  assert.ok(
    !servidor.llamadas.includes("/api/cuaderno-cyl/leer"),
    "ha intentado subir sin conexión",
  );
});

// ---------------------------------------------------------------------------
// Las facturas: subirlas, leerlas y confirmarlas
// ---------------------------------------------------------------------------

/** Elige el fichero de la factura, como lo haría el agricultor con la cámara o el explorador. */
function elegirLaFactura(entorno, nombre = "factura.jpg") {
  entorno.nodos.set("factura-fichero", { id: "factura-fichero", files: [{ name: nombre }] });
}

// ---------------------------------------------------------------------------
// Las facturas se pasaron a React (la lista y el alta) en la ronda 56
//
// Lo que se ve dentro (el título, el aviso de que no hay ninguna, el campo del fichero, los tres
// botones y las facturas con su total) está en `tests_js/react.test.js`, contra los componentes. Aquí
// queda lo que solo se ve desde `app.js`: que **se le piden a React** con los datos ya contados, y
// que lo que el servidor dice (el error, la lectura pendiente, la factura recién guardada) llega
// como propiedad.
// ---------------------------------------------------------------------------

test("desde el almacén se llega a las facturas, y la lista se le pide a React", async () => {
  // Las facturas demuestran la compra, así que están donde se pregunta por el producto: en «lo que
  // tengo en el almacén». Que el almacén **lleve** a las facturas es cosa del manejador de clics.
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "cesta-ver");

  const antes = montajes.length;
  await pulsar(entorno, "facturas-abrir");
  const pedidos = montajes.slice(antes);
  assert.equal(pedidos.length, 1, `se han pedido ${pedidos.length} montajes: solo la lista`);
  const elemento = pedidos[0].elemento;
  assert.equal(elemento.type.name, "PantallaFacturas");
  assert.equal(elemento.props.textos.facturas.titulo, "Mis facturas");
  assert.deepEqual(elemento.props.facturas, [], "la finca de la prueba no tiene facturas");
  assert.equal(elemento.props.guardada, "", "enseña la confirmación sin haber guardado nada");
  assert.equal(pantallaDe(entorno), "", "la lista se ha pintado además con `pintar()`");
});

test("el papel de una factura ya apuntada se puede subir y se puede ver", async () => {
  // **Esto faltaba entero** (diseño de Stitch de la pantalla de facturas, ronda 90): los dos caminos
  // estaban en el servidor desde la ronda 40 y ninguna pantalla los pedía, así que una factura escrita a
  // mano se quedaba sin su papel para siempre. El papel es lo que se pide en una inspección.
  const conPapel = await cargarAplicacion({
    "/api/facturas": [
      {
        id: 5,
        campana_id: 1,
        fecha: "2026-03-15",
        proveedor: "COOPERATIVA AGRICOLA DE PEÑARANDA S.C.L.",
        numero_factura: "2026/00123",
        total: 980.1,
        anulada: false,
        tiene_fichero: true,
        lineas: [{ id: 1, descripcion: "GLIFOSATO", importe: 170.0 }],
      },
    ],
  });
  await pulsar(conPapel.entorno, "facturas-abrir");
  const elemento = montajes[montajes.length - 1].elemento;
  assert.equal(elemento.props.facturas[0].tiene_fichero, true, "no le llega si la factura tiene papel");
  assert.equal(elemento.props.resumen, "1 factura guardada", "no le llega la cuenta de facturas");

  // Verla: se pide el fichero al servidor.
  const antes = conPapel.servidor.llamadas.length;
  await pulsar(conPapel.entorno, "factura-papel-ver", { id: "5" });
  assert.ok(
    conPapel.servidor.llamadas.slice(antes).includes("/api/facturas/5/fichero"),
    `no ha pedido el papel: ${conPapel.servidor.llamadas.slice(antes).join(", ")}`,
  );

  // Y sin papel, se sube con el fichero que se elija: el campo se lee **por su `id`**.
  const sinPapel = await cargarAplicacion();
  await pulsar(sinPapel.entorno, "facturas-abrir");
  sinPapel.entorno.nodos.set("factura-papel-5", { id: "factura-papel-5", files: [{ name: "foto.jpg" }] });
  await pulsar(sinPapel.entorno, "factura-papel-subir", { id: "5" });
  assert.ok(
    sinPapel.servidor.llamadasConMetodo.includes("POST /api/facturas/5/fichero"),
    `no ha subido el papel: ${sinPapel.servidor.llamadasConMetodo.join(", ")}`,
  );
});

test("el alta de una factura se le pide a React", async () => {
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "facturas-abrir");
  const antes = montajes.length;
  await pulsar(entorno, "factura-nueva");
  const pedidos = montajes.slice(antes);
  assert.equal(pedidos.length, 1, `se han pedido ${pedidos.length} montajes: solo el alta`);
  const elemento = pedidos[0].elemento;
  assert.equal(elemento.type.name, "PantallaNuevaFactura");
  assert.equal(elemento.props.leyendo, false, "dice que está leyendo sin estarlo");
  assert.equal(elemento.props.error, "");
});

test("sin elegir fichero lo dice en vez de no hacer nada", async () => {
  const { entorno, servidor } = await cargarAplicacion();
  await pulsar(entorno, "facturas-abrir");
  await pulsar(entorno, "factura-nueva");
  const antes = montajes.length;
  await pulsar(entorno, "factura-leer");

  // El aviso le llega al componente como propiedad (que se pinte es cosa del componente, y se
  // comprueba en `react.test.js`). Y **no se ha llamado al servidor**: no hay nada que leer.
  const elemento = montajes[montajes.length - 1].elemento;
  assert.equal(elemento.type.name, "PantallaNuevaFactura");
  assert.ok(elemento.props.error, "no dice que falta elegir el fichero");
  assert.ok(antes >= 0);
  assert.ok(
    !servidor.llamadas.includes("/api/facturas/leer"),
    "ha llamado al servidor sin fichero",
  );
});

test("se enseña lo que el programa ha leído, para que el agricultor lo confirme", async () => {
  // **Esta es la pantalla que hace que esto se pueda usar.** Lo que se ha leído de una foto es una
  // propuesta: el agricultor la mira, la corrige y da el visto bueno.
  const { entorno, servidor } = await cargarAplicacion();
  await pulsar(entorno, "facturas-abrir");
  await pulsar(entorno, "factura-nueva");
  elegirLaFactura(entorno);
  await pulsar(entorno, "factura-leer");

  assert.ok(servidor.llamadas.includes("/api/facturas/leer"), "no ha leído la factura");

  // La interpretación **se le pide a React** con todo lo necesario para pintarla. Lo que se ve dentro
  // (los campos con lo leído, el aviso de la línea que no cuadra, de dónde sale la lectura) está en
  // `tests_js/react.test.js`, contra el componente.
  const elemento = montajes[montajes.length - 1].elemento;
  assert.equal(elemento.type.name, "PantallaInterpretacionDeLaFactura");
  const leida = elemento.props.leida;

  // Los ocho campos de la cabecera, con su etiqueta y lo que se ha leído dentro.
  const porId = Object.fromEntries(leida.cabecera.map((campo) => [campo.id, campo]));
  assert.ok(porId["factura-proveedor"], "no viene el campo del proveedor");
  assert.ok(porId["factura-proveedor"].valor.includes("COOPERATIVA AGRICOLA"), "no viene el proveedor");
  assert.equal(porId["factura-proveedor-nif"].valor, "F37012345", "no viene el NIF");
  assert.equal(porId["factura-numero"].valor, "2026/00123", "no viene el número de factura");
  assert.ok(porId["factura-total"].valor.includes("980"), "no viene el total");
  assert.equal(porId["factura-fecha"].tipo, "date", "la fecha no se pide como fecha");

  // Y las líneas, con sus opciones de producto y el aviso de la que no cuadra. Son dos: la primera
  // cuadra y la segunda no, así que el aviso tiene que venir **solo en la segunda**.
  assert.equal(leida.lineas.length, 2, "no vienen las dos líneas leídas");
  const [primera, segunda] = leida.lineas;
  assert.ok(primera.descripcion.includes("GLIFOSATO"), "no viene la descripción leída");
  assert.ok(primera.sugerida.includes("Es este: Glifosato 36 SL"), "no dice qué producto suyo es");
  assert.equal(primera.no_cuadra, false, "avisa de que no cuadra una línea que sí cuadra");
  assert.equal(segunda.no_cuadra, true, "no viene el aviso de la línea que no cuadra");
  assert.equal(segunda.sugerida, "", "inventa un producto para una línea que no lo tiene");
  // Las opciones del producto salen de la cesta del agricultor, y esta finca de prueba no tiene
  // ninguno: están las dos opciones fijas («no es de la cesta» y «crear el producto»). Que el
  // producto sugerido salga **elegido** cuando está en la cesta se comprueba en `react.test.js`,
  // contra el componente, con una cesta de verdad.
  assert.deepEqual(
    primera.opciones.map((opcion) => opcion.valor),
    ["", "nuevo"],
    "las opciones del producto no salen de la cesta del agricultor",
  );
  // Y de dónde sale la lectura: es lo que explica por qué puede haber erratas en las palabras. La
  // frase viene montada de aquí, con el rótulo del servidor y la fuente («Leída de: Una foto»),
  // porque son dos textos unidos.
  assert.ok(leida.de_donde.includes("Leída de:"), `falta el rótulo: ${leida.de_donde}`);
  assert.ok(leida.de_donde.includes("Una foto"), `no dice de dónde sale: ${leida.de_donde}`);
  // Y nada se ha guardado todavía: `/api/facturas` se pide para la lista, pero no se manda nada.
  assert.ok(
    !servidor.llamadasConMetodo.includes("POST /api/facturas"),
    "ha guardado la factura sin preguntar",
  );
});

test("la factura siguiente lleva su propia clave de reenvío", async () => {
  // **La otra mitad de la clave** (CRM-00, 11/10/2026): si la clave se quedara puesta después de guardar,
  // la segunda factura del día viajaría con la clave de la primera y el servidor la tomaría por un
  // **reenvío** —contestarle «ya estaba»— así que **no se apuntaría**, y el agricultor vería su factura
  // desaparecer sin un error. Por eso se apunta la clave al abrir el alta y se suelta al guardar: dos altas
  // distintas tienen que llevar dos claves distintas.
  const { entorno, servidor } = await cargarAplicacion();
  await pulsar(entorno, "facturas-abrir");

  const apuntarUnaFactura = async () => {
    await pulsar(entorno, "factura-nueva");
    elegirLaFactura(entorno);
    await pulsar(entorno, "factura-leer");
    rellenarLasLineasDeLaFactura(entorno);
    await pulsar(entorno, "factura-guardar");
  };

  await apuntarUnaFactura();
  await apuntarUnaFactura();

  const claves = servidor.enviados
    .filter((uno) => uno.metodo === "POST" && uno.ruta === "/api/facturas")
    .map((uno) => uno.cuerpo && uno.cuerpo.clave_de_reenvio);
  assert.equal(claves.length, 2, `tienen que salir dos altas, salieron ${claves.length}`);
  assert.ok(claves[0] && claves[1], `las dos altas tienen que llevar clave: ${JSON.stringify(claves)}`);
  assert.notEqual(
    claves[0],
    claves[1],
    "la segunda factura viaja con la clave de la primera: el servidor la daría por reenviada y no la apuntaría",
  );
});

test("con la factura escrita a mano sale la pantalla en blanco para rellenarla", async () => {
  // Quien no quiere (o no puede) hacer la foto tiene que poder apuntar la factura igual.
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "facturas-abrir");
  await pulsar(entorno, "factura-nueva");
  await pulsar(entorno, "factura-mano");
  const leida = montajes[montajes.length - 1].elemento.props.leida;
  assert.ok(leida.de_donde.includes("Escrita a mano"), `no dice que la escribes tú: ${leida.de_donde}`);
  // Y viene con una línea en blanco para poder rellenarla.
  assert.equal(leida.lineas.length, 1, "no hay ninguna línea para rellenar");
  assert.equal(leida.lineas[0].descripcion, "", "la línea en blanco trae texto");
  assert.ok(leida.cabecera.some((campo) => campo.id === "factura-proveedor"), "faltan los campos");
});

test("al confirmar se guarda lo que está en la pantalla", async () => {
  const { entorno, servidor } = await cargarAplicacion();
  await pulsar(entorno, "facturas-abrir");
  await pulsar(entorno, "factura-nueva");
  elegirLaFactura(entorno);
  await pulsar(entorno, "factura-leer");
  // Las casillas de las líneas vienen rellenas con lo que se ha leído; aquí se ponen porque el DOM
  // de mentira no tiene formularios de verdad (ver `escribir`).
  rellenarLasLineasDeLaFactura(entorno);
  // Y el agricultor corrige el total, que es lo normal con una foto.
  escribir(entorno, "factura-total", "980,10");
  const antes = montajes.length;
  await pulsar(entorno, "factura-guardar");
  assert.ok(
    servidor.llamadasConMetodo.includes("POST /api/facturas"),
    "no ha guardado la factura",
  );
  // **Y el alta lleva su clave de reenvío** (CRM-00, 11/10/2026). Esto se comprobaba leyendo el texto de
  // `app.js` —un guardián de texto, que la guía del perfil prohíbe como sustituto de una comprobación de
  // comportamiento—, y ahora se mira **lo que de verdad sale por la puerta**: sin clave, un reintento del
  // mismo formulario (un doble toque, un corte de red) apuntaría la factura **dos veces**.
  const elAlta = servidor.enviados.filter((uno) => uno.metodo === "POST" && uno.ruta === "/api/facturas");
  assert.ok(elAlta.length >= 1, "no se ha mandado el alta");
  const suClave = elAlta[elAlta.length - 1].cuerpo && elAlta[elAlta.length - 1].cuerpo.clave_de_reenvio;
  assert.ok(
    typeof suClave === "string" && suClave.length > 0,
    `el alta de la factura no manda clave de reenvío: ${JSON.stringify(elAlta[elAlta.length - 1].cuerpo)}`,
  );
  assert.match(suClave, /^factura-de-compra-/, `la clave no es de este alta: ${suClave}`);
  // Y después de guardar se enseña la confirmación, que también es de React: se le pasa la frase
  // del servidor, y **no** la lista (que es lo que se vería si se hubiera quedado a medias).
  const elemento = montajes[montajes.length - 1].elemento;
  assert.equal(elemento.type.name, "PantallaFacturas");
  assert.ok(elemento.props.guardada, `no dice que se ha guardado: ${elemento.props.guardada}`);
  assert.ok(antes >= 0);
});

/** Rellena las casillas de las líneas de la factura, como estarían en la pantalla de verdad. */
function rellenarLasLineasDeLaFactura(entorno, cuantas = 2) {
  escribir(entorno, "factura-0-descripcion", "GLIFOSATO 36% SL 20 L");
  escribir(entorno, "factura-0-cantidad", "2");
  escribir(entorno, "factura-0-unidad", "ud");
  escribir(entorno, "factura-0-precio", "85");
  escribir(entorno, "factura-0-importe", "170");
  escribir(entorno, "factura-0-producto", "1");
  if (cuantas > 1) {
    escribir(entorno, "factura-1-descripcion", "NITRATO AMONICO 33,5%");
    escribir(entorno, "factura-1-cantidad", "1000");
    escribir(entorno, "factura-1-unidad", "kg");
    escribir(entorno, "factura-1-precio", "0,45");
    escribir(entorno, "factura-1-importe", "450");
  }
}

test("si la misma factura ya estaba subida, se avisa", async () => {
  // Subir dos veces la misma foto es lo que hace todo el mundo, y apuntarla dos veces descuadraría
  // el almacén y las cuentas.
  const leida = { ...RESPUESTAS["/api/facturas/leer"], ya_estaba: 7, numero_factura: "2026/00123" };
  const { entorno } = await cargarAplicacion({ "/api/facturas/leer": leida });
  await pulsar(entorno, "facturas-abrir");
  await pulsar(entorno, "factura-nueva");
  elegirLaFactura(entorno);
  await pulsar(entorno, "factura-leer");
  const avisos = montajes[montajes.length - 1].elemento.props.leida.avisos;
  assert.ok(
    avisos.some((aviso) => aviso.includes("ya la has subido")),
    `no avisa de que ya estaba: ${JSON.stringify(avisos)}`,
  );
});

test("sin conexión no se intenta leer la factura", async () => {
  const { entorno, servidor } = await cargarAplicacion();
  entorno.navigator.onLine = false;
  globalThis.navigator = entorno.navigator;
  await pulsar(entorno, "facturas-abrir");
  await pulsar(entorno, "factura-nueva");
  elegirLaFactura(entorno);
  await pulsar(entorno, "factura-leer");
  const elemento = montajes[montajes.length - 1].elemento;
  assert.equal(elemento.type.name, "PantallaNuevaFactura");
  assert.ok(elemento.props.error, "no avisa de que sin cobertura no se puede leer");
  assert.ok(
    !servidor.llamadas.includes("/api/facturas/leer"),
    "ha intentado leer sin conexión",
  );
});

test("las facturas guardadas se ven con su proveedor, su número y su total", async () => {
  const { entorno } = await cargarAplicacion({
    "/api/facturas": [
      {
        id: 5,
        fecha: "2026-03-15",
        proveedor: "COOPERATIVA AGRICOLA DE PEÑARANDA S.C.L.",
        numero_factura: "2026/00123",
        total: 980.1,
        anulada: false,
        lineas: [{ id: 1, descripcion: "GLIFOSATO 36% SL 20 L", importe: 170.0 }],
      },
    ],
  });
  const antes = montajes.length;
  await pulsar(entorno, "facturas-abrir");
  const elemento = montajes[montajes.length - 1].elemento;
  assert.equal(elemento.type.name, "PantallaFacturas");
  const factura = elemento.props.facturas[0];
  assert.ok(factura.proveedor.includes("COOPERATIVA AGRICOLA"), "no viene el proveedor");
  assert.ok(factura.detalle.includes("2026/00123"), `no viene el número: ${factura.detalle}`);
  assert.equal(factura.total, "980,10 €", `el total no viene escrito: ${factura.total}`);
  assert.equal(factura.lineas, "1", "no viene cuántas líneas trae");
  assert.ok(antes >= 0);
});

test("una factura sin total no se enseña como cero", async () => {
  // Un total que no se dijo **no es un cero**: es un dato que falta. Enseñarlo como cero sería
  // inventarse un número, y las cuentas del almacén saldrían mal sin que nadie lo note.
  const { entorno } = await cargarAplicacion({
    "/api/facturas": [
      { id: 6, fecha: "2026-04-01", proveedor: "Talleres Pepe", numero_factura: null, total: null, anulada: false, lineas: [] },
    ],
  });
  await pulsar(entorno, "facturas-abrir");
  const factura = montajes[montajes.length - 1].elemento.props.facturas[0];
  assert.equal(factura.total, "—", `un total desconocido no puede ser un número: ${factura.total}`);
  assert.equal(factura.detalle, "01/04/2026", "la línea de detalle no aguanta un número vacío");
});

test("lo que se apunta de cómo fue llega al resumen y no se pierde", async () => {
  const { entorno } = await cargarAplicacion({ "/api/productos": UN_PRODUCTO });
  await hastaLasMedidas(entorno);
  // Un salto lleva a las observaciones y el siguiente a «cómo fue»: los dos pasos opcionales van
  // seguidos, así que el que tiene prisa se los salta de dos toques.
  await pulsar(entorno, "asistente-saltar"); // las observaciones
  await pulsar(entorno, "asistente-saltar"); // y ya está en «cómo fue»
  const pantalla = pantallaPedida(entorno);
  assert.ok(
    pantalla.includes("¿Quieres apuntar cómo fue?"),
    `no ha llegado a la pantalla de cómo fue: ${pantalla.replace(/<[^>]*>/g, " ").slice(0, 200)}`,
  );
  escribir(entorno, "hora_inicio", "07:30");
  escribir(entorno, "hora_fin", "10:15");
  escribir(entorno, "estado_cultivo", "Espigando");
  escribir(entorno, "viento_kmh", "12");
  escribir(entorno, "viento_direccion", "Norte");
  await pulsar(entorno, "asistente-seguir"); // el resumen
  const resumen = resumenPedido();
  assert.ok(resumen.includes("07:30"), `el resumen no dice la hora: ${resumen}`);
  assert.ok(resumen.includes("Espigando"), "el resumen no dice cómo estaba la planta");
  assert.ok(resumen.includes("km/h"), "el resumen no dice el viento");
});

test("sin medidas declaradas, el apunte las pregunta igual y ofrece declararlas", async () => {
  // Las diez preguntas salen aunque no haya declaración: esta vez el agricultor dice lo
  // que hizo. Y además se le dice dónde se contesta una vez para todo el año.
  const { entorno } = await cargarAplicacion({ "/api/productos": UN_PRODUCTO });
  await hastaLasMedidas(entorno);
  // Las diez preguntas y el aviso los pide React: se mira lo que se le pide.
  const textos = textoDeLaLista();
  assert.ok(textos.includes("¿Cambias de cultivo de un año a otro?"), `no pregunta las medidas: ${textos.slice(0, 300)}`);
  const aviso = avisoDeLaLista();
  assert.ok(aviso.includes("Todavía no has dicho qué haces sin echar producto."), aviso);
  assert.ok(aviso.includes("MARCAR LO QUE HAGO"), `se dice qué falta pero no se puede hacer: ${aviso}`);
});

// ---------------------------------------------------------------------------
// Los análisis de laboratorio
// ---------------------------------------------------------------------------

/** Un análisis de suelo como el que devuelve el servidor. */
function unAnalisis(cambios = {}) {
  return {
    id: 1,
    campana_id: 1,
    tipo: "suelo",
    etiqueta_tipo: "La tierra",
    fecha_toma_muestra: "2026-02-14",
    fecha_resultado: "2026-02-28",
    parcela_id: 1,
    instalacion_id: null,
    lote: null,
    laboratorio: "Laboratorio Agrario de Villamuriel",
    nif_laboratorio: "B34123456",
    numero_informe: "2026/0417",
    tipo_analisis: null,
    sustancia_detectada: null,
    parametros: [
      { clave: "materia_organica", valor: 1.8, unidad: "%" },
      { clave: "ph", valor: 7.4, unidad: "" },
    ],
    parametros_con_nombre: [
      { clave: "materia_organica", etiqueta: "Materia orgánica", valor: 1.8, unidad: "%", texto: "1,80 %" },
      { clave: "ph", etiqueta: "pH", valor: 7.4, unidad: "", texto: "7,40" },
    ],
    fichero_nombre: "boletin.pdf",
    fichero_tipo: "application/pdf",
    fichero_bytes: 12345,
    observaciones: null,
    anulado: false,
    anios: 0,
    donde: "El Prado",
    ...cambios,
  };
}

test("sin análisis, mi cuaderno lo dice y ofrece apuntar uno", async () => {
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "inicio", { ir: "mi_cuaderno" });
  const analiticas = ultimoCuadernoPedido().analiticas;
  assert.equal(analiticas.titulo, "Los análisis", "no hay apartado de análisis");
  assert.equal(analiticas.hay, false);
  assert.ok(analiticas.sin_analisis.includes("Todavía no has apuntado ningún análisis."));
  assert.deepEqual(
    analiticas.acciones.map((accion) => accion.accion),
    ["analisis-nuevo"],
    "avisa pero no ofrece arreglarlo",
  );
});

test("con análisis, mi cuaderno enseña los últimos con sus números", async () => {
  const { entorno } = await cargarAplicacion({ "/api/analiticas": [unAnalisis()] });
  await pulsar(entorno, "inicio", { ir: "mi_cuaderno" });
  const analiticas = ultimoCuadernoPedido().analiticas;
  assert.equal(analiticas.hay, true);
  const fila = analiticas.filas[0];
  assert.ok(fila.titulo.includes("Análisis de La tierra de El Prado"), `no dice cuál es: ${fila.titulo}`);
  assert.equal(fila.fecha, "14/02/2026", "la fecha no viene escrita en el formato de aquí");
  // Los números llegan montados en una línea: el componente no junta etiquetas con valores.
  assert.ok(fila.detalle.includes("Materia orgánica: 1,80 %"), `no enseña los números: ${fila.detalle}`);
});

// ---------------------------------------------------------------------------
// «Los análisis» se pasó a React
//
// Aquí había dos pruebas que miraban el HTML de esta pantalla en el contenedor de mentira («abre
// desde mi cuaderno» y «dice de dónde sale cada lista de números»). **Se han reescrito contra el
// componente**, en `tests_js/react.test.js`, junto con las de la ficha, el papel del laboratorio y
// el campo del fichero. Aquí queda lo que solo se ve desde `app.js`: que la pantalla **se le pide
// a React** con los datos ya preparados, y que las fechas y los textos con huecos se rellenan allí.
// ---------------------------------------------------------------------------

test("la pantalla de análisis se le pide a React, con las fichas ya preparadas", async () => {
  const { entorno } = await cargarAplicacion({ "/api/analiticas": [unAnalisis()] });
  // Se cuenta a partir de aquí: al arrancar ya se ha pedido la pantalla de inicio.
  const antes = montajes.length;
  await pulsar(entorno, "analisis-ver");

  const pedidos = montajes.slice(antes);
  assert.equal(pedidos.length, 1, `se han pedido ${pedidos.length} montajes: solo la pantalla`);
  const elemento = pedidos[0].elemento;
  assert.ok(elemento, "no se le ha pedido nada a React: la pantalla se pinta a mano otra vez");
  assert.equal(elemento.type.name, "PantallaAnaliticas", "lo que se le pide no es esta pantalla");
  assert.equal(pedidos[0].contenedor, entorno.nodos.get("pantalla"));

  // Los textos son los del servidor.
  assert.equal(elemento.props.textos.analitica.titulo, "Los análisis");

  // Y la ficha llega **ya preparada**: el título con el hueco relleno, las fechas escritas en
  // castellano y la línea del informe armada. El componente no sabe nada de eso.
  const ficha = elemento.props.analisis[0];
  assert.equal(ficha.id, 1);
  assert.ok(ficha.titulo.startsWith("Análisis de"), `el título no viene hecho: ${ficha.titulo}`);
  assert.ok(
    ficha.filas.some(([, valor]) => valor === "14/02/2026"),
    `la fecha no viene escrita en castellano: ${JSON.stringify(ficha.filas)}`,
  );
  assert.ok(
    ficha.filas.some(([, valor]) => valor === "Laboratorio Agrario de Villamuriel"),
    "no viene quién hizo el análisis",
  );
  assert.ok(ficha.numeros.length > 0, "no vienen los números del boletín");
  assert.equal(typeof ficha.linea_informe, "string");
  assert.ok(ficha.linea_informe.length > 0);
  assert.equal(ficha.tiene_informe, true);

  // Y no se ha pintado además con `pintar()`: la pantalla es de React y de nadie más.
  assert.equal(
    pantallaDe(entorno),
    "",
    "la pantalla de análisis se ha pintado además con `pintar()`",
  );
});

test("apuntar un análisis empieza preguntando qué se ha analizado", async () => {
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "analisis-nuevo");
  const html = pantallaPedida(entorno);
  assert.ok(html.includes("¿Qué has mandado analizar?"), `no pregunta el material: ${html.slice(0, 200)}`);
  // Las cinco clases de análisis se eligen de una lista que pinta React: se mira el `data-valor` que
  // lleva cada botón, que es el que se apunta.
  const valores = botonesDeLaLista().map((boton) => boton.datos.valor);
  for (const tipo of ["suelo", "agua_riego", "cultivo", "producto_cosechado", "residuos"]) {
    assert.ok(valores.includes(tipo), `falta la opción ${tipo}: ${valores.join(", ")}`);
  }
  assert.equal(botonesDeLaLista()[0].datos.campo, "tipo", "la clase no dice a qué campo contesta");
});

test("eligiendo la tierra, pregunta de qué parcela salió la muestra", async () => {
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "analisis-nuevo");
  await pulsar(entorno, "elegir", { campo: "tipo", valor: "suelo" });
  // Este paso monta **dos piezas** (la lista de tierras y, debajo, la salida para el agua o un lote), así
  // que lo que se mira es **todo lo que se le ha pedido a React**, que es donde están las dos.
  const html = pantallaPedida(entorno);
  assert.ok(html.includes("¿De dónde salió?"), `no pregunta el sitio: ${html.slice(0, 200)}`);
  const todo = textosDeLoPedido();
  assert.ok(todo.includes("El Prado"), `no lista las parcelas: ${todo.slice(0, 300)}`);
  assert.ok(todo.includes("¿No es de una parcela?"), "no hay salida para el agua o un lote");
});

test("elegida la parcela, pregunta el día de la muestra", async () => {
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "analisis-nuevo");
  await pulsar(entorno, "elegir", { campo: "tipo", valor: "suelo" });
  await pulsar(entorno, "elegir", { campo: "parcela_id", valor: "1", superficie: "2.43" });
  const html = pantallaPedida(entorno);
  assert.ok(html.includes("¿Cuándo cogiste la muestra?"), `no pregunta la fecha: ${html.slice(0, 200)}`);
});

test("los números que se piden son los del boletín de esa clase de análisis", async () => {
  // Un boletín de agua no trae los nueve del suelo: los números salen del catálogo del
  // servidor, no de una lista escrita en la interfaz.
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "analisis-nuevo");
  await pulsar(entorno, "elegir", { campo: "tipo", valor: "suelo" });
  await pulsar(entorno, "elegir", { campo: "parcela_id", valor: "1", superficie: "2.43" });
  await pulsar(entorno, "asistente-seguir");
  // Los números los pide React, con el `id` de siempre (`param-<clave>`), que es como los lee
  // `recogeParametros()`: si cambiara, el boletín se rellenaría y se guardaría sin un solo número.
  const ids = idsDeLosBloques();
  assert.ok(ids.includes("param-materia_organica"), `falta la materia orgánica: ${ids.slice(0, 6)}`);
  assert.ok(ids.includes("param-ph"), "falta el pH");
  assert.ok(!ids.includes("param-nitratos"), "el nitrato no es de un análisis de tierra");
});

test("el agua pide nitratos y no los parámetros de la tierra", async () => {
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "analisis-nuevo");
  await pulsar(entorno, "elegir", { campo: "tipo", valor: "agua_riego" });
  await pulsar(entorno, "asistente-saltar"); // el agua puede no ser de una parcela
  await pulsar(entorno, "asistente-seguir");
  const ids = idsDeLosBloques();
  assert.ok(ids.includes("param-nitratos"), `falta el nitrato: ${ids.slice(0, 6)}`);
  assert.ok(!ids.includes("param-materia_organica"), "la materia orgánica es de tierra");
});

test("un análisis de tierra no se puede apuntar sin decir de qué parcela", async () => {
  // Sin parcela, el análisis no se puede usar para el plan de abono de nadie.
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "analisis-nuevo");
  await pulsar(entorno, "elegir", { campo: "tipo", valor: "suelo" });
  await pulsar(entorno, "asistente-seguir");
  const html = pantallaPedida(entorno);
  assert.ok(html.includes("¿De dónde salió?"), "ha dejado seguir sin parcela");
});

test("el agua sí se puede apuntar sin parcela", async () => {
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "analisis-nuevo");
  await pulsar(entorno, "elegir", { campo: "tipo", valor: "agua_riego" });
  await pulsar(entorno, "asistente-seguir");
  const html = pantallaPedida(entorno);
  assert.ok(!html.includes("¿De dónde salió?"), "se ha quedado atascado en el sitio");
});

test("se puede saltar todo lo que no se sepa y llegar al resumen", async () => {
  // El agricultor puede tener el boletín en casa: tiene que poder apuntar lo que sabe.
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "analisis-nuevo");
  await pulsar(entorno, "elegir", { campo: "tipo", valor: "suelo" });
  await pulsar(entorno, "elegir", { campo: "parcela_id", valor: "1", superficie: "2.43" });
  await pulsar(entorno, "asistente-seguir"); // fecha
  await pulsar(entorno, "asistente-saltar"); // números
  await pulsar(entorno, "asistente-saltar"); // laboratorio
  await pulsar(entorno, "asistente-saltar"); // resultado y lo demás
  const html = pantallaPedida(entorno);
  assert.ok(html.includes("APUNTARLO"), `no llega al resumen: ${html.slice(0, 300)}`);
  assert.ok(
    resumenPedido().includes("La tierra"),
    `el resumen no dice qué se ha analizado: ${resumenPedido()}`,
  );
});

// ---------------------------------------------------------------------------
// El cuaderno de la Junta relleno: sacarlo y decir lo que falta
// ---------------------------------------------------------------------------

test("mi cuaderno dice lo que le falta al cuaderno de la Junta, y dónde se apunta", async () => {
  // Esto es lo que contesta a «¿qué datos me piden?»: no una lista escrita a mano, sino lo que sale
  // de comparar el cuaderno oficial con lo que el agricultor tiene apuntado.
  const { entorno, servidor } = await cargarAplicacion();
  await pulsar(entorno, "inicio", { ir: "mi_cuaderno" });
  assert.ok(servidor.llamadas.includes("/api/cuaderno-cyl/que-falta"), "no ha pedido lo que falta");

  const cuaderno = ultimoCuadernoPedido().cuaderno;
  assert.equal(cuaderno.hay, true, "no le llega el bloque del cuaderno de la Junta");
  assert.ok(cuaderno.titulo.includes("Sacar mi cuaderno para la Junta"), "no ofrece sacar el cuaderno");
  assert.ok(
    cuaderno.falta_titulo.includes("Lo que te falta para tenerlo completo"),
    "no dice lo que falta",
  );
  assert.ok(cuaderno.hojas.includes("9 hojas de 25"), `no dice cuántas hojas: ${cuaderno.hojas}`);
  const falta = cuaderno.faltan[0];
  assert.ok(falta.que_falta.includes("las máquinas con las que echas el producto"), `no dice qué falta: ${falta.que_falta}`);
  assert.ok(
    falta.donde.includes("Mis cosas → máquinas de echar producto"),
    `no dice dónde se apunta: ${falta.donde}`,
  );
  assert.ok(falta.hoja.includes(":"), `la hoja no viene con su rótulo: ${falta.hoja}`);
  assert.ok(
    cuaderno.acciones.some((accion) => accion.accion === "cuaderno-sacar"),
    "no hay botón para sacarlo",
  );
});

test("cuando no falta nada, se dice en vez de dejar la lista vacía", async () => {
  const { entorno } = await cargarAplicacion({
    "/api/cuaderno-cyl/que-falta": {
      anio: 2026,
      hojas: 25,
      hojas_con_datos: 20,
      filas: 60,
      cuantas_faltan: 0,
      faltan: [],
    },
  });
  await pulsar(entorno, "inicio", { ir: "mi_cuaderno" });
  const cuaderno = ultimoCuadernoPedido().cuaderno;
  assert.deepEqual(cuaderno.faltan, []);
  assert.ok(
    cuaderno.todo_completo.includes("No le falta nada"),
    `no lo dice: ${cuaderno.todo_completo}`,
  );
});

test("sacar el cuaderno pide el fichero del año que se está mirando", async () => {
  // Y **del año que se está mirando**, no del que le parezca al servidor (06/10/2026): la ruta, sin
  // decírselo, sacaba el del año en curso, así que quien tenía delante el cuaderno de otro año
  // descargaba uno distinto del que la pantalla le estaba describiendo.
  const { entorno, servidor } = await cargarAplicacion();
  await pulsar(entorno, "inicio", { ir: "mi_cuaderno" });
  await pulsar(entorno, "cuaderno-sacar");
  assert.ok(
    servidor.llamadas.includes("/api/cuaderno-cyl/exportar?campana_id=1"),
    `no ha pedido el fichero del cuaderno del año que se ve: ${servidor.llamadas.filter((u) => u.includes("cuaderno-cyl")).join(", ")}`,
  );
});

test("si no se puede dar la lista de lo que falta, no se enseña un hueco", async () => {
  // Sin datos no se pone el bloque: es mejor no poner nada que un botón que no lleva a ninguna parte.
  const { entorno } = await cargarAplicacion({ "/api/cuaderno-cyl/que-falta": undefined });
  await pulsar(entorno, "inicio", { ir: "mi_cuaderno" });
  const cuaderno = ultimoCuadernoPedido().cuaderno;
  assert.equal(cuaderno.hay, false, "enseña el bloque sin datos");
  assert.deepEqual(cuaderno.faltan, []);
});

test("al apuntar una máquina se pregunta lo que pide el cuaderno de la Junta", async () => {
  // La hoja 1.3 pide la descripción del equipo **con su tipo, marca y modelo**, el nº de ROMA y las
  // fechas; y la app oficial tiene tres listas distintas (propia, ajena y equipos sin ROMA). Eso es
  // lo que hace falta para que el cuaderno salga completo.
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "anadir-maestro", { tipo: "equipo" });
  // La primera pantalla pide el nombre, el tipo y de quién es la máquina, y ofrece las tres
  // titularidades. El título del paso es genérico («¿Quieres afinar más?») porque son varios datos
  // juntos: lo que se lee son las etiquetas de los bloques, y eso es lo que se comprueba aquí.
  let textos = textosDeLosBloques();
  for (const pregunta of ["¿Cómo llamas tú a la máquina?", "¿Qué máquina es?", "¿De quién es?"]) {
    assert.ok(textos.includes(pregunta), `no pregunta «${pregunta}»: ${textos}`);
  }
  assert.ok(textos.includes("No va inscrita en el ROMA"), `no ofrece los equipos sin ROMA: ${textos}`);
  // El nombre es obligatorio: sin él el asistente no deja pasar de pantalla (y hace bien).
  escribir(entorno, "nombre", "El pulverizador");
  await pulsar(entorno, "elegir", { campo: "titularidad", valor: "propia" });
  await pulsar(entorno, "asistente-seguir");

  // La segunda pantalla: la marca, el modelo y cuándo se compró, que es lo que pide la hoja 1.3.
  textos = textosDeLosBloques();
  for (const pregunta of ["¿De qué marca es?", "¿Cuándo la compraste?"]) {
    assert.ok(textos.includes(pregunta), `no pregunta «${pregunta}» (lo pide la hoja 1.3): ${textos}`);
  }
  await pulsar(entorno, "asistente-seguir");

  // Y la tercera: el número de ROMA y las dos fechas de la inspección. Las dos fechas están porque con
  // la ITV caducada no se puede echar producto, y al agricultor hay que avisarle antes.
  textos = textosDeLosBloques();
  assert.ok(textos.includes("¿Cuándo pasó la última inspección?"), `no pregunta la última inspección: ${textos}`);
  assert.ok(textos.includes("número de registro"), `no pregunta el nº de ROMA: ${textos}`);
});

// ---------------------------------------------------------------------------
// «Mis datos» se pasó a React en la ronda 40: es la **primera pantalla con campos** en React, y la
// que marca cómo se harán las demás (ver `docs/REACT.md`).
//
// Lo que comprobaba esta prueba —que los campos existen, que enseñan lo que ya hay guardado y que al
// guardar se manda al servidor— **sigue comprobándose aquí**, porque el que guarda y el que lee los
// campos sigue siendo `app.js`: los campos llevan su `id` a propósito. Lo que se comprueba ahora
// además es que los dibuja React y que le llegan los valores.
// ---------------------------------------------------------------------------

test("mis datos se le piden a React, con los valores que ya hay guardados", async () => {
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "inicio", { ir: "mi_cuaderno" });
  const antes = montajes.length;
  await pulsar(entorno, "mis-datos-abrir");
  const pedidos = montajes.slice(antes);

  assert.equal(pedidos.length, 1, `se han pedido ${pedidos.length} montajes: solo «mis datos»`);
  const elemento = pedidos[0].elemento;
  assert.ok(elemento, "no se le pide nada a React: la pantalla se está pintando a mano otra vez");
  assert.equal(elemento.type.name, "PantallaMisDatos");

  const campos = elemento.props.campos;
  // **Doce desde el 05/10/2026, y once antes.** El que se ha añadido es la producción ecológica de la
  // finca (A13 de `docs/T02_VALORES_POR_DEFECTO.md`): estaba en el modelo desde el primer día, **salía en
  // el documento que se firma** y **apagaba la comprobación ecológica**, y no había ninguna pantalla donde
  // contestarla. Este número se actualiza a propósito y con el motivo escrito; lo que de verdad importa
  // —que el campo llegue, que tenga sus tres respuestas y que su valor sea el que hay guardado— se
  // comprueba unas líneas más abajo.
  assert.equal(campos.length, 12, `le llegan ${campos.length} campos, y son doce`);
  const porNombre = Object.fromEntries(campos.map((campo) => [campo.campo, campo.valor]));
  assert.equal(porNombre.registro_autonomico, "0837267320", "no le llega el nº de registro guardado");
  assert.ok("direccion" in porNombre, "no le llega la dirección");
  assert.equal(porNombre.localidad, "Salamanca", "no le llega la localidad guardada");
  // **Y el campo nuevo, con sus tres estados** (A13): el valor que llega tiene que ser el que se lee en el
  // desplegable —«si», «no» o vacío para «no lo sé»— y su tipo el que hace que se pinte con las tres
  // opciones. Si alguien lo dejara como un campo de texto, esto se pone rojo.
  const elEcologico = campos.find((campo) => campo.campo === "produccion_ecologica");
  assert.ok(elEcologico, "el campo de la producción ecológica no llega a la pantalla: no tiene puerta");
  assert.equal(elEcologico.tipo, "si_no_no_se", "el ecológico tiene que preguntarse con tres respuestas");
  assert.ok(
    ["si", "no", ""].includes(elEcologico.valor),
    `el valor del ecológico no es uno de los tres: ${JSON.stringify(elEcologico.valor)}`,
  );
});

test("los campos de mis datos llevan su id, que es como los lee el programa al guardar", async () => {
  // **Esto no es un detalle:** el manejador de clics de esta aplicación es uno solo y vive en
  // `app.js`, así que es él quien lee los campos al pulsar GUARDAR, y los busca por su `id`. Decenas
  // de pruebas escriben en ellos igual (con `escribir`), que es como lo hace una persona.
  const { entorno, servidor } = await cargarAplicacion();
  await pulsar(entorno, "inicio", { ir: "mi_cuaderno" });
  await pulsar(entorno, "mis-datos-abrir");

  escribir(entorno, "finca-localidad", "Salamanca");
  const antes = montajes.length;
  await pulsar(entorno, "mis-datos-guardar");
  assert.ok(
    servidor.llamadasConMetodo.includes("PUT /api/mi-finca"),
    "no ha guardado los datos",
  );

  // Que se diga «Tus datos están guardados» se comprueba en lo que se le pide a React, porque el
  // aviso lo dibuja el componente (el DOM de mentira de este fichero no puede montar React).
  const nuevos = montajes.slice(antes);
  assert.equal(nuevos.length, 1, "al guardar no se ha vuelto a pedir la pantalla");
  assert.equal(
    nuevos[0].elemento.props.guardado,
    true,
    "después de guardar no se le dice al agricultor que se ha guardado",
  );
});

// ---------------------------------------------------------------------------
// «Quién entra en mi finca» (ronda 89): varias cuentas en la misma finca
//
// Lo que se comprueba aquí es lo que solo se puede ver desde `app.js`: que la pantalla se le pide a React
// con los datos que ha traído el servidor, que el correo que se escribe **llega al servidor** por el `id`
// del campo, que quitar pregunta antes, y que cambiar de finca cambia el vale y vuelve a pedir todo. Lo
// que se ve en la pantalla se comprueba en `react.test.js`, contra el componente.
// ---------------------------------------------------------------------------

/** La última pantalla que se le ha pedido a React. */
function ultimoMontaje() {
  return montajes[montajes.length - 1].elemento;
}

test("el botón de quién entra está en mis datos, que es la pantalla de la finca", async () => {
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "inicio", { ir: "mi_cuaderno" });
  await pulsar(entorno, "mis-datos-abrir");
  const props = ultimoMontaje().props;
  assert.equal(props.textos.fincas.titulo, "Quién entra en mi finca", "no le llegan los textos de las fincas");
  assert.ok(
    props.textos.fincas.anadir,
    "sin los textos, el botón de «quién entra» sale en blanco",
  );
});

test("quién entra se le pide a React, con lo que dice el servidor", async () => {
  const { entorno, servidor } = await cargarAplicacion();
  await pulsar(entorno, "inicio", { ir: "mi_cuaderno" });
  await pulsar(entorno, "mis-datos-abrir");
  const antes = montajes.length;
  await pulsar(entorno, "quien-entra-abrir");
  const pedidos = montajes.slice(antes);

  assert.equal(pedidos.length, 1, `se han pedido ${pedidos.length} montajes: solo esta pantalla`);
  const elemento = pedidos[0].elemento;
  assert.equal(elemento.type.name, "PantallaQuienEntra", "no se le pide la pantalla de las fincas a React");

  // Las dos listas se piden al servidor, y **juntas**: una sin la otra deja la pantalla mintiendo.
  assert.ok(servidor.llamadas.includes("/api/fincas"), "no ha pedido las fincas de la cuenta");
  assert.ok(servidor.llamadas.includes("/api/fincas/quien-entra"), "no ha pedido quién entra");

  assert.equal(elemento.props.finca, "La finca de David", "no le llega en qué finca está");
  assert.equal(elemento.props.fincas.length, 2, "no le llegan las fincas en las que puede entrar");
  assert.equal(elemento.props.soyTitular, true, "no le llega si es el titular");
  assert.equal(elemento.props.personas.length, 2, "no le llega quién entra");
  assert.equal(elemento.props.personas[1].correo, "ana@ejemplo.test");
  assert.equal(elemento.props.error, "", "enseña un error sin que haya pasado nada");
});

test("el correo que se escribe llega al servidor, leído por el id del campo", async () => {
  // **Esto es lo que se rompe sin que salte nada**: el campo lo dibuja React, pero quien lo lee al pulsar
  // AÑADIR UNA CUENTA es `app.js`, y lo busca por su `id`. Si el `id` cambia, se manda un correo vacío y el
  // agricultor ve «no hay ninguna cuenta con ese correo» sin haber escrito nada mal.
  const { entorno, servidor } = await cargarAplicacion();
  await pulsar(entorno, "inicio", { ir: "mi_cuaderno" });
  await pulsar(entorno, "mis-datos-abrir");
  await pulsar(entorno, "quien-entra-abrir");

  escribir(entorno, "persona-correo", "  Juan@Ejemplo.test  ");
  await pulsar(entorno, "finca-anadir");

  const enviado = servidor.enviados.find((uno) => uno.metodo === "POST" && uno.ruta === "/api/fincas/quien-entra");
  assert.ok(enviado, "no ha mandado nada al servidor");
  assert.deepEqual(enviado.cuerpo, { correo: "Juan@Ejemplo.test" }, "el correo no va como toca");

  // Y se enseña lo que ha contestado el servidor (la lista ya con la cuenta nueva), con su aviso.
  const props = ultimoMontaje().props;
  assert.equal(props.personas.length, 3, "no se enseña la lista que ha devuelto el servidor");
  assert.equal(props.aviso, "Ya puede entrar en tu finca.", "no se dice que se ha añadido");
});

test("si el servidor dice que esa cuenta no existe, se lee tal cual", async () => {
  const { entorno } = await cargarAplicacion({
    "POST /api/fincas/quien-entra": falla({ detail: "No hay ninguna cuenta con ese correo." }),
  });
  await pulsar(entorno, "inicio", { ir: "mi_cuaderno" });
  await pulsar(entorno, "mis-datos-abrir");
  await pulsar(entorno, "quien-entra-abrir");
  escribir(entorno, "persona-correo", "nadie@ejemplo.test");
  await pulsar(entorno, "finca-anadir");

  const props = ultimoMontaje().props;
  assert.equal(props.error, "No hay ninguna cuenta con ese correo.", "no se enseña lo que ha dicho el servidor");
  assert.equal(props.aviso, "", "dice que se ha añadido cuando no se ha podido");
  assert.equal(props.personas.length, 2, "se ha añadido a alguien que el servidor no ha aceptado");
});

test("quitar el acceso se pregunta antes y se manda", async () => {
  // Quitar el acceso es lo único de esta pantalla que no se deshace con otro toque (habría que volver a
  // escribir el correo), así que se pregunta con el mismo `window.confirm` que usa el botón de salir. El
  // `confirm` del entorno de mentira dice que sí; lo que se comprueba es que se llama.
  const { entorno, servidor } = await cargarAplicacion();
  let preguntas = 0;
  entorno.window.confirm = (texto) => {
    preguntas += 1;
    assert.equal(texto, "¿Quitarle el acceso a esta cuenta? Podrás volver a añadirla cuando quieras.");
    return true;
  };
  await pulsar(entorno, "inicio", { ir: "mi_cuaderno" });
  await pulsar(entorno, "mis-datos-abrir");
  await pulsar(entorno, "quien-entra-abrir");
  await pulsar(entorno, "finca-quitar", { persona: "4" });

  assert.equal(preguntas, 1, "no ha preguntado antes de quitar el acceso");
  assert.ok(
    servidor.llamadasConMetodo.includes("DELETE /api/fincas/quien-entra/4"),
    `no ha quitado el acceso: ${servidor.llamadasConMetodo.join(", ")}`,
  );
  const props = ultimoMontaje().props;
  assert.equal(props.personas.length, 1, "se sigue enseñando la cuenta que se ha quitado");
  assert.equal(props.aviso, "Ya no entra en tu finca.");
});

test("si se dice que no a la pregunta, no se quita nada", async () => {
  const { entorno, servidor } = await cargarAplicacion();
  entorno.window.confirm = () => false;
  await pulsar(entorno, "inicio", { ir: "mi_cuaderno" });
  await pulsar(entorno, "mis-datos-abrir");
  await pulsar(entorno, "quien-entra-abrir");
  const antes = montajes.length;
  await pulsar(entorno, "finca-quitar", { persona: "4" });

  assert.ok(
    !servidor.llamadasConMetodo.includes("DELETE /api/fincas/quien-entra/4"),
    "ha quitado el acceso después de decirle que no",
  );
  assert.equal(montajes.length, antes, "ha vuelto a pintar la pantalla sin haber cambiado nada");
});

test("cambiar de finca guarda el vale nuevo y vuelve a pedir todo", async () => {
  // **Las dos mitades del mismo trabajo.** El vale dice en qué finca se está trabajando, así que el viejo
  // ya no vale; y todo lo que hay en memoria (tierras, apuntes, cuaderno) es de la finca anterior, así que
  // enseñarlo después de cambiar sería enseñarle a un agricultor los datos de otra finca.
  const { entorno, servidor } = await cargarAplicacion({}, { almacen: { "cuedigital.ultimo": { tipo: "tratamiento" } } });
  await pulsar(entorno, "inicio", { ir: "mi_cuaderno" });
  await pulsar(entorno, "mis-datos-abrir");
  await pulsar(entorno, "quien-entra-abrir");
  const antes = montajes.length;
  await pulsar(entorno, "finca-entrar", { id: "3" });

  const enviado = servidor.enviados.find((uno) => uno.metodo === "POST" && uno.ruta === "/api/fincas/cambiar");
  assert.ok(enviado, "no ha pedido cambiar de finca");
  assert.deepEqual(enviado.cuerpo, { explotacion_id: 3 }, "no dice a qué finca se cambia");

  // El vale nuevo, guardado en el móvil (que es de donde lo lee el arranque siguiente).
  assert.equal(
    entorno.window.localStorage.getItem("cuedigital.token"),
    "vale-de-la-otra-finca",
    "no se ha guardado el vale nuevo",
  );
  // Y se olvida «lo mismo que la última vez»: ese atajo repetiría un apunte de la finca anterior.
  assert.equal(
    entorno.window.localStorage.getItem("cuedigital.ultimo"),
    null,
    "el atajo de repetir sigue apuntando a la finca anterior",
  );
  // Y se vuelven a pedir los datos: se pregunta otra vez por las tierras y por quién entra.
  assert.ok(
    servidor.llamadas.filter((ruta) => ruta === "/api/parcelas").length >= 2,
    "no ha vuelto a pedir las tierras de la finca nueva",
  );
  // Y se sale de esta pantalla al inicio, que es donde se apunta.
  assert.equal(
    montajes[montajes.length - 1].elemento.type.name,
    "PantallaInicio",
    "después de cambiar de finca no se va al inicio",
  );
  assert.ok(montajes.length > antes, "no ha pintado nada después de cambiar de finca");
});

test("al cambiar de finca se olvida lo que no viene de ninguna lista", async () => {
  // **El agujero que quedaba** (T04, 02/10/2026). `cargarDatos()` vuelve a pedir las listas y las
  // sobrescribe, pero no toca lo que no es una lista: la **fila elegida** en una tabla y lo escrito en el
  // buscador. Así, después de cambiar de finca, el panel de detalle seguía enseñando **una tierra de la
  // otra finca**. Es el aislamiento entre explotaciones, no una cuestión de estética.
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "inicio", { ir: "mis_cosas" });
  await pulsar(entorno, "elegir-fila", { tabla: "tierras", id: "1" });
  escribir(entorno, "buscar_tierra_mis_cosas", "vega");
  await pulsar(entorno, "buscar-tierra-mis-cosas");
  // Se comprueba que de verdad había algo que olvidar: si no, la prueba no probaría nada.
  assert.equal(
    montajes[montajes.length - 1].elemento.props.secciones[0].elementos.length,
    1,
    "la búsqueda no ha filtrado nada, así que no hay nada que olvidar",
  );

  await pulsar(entorno, "inicio", { ir: "mis_datos" });
  await pulsar(entorno, "quien-entra-abrir");
  await pulsar(entorno, "finca-entrar", { id: "3" });

  // Y al volver a mirar las tierras de la finca nueva: nada buscado y **ninguna fila elegida**.
  await pulsar(entorno, "inicio", { ir: "mis_cosas" });
  const seccion = montajes[montajes.length - 1].elemento.props.secciones[0];
  assert.equal(
    seccion.elementos.length,
    2,
    "el buscador sigue filtrando con lo que se escribió en la finca anterior",
  );
  assert.equal(seccion.buscar.props.valor, "", "el buscador sigue con lo escrito en la otra finca");
  assert.equal(
    seccion.tabla.panel.elegida,
    false,
    "sigue elegida una tierra de la finca anterior: el panel enseñaría una tierra que no es de aquí",
  );
  assert.ok(
    seccion.tabla.filas.every((fila) => !fila.elegida),
    "alguna fila sigue marcada como elegida desde la finca anterior",
  );
});

test("si no se puede cambiar de finca, se dice y no se cambia el vale", async () => {
  const { entorno } = await cargarAplicacion({
    "POST /api/fincas/cambiar": falla({ detail: "Esa finca no es tuya o ya no tienes acceso a ella." }),
  });
  await pulsar(entorno, "inicio", { ir: "mi_cuaderno" });
  await pulsar(entorno, "mis-datos-abrir");
  await pulsar(entorno, "quien-entra-abrir");
  await pulsar(entorno, "finca-entrar", { id: "3" });

  assert.equal(
    entorno.window.localStorage.getItem("cuedigital.token"),
    "token-de-prueba",
    "ha cambiado el vale sin que el servidor lo haya aceptado",
  );
  assert.match(ultimoMontaje().props.error, /no es tuya/);
  assert.equal(ultimoMontaje().type.name, "PantallaQuienEntra", "se ha ido del sitio sin haber cambiado");
});

test("la aplicación dice dónde se apunta cada cosa y con el enlace del sitio oficial", async () => {
  // David preguntó «¿a qué se refiere con registro electrónico? ¿dónde debo registrar los apuntes?».
  // La respuesta tiene que estar en la aplicación, y con la dirección de cada sitio oficial, porque
  // cuando hay que traer un dato de fuera el enlace ahorra media hora de búsqueda.
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "inicio", { ir: "mi_cuaderno" });
  const registro = ultimoCuadernoPedido().registro;
  assert.equal(registro.hay, true, "no le llega el bloque del registro electrónico");
  assert.ok(registro.que_es.includes("guardado en un programa"), `no explica qué es: ${registro.que_es}`);
  assert.ok(registro.titulo.includes("Dónde apunto lo que hago"), "no dice dónde se apunta");
  assert.ok(
    registro.donde.includes("en esta aplicación"),
    `no dice que se puede apuntar aquí: ${registro.donde}`,
  );
  assert.ok(registro.desde_cuando.includes("31 de diciembre de 2026"), "no dice hasta cuándo vale el papel");
  assert.ok(registro.desde_cuando.includes("1 de enero de 2027"), "no dice desde cuándo es obligatorio");
  assert.ok(
    registro.es_voluntario.includes("a la Junta por internet es voluntario"),
    "no dice qué es voluntario",
  );
  const direcciones = registro.enlaces.map((enlace) => enlace.url).join(" ");
  assert.ok(
    direcciones.includes("https://particulares.ayg.jcyl.es"),
    `no está el enlace del cuaderno de la Junta: ${direcciones}`,
  );
  assert.ok(
    direcciones.includes("registro-productos"),
    "no está el enlace para mirar los productos autorizados",
  );
});

// ---------------------------------------------------------------------------
// «Los papeles» se pasó a React en la ronda 33
//
// Aquí se comprueba lo que solo se ve desde `app.js`: que la pantalla **se le pide a React** con los
// papeles ya agrupados por carpeta. Lo que se ve dentro (los dos botones distintos, el campo del
// fichero con su `id`, el aviso de que no hay ninguno y el error del servidor) está en
// `tests_js/react.test.js`, contra el componente.
// ---------------------------------------------------------------------------

test("los papeles se le piden a React, agrupados por carpeta", async () => {
  const { entorno } = await cargarAplicacion();
  const antes = montajes.length;
  await pulsar(entorno, "papel-ver-todos");
  const pedidos = montajes.slice(antes);

  assert.equal(pedidos.length, 1, `se han pedido ${pedidos.length} montajes: solo «los papeles»`);
  const elemento = pedidos[0].elemento;
  assert.ok(elemento, "no se le pide nada a React: la pantalla se está pintando a mano otra vez");
  assert.equal(elemento.type.name, "PantallaDocumentos");

  // Los grupos ya vienen preparados desde `app.js`, con sus papeles y su detalle.
  assert.ok(Array.isArray(elemento.props.carpetas), "no le llegan las carpetas");
  assert.equal(typeof elemento.props.total, "number", "no le llega cuántos papeles hay");
  assert.ok("error" in elemento.props, "no le llega el error del servidor (aunque sea vacío)");

  const todosLosPapeles = elemento.props.carpetas.flatMap((carpeta) => carpeta.papeles);
  for (const papel of todosLosPapeles) {
    assert.ok(papel.titulo, "un papel sin título");
    assert.equal(typeof papel.tiene_fichero, "boolean", "no se sabe si el papel tiene fichero");
    assert.ok(papel.detalle, "un papel sin detalle");
  }

  assert.equal(entorno.nodos.get("pantalla").innerHTML, "");
});

// ---------------------------------------------------------------------------
// «Guardar un papel» se pasó a React (el formulario, que es lo que faltaba)
//
// La lista ya era de React; lo que quedaba era el formulario. Y este es el sitio donde se comprueba
// lo que **de verdad** importa al migrar un formulario: que lo que el agricultor escribe llegue al
// servidor. Los `id` de los seis campos viven en el componente (`tests_js/react.test.js` los mira
// uno a uno) y los lee `app.js`; si uno se cambia, aquí se ve.
// ---------------------------------------------------------------------------

test("lo escrito en el formulario de papeles se guarda con sus datos", async () => {
  const { entorno, servidor } = await cargarAplicacion({
    "POST /api/documentos": { id: 1, titulo: "Contrato de la finca del rio" },
  });
  await pulsar(entorno, "papel-ver-todos");
  const antes = montajes.length;
  await pulsar(entorno, "papel-nuevo");

  const pedidos = montajes.slice(antes);
  assert.equal(pedidos.length, 1, `se han pedido ${pedidos.length} montajes: solo el formulario`);
  const elemento = pedidos[0].elemento;
  assert.equal(elemento.type.name, "PantallaNuevoDocumento");
  assert.ok(Array.isArray(elemento.props.tipos), "no le llegan las clases de papel del servidor");
  assert.ok(Array.isArray(elemento.props.carpetas), "no le llegan las carpetas que ya tiene");

  // Se rellena como lo haria el agricultor.
  escribir(entorno, "papel-titulo", "Contrato de la finca del rio");
  escribir(entorno, "papel-carpeta", "Contratos");
  escribir(entorno, "papel-fecha", "2026-03-01");
  escribir(entorno, "papel-quien", "Dueno de la tierra");
  escribir(entorno, "papel-notas", "Se renueva en septiembre");
  const antesDeGuardar = montajes.length;
  await pulsar(entorno, "papel-guardar");

  const guardado = servidor.enviados.find(
    (envio) => envio.metodo === "POST" && envio.ruta === "/api/documentos",
  );
  assert.ok(guardado, "no se ha mandado el papel al servidor");
  assert.equal(guardado.cuerpo.titulo, "Contrato de la finca del rio");
  assert.equal(guardado.cuerpo.carpeta, "Contratos");
  assert.equal(guardado.cuerpo.fecha, "2026-03-01");
  assert.equal(guardado.cuerpo.quien, "Dueno de la tierra");
  assert.equal(guardado.cuerpo.notas, "Se renueva en septiembre");
  assert.equal(guardado.cuerpo.tipo, "otros", "no se manda el tipo elegido por defecto");

  // Y al guardarlo se vuelve a la lista, que tambien es de React.
  const despues = montajes.slice(antesDeGuardar);
  assert.ok(
    despues.some((pedido) => pedido.elemento && pedido.elemento.type.name === "PantallaDocumentos"),
    "despues de guardar no se vuelve a la lista de papeles",
  );
});

test("sin titulo no se guarda nada y se dice", async () => {
  // El titulo es lo unico obligatorio: un papel sin nombre no se encuentra luego. Y se comprueba
  // que **no** se manda nada al servidor.
  const { entorno, servidor } = await cargarAplicacion();
  await pulsar(entorno, "papel-nuevo");
  await pulsar(entorno, "papel-guardar");
  assert.ok(
    !servidor.llamadasConMetodo.includes("POST /api/documentos"),
    "ha mandado al servidor un papel sin nombre",
  );
});

test("tocar una carpeta la escribe en el campo, sin teclear", async () => {
  // Del diseño de Stitch de esta pantalla (ronda 90): en el móvil, y con guantes, escribir el nombre de la
  // carpeta es lo que más cuesta. Se toca y el campo queda escrito; seguir escribiendo otra sigue valiendo.
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "papel-nuevo");
  // El campo existe (lo pinta React) y está vacío.
  escribir(entorno, "papel-carpeta", "");
  await pulsar(entorno, "papel-carpeta", { nombre: "Contratos" });
  assert.equal(
    entorno.nodos.get("papel-carpeta").value,
    "Contratos",
    "tocar la carpeta no escribe su nombre en el campo",
  );
});

test("el papel se puede subir al guardarlo, en la misma pantalla", async () => {
  // **Esto faltaba entero** (diseño de Stitch de «guardar un papel», ronda 90): antes había que guardar el
  // papel, ir a la lista y subir la foto desde allí. Ahora se elige el fichero aquí y `app.js` lo manda
  // después de crear el papel, por el camino que ya existía (`POST /api/documentos/{id}/fichero`).
  const { entorno, servidor } = await cargarAplicacion({
    "POST /api/documentos": { id: 7, titulo: "Contrato de la finca del rio" },
  });
  await pulsar(entorno, "papel-nuevo");
  escribir(entorno, "papel-titulo", "Contrato de la finca del rio");
  entorno.nodos.set("papel-fichero", { id: "papel-fichero", files: [{ name: "contrato.jpg" }] });
  await pulsar(entorno, "papel-guardar");

  assert.ok(
    servidor.llamadasConMetodo.includes("POST /api/documentos/7/fichero"),
    `no ha subido el papel: ${servidor.llamadasConMetodo.join(", ")}`,
  );
  // Y el papel se crea **antes** de subir el fichero: sin el papel no hay a qué subirle nada.
  const crear = servidor.llamadasConMetodo.indexOf("POST /api/documentos");
  const subir = servidor.llamadasConMetodo.indexOf("POST /api/documentos/7/fichero");
  assert.ok(crear >= 0 && subir > crear, "ha subido el fichero antes de crear el papel");
});

test("si el papel no se puede subir, el apunte no se pierde", async () => {
  // El papel ya está creado cuando se sube el fichero: si la subida falla, se dice y se queda en la lista,
  // donde se puede volver a subir. Perder el apunte por un fichero que falla sería lo peor de todo.
  const { entorno } = await cargarAplicacion({
    "POST /api/documentos": { id: 7, titulo: "Contrato de la finca del rio" },
    "POST /api/documentos/7/fichero": falla({ detail: "El fichero no vale." }),
  });
  await pulsar(entorno, "papel-nuevo");
  escribir(entorno, "papel-titulo", "Contrato de la finca del rio");
  entorno.nodos.set("papel-fichero", { id: "papel-fichero", files: [{ name: "contrato.jpg" }] });
  await pulsar(entorno, "papel-guardar");

  const elemento = montajes[montajes.length - 1].elemento;
  assert.equal(elemento.type.name, "PantallaDocumentos", "no se vuelve a la lista de papeles");
  assert.match(elemento.props.error || "", /El fichero no vale\./, "no se dice por qué no ha subido");
});

// ---------------------------------------------------------------------------
// Los avisos de error: lo que sale cuando el servidor falla (ronda 71)
//
// Hasta la ronda 71 esto era lo último que se seguía pintando a mano: `pintar(bloqueError(...))`
// escribía el aviso con `innerHTML` **en vez de** la pantalla, y siete de los nueve sitios se quedaban
// **sin ningún botón**: el agricultor veía «No se ha podido guardar» y no tenía dónde pulsar, ni
// siquiera para volver. Ahora el aviso y su botón se le piden a React (`avisarDelError`), y aquí se
// comprueba lo que solo se ve desde `app.js`: que cada fallo **enseña el mensaje del servidor** y que
// **siempre hay salida**.
//
// Estos caminos no tenían ni una prueba: se llega a ellos solo cuando el servidor falla, y el servidor
// de mentira de este fichero da por bueno todo lo que esté en su lista. Se prueban pidiendo una ruta que
// **no está** en esa lista (así contesta 404, que es un fallo de verdad).
// ---------------------------------------------------------------------------

/**
 * Lo último que se le ha pedido a React como pantalla de error: el mensaje y, si lo lleva, el botón.
 *
 * `avisarDelError()` compone el aviso y el botón con la plantilla `html` (sin envolverlos en nada, para
 * que en la pantalla queden los dos igual que quedaban), y eso da una **lista** de elementos: el aviso
 * primero y el botón después (o `null` si ese aviso no lleva botón).
 */
function ultimoErrorPedido() {
  const elemento = montajes[montajes.length - 1].elemento;
  assert.ok(Array.isArray(elemento), "lo último que se le pide a React no es un aviso de error");
  const aviso = elemento[0];
  assert.ok(
    aviso && aviso.type && aviso.type.name === "AvisoDeError",
    `lo último que se le pide a React no es un aviso de error: ${aviso && aviso.type && aviso.type.name}`,
  );
  return { texto: aviso.props.texto, boton: elemento[1] || null };
}

test("si no se pueden guardar las medidas, se dice el motivo y se puede volver", async () => {
  // Se guarda desde la pantalla de las medidas, y si el servidor falla el agricultor se queda ahí: sin
  // el botón no tendría forma de salir de un aviso que ha borrado la pantalla donde estaba.
  //
  // **Y se guarda con `PUT`, no con `POST`** (ronda 93): la ruta del servidor está escrita así a
  // propósito («no se crea un apunte más, se sustituye la declaración entera») y un `POST` contesta 405.
  // Esta prueba tenía la respuesta copiada en `POST /api/medidas` y por eso **daba por bueno un guardado
  // que en la aplicación de verdad decía «No se ha podido»**: lo cazó probar la aplicación contra un
  // servidor de verdad. Se deja escrito aquí para que nadie lo vuelva a poner en `POST`.
  const { entorno, servidor } = await cargarAplicacion({
    "PUT /api/medidas": falla({
      detail: { avisos: [{ mensaje: "No se han podido guardar: has marcado una medida que no existe." }] },
    }),
  });
  await pulsar(entorno, "medidas-ver");
  await pulsar(entorno, "medidas-guardar");

  const { texto, boton } = ultimoErrorPedido();
  // **El motivo es el del servidor**, no uno inventado por la interfaz: la interfaz no compone frases.
  assert.equal(texto, "No se han podido guardar: has marcado una medida que no existe.");
  assert.ok(boton, "el aviso del error no lleva ninguna salida");
  assert.equal(boton.type.name, "BotonSencillo");
  assert.equal(boton.props.accion, "ir-inicio");
  assert.equal(boton.props.clase, "", "el botón de volver no lleva la clase de los botones claros");
  assert.equal(boton.props.etiqueta, "VOLVER");
  // Y se ha mandado con el método que el servidor acepta: con `POST` esto sería un 405 y la pantalla
  // diría «No se ha podido» sin que nada estuviera mal.
  assert.ok(
    servidor.llamadasConMetodo.includes("PUT /api/medidas"),
    `las medidas se han guardado con otro método: ${servidor.llamadasConMetodo.filter((una) => una.includes("medidas")).join(", ")}`,
  );
  assert.ok(
    !servidor.llamadasConMetodo.includes("POST /api/medidas"),
    "las medidas se han mandado con POST, que el servidor no acepta (405)",
  );
});

test("quitar la declaración de las medidas pregunta antes, y solo entonces la quita", async () => {
  // **Ronda 93.** El camino estaba en el servidor desde antes (`DELETE /api/medidas`) y ninguna pantalla
  // lo pedía. No es lo mismo que «no hago ninguna»: eso es una respuesta, y esto deja la finca sin
  // contestar, que es lo que hace falta para volver a empezar.
  const { entorno, servidor } = await cargarAplicacion({
    "/api/medidas": declaracionDeMedidas(["rotacion", "higiene"]),
    "DELETE /api/medidas": declaracionDeMedidas(),
  });
  await pulsar(entorno, "medidas-ver");
  const pantalla = montajes[montajes.length - 1].elemento;
  assert.equal(pantalla.props.hay_declaracion, true, "no dice que la finca ya tiene declaración");

  await pulsar(entorno, "medidas-quitar");
  const pregunta = montajes[montajes.length - 1].elemento;
  assert.equal(pregunta.props.pregunta, "¿Seguro que quieres borrarlo?");
  // Lo que va a desaparecer, con el mensaje del servidor: cuántas medidas tenía declaradas.
  assert.match(
    JSON.stringify(pregunta.props.contenido),
    /Tienes marcadas 2 medidas/,
    "la pregunta no dice lo que se va a borrar",
  );
  assert.deepEqual(
    pregunta.props.acciones.map((una) => una.accion),
    ["medidas-quitar-si", "medidas-ver", "inicio"],
    "la pregunta no ofrece sus salidas (quitarla, volver a mirarla y volver)",
  );
  // Abrir la pregunta **no quita nada**: eso es lo que hace que se pueda mirar sin miedo.
  assert.equal(
    servidor.enviados.filter((uno) => uno.metodo === "DELETE").length,
    0,
    "se ha quitado la declaración solo con abrir la pantalla que pregunta",
  );

  await pulsar(entorno, "medidas-quitar-si");
  assert.ok(
    servidor.llamadasConMetodo.includes("DELETE /api/medidas"),
    `no ha quitado la declaración: ${servidor.llamadasConMetodo.filter((una) => una.includes("medidas")).join(", ")}`,
  );
  await new Promise((resolver) => setTimeout(resolver, 200));
  const despues = montajes[montajes.length - 1].elemento;
  assert.equal(despues.props.titulo, "Borrado", "el final del quitado no dice que se ha borrado");
  // Y una finca **sin declarar** no ofrece quitar nada: no hay nada que quitar.
  const sinDeclarar = await cargarAplicacion({
    "/api/medidas": declaracionDeMedidas(),
  });
  await pulsar(sinDeclarar.entorno, "medidas-ver");
  assert.equal(
    montajes[montajes.length - 1].elemento.props.hay_declaracion,
    false,
    "una finca sin declarar dice que tiene declaración",
  );
});

test("si no se puede subir el boletín del laboratorio, se dice cuál es el papel que falta", async () => {
  // El camino más común de todos: se pulsa SUBIR EL PAPEL sin haber elegido ningún fichero.
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "analisis-informe-subir", { id: "1" });

  const { texto, boton } = ultimoErrorPedido();
  assert.equal(texto, "El papel del laboratorio");
  assert.ok(boton, "el aviso no lleva salida");
});

test("si no se puede bajar el boletín del laboratorio, se dice", async () => {
  const { entorno } = await cargarAplicacion({
    "/api/analiticas/1/informe": falla({ detail: "Ese boletín ya no está en el servidor." }),
  });
  await pulsar(entorno, "analisis-informe-bajar", { id: "1" });

  const { texto, boton } = ultimoErrorPedido();
  assert.equal(texto, "Ese boletín ya no está en el servidor.", "no se dice el motivo del servidor");
  assert.ok(boton, "el aviso no lleva salida");
});

test("si no se puede sacar el cuaderno en papel ni los datos, se dice y se puede volver", async () => {
  // Las dos descargas del cuaderno: el PDF y el fichero de datos. Eran los dos únicos avisos que ya
  // llevaban su botón de volver, y se comprueba que lo siguen llevando.
  const { entorno } = await cargarAplicacion({
    "/api/cuaderno/pdf": undefined,
    "/api/cuaderno/export.csv": undefined,
  });

  await pulsar(entorno, "sacar-papel");
  const papel = ultimoErrorPedido();
  assert.ok(papel.texto, "no se dice qué ha pasado al sacar el papel");
  assert.ok(papel.boton, "sacar el papel sin salida");

  await pulsar(entorno, "sacar-datos");
  const datos = ultimoErrorPedido();
  assert.ok(datos.texto, "no se dice qué ha pasado al sacar los datos");
  assert.ok(datos.boton, "sacar los datos sin salida");
});

test("si no se puede anular un apunte, se dice y se puede volver", async () => {
  // «DESHACER» es el botón que sale después de apuntar: si el servidor falla al anular, el agricultor
  // tiene que saber que su apunte sigue ahí y poder volver.
  const { entorno } = await cargarAplicacion({ "POST /api/tratamientos/1/anular": undefined });
  await pulsar(entorno, "deshacer", { tipo: "tratamiento", id: "1" });

  const { texto, boton } = ultimoErrorPedido();
  assert.ok(texto, "no se dice qué ha pasado");
  assert.ok(boton, "el aviso no lleva salida");
});

test("si el servidor no contesta al arrancar, se dice el fallo y no se inventa un botón", async () => {
  // Este es el único aviso **sin botón**, y no es un olvido: aquí no ha llegado ni la interfaz, así que
  // el botón diría «volver» (la clave del texto) en vez de VOLVER. Lo que sale es el mensaje del fallo.
  const { entorno } = await cargarAplicacion({ "/api/interfaz": undefined });
  const { texto, boton } = ultimoErrorPedido();
  assert.ok(texto, "no se dice qué ha pasado");
  assert.equal(boton, null, "sale un botón que no tiene texto que poner");
  assert.equal(entorno.nodos.get("pantalla").innerHTML, "");
});

// ---------------------------------------------------------------------------
// Corregir y borrar lo que ya está apuntado (ronda 91)
//
// David lo pidió así: «recuerda también dejar borrar las cosas que introduzca porque puede que me
// equivoque, o modificar también». Lo que se prueba aquí es **el cableado de `app.js`**, que es donde
// de verdad se puede romper en silencio:
//
//   · que cada apunte del cuaderno traiga sus dos botones, con su tipo y su identificador;
//   · que CORREGIR abra el asistente **con lo que había puesto** y en modo corrección;
//   · que guardar en modo corrección mande un **PUT a ese apunte** y no un POST (un POST apuntaría el
//     tratamiento dos veces, y la Junta vería dos aplicaciones donde hubo una);
//   · que BORRAR pregunte antes, enseñando lo que va a desaparecer, y que no ofrezca borrar un apunte
//     firmado (con la salida que sí vale: anularlo);
//   · y que la lista del cuaderno traiga los **cuatro** tipos de apunte, que era el otro agujero: un
//     abono, un trabajo o una cosecha no salían en ninguna pantalla después de guardarlos.
// ---------------------------------------------------------------------------

/**
 * Un tratamiento **dentro de la tierra que tiene**: 2,43 ha en una parcela de 2,43 ha.
 *
 * El de arriba (`unTratamiento`) trae 4,9 ha sobre una parcela de 2,43, que es un imposible que el
 * asistente **no deja pasar** (avisa de que has puesto más hectáreas de las que tiene la tierra). Vale
 * para las pruebas que solo miran la pantalla, pero no para las que **avanzan por el asistente**: se
 * quedarían encerradas en ese paso y la prueba diría que el asistente no llega al resumen.
 */
const DENTRO_DE_LA_TIERRA = { superficie_tratada_ha: 2.43 };

/** Un abono del año, tal y como lo devuelve `/api/fertilizaciones`. */
function unaFertilizacion(extra = {}) {
  return {
    id: 21,
    campana_id: 1,
    fecha: "2026-02-20",
    parcela_id: 1,
    grupo_id: null,
    superficie_ha: 2.43,
    fertilizante_id: 3,
    fertilizante_nombre: "Nitrato amónico 33,5%",
    kg_ha_producto: 300,
    cantidad_total_kg: 729,
    observaciones: null,
    anulado: false,
    ...extra,
  };
}

/** Un trabajo del campo, tal y como lo devuelve `/api/labores`. */
function unaLabor(extra = {}) {
  return {
    id: 31,
    campana_id: 1,
    // «laboreo» es una de las prácticas de verdad (las que ofrece la pantalla de inicio). Una
    // inventada no probaría nada: el nombre de la práctica se busca en la lista del servidor.
    tipo: "laboreo",
    fecha: "2026-03-15",
    parcela_id: 1,
    grupo_id: null,
    superficie_ha: 2.43,
    cultivo: "Trigo blando",
    detalles: { nota: "Con el apero de siempre" },
    observaciones: "Con el apero de siempre",
    anulado: false,
    ...extra,
  };
}

/** Una cosecha: es una labor con `tipo: "cosecha"` y los kilos dentro de `detalles`. */
function unaCosecha(extra = {}) {
  return unaLabor({
    id: 41,
    tipo: "cosecha",
    fecha: "2026-08-20",
    detalles: { producto: "Trigo blando", cantidad_kg: 12000 },
    observaciones: null,
    ...extra,
  });
}

/** Los apuntes que le llegan a la pantalla del cuaderno. */
async function apuntesDelCuaderno(cambios = {}) {
  const { entorno, servidor } = await cargarAplicacion(cambios);
  await pulsar(entorno, "inicio", { ir: "mi_cuaderno" });
  return { apuntes: ultimoCuadernoPedido().apuntes, entorno, servidor };
}

/**
 * Avanza por el asistente hasta el resumen y devuelve lo que se le ha pedido a React.
 *
 * Se busca el botón del último paso (APUNTARLO, o GUARDAR LOS CAMBIOS si se está corrigiendo) en vez de
 * contar pulsaciones: los pasos opcionales y los que solo salen en algunos casos hacen que el número de
 * toques cambie, y una prueba que cuenta toques se rompe sin que la aplicación tenga nada malo.
 */
async function irHastaElResumen(entorno, intentos = 20) {
  for (let paso = 0; paso < intentos; paso += 1) {
    const montado = montajes[montajes.length - 1].elemento;
    const botones = (montado && montado.props && montado.props.botones) || [];
    const etiquetas = botones.map((boton) => boton.etiqueta);
    if (etiquetas.includes("GUARDAR LOS CAMBIOS") || etiquetas.includes("APUNTARLO")) {
      return montado;
    }
    // En un paso opcional se salta: lo que se busca es llegar al resumen, y un paso opcional sin
    // contestar no cambia nada de lo que se está comprobando.
    const accion = botones.some((boton) => boton.accion === "asistente-saltar")
      ? "asistente-saltar"
      : "asistente-seguir";
    await pulsar(entorno, accion);
  }
  assert.fail("el asistente no ha llegado al resumen");
}

test("cada apunte del cuaderno lleva sus botones: sacar del almacén, corregir y borrar", async () => {
  const { apuntes } = await apuntesDelCuaderno({ "/api/tratamientos": [unTratamiento(DENTRO_DE_LA_TIERRA)] });
  const acciones = apuntes.filas[0].acciones;
  // **Tres botones desde el T09**, y el primero es el que le faltaba al almacén: un tratamiento descuenta
  // del almacén diciendo **de qué envase salió** (`POST /api/almacen/salidas`), y esa puerta tiene que
  // estar donde está el apunte, porque es el apunte el que dice lo que se gastó. Antes de esto, el libro
  // del almacén no tenía forma de saber de qué lote salía lo que se echaba.
  assert.equal(acciones.length, 3, "el apunte no lleva sus tres botones");
  assert.equal(acciones[0].accion, "salida-de-un-lote", "no se puede sacar del almacén desde el apunte");
  assert.equal(acciones[0].etiqueta, "SACAR DE UN LOTE");
  assert.equal(acciones[0].datos.tipo, "tratamiento");
  assert.equal(acciones[0].datos.id, 7, "el botón del almacén no dice de qué apunte sale");
  assert.equal(acciones[1].accion, "cosa-corregir", "no se puede corregir el apunte");
  assert.equal(acciones[1].etiqueta, "CORREGIR");
  assert.equal(acciones[1].datos.tipo, "tratamiento");
  assert.equal(acciones[1].datos.id, 7, "el botón de corregir no dice qué apunte es");
  // **Corregir va antes que borrar**: el que puede quitar algo del cuaderno no puede ser el que
  // más a mano esté.
  assert.equal(acciones[2].accion, "cosa-borrar", "no se puede borrar el apunte");
  assert.equal(acciones[2].etiqueta, "BORRAR");
  assert.equal(acciones[2].clase, "boton-peligro", "el botón de borrar no va marcado como peligro");
  assert.equal(acciones[2].datos.id, 7, "el botón de borrar no dice qué apunte es");
});

test("solo los apuntes que gastan producto llevan el botón de sacar del almacén", async () => {
  // Un trabajo del campo y una cosecha **no sacan nada del almacén** (el servidor lo contesta con
  // `AL15`), así que un botón que llevara a «eso no gasta del almacén» sería un botón de más. El abono sí:
  // son los dos apuntes que gastan producto, y son los que el servidor acepta (`APUNTES_QUE_GASTAN`).
  const { apuntes } = await apuntesDelCuaderno({
    "/api/tratamientos": [unTratamiento(DENTRO_DE_LA_TIERRA)],
    "/api/fertilizaciones": [unaFertilizacion({ fecha: "2026-02-20" })],
    "/api/labores": [unaLabor({ fecha: "2026-03-15" })],
  });
  const porEtiqueta = Object.fromEntries(apuntes.filas.map((fila) => [fila.lineas[1], fila]));
  for (const clase of ["Producto", "Abono"]) {
    assert.ok(
      porEtiqueta[clase].acciones.some((una) => una.accion === "salida-de-un-lote"),
      `${clase} no ofrece sacar del almacén`,
    );
  }
  assert.ok(
    !porEtiqueta["Trabajo"].acciones.some((una) => una.accion === "salida-de-un-lote"),
    "un trabajo del campo ofrece sacar producto del almacén, y no gasta nada",
  );
});

test("el cuaderno enseña los cuatro tipos de apunte, y de lo más nuevo a lo más viejo", async () => {
  // Hasta la ronda 91 la lista era solo de tratamientos: un abono, un trabajo o una cosecha
  // desaparecían de la vista en cuanto se guardaban, así que no había forma de arreglarlos.
  const { apuntes } = await apuntesDelCuaderno({
    "/api/tratamientos": [unTratamiento({ ...DENTRO_DE_LA_TIERRA, fecha: "2026-04-10" })],
    "/api/fertilizaciones": [unaFertilizacion({ fecha: "2026-02-20" })],
    "/api/labores": [unaLabor({ fecha: "2026-03-15" }), unaCosecha({ fecha: "2026-08-20" })],
  });

  assert.equal(apuntes.titulo, "4 apuntes en el cuaderno", "no cuenta los cuatro apuntes");
  assert.equal(apuntes.filas.length, 4, "no le llegan los cuatro apuntes");
  assert.deepEqual(
    apuntes.filas.map((fila) => fila.etiqueta),
    ["Trigo blando", "Glifosato 36 SL", "Laboreo", "Nitrato amónico 33,5%"],
    "no salen ordenados de lo más nuevo a lo más viejo, o falta alguno",
  );
  // Y cada uno dice de qué clase es: en la misma lista, un abono y un trabajo se leerían igual.
  assert.deepEqual(
    apuntes.filas.map((fila) => fila.lineas[1]),
    ["Cosecha", "Producto", "Trabajo", "Abono"],
    "los apuntes no dicen de qué clase son",
  );
  // Los kilos de la cosecha (que viven dentro de `detalles`) y las hectáreas del abono.
  const cosecha = Object.fromEntries(apuntes.filas[0].filas.map((f) => [f.etiqueta, f.valor]));
  assert.equal(cosecha["Kilos"], "12.000 kg", "la cosecha no dice cuánto se recogió");
  const abono = Object.fromEntries(apuntes.filas[3].filas.map((f) => [f.etiqueta, f.valor]));
  assert.equal(abono["Kilos por hectárea"], "300 kg", "el abono no dice cuánto se echó");
});

test("corregir un apunte abre el asistente con lo que ya estaba puesto", async () => {
  const { entorno } = await apuntesDelCuaderno({ "/api/tratamientos": [unTratamiento(DENTRO_DE_LA_TIERRA)] });
  await pulsar(entorno, "cosa-corregir", { tipo: "tratamiento", id: "7" });

  const montado = montajes[montajes.length - 1].elemento;
  assert.equal(montado.type.name, "PantallaAsistente", "corregir no abre el asistente");
  // El título y la pista dicen que se está **corrigiendo**, no apuntando otra vez: el asistente se abre
  // con los datos del apunte y sin decirlo parecería que se va a apuntar lo mismo por segunda vez.
  assert.equal(montado.props.titulo, "Corregir lo que apuntaste");
  assert.ok(
    montado.props.pista.includes("Cambia lo que esté mal"),
    "no se explica que lo que se va a hacer es cambiar el apunte",
  );
  // Y en el resumen (el último paso) el botón no dice APUNTARLO, dice GUARDAR LOS CAMBIOS.
  const ultimo = await irHastaElResumen(entorno);
  const etiquetas = ultimo.props.botones.map((boton) => boton.etiqueta);
  assert.ok(
    etiquetas.includes("GUARDAR LOS CAMBIOS"),
    `el último paso no ofrece guardar los cambios: ${etiquetas.join(", ")}`,
  );
});

test("guardar una corrección manda un PUT a ese apunte, no un POST", async () => {
  // **El fallo que esto persigue**: si la corrección mandara un POST, el tratamiento se apuntaría dos
  // veces. El cuaderno diría que se trató dos veces y la Junta tendría dos actividades donde hubo una.
  const { entorno, servidor } = await apuntesDelCuaderno({
    "/api/tratamientos": [unTratamiento(DENTRO_DE_LA_TIERRA)],
    "PUT /api/tratamientos/7": unTratamiento({ ...DENTRO_DE_LA_TIERRA, dosis: 2 }),
  });
  await pulsar(entorno, "cosa-corregir", { tipo: "tratamiento", id: "7" });
  // Hasta el final del asistente: el resumen es el último paso.
  await irHastaElResumen(entorno);
  await pulsar(entorno, "asistente-seguir");

  const correccion = servidor.enviados.find((uno) => uno.metodo === "PUT");
  assert.ok(correccion, "la corrección no se ha mandado como PUT");
  assert.equal(correccion.ruta, "/api/tratamientos/7", "no se corrige ese apunte");
  assert.equal(correccion.cuerpo.dosis, 3, "lo que se manda no lleva los datos del apunte corregido");
  assert.equal(correccion.cuerpo.producto_id, 5, "el producto del apunte se ha perdido al corregirlo");
  assert.equal(
    correccion.cuerpo.parcela_id,
    1,
    "la tierra del apunte se ha perdido al corregirlo",
  );
  assert.ok(
    !servidor.enviados.some((uno) => uno.metodo === "POST" && uno.ruta === "/api/tratamientos"),
    "además de corregir, se ha apuntado un tratamiento nuevo",
  );
  // Y la pantalla lo dice: «Corregido», no «Apuntado».
  const montado = montajes[montajes.length - 1].elemento;
  assert.equal(montado.props.resultado.corregido, true, "la pantalla no dice que se ha corregido");
});

test("un apunte nuevo se sigue apuntando con POST, aunque antes se haya corregido otro", async () => {
  // Lo que persigue esta prueba es el peor fallo posible de esta función: que el «estoy corrigiendo el
  // apunte 7» se quede pegado y el siguiente apunte, en vez de crearse, **cambie el 7**.
  const { entorno, servidor } = await apuntesDelCuaderno({
    "/api/tratamientos": [unTratamiento(DENTRO_DE_LA_TIERRA)],
    "PUT /api/tratamientos/7": unTratamiento(DENTRO_DE_LA_TIERRA),
    "POST /api/tratamientos": unTratamiento({ ...DENTRO_DE_LA_TIERRA, id: 8 }),
  });
  await pulsar(entorno, "cosa-corregir", { tipo: "tratamiento", id: "7" });
  await irHastaElResumen(entorno);
  await pulsar(entorno, "asistente-seguir");
  const correcciones = servidor.enviados.filter((uno) => uno.metodo === "PUT").length;
  assert.equal(correcciones, 1, "la corrección no se ha mandado");

  // Y ahora un tratamiento nuevo, desde el inicio: se contesta lo obligatorio y se sigue hasta el
  // final. Lo que se comprueba es que se cree **uno nuevo** y que no se toque el que se corrigió antes.
  await pulsar(entorno, "inicio", { ir: "echar_producto" });
  await pulsar(entorno, "elegir", { campo: "parcela_id", valor: "1", superficie: "2.43" });
  await pulsar(entorno, "asistente-seguir"); // la fecha
  await pulsar(entorno, "asistente-seguir"); // las hectáreas
  await pulsar(entorno, "elegir", {
    campo: "justificacion",
    valor: "Vi la plaga o la hierba en el campo",
  });
  await pulsar(entorno, "elegir", { campo: "producto_id", valor: "5" });
  await irHastaElResumen(entorno);
  await pulsar(entorno, "asistente-seguir");
  const altas = servidor.enviados.filter(
    (uno) => uno.metodo === "POST" && uno.ruta === "/api/tratamientos",
  );
  assert.equal(altas.length, 1, "el apunte nuevo no se ha creado (o se ha creado dos veces)");
  // Y la corrección de antes sigue siendo la única: el modo «corregir» no se ha quedado pegado.
  assert.equal(
    servidor.enviados.filter((uno) => uno.metodo === "PUT").length,
    correcciones,
    "un apunte nuevo ha acabado corrigiendo el apunte anterior",
  );
});

test("borrar un apunte pregunta antes, y enseña lo que va a desaparecer", async () => {
  const { entorno, servidor } = await apuntesDelCuaderno({ "/api/tratamientos": [unTratamiento(DENTRO_DE_LA_TIERRA)] });
  const antes = servidor.enviados.length;
  await pulsar(entorno, "cosa-borrar", { tipo: "tratamiento", id: "7" });

  const montado = montajes[montajes.length - 1].elemento;
  assert.equal(montado.type.name, "Confirmacion", "borrar no pregunta nada");
  assert.equal(montado.props.pregunta, "¿Seguro que quieres borrarlo?");
  // Lo mismo que enseñaba la tarjeta que se acaba de tocar: así se comprueba que es ese apunte.
  //
  // **Y la forma importa**: el resumen de un apunte son **pares** (`[etiqueta, valor]`), que es como
  // los prepara `datosDelResumen`. Con objetos, la pieza revienta al dibujarse y la pantalla se queda
  // en blanco **sin que ninguna prueba de aquí lo note** (aquí no se dibuja el componente): lo cazó la
  // comprobación en un navegador de verdad.
  const filas = montado.props.contenido.props.filas;
  assert.ok(Array.isArray(filas[0]), "las filas del resumen no son pares: la pantalla saldría en blanco");
  assert.equal(filas[0][0], "Producto", "no dice de qué clase es el apunte que se va a borrar");
  assert.equal(filas[0][1], "Glifosato 36 SL", "no dice qué apunte se va a borrar");
  assert.ok(
    filas.some((fila) => fila[1] === "El Prado"),
    "no dice en qué tierra estaba el apunte que se va a borrar",
  );
  // Las dos salidas: borrar y **corregir**, que es lo que de verdad quiere quien se ha equivocado.
  const acciones = montado.props.acciones.map((accion) => accion.accion);
  assert.deepEqual(acciones, ["cosa-borrar-si", "cosa-corregir", "inicio"]);
  // Y todavía no se ha borrado nada: la pregunta es una pregunta.
  assert.equal(
    servidor.enviados.length,
    antes,
    "se ha borrado el apunte sin esperar a que el agricultor diga que sí",
  );
});

test("decir que sí borra el apunte, en su ruta y con DELETE", async () => {
  const { entorno, servidor } = await apuntesDelCuaderno({
    "/api/tratamientos": [unTratamiento(DENTRO_DE_LA_TIERRA)],
    "DELETE /api/tratamientos/7": { borrado: true, id: 7 },
  });
  await pulsar(entorno, "cosa-borrar", { tipo: "tratamiento", id: "7" });
  await pulsar(entorno, "cosa-borrar-si", { tipo: "tratamiento", id: "7" });

  const borrado = servidor.enviados.find((uno) => uno.metodo === "DELETE");
  assert.ok(borrado, "no se ha mandado el borrado");
  assert.equal(borrado.ruta, "/api/tratamientos/7", "se ha borrado otro apunte");
  const montado = montajes[montajes.length - 1].elemento;
  assert.equal(montado.type.name, "Confirmacion");
  assert.equal(montado.props.titulo, "Borrado");
  assert.equal(montado.props.pista, "Ese apunte ya no está en tu cuaderno.");
});

test("un abono se borra por su ruta, y una labor por la de las labores", async () => {
  // Las cuatro clases de apunte viven en tres tablas y se borran por tres rutas distintas: si el
  // despachador se equivoca, borra el apunte de al lado (o ninguno).
  const abono = await apuntesDelCuaderno({
    "/api/fertilizaciones": [unaFertilizacion()],
    "DELETE /api/fertilizaciones/21": { borrado: true, id: 21 },
  });
  await pulsar(abono.entorno, "cosa-borrar", { tipo: "fertilizacion", id: "21" });
  await pulsar(abono.entorno, "cosa-borrar-si", { tipo: "fertilizacion", id: "21" });
  assert.ok(
    abono.servidor.enviados.some(
      (uno) => uno.metodo === "DELETE" && uno.ruta === "/api/fertilizaciones/21",
    ),
    "el abono no se borra por su ruta",
  );

  const trabajo = await apuntesDelCuaderno({
    "/api/labores": [unaLabor()],
    "DELETE /api/labores/31": { borrado: true, id: 31 },
  });
  await pulsar(trabajo.entorno, "cosa-borrar", { tipo: "laboreo", id: "31" });
  await pulsar(trabajo.entorno, "cosa-borrar-si", { tipo: "laboreo", id: "31" });
  assert.ok(
    trabajo.servidor.enviados.some((uno) => uno.metodo === "DELETE" && uno.ruta === "/api/labores/31"),
    "el trabajo no se borra por la ruta de las labores",
  );

  const cosecha = await apuntesDelCuaderno({
    "/api/labores": [unaCosecha()],
    "DELETE /api/cosecha/41": { borrado: true, id: 41 },
  });
  await pulsar(cosecha.entorno, "cosa-borrar", { tipo: "cosecha", id: "41" });
  await pulsar(cosecha.entorno, "cosa-borrar-si", { tipo: "cosecha", id: "41" });
  assert.ok(
    cosecha.servidor.enviados.some((uno) => uno.metodo === "DELETE" && uno.ruta === "/api/cosecha/41"),
    "la cosecha no se borra por su ruta",
  );
});

test("en la tabla, el botón de un apunte firmado dice ANULARLO, y el pie los cuenta", async () => {
  // **30/09/2026, y lo pide el diseño de escritorio del cuaderno** (`docs/stitch/escritorio/cuaderno.png`):
  // un apunte firmado no se borra, se anula. La pantalla que pregunta ya lo decía, pero **el botón seguía
  // diciendo BORRAR**: el agricultor pulsaba creyendo que iba a quitar algo y se encontraba otra cosa. Y al
  // pie, cuántos están firmados, que es lo que mira una inspección.
  const { apuntes } = await apuntesDelCuaderno({
    "/api/tratamientos": [unTratamiento(DENTRO_DE_LA_TIERRA), unTratamiento({ id: 9, fecha: "2026-06-01" })],
    "/api/firmas": [
      {
        id: 1,
        entidad: "tratamiento",
        entidad_id: 7,
        campana_id: 1,
        huella: "0".repeat(64),
        firmado_en: "2026-09-01T10:00:00",
      },
    ],
  });
  const tabla = apuntes.tabla;
  // El firmado (el 7) lleva su etiqueta y su botón de quitar dice ANULARLO; el otro, BORRAR. Los dos
  // llevan delante el botón del almacén (T09), así que el de borrar ya no es el primero de la fila.
  const porId = Object.fromEntries(
    tabla.filas.map((fila) => [fila.acciones[0].datos.id, fila]),
  );
  const elDeBorrar = (fila) => fila.acciones.find((una) => una.accion === "cosa-borrar");
  assert.equal(elDeBorrar(porId[7]).etiqueta, "ANULARLO", "un apunte firmado sigue diciendo BORRAR");
  assert.equal(elDeBorrar(porId[9]).etiqueta, "BORRAR");
  assert.equal(porId[7].celdas[1].estado.texto, "Firmado");
  // Y el pie: los apuntes, las hectáreas y cuántos están firmados.
  assert.match(tabla.resumen, /2 apuntes · [\d.,]+ ha tratadas · 1 firmado/, tabla.resumen);
});

test("el panel de una tierra lleva su forma dibujada y lo último que se le ha hecho", async () => {
  // **30/09/2026.** Lo pide el diseño de escritorio de la tabla de tierras
  // (`docs/stitch/escritorio/estructura.png`): el panel de la tierra elegida lleva **el dibujo de su
  // recinto** —es como el agricultor reconoce una tierra: la ve así en el SIGPAC, y la tarjeta del móvil lo
  // lleva desde la ronda 78— y **sus últimos apuntes**, que es la pregunta que se hace en el despacho
  // («¿qué le he hecho este año?»). Los apuntes salen de los que ya están cargados: ni una petición más.
  const { apuntes: _sinUsar, entorno } = await apuntesDelCuaderno({
    "/api/tratamientos": [
      unTratamiento({ ...DENTRO_DE_LA_TIERRA, fecha: "2026-05-02" }),
      unTratamiento({ ...DENTRO_DE_LA_TIERRA, id: 9, fecha: "2026-06-10", producto_nombre: "Cobre 50 WP" }),
    ],
    // La tierra, con la forma de su recinto dibujada: es el dato que el panel tiene que enseñar (la copia de
    // prueba no la traía, y por eso la primera vez esta prueba falló: el panel no tenía qué dibujar).
    "/api/parcelas": [
      {
        id: 1,
        alias: "El Prado",
        superficie_ha: 2.43,
        sistema: "secano",
        municipio: "Calvarrasa de Arriba",
        ref_sigpac: "37-70-0-0-503-51-1",
        dibujo: "M10 10 L90 10 L90 60 L10 60 Z",
      },
      {
        id: 2,
        alias: "La Vega",
        superficie_ha: 5.0,
        sistema: "regadío",
        municipio: "Peñaranda de Bracamonte",
        ref_sigpac: "37-70-0-0-112-4-2",
      },
    ],
  });
  await pulsar(entorno, "mis-cosas");
  await pulsar(entorno, "elegir-fila", { tabla: "tierras", id: 1 });
  const panel = tablaDeTierrasPedida().panel;
  assert.equal(panel.elegida, true);
  // El dibujo de la forma (viene en la ficha de la tierra).
  assert.ok(panel.dibujo, "el panel de la tierra no lleva el dibujo de su forma");
  // Y sus últimos apuntes, del más nuevo al más viejo (los apuntes del año ya vienen ordenados así).
  assert.equal(panel.ultimos.titulo, "Lo último que le has hecho");
  assert.equal(panel.ultimos.filas.length, 2);
  assert.match(panel.ultimos.filas[0], /10\/06\/2026/);
  assert.match(panel.ultimos.filas[1], /02\/05\/2026/);
});

test("un apunte firmado no ofrece borrar: ofrece anularlo, que es lo que sí vale", async () => {  // La firma es la prueba de lo que había apuntado, así que el servidor no deja borrar el apunte (409).
  // Enseñar el botón de borrar sería mandar al agricultor a un «no se puede»: se le ofrece la salida
  // que de verdad tiene.
  const { entorno } = await apuntesDelCuaderno({
    "/api/tratamientos": [unTratamiento(DENTRO_DE_LA_TIERRA)],
    "/api/firmas": [
      {
        id: 1,
        entidad: "tratamiento",
        entidad_id: 7,
        campana_id: 1,
        huella: "0".repeat(64),
        firmado_en: "2026-09-01T10:00:00",
      },
    ],
  });
  await pulsar(entorno, "cosa-borrar", { tipo: "tratamiento", id: "7" });

  const montado = montajes[montajes.length - 1].elemento;
  assert.equal(montado.props.pregunta, "Este apunte está firmado, así que no se puede borrar.");
  const acciones = montado.props.acciones.map((accion) => accion.accion);
  assert.ok(!acciones.includes("cosa-borrar-si"), "se ofrece borrar un apunte firmado");
  assert.equal(acciones[0], "cosa-anular", "no se ofrece la salida que sí vale: anularlo");
});

test("anular un apunte firmado lo manda por la ruta de anular", async () => {
  const { entorno, servidor } = await apuntesDelCuaderno({
    "/api/tratamientos": [unTratamiento(DENTRO_DE_LA_TIERRA)],
    "/api/firmas": [
      { id: 1, entidad: "tratamiento", entidad_id: 7, campana_id: 1, huella: "0".repeat(64) },
    ],
    "POST /api/tratamientos/7/anular": { anulado: true, motivo: "Me he equivocado" },
  });
  await pulsar(entorno, "cosa-borrar", { tipo: "tratamiento", id: "7" });
  await pulsar(entorno, "cosa-anular", { tipo: "tratamiento", id: "7" });

  const anulado = servidor.enviados.find((uno) => uno.ruta === "/api/tratamientos/7/anular");
  assert.ok(anulado, "no se ha anulado el apunte");
  assert.equal(anulado.metodo, "POST");
  // El motivo va escrito: una anulación sin motivo no sirve para nada en una inspección.
  assert.ok(anulado.cuerpo.motivo.length >= 3, "la anulación no lleva motivo");
});

test("corregir una labor abre los pasos de esa práctica, no los genéricos", async () => {
  // Un trabajo tiene sus propios pasos (sembrar pregunta la semilla y la dosis; regar, el agua). Si la
  // corrección abriera el asistente genérico, esos datos no se podrían cambiar. Lo que se comprueba es
  // **lo que se manda al corregir**: la práctica de verdad y lo que el asistente no pregunta (las
  // observaciones, que viven dentro de `detalles.nota` y se perderían si no se devolvieran).
  const { entorno, servidor } = await apuntesDelCuaderno({
    "/api/labores": [unaLabor({ tipo: "siembra" })],
    "PUT /api/labores/31": unaLabor({ tipo: "siembra" }),
  });
  await pulsar(entorno, "cosa-corregir", { tipo: "siembra", id: "31" });
  const montado = montajes[montajes.length - 1].elemento;
  assert.equal(montado.type.name, "PantallaAsistente");
  assert.equal(montado.props.titulo, "Corregir lo que apuntaste");
  await irHastaElResumen(entorno);
  await pulsar(entorno, "asistente-seguir");

  const correccion = servidor.enviados.find((uno) => uno.metodo === "PUT");
  assert.ok(correccion, "la corrección de la labor no se ha mandado");
  assert.equal(correccion.ruta, "/api/labores/31", "no se corrige esa labor");
  assert.equal(correccion.cuerpo.tipo, "siembra", "la labor se guardaría como otro trabajo");
  assert.equal(correccion.cuerpo.parcela_id, 1, "la tierra de la labor se ha perdido");
  assert.equal(correccion.cuerpo.superficie_ha, 2.43, "la superficie de la labor se ha perdido");
  assert.deepEqual(
    correccion.cuerpo.detalles,
    { nota: "Con el apero de siempre" },
    "las observaciones de la labor se han perdido al corregirla",
  );
});

test("un tratamiento de una nave no manda cero hectáreas", async () => {
  // **Este fallo lo encontró la prueba de humo** (ronda 91), al añadirle la comprobación de corregir un
  // apunte: se manda de vuelta lo que devuelve la API, y un tratamiento de una nave tiene **cero**
  // hectáreas guardadas. La API pide que la superficie sea mayor que cero **cuando se manda**, porque
  // «0 ha» no es un dato sino un hueco, así que mandar el cero **no dejaba guardar** un tratamiento de
  // una nave ni corregirlo: el agricultor veía un error de superficie en una pantalla donde las
  // hectáreas ni se preguntan. En una nave no hay hectáreas: se manda a nulo.
  const { entorno, servidor } = await apuntesDelCuaderno({
    "/api/tratamientos": [
      unTratamiento({
        tipo: "instalaciones",
        parcela_id: null,
        instalacion_id: 1,
        producto_cosechado: "Trigo",
        lote_cosecha: "L-2026-07",
        superficie_tratada_ha: 0,
      }),
    ],
    "PUT /api/tratamientos/7": unTratamiento({ tipo: "instalaciones" }),
  });
  await pulsar(entorno, "cosa-corregir", { tipo: "tratamiento", id: "7" });
  await irHastaElResumen(entorno);
  await pulsar(entorno, "asistente-seguir");

  const correccion = servidor.enviados.find((uno) => uno.metodo === "PUT");
  assert.ok(correccion, "la corrección del tratamiento de la nave no se ha mandado");
  assert.equal(correccion.cuerpo.tipo, "instalaciones", "la nave se ha perdido al corregir");
  assert.equal(correccion.cuerpo.instalacion_id, 1, "la nave se ha perdido al corregir");
  assert.equal(correccion.cuerpo.parcela_id, null, "un tratamiento de una nave no es de una tierra");
  assert.equal(
    correccion.cuerpo.superficie_tratada_ha,
    null,
    "manda cero hectáreas en una nave: el servidor lo rechaza y el apunte no se puede guardar",
  );
});

test("mientras se corrige, el asistente lo dice en cada paso y volver avisa de que no guarda", async () => {
  // **Diseño de Stitch de la ronda 92.** El título de la pantalla ya dice «Corregir lo que apuntaste»,
  // pero se lee una vez: en el paso 6 de 9 el agricultor solo tiene delante la barra de progreso, y sin
  // esta etiqueta no sabe si está arreglando lo que había o apuntando algo nuevo. Y el botón de volver
  // dice **sin guardar**, que es lo único que no se puede deducir.
  const { entorno } = await apuntesDelCuaderno({ "/api/tratamientos": [unTratamiento(DENTRO_DE_LA_TIERRA)] });
  await pulsar(entorno, "cosa-corregir", { tipo: "tratamiento", id: "7" });
  const montado = montajes[montajes.length - 1].elemento;
  assert.equal(montado.props.modo, "CORRIGIENDO LO APUNTADO", "no se dice que se está corrigiendo");
  assert.equal(
    montado.props.botones.map((boton) => boton.etiqueta).includes("VOLVER SIN GUARDAR"),
    false,
    "en el primer paso no hay VOLVER, así que no puede decir nada",
  );

  // En el segundo paso ya hay botón de volver, y es donde tiene que avisar.
  await pulsar(entorno, "asistente-seguir");
  const segundo = montajes[montajes.length - 1].elemento;
  const volver = segundo.props.botones.find((boton) => boton.accion === "asistente-atras");
  assert.ok(volver, "en el segundo paso no hay forma de volver");
  assert.equal(volver.etiqueta, "VOLVER SIN GUARDAR", "el botón de volver no avisa de que no guarda");

  // Y en un apunte nuevo no se dice nada: no hay nada que corregir.
  await pulsar(entorno, "inicio", { ir: "echar_producto" });
  const nuevo = montajes[montajes.length - 1].elemento;
  assert.equal(nuevo.props.modo, "", "un apunte nuevo dice que se está corrigiendo");
});

test("la pregunta de borrar dice con un rótulo qué es lo que está enseñando", async () => {
  const { entorno } = await apuntesDelCuaderno({ "/api/tratamientos": [unTratamiento(DENTRO_DE_LA_TIERRA)] });
  await pulsar(entorno, "cosa-borrar", { tipo: "tratamiento", id: "7" });
  const montado = montajes[montajes.length - 1].elemento;
  assert.equal(
    montado.props.contenido.props.titulo,
    "Lo que va a desaparecer de tu cuaderno",
    "la caja de datos no dice qué está enseñando",
  );
});

test("un papel se corrige en su propia pantalla, con los campos puestos", async () => {
  // **Ronda 93.** Los papeles no se corrigen con el asistente: cada uno tiene su pantalla (la de guardar un
  // papel, con sus seis campos). Lo que se comprueba aquí es que esa pantalla se abre **con lo que había**
  // y que guardar manda un `PUT` a ese papel y no crea otro.
  const { entorno, servidor } = await cargarAplicacion({
    "/api/documentos": {
      documentos: [
        {
          id: 4,
          titulo: "Contrato del alquiler",
          tipo: "contrato",
          etiqueta_tipo: "Contrato",
          carpeta: "La finca",
          fecha: "2026-01-15",
          quien: "Juan Pérez",
          notas: "Hasta 2030",
          tiene_fichero: true,
        },
      ],
      carpetas: [{ nombre: "La finca", cuantos: 1 }],
      sugeridas: ["La finca"],
      tipos: [{ valor: "contrato", etiqueta: "Contrato" }],
    },
    "PUT /api/documentos/4": { id: 4, titulo: "Contrato del alquiler" },
  });
  await pulsar(entorno, "papel-ver-todos");
  const pantalla = montajes[montajes.length - 1].elemento;
  const papel = pantalla.props.carpetas[0].papeles[0];
  assert.equal(papel.acciones[0].accion, "cosa-corregir");
  assert.equal(papel.acciones[0].datos.tipo, "documento");

  await pulsar(entorno, "cosa-corregir", { tipo: "documento", id: "4" });
  const formulario = montajes[montajes.length - 1].elemento;
  assert.equal(formulario.type.name, "PantallaNuevoDocumento", "corregir un papel no abre su pantalla");
  assert.equal(formulario.props.corrigiendo, true, "la pantalla no dice que está corrigiendo");
  assert.equal(formulario.props.papel.titulo, "Contrato del alquiler", "no llega el papel que se corrige");

  // Y lo que se escriba se manda al papel que ya existe.
  escribir(entorno, "papel-titulo", "Contrato del alquiler (corregido)");
  await pulsar(entorno, "papel-guardar");
  const correccion = servidor.enviados.find((uno) => uno.metodo === "PUT");
  assert.ok(correccion, "la corrección del papel no se ha mandado como PUT");
  assert.equal(correccion.ruta, "/api/documentos/4");
  assert.equal(correccion.cuerpo.titulo, "Contrato del alquiler (corregido)");
  assert.ok(
    !servidor.enviados.some((uno) => uno.metodo === "POST" && uno.ruta === "/api/documentos"),
    "además de corregir, se ha guardado un papel nuevo",
  );
});

test("una factura ofrece corregirse y borrarse, y borrar pregunta antes", async () => {
  const { entorno, servidor } = await cargarAplicacion({
    "/api/facturas": [
      {
        id: 9,
        proveedor: "Cooperativa Agrícola",
        proveedor_nif: "F37012345",
        numero_factura: "2026/00123",
        fecha: "2026-03-02",
        total: 750.2,
        tiene_fichero: true,
        cuadra: true,
        // La lista de líneas la manda **siempre** el servidor (`FacturaSalida.lineas`, vacía si la factura
        // se escribió a mano). Faltaba en esta prueba y el listado se caía al contar cuántas trae.
        lineas: [],
      },
    ],
    "DELETE /api/facturas/9": { borrado: true, id: 9 },
  });
  await pulsar(entorno, "facturas-abrir");
  const pantalla = montajes[montajes.length - 1].elemento;
  const factura = pantalla.props.facturas[0];
  // **Tres salidas desde el S11 (09/10/2026)**: ver la compra entera (facturado, recibido, pagado y
  // pendiente), corregirla y borrarla. El botón nuevo va **el primero** a propósito: es lo que se quiere
  // hacer con una factura antes de tocar nada —mirarla entera—, y hasta hoy esa ficha existía en el
  // servidor y **no había ningún botón que llevara a ella**, que es el mismo defecto que ya apareció con
  // la historia de una tierra.
  assert.deepEqual(
    factura.acciones.map((accion) => accion.accion),
    ["compra-abrir", "cosa-corregir", "cosa-borrar"],
    "la ficha de una factura no ofrece sus tres salidas (verla entera, corregirla y borrarla)",
  );

  await pulsar(entorno, "cosa-borrar", { tipo: "factura", id: "9" });
  const pregunta = montajes[montajes.length - 1].elemento;
  assert.equal(pregunta.props.pregunta, "¿Seguro que quieres borrarlo?");
  // Y volver lleva a **la lista de facturas**, que se abre por su acción (`facturas-abrir`), no por un
  // nombre de pantalla: es el fallo que se arregló en la ronda 92 con `mis_cosas`. Y **no hay botón de
  // «volver al cuaderno»** porque este ya vuelve a donde se salió: la lista de facturas.
  assert.deepEqual(
    pregunta.props.acciones.map((accion) => accion.accion),
    ["cosa-borrar-si", "cosa-corregir", "facturas-abrir"],
    "la pregunta de borrar una factura no ofrece sus dos salidas verdaderas",
  );
  // Y el borrado se manda **solo al confirmar**: la pantalla que pregunta no borra nada por abrirse.
  await pulsar(entorno, "cosa-borrar-si", { tipo: "factura", id: "9" });
  assert.match(
    JSON.stringify(servidor.enviados.filter((uno) => uno.metodo === "DELETE")),
    /apifacturas9|\/api\/facturas\/9/,
    "no se ha mandado el borrado de la factura",
  );
});

test("corregir una factura abre la pantalla de lo guardado y guarda con PUT, no con otra factura", async () => {
  // **Ronda 93.** Es la mitad que faltaba del «o modificar también» que pidió David. Lo que se comprueba
  // aquí es el cableado, que es donde se rompe en silencio: que CORREGIR abra la pantalla que revisa las
  // líneas **con lo que ya estaba guardado** (y no con lo último leído, ni en blanco), que el botón final
  // diga que se guardan cambios, y que al guardar se mande un `PUT` a **esa** factura y no un alta.
  const laFactura = {
    id: 9,
    proveedor: "Cooperativa Agrícola",
    proveedor_nif: "F37012345",
    numero_factura: "2026/00123",
    fecha: "2026-03-02",
    base_imponible: 620.0,
    cuota_iva: 130.2,
    tipo_iva_pct: 21.0,
    total: 750.2,
    // **Dos datos que ninguna pantalla pregunta** y que tienen que viajar igual, o corregir un número
    // los borraría sin decir nada: las notas de la factura y, en su línea, el lote y el número de registro.
    notas: "Pagada a 30 días",
    leida_por: "pdf",
    tiene_fichero: true,
    lineas: [
      {
        id: 31,
        descripcion: "GLIFOSATO 36% SL 20 L",
        cantidad: 40,
        unidad: "L",
        precio_unitario: 4.25,
        importe: 170.0,
        numero_registro: "24.123",
        lote: "L-2026-07",
        producto_id: 5,
        fertilizante_id: null,
        cuadra: true,
      },
    ],
  };
  const { entorno, servidor } = await cargarAplicacion({
    // Se pide dos veces: una para la lista y otra al recargar los datos después de corregir.
    "/api/facturas": [laFactura],
    "PUT /api/facturas/9": { ...laFactura, total: 900 },
  });
  await pulsar(entorno, "facturas-abrir");
  await pulsar(entorno, "cosa-corregir", { tipo: "factura", id: "9" });

  // La pantalla que se abre es la de la interpretación, y **con los datos guardados dentro**.
  const pantalla = montajes[montajes.length - 1].elemento;
  assert.equal(
    pantalla.type.name,
    "PantallaInterpretacionDeLaFactura",
    "corregir una factura no abre su propia pantalla",
  );
  assert.equal(pantalla.props.corrigiendo, true, "la pantalla no dice que está corrigiendo");
  const cabecera = Object.fromEntries(pantalla.props.leida.cabecera.map((campo) => [campo.id, campo.valor]));
  assert.equal(cabecera["factura-proveedor"], "Cooperativa Agrícola", "no llega lo guardado");
  assert.equal(cabecera["factura-numero"], "2026/00123");
  assert.equal(cabecera["factura-total"], "750.2");
  assert.equal(pantalla.props.leida.lineas.length, 1, "no llegan las líneas guardadas");
  assert.equal(pantalla.props.leida.lineas[0].descripcion, "GLIFOSATO 36% SL 20 L");
  assert.match(pantalla.props.leida.de_donde, /pdf|fichero/i, "no dice de dónde salió la factura");

  // Y se cambia el total, como haría el agricultor que ve que no es el que puso. Los campos de la
  // pantalla se escriben uno a uno porque el DOM de mentira no los tiene: `app.js` los lee **por su
  // `id`**, que es justo lo que hay que demostrar (un `id` perdido se guardaría vacío sin avisar).
  escribir(entorno, "factura-proveedor", "Cooperativa Agrícola");
  escribir(entorno, "factura-proveedor-nif", "F37012345");
  escribir(entorno, "factura-numero", "2026/00123");
  escribir(entorno, "factura-fecha", "2026-03-02");
  escribir(entorno, "factura-base", "620");
  escribir(entorno, "factura-iva", "130,2");
  escribir(entorno, "factura-tipo-iva", "21");
  escribir(entorno, "factura-total", "900");
  escribir(entorno, "factura-0-descripcion", "GLIFOSATO 36% SL 20 L");
  escribir(entorno, "factura-0-cantidad", "40");
  escribir(entorno, "factura-0-unidad", "L");
  escribir(entorno, "factura-0-precio", "4,25");
  escribir(entorno, "factura-0-importe", "170");
  escribir(entorno, "factura-0-producto", "5");
  await pulsar(entorno, "factura-guardar");
  const correccion = servidor.enviados.find((uno) => uno.metodo === "PUT");
  assert.ok(correccion, "la corrección de la factura no se ha mandado como PUT");
  assert.equal(correccion.ruta, "/api/facturas/9");
  assert.equal(correccion.cuerpo.total, 900);
  // Y **lo que la pantalla no pregunta viaja igual**: sin esto, corregir el total borraría las notas y
  // los datos del papel que van en la línea (es el fallo que ya apareció con la forma de una tierra).
  assert.equal(correccion.cuerpo.notas, "Pagada a 30 días", "la corrección se lleva por delante las notas");
  assert.equal(correccion.cuerpo.lineas[0].numero_registro, "24.123", "se pierde el nº de registro");
  assert.equal(correccion.cuerpo.lineas[0].lote, "L-2026-07", "se pierde el lote");
  assert.equal(correccion.cuerpo.lineas[0].producto_id, 5, "la línea se desengancha de su producto");
  assert.ok(
    !servidor.enviados.some((uno) => uno.metodo === "POST" && uno.ruta === "/api/facturas"),
    "además de corregir, se ha dado de alta una factura nueva (contaría dos veces)",
  );
  // Y no se enseña «Factura guardada»: al corregir no se ha añadido nada, y decir «guardada» haría
  // pensar que hay dos facturas. Se dice «Corregido», que es lo mismo que se dice al corregir un apunte,
  // una tierra o un producto.
  const despues = montajes[montajes.length - 1].elemento;
  assert.equal(despues.props.titulo, "Corregido", "no dice que se ha corregido");
  assert.ok(
    despues.props.acciones.some((accion) => accion.accion === "facturas-abrir"),
    "la confirmación no lleva de vuelta a la lista de facturas",
  );
});

// ---------------------------------------------------------------------------
// LOS AÑOS DEL CUADERNO: verlos, corregirlos, borrarlos y empezar uno nuevo (ronda 93)
//
// Es lo último que faltaba por poder tocar desde la pantalla, y lo que más pesa: **de la campaña cuelga el
// año entero** (cada apunte guarda su `campana_id`), así que un año mal escrito dejaba todos los apuntes
// de ese año colgando de un año que no es el suyo. Y empezar el año siguiente **no se podía hacer de
// ninguna forma**: la campaña la creaba el programa al darse de alta la cuenta.
//
// Lo que se comprueba aquí es el cableado, que es donde se rompe en silencio: que la lista llegue
// preparada (cuál se está llevando, cuánto tiene dentro cada uno y si se puede quitar), que el BORRAR de
// un año con cosas dentro vaya **apagado** con su explicación al lado, y que corregir y empezar un año
// manden lo que tienen que mandar.
// ---------------------------------------------------------------------------

test("los años del cuaderno llegan contados, y el que tiene cosas dentro no se puede quitar", async () => {
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "campanas-abrir");
  const pantalla = montajes[montajes.length - 1].elemento;
  assert.equal(pantalla.type.name, "PantallaCampanas");
  const suyos = pantalla.props.campanas;
  assert.equal(suyos.length, 3, "no llegan los años que hay");
  // **Cuál se está llevando** (el más nuevo, `estado.campana`) y cuánto tiene dentro cada uno. El número es
  // lo que explica por qué un año no se puede quitar, así que no puede venir en blanco. Y va **dicho por lo
  // que es** (30/09/2026): los apuntes del cuaderno y lo que hay dentro que no son apuntes, porque antes el
  // año decía «42 cosas apuntadas dentro» y el cuaderno del mismo año decía «0 apuntes».
  assert.equal(suyos[0].es_la_que_llevo, true, "no dice cuál es el año que está llevando");
  assert.equal(
    suyos[0].dentro,
    "5 apuntes · 35 tierras con su cultivo dicho · 2 cosas más dentro",
    "no dice qué tiene dentro el año que lleva, dicho por lo que es",
  );
  // Y el total sigue ahí, que es lo que decide si el año se puede quitar.
  assert.equal(suyos[0].cuantas_cosas, 42, "no llega el total de cosas que hay dentro del año");
  assert.equal(suyos[0].se_puede_quitar, false, "deja quitar un año que tiene 42 cosas dentro");
  assert.equal(suyos[2].dentro, "No tiene nada apuntado");
  assert.equal(suyos[2].se_puede_quitar, true, "no deja quitar un año vacío");
  // Y el BORRAR del año con cosas dentro va **apagado**, con el aviso al lado explicándolo (diseño de
  // Stitch): un botón que va a fallar y no dice nada hasta que se pulsa parece un programa roto.
  const borrar = suyos[0].acciones.find((una) => una.accion === "cosa-borrar");
  assert.equal(borrar.deshabilitado, true, "el BORRAR de un año con cosas dentro se puede pulsar");
  const borrarVacio = suyos[2].acciones.find((una) => una.accion === "cosa-borrar");
  assert.ok(!borrarVacio.deshabilitado, "el BORRAR de un año vacío sale apagado");
  // Y el año cerrado se dice.
  assert.equal(suyos[1].cerrada, true);
});

/**
 * Un bloque del maestro que se le ha pedido a React, por el nombre de su campo.
 *
 * Los campos de escribir llevan `id` y los de elegir llevan `campo` (ver `bloquesDelMaestro` en
 * `app.js`): esta prueba busca por los dos, que es lo que hace falta para leer **lo que se le pide**.
 */
function bloquePedido(campo) {
  return bloquesDelMaestroPedidos().find((uno) => (uno.id || uno.campo) === campo);
}

test("corregir un año del cuaderno abre su formulario con lo que ya estaba", async () => {
  const { entorno, servidor } = await cargarAplicacion({
    "PUT /api/campanas/1": { id: 1, anio: 2026, cerrada: true },
  });
  await pulsar(entorno, "campanas-abrir");
  await pulsar(entorno, "cosa-corregir", { tipo: "campana", id: "1" });
  // El formulario lleva **lo que ya estaba**: el año que tenía. Se comprueba lo que se le pide a React
  // —el `id` del campo y su valor—, que es lo que hace que corregir sea corregir y no volver a escribir
  // todo. Un `id` perdido se guardaría vacío sin que saltara ningún error.
  assert.equal(String(bloquePedido("anio").valor), "2026", "no llega el año que ya estaba");
  // Se escribe y se sigue: el paso guarda lo que se ha escrito en el borrador al salir (por eso se
  // escribe **antes** de seguir, como lo haría el agricultor).
  escribir(entorno, "anio", "2026");
  await pulsar(entorno, "asistente-seguir"); // el año
  const fechas = bloquesDelMaestroPedidos();
  assert.deepEqual(
    idsDeLosBloques(fechas),
    ["fecha_inicio", "fecha_fin"],
    "las dos fechas del año no se preguntan juntas",
  );
  assert.equal(bloquePedido("fecha_inicio").valor, "2025-09-01", "no llegan las fechas que ya estaban");
  assert.equal(bloquePedido("fecha_fin").valor, "2026-08-31");
  escribir(entorno, "fecha_inicio", "2025-09-01");
  escribir(entorno, "fecha_fin", "2026-08-31");
  await pulsar(entorno, "asistente-seguir"); // las dos fechas
  // Y el «sí o no» llega como lo pinta la pantalla ("bool:false"), no como verdadero/falso: si no, la
  // opción que ya estaba elegida **no saldría marcada** y el agricultor tendría que volver a elegirla, con
  // el riesgo de elegir lo contrario de lo que había.
  const cerrada = bloquePedido("cerrada");
  assert.deepEqual(
    cerrada.opciones.map((una) => [una.valor, una.elegido]),
    [["bool:true", false], ["bool:false", true]],
    "el «sí o no» de si el año está terminado no sale con lo que había",
  );

  // Y el resumen guarda: un `PUT` a **ese** año, no un alta. El último paso del asistente (el «sí o no»)
  // guarda al pulsar SEGUIR, así que aquí no hay un paso de resumen aparte.
  await pulsar(entorno, "asistente-seguir"); // si está cerrado: y guarda
  const correccion = servidor.enviados.find((uno) => uno.metodo === "PUT");
  assert.ok(correccion, `no ha corregido el año: ${servidor.llamadasConMetodo.join(", ")}`);
  assert.equal(correccion.ruta, "/api/campanas/1");
  // `cerrada` **siempre** viaja (la API lo exige): si se pudiera omitir, corregir solo el año de una
  // campaña cerrada la volvería a abrir sin que nadie lo pidiera.
  assert.equal(correccion.cuerpo.cerrada, false, "no manda si el año está cerrado");
  assert.equal(correccion.cuerpo.anio, 2026);
});

test("empezar un año nuevo propone el año siguiente, con sus fechas, y lo manda al servidor", async () => {
  // Lo que faltaba entero: cuando llegaba el año nuevo, el cuaderno se quedaba en el año viejo.
  const { entorno, servidor } = await cargarAplicacion({
    "POST /api/campanas": { id: 4, anio: 2027, cerrada: false },
  });
  await pulsar(entorno, "campanas-abrir");
  await pulsar(entorno, "campana-nueva");
  // El año que se propone es **el siguiente al último que tiene** (2026 → 2027) y las fechas salen del año
  // natural. No es inventar un dato: es lo que iba a escribir, y lo cambia si su cosecha empieza en
  // septiembre (la pista de la pantalla lo dice).
  assert.equal(String(bloquePedido("anio").valor), "2027", "no propone el año siguiente");
  escribir(entorno, "anio", "2027");
  await pulsar(entorno, "asistente-seguir"); // el año
  assert.equal(bloquePedido("fecha_inicio").valor, "2027-01-01");
  assert.equal(bloquePedido("fecha_fin").valor, "2027-12-31");
  escribir(entorno, "fecha_inicio", "2027-01-01");
  escribir(entorno, "fecha_fin", "2027-12-31");
  // Y se guarda de verdad: un alta, con las tres cosas.
  await pulsar(entorno, "asistente-seguir"); // las dos fechas
  await pulsar(entorno, "asistente-seguir"); // si está cerrado: y guarda
  const alta = servidor.enviados.find(
    (uno) => uno.metodo === "POST" && uno.ruta === "/api/campanas",
  );
  assert.ok(alta, `no ha empezado el año: ${servidor.llamadasConMetodo.join(", ")}`);
  assert.equal(alta.cuerpo.anio, 2027);
  assert.equal(alta.cuerpo.fecha_inicio, "2027-01-01");
  assert.equal(alta.cuerpo.cerrada, false);
  assert.ok(
    !servidor.enviados.some((uno) => uno.metodo === "PUT" && uno.ruta.startsWith("/api/campanas")),
    "ha corregido un año en vez de empezar uno nuevo",
  );
  // Y el final dice que el año está **listo**, no «Apuntado»: el año no es una ficha más.
  await new Promise((resolver) => setTimeout(resolver, 200));
  const despues = montajes[montajes.length - 1].elemento;
  assert.match(despues.props.titulo, /Año guardado/, "el final no dice que el año está listo");
  assert.ok(
    despues.props.acciones.some(
      (una) => una.accion === "inicio" && una.datos && una.datos.ir === "campanas",
    ),
    "el final no lleva a ver los años",
  );
});

test("borrar un año pregunta antes, y su ficha dice cuántas cosas tiene dentro", async () => {
  const { entorno, servidor } = await cargarAplicacion({
    "DELETE /api/campanas/3": { borrado: true, id: 3 },
  });
  await pulsar(entorno, "campanas-abrir");
  await pulsar(entorno, "cosa-borrar", { tipo: "campana", id: "3" });
  const pregunta = montajes[montajes.length - 1].elemento;
  assert.equal(pregunta.props.pregunta, "¿Seguro que quieres borrarlo?");
  const contenido = JSON.stringify(pregunta.props.contenido);
  assert.match(contenido, /2024/, "la pregunta no dice qué año se va a borrar");
  assert.match(contenido, /No tiene nada apuntado/, "la pregunta no dice qué hay dentro");
  assert.equal(
    servidor.enviados.filter((uno) => uno.metodo === "DELETE").length,
    0,
    "se ha borrado el año solo con abrir la pantalla que pregunta",
  );
  await pulsar(entorno, "cosa-borrar-si", { tipo: "campana", id: "3" });
  assert.ok(
    servidor.enviados.some((uno) => uno.metodo === "DELETE" && uno.ruta === "/api/campanas/3"),
    `no ha borrado el año: ${servidor.llamadasConMetodo.join(", ")}`,
  );
});

// ---------------------------------------------------------------------------
// LA TABLA DE TIERRAS, PARA EL ORDENADOR (30/09/2026)
//
// David: *«no es una app usable de gestión»*. Con 64 tierras, en el móvil se miran de una en una y en el
// ordenador lo que se quiere es **verlas todas de arriba abajo, comparar las hectáreas y ordenarlas**.
//
// Lo que se comprueba aquí es el cableado: que la sección de las tierras lleve su tabla con las columnas
// (del servidor), las celdas de cada tierra y **el total del pie**; y que pulsar una cabecera **ordene de
// verdad** y que pulsarla otra vez le dé la vuelta. Lo que se ve dentro está en `tests_js/react.test.js`,
// contra la pieza; y que en un ordenador se dibuje, en la comprobación de navegador.
// ---------------------------------------------------------------------------

/** La tabla de la sección de las tierras que se le ha pedido a React. */
function tablaDeTierrasPedida() {
  const pantalla = montajes[montajes.length - 1].elemento;
  const seccion = pantalla.props.secciones[0];
  assert.ok(seccion.tabla, "la sección de las tierras no lleva tabla");
  return seccion.tabla;
}

/** Los nombres de una columna de la tabla, en el orden en que salen. */
function columnaDeLaTabla(tabla, indice) {
  return tabla.filas.map((fila) => fila.celdas[indice].texto || fila.celdas[indice].estado?.texto || "");
}

test("la tabla de tierras llega con sus columnas, sus celdas y el total", async () => {
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "mis-cosas");
  const tabla = tablaDeTierrasPedida();
  // **Cinco columnas**: el pueblo y la referencia del SIGPAC están en el panel de al lado (y en la tarjeta
  // del móvil), y repetirlos aquí ensancha la tabla hasta cortar los botones de la última columna.
  assert.deepEqual(
    tabla.columnas.map((columna) => columna.texto),
    ["Nº", "Nombre", "Hectáreas", "Qué tiene este año", "Acciones"],
  );
  assert.deepEqual(
    tabla.columnas.map((columna) => columna.campo || null),
    ["numero", "alias", "superficie_ha", "cultivo", null],
  );
  // Las tierras de la finca, una por fila, con sus datos en su celda.
  assert.equal(tabla.filas.length, 2, "no salen las tierras que hay");
  assert.deepEqual(columnaDeLaTabla(tabla, 0), ["1", "2"]);
  assert.deepEqual(columnaDeLaTabla(tabla, 1), ["El Prado", "La Vega"]);
  assert.deepEqual(columnaDeLaTabla(tabla, 2), ["2,43", "5,00"]);
  // **La tierra a la que le falta decir qué tiene lo dice con la etiqueta corta** (30/09/2026): la frase
  // entera («Todavía no has dicho qué hay aquí este año.») ocupaba tres renglones en la celda y dejaba la
  // columna alta y estrecha, y sigue estando donde se lee: en la tarjeta del móvil y en el panel de al lado.
  assert.deepEqual(columnaDeLaTabla(tabla, 3), ["Falta decirlo", "Maíz"]);
  assert.equal(tabla.filas[0].celdas[3].estado.tipo, "mirar");
  // **El total del pie**, que es la cuenta que se viene a hacer aquí: las hectáreas de todas.
  assert.equal(tabla.resumen, "2 tierras · 7,43 ha");
  // **En la tabla, un solo botón por fila** (el de la fila, con su etiqueta corta): corregir y borrar están
  // en el panel de al lado, y con los tres en cada fila un cuaderno de 64 tierras se hacía interminable.
  const acciones = tabla.filas[0].acciones.map((una) => una.accion);
  assert.deepEqual(acciones, ["cultivo-decir"]);
  assert.equal(tabla.filas[0].acciones[0].etiqueta, "DECIRLO", "la etiqueta larga ensancha la tabla");
  assert.equal(tabla.filas[0].acciones[0].datos.id, 1, "el botón de la fila no dice de qué tierra es");
});

test("pulsar una cabecera ordena la tabla, y volver a pulsarla le da la vuelta", async () => {
  // Es lo que se hace con 64 tierras: «¿cuál es la más grande?».
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "mis-cosas");
  // De entrada, por número: el orden en el que el agricultor las dio de alta.
  assert.deepEqual(columnaDeLaTabla(tablaDeTierrasPedida(), 1), ["El Prado", "La Vega"]);
  const primera = tablaDeTierrasPedida().columnas.find((columna) => columna.ordenada);
  assert.equal(primera.campo, "numero");
  assert.equal(primera.descendente, false);

  // Por hectáreas: la más pequeña primero (El Prado, 2,43) y marcada esa columna.
  await pulsar(entorno, "ordenar-tabla", { campo: "superficie_ha" });
  const porHectareas = tablaDeTierrasPedida();
  assert.deepEqual(columnaDeLaTabla(porHectareas, 1), ["El Prado", "La Vega"]);
  assert.equal(porHectareas.columnas.find((columna) => columna.ordenada).campo, "superficie_ha");
  // Y otra vez: la más grande primero. Aquí es donde se ve que ordena de verdad.
  await pulsar(entorno, "ordenar-tabla", { campo: "superficie_ha" });
  const alReves = tablaDeTierrasPedida();
  assert.deepEqual(columnaDeLaTabla(alReves, 1), ["La Vega", "El Prado"]);
  assert.equal(alReves.columnas.find((columna) => columna.ordenada).descendente, true);
  // Cambiar de columna empieza de nuevo en ascendente: dar la vuelta a una columna distinta sería
  // desconcertante.
  await pulsar(entorno, "ordenar-tabla", { campo: "alias" });
  const porNombre = tablaDeTierrasPedida();
  assert.equal(porNombre.columnas.find((columna) => columna.ordenada).campo, "alias");
  assert.equal(porNombre.columnas.find((columna) => columna.ordenada).descendente, false);
  // **Y el número de cada tierra no cambia al ordenar**: «Tierra n.º 2» sigue siendo la 2 aunque salga
  // primero. Es como la llama el agricultor, y renumerarla sería mentirle.
  assert.deepEqual(columnaDeLaTabla(porNombre, 0), ["1", "2"]);
});

test("con el buscador, el pie dice cuántas se están viendo de cuántas", async () => {
  // Un filtro sin decir qué está filtrando deja al agricultor creyendo que ha perdido tierras.
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "mis-cosas");
  escribir(entorno, "buscar_tierra_mis_cosas", "vega");
  await pulsar(entorno, "buscar-tierra-mis-cosas");
  const tabla = tablaDeTierrasPedida();
  assert.equal(tabla.filas.length, 1, "el buscador no ha filtrado la tabla");
  assert.match(tabla.resumen, /^1 de 2 tierras/, `el pie dice: «${tabla.resumen}»`);
});

// ---------------------------------------------------------------------------
// LA TABLA DEL CUADERNO (los apuntes del año), 30/09/2026
//
// «Mi cuaderno» es lo que más se mira del programa. En el móvil se mira apunte a apunte; en el ordenador,
// lo que quiere un agricultor es **la lista del año entera**: qué hizo, dónde, cuántas hectáreas y cuándo,
// con lo último arriba, y pudiendo ordenar por hectáreas o por tierra. Al pie, el total de hectáreas del
// año, que es el primer número que se pregunta.
// ---------------------------------------------------------------------------

/** La tabla de los apuntes que se le ha pedido a React (en la última pantalla del cuaderno). */
function tablaDeApuntesPedida() {
  return ultimoCuadernoPedido().apuntes.tabla;
}

/** Dos apuntes de verdad, con fechas y hectáreas distintas: hacen falta para el orden y el total del pie. */
const DOS_APUNTES = {
  "/api/tratamientos": [
    unTratamiento({ id: 7, fecha: "2026-04-10", superficie_tratada_ha: 4.9 }),
    unTratamiento({
      id: 8,
      fecha: "2026-05-02",
      superficie_tratada_ha: 1.2,
      producto_nombre: "Cobre 50 WP",
    }),
  ],
};

test("la tabla del cuaderno llega con lo que se apuntó, dónde y cuántas hectáreas", async () => {
  const { apuntes } = await apuntesDelCuaderno(DOS_APUNTES);
  const tabla = apuntes.tabla;
  assert.ok(tabla, "el bloque de los apuntes no lleva tabla");
  assert.deepEqual(
    tabla.columnas.map((columna) => columna.texto),
    ["Fecha", "Clase", "Qué", "Tierra", "Hectáreas", "Cultivo", "Acciones"],
  );
  assert.deepEqual(
    tabla.columnas.map((columna) => columna.campo || null),
    ["fecha", "queEs", "etiqueta", "donde", "hectareas", "cultivo", null],
  );
  assert.equal(tabla.filas.length, 2, "no salen los apuntes que hay");
  const primera = tabla.filas[0].celdas.map((celda) => celda.texto || celda.estado?.texto || "");
  // **Lo último apuntado va arriba**: la primera fila es la del 2 de mayo, no la del 10 de abril.
  assert.equal(primera[0], "02/05/2026", `la primera fila es del: ${primera[0]}`);
  assert.equal(primera[1], "Producto", "no dice de qué clase es el apunte");
  assert.equal(primera[2], "Cobre 50 WP", "no dice qué se echó");
  assert.equal(primera[3], "El Prado", "no dice en qué tierra se hizo");
  assert.equal(primera[4], "1,20", `las hectáreas no van con dos decimales: ${primera[4]}`);
  // Y el pie con el total de hectáreas del año, que es lo que se viene a mirar.
  assert.equal(tabla.resumen, "2 apuntes · 6,10 ha tratadas");
  // Cada fila lleva sus botones de siempre, los mismos que la tarjeta del móvil, y desde el T09 el del
  // almacén va el primero (es el apunte el que dice lo que se gastó).
  assert.deepEqual(
    tabla.filas[0].acciones.map((una) => una.accion),
    ["salida-de-un-lote", "cosa-corregir", "cosa-borrar"],
  );
  assert.equal(tabla.filas[0].acciones[1].datos.id, 8, "el botón de la fila no dice qué apunte es");
});

test("el cuaderno empieza por lo último apuntado, y se puede ordenar por hectáreas", async () => {
  // De lo más nuevo a lo más viejo, que es como lo cuenta el agricultor («lo de la semana pasada»).
  const { entorno } = await apuntesDelCuaderno(DOS_APUNTES);
  const alPrincipio = tablaDeApuntesPedida();
  assert.deepEqual(
    alPrincipio.filas.map((fila) => fila.celdas[0].texto),
    ["02/05/2026", "10/04/2026"],
  );
  assert.equal(alPrincipio.columnas.find((columna) => columna.ordenada).campo, "fecha");
  assert.equal(alPrincipio.columnas.find((columna) => columna.ordenada).descendente, true);

  // Y ordenando por hectáreas (de la más pequeña a la más grande), la tabla se reordena y el cuaderno se
  // vuelve a pintar: la acción es la misma que la de las tierras, pero cada tabla tiene su propio orden.
  await pulsar(entorno, "ordenar-tabla", { tabla: "apuntes", campo: "hectareas" });
  const ordenada = tablaDeApuntesPedida();
  assert.equal(ordenada.columnas.find((columna) => columna.ordenada).campo, "hectareas");
  assert.deepEqual(
    ordenada.filas.map((fila) => fila.celdas[4].texto),
    ["1,20", "4,90"],
  );
  // Y el orden de las tierras **no se ha tocado**: cada tabla se acuerda del suyo.
  await pulsar(entorno, "mis-cosas");
  assert.equal(tablaDeTierrasPedida().columnas.find((columna) => columna.ordenada).campo, "numero");
});

test("la tabla de los años llega con lo que tiene dentro cada uno", async () => {
  // **30/09/2026.** Los años, uno debajo de otro: cuál se está llevando, cuál está cerrado, cuánto tiene
  // cada uno dentro y cuáles se pueden quitar. Es lo que se mira al empezar el año o al arreglar uno mal
  // puesto. Lo que se ve dentro está en `tests_js/react.test.js`; aquí, el cableado.
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "campanas-abrir");
  const tabla = montajes[montajes.length - 1].elemento.props.tabla;
  assert.ok(tabla, "la pantalla de los años no lleva tabla");
  assert.deepEqual(
    tabla.columnas.map((columna) => columna.texto),
    ["Año", "Empieza", "Termina", "Qué tiene dentro", "Estado", "Acciones"],
  );
  assert.deepEqual(
    tabla.columnas.map((columna) => columna.campo || null),
    ["anio_numero", "desde_iso", "hasta_iso", "apuntes", null, null],
  );
  // Los tres años del servidor, del más nuevo al más viejo (así vienen ya ordenados).
  assert.deepEqual(
    tabla.filas.map((fila) => fila.celdas[0].texto),
    ["2026", "2025", "2024"],
  );
  assert.equal(tabla.resumen, "3 años en tu cuaderno");
  // Las fechas, escritas como se leen en España.
  assert.equal(tabla.filas[0].celdas[1].texto, "01/09/2025");
  assert.equal(tabla.filas[0].celdas[2].texto, "31/08/2026");
  // **Lo que tiene dentro va dicho por lo que es** (30/09/2026): los apuntes del cuaderno —que es lo que el
  // agricultor cuenta, y lo que dice la pantalla de «mi cuaderno»— y, detrás, lo que hay dentro que no son
  // apuntes. Antes solo se decía el total («42 cosas apuntadas dentro») y el cuaderno del mismo año decía
  // «0 apuntes»: dos números que parecían contradecirse.
  assert.equal(
    tabla.filas[0].celdas[3].texto,
    "5 apuntes · 35 tierras con su cultivo dicho · 2 cosas más dentro",
  );
  // El año que solo tiene apuntes (nada más dentro) lo dice sin añadidos.
  assert.equal(tabla.filas[1].celdas[3].texto, "38 apuntes");
  // El vacío dice que no tiene nada, y no un cero.
  assert.equal(tabla.filas[2].celdas[3].texto, "No tiene nada apuntado");
  // Y el que no se puede quitar lo dice ahí mismo (es lo que explica que su BORRAR salga apagado), **con la
  // etiqueta corta**: la frase entera ponía la fila alta.
  assert.equal(tabla.filas[0].celdas[3].estado.texto, "Hay cosas dentro");
  assert.ok(tabla.filas[0].celdas[3].estado, "un año con cosas dentro no dice que no se puede quitar");
  assert.ok(!tabla.filas[2].celdas[3].estado, "un año vacío dice que no se puede quitar, y sí se puede");
  // Y el año que se está llevando va dicho en su etiqueta.
  assert.equal(tabla.filas[0].celdas[4].estado.texto, "Estás apuntando en este");
  assert.equal(tabla.filas[1].celdas[4].texto, "Año cerrado");
  // Con sus dos botones por fila.
  assert.deepEqual(
    tabla.filas[0].acciones.map((una) => una.accion),
    ["cosa-corregir", "cosa-borrar"],
  );
});

test("la tabla de las facturas llega con sus números, su papel y el total del año", async () => {
  const laFactura = {
    id: 9,
    proveedor: "Cooperativa Agrícola",
    numero_factura: "2026/00123",
    fecha: "2026-03-02",
    base_imponible: 620.0,
    cuota_iva: 130.2,
    total: 750.2,
    tiene_fichero: true,
    lineas: [],
  };
  const sinPapel = { ...laFactura, id: 10, numero_factura: "2026/00999", total: 100, tiene_fichero: false };
  const { entorno } = await cargarAplicacion({ "/api/facturas": [laFactura, sinPapel] });
  await pulsar(entorno, "facturas-abrir");
  const tabla = montajes[montajes.length - 1].elemento.props.tabla;
  assert.ok(tabla, "la lista de facturas no lleva tabla");
  assert.deepEqual(
    tabla.columnas.map((columna) => columna.texto),
    ["Fecha", "Quién te lo vendió", "Nº de factura", "Base", "IVA", "Total", "El papel", "Acciones"],
  );
  assert.equal(tabla.filas.length, 2, "no salen las facturas que hay");
  // Los números, con su euro y con dos decimales (es un importe, y se lee como se escribe).
  assert.equal(tabla.filas[0].celdas[5].texto, "750,20 €");
  assert.equal(tabla.filas[0].celdas[3].texto, "620,00 €");
  assert.equal(tabla.filas[0].celdas[4].texto, "130,20 €");
  // **Y el papel**: la que lo tiene lo dice, y la que no lo tiene lo dice **en ámbar y corto** («Falta el
  // papel»), porque es lo que hay que arreglar (es lo primero que se pide en una inspección). La frase
  // larga se queda en la ficha del móvil: en una celda de la tabla ocuparía cinco renglones.
  assert.match(tabla.filas[0].celdas[6].texto, /papel guardada/i);
  assert.ok(!tabla.filas[0].celdas[6].estado, "una factura con papel avisa de que le falta el papel");
  assert.equal(tabla.filas[1].celdas[6].estado.texto, "Falta el papel");
  assert.equal(tabla.filas[1].celdas[6].texto, "", "la frase larga del papel se cuela en la tabla");
  // Y el pie: el total del año, que es la cuenta que se viene a hacer.
  assert.equal(tabla.resumen, "2 facturas · 850,20 €");
  assert.deepEqual(tabla.indicadores.map((uno) => uno.valor),
    ["2", "1.240,00 €", "260,40 €", "850,20 €", "1"]);
});

test("una factura sin cifra deja pendiente el total del año y cada suma incompleta", async () => {
  const { entorno } = await cargarAplicacion({ "/api/facturas": [
    { id: 9, fecha: "2026-03-02", proveedor: "Cooperativa", base_imponible: 620,
      cuota_iva: 130.2, total: 750.2, tiene_fichero: true, lineas: [] },
    { id: 10, fecha: "2026-03-03", proveedor: "Taller", base_imponible: null,
      cuota_iva: null, total: null, tiene_fichero: false, lineas: [] },
  ] });
  await pulsar(entorno, "facturas-abrir");
  const tabla = montajes[montajes.length - 1].elemento.props.tabla;
  assert.equal(tabla.resumen, "2 facturas · falta el total de alguna");
  assert.deepEqual(tabla.indicadores.map((uno) => uno.valor), ["2", "—", "—", "—", "1"]);
  assert.deepEqual(tabla.filas.map((fila) => fila.celdas[5].texto).sort(),
    ["", "750,20 €"], "cada factura conserva su cifra o su vacío, con independencia del orden");
});

test("elegir una tierra la enseña en el panel de al lado, sin salir de la página", async () => {
  // **Fase 3, 30/09/2026.** Es la mitad de lo que hace que una tabla sirva: se mira la lista, se toca un
  // nombre y se ve su ficha al lado, con sus datos y sus botones. Lo que se comprueba aquí es el cableado:
  // que tocar el nombre deje esa fila elegida y que el panel llegue con **la tierra que se ha tocado** (no
  // con otra), y que volver a tocarla lo cierre.
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "mis-cosas");
  // De entrada no hay nada elegido: el panel lo dice, no se queda en blanco.
  const sinElegir = tablaDeTierrasPedida();
  assert.equal(sinElegir.panel.elegida, false, "hay una tierra elegida sin haber tocado nada");
  assert.match(sinElegir.panel.vacio, /Toca el nombre/, "el panel vacío no dice qué hacer");
  assert.ok(
    sinElegir.filas.every((fila) => !fila.elegida),
    "alguna fila viene marcada como elegida sin tocarla",
  );

  // Se toca el nombre de la segunda tierra.
  await pulsar(entorno, "elegir-fila", { tabla: "tierras", id: "2" });
  const conElegida = tablaDeTierrasPedida();
  assert.equal(conElegida.panel.elegida, true, "el panel no enseña la tierra elegida");
  assert.equal(conElegida.panel.detalle, "Tierra n.º 2", "el panel no dice qué tierra es");
  // **La elegida es la que se ha tocado**, no la primera de la lista.
  const marcadas = conElegida.filas.filter((fila) => fila.elegida);
  assert.equal(marcadas.length, 1, `hay ${marcadas.length} filas marcadas`);
  assert.equal(marcadas[0].celdas[1].texto, "La Vega", "la fila marcada no es la que se ha tocado");
  // Los datos de la tierra, con su nombre delante (los mismos que su ficha), y su botón.
  const etiquetas = conElegida.panel.filas.map((fila) => fila.etiqueta);
  assert.ok(etiquetas.includes("Referencia oficial SIGPAC"), `sin la referencia: ${etiquetas.join(", ")}`);
  assert.ok(etiquetas.includes("Hectáreas"), `sin las hectáreas: ${etiquetas.join(", ")}`);
  assert.deepEqual(
    conElegida.panel.acciones.map((una) => una.accion),
    // **El primero es el de su historia** (T15, 05/10/2026): lo que ha pasado en esa tierra. Va detrás
    // del que abre lo sembrado —que es lo que más se usa— y delante de CORREGIR y BORRAR. Esta lista
    // cambió al añadirlo, y se cambia aquí **diciendo por qué**. (En el móvil ese botón no se pinta: allí
    // la tarjeta entera abre ya la ficha —07/10/2026—, y el que lo quita es la pantalla de la tarjeta,
    // no esta lista, porque el panel del ordenador lo necesita.)
    ["cultivo-decir", "tierra-historia", "cosa-corregir", "cosa-borrar"],
  );

  // Y volver a tocar la misma tierra cierra el panel: es como se quita sin buscar un botón de cerrar.
  await pulsar(entorno, "elegir-fila", { tabla: "tierras", id: "2" });
  assert.equal(tablaDeTierrasPedida().panel.elegida, false, "volver a tocar la tierra no cierra el panel");
});

test("desde la pantalla de «apuntado» también se puede corregir lo que se acaba de apuntar", async () => {
  // Es el momento en el que el agricultor se da cuenta de la mitad de las equivocaciones: acaba de leer
  // el resumen en el móvil. Antes la única salida era DESHACER, que anula el apunte entero.
  const { entorno, servidor } = await cargarAplicacion({
    "/api/tratamientos": [unTratamiento(DENTRO_DE_LA_TIERRA)],
    "PUT /api/tratamientos/7": unTratamiento(),
  });
  await pulsar(entorno, "deshacer", { tipo: "tratamiento", id: "7" });
  assert.ok(
    servidor.enviados.some((uno) => uno.ruta === "/api/tratamientos/7/anular"),
    "DESHACER ya no anula",
  );
});

// ---------------------------------------------------------------------------
// Corregir y borrar las TIERRAS y los GRUPOS (ronda 92)
//
// Lo mismo que la ronda 91 hizo con los apuntes del cuaderno, pero para lo que David dio de alta él:
// las tierras y los grupos. Se pidió así: «recuerda también dejar borrar las cosas que introduzca
// porque puede que me equivoque, o modificar también», y una tierra con la referencia del SIGPAC mal
// copiada es justo la clase de cosa que hay que poder arreglar.
//
// Lo que se comprueba aquí es **el cableado de `app.js`**, que es donde se rompe en silencio: que cada
// tierra tenga sus dos botones, que corregir abra el formulario **con lo que ya había** y guarde con
// `PUT` (no con `POST`: sería una tierra nueva, y el agricultor tendría las dos, la vieja con todos sus
// apuntes), y que borrar pregunte antes y avise de lo que va a desaparecer.
// ---------------------------------------------------------------------------

/** La sección de las tierras de «mis cosas», ya pedida a React. */
async function tierrasDeMisCosasPedidas(cambios = {}) {
  const { entorno, servidor } = await cargarAplicacion(cambios);
  await pulsar(entorno, "mis-cosas");
  return { tierras: tierrasDeMisCosas(), entorno, servidor };
}

/** Los grupos de la pantalla de grupos, ya pedidos a React. */
async function gruposPedidos(cambios = {}) {
  const { entorno, servidor } = await cargarAplicacion(cambios);
  await pulsar(entorno, "grupo-ver");
  const montado = montajes[montajes.length - 1].elemento;
  assert.equal(montado.type.name, "PantallaGrupos", "los grupos no se le piden a React");
  return { grupos: montado.props.grupos, entorno, servidor };
}

test("cada tierra de «mis cosas» lleva sus tres botones: su historia, corregir y borrar", async () => {
  // **Tres desde el 05/10/2026, y el primero es nuevo**: el que abre lo que ha pasado en esa tierra
  // (T15). Antes de él, esa pantalla **no tenía puerta**: existía y su dirección funcionaba, pero no
  // había ningún botón que llevara a ella. Esta prueba cambió al añadirlo, y se cambia aquí diciendo por
  // qué: los otros dos siguen siendo los mismos y en el mismo orden, con borrar al final y en rojo.
  //
  // **Y el 07/10/2026 la tarjeta pasó a abrir la ficha** (la misma pantalla que abre la fila en el
  // ordenador: una tierra, una ficha), así que cambia la acción de la tarjeta y no la lista de botones:
  // el de «su historia» sigue en la lista del panel, y es **la pantalla de la tarjeta** la que no lo
  // pinta, porque allí lo hace la tarjeta entera.
  const { tierras } = await tierrasDeMisCosasPedidas();
  const acciones = tierras[0].acciones;
  assert.equal(acciones.length, 3, "la tierra no lleva sus tres botones");
  assert.equal(acciones[0].accion, "tierra-historia", "no se puede ver lo que ha pasado en la tierra");
  assert.equal(acciones[0].etiqueta, "LO QUE HA PASADO EN ESTA TIERRA");
  assert.equal(acciones[0].datos.id, 1, "el botón no dice de qué tierra es la historia");
  assert.equal(acciones[1].accion, "cosa-corregir", "no se puede corregir la tierra");
  assert.equal(acciones[1].etiqueta, "CORREGIR");
  assert.equal(acciones[1].datos.tipo, "parcela", "el botón no dice que esto es una tierra");
  assert.equal(acciones[1].datos.id, 1, "el botón no dice de qué tierra habla");
  assert.equal(acciones[2].accion, "cosa-borrar", "no se puede borrar la tierra");
  assert.equal(acciones[2].etiqueta, "BORRAR");
  assert.equal(acciones[2].clase, "boton-peligro", "el botón de borrar no va marcado como peligro");
  // Y la tarjeta hace lo suyo: **abre la ficha de esa tierra**, igual que la fila en el ordenador (antes
  // abría lo que hay sembrado, y la misma tierra llevaba a dos pantallas distintas según el aparato).
  assert.equal(tierras[0].accion, "tierra-historia", "la tarjeta no abre la ficha de la tierra");
});

test("corregir una tierra abre el formulario con lo que ya estaba, y guarda con PUT", async () => {
  // **El fallo que esto persigue**: si la corrección mandara un POST, se daría de alta una tierra
  // nueva. El agricultor tendría las dos —la buena y la mala— y la vieja con todos sus apuntes dentro.
  const { entorno, servidor } = await tierrasDeMisCosasPedidas({
    "PUT /api/parcelas/1": { id: 1, alias: "El Prado de arriba" },
  });
  await pulsar(entorno, "cosa-corregir", { tipo: "parcela", id: "1" });

  const montado = montajes[montajes.length - 1].elemento;
  assert.equal(montado.type.name, "PantallaAsistente", "corregir una tierra no abre el formulario");
  assert.equal(montado.props.titulo, "Corregir lo que apuntaste");
  await irHastaElResumen(entorno);
  await pulsar(entorno, "asistente-seguir");

  const correccion = servidor.enviados.find((uno) => uno.metodo === "PUT");
  assert.ok(correccion, "la corrección de la tierra no se ha mandado como PUT");
  assert.equal(correccion.ruta, "/api/parcelas/1", "no se corrige esa tierra");
  assert.equal(correccion.cuerpo.alias, "El Prado", "lo que se manda no lleva el nombre de la tierra");
  assert.equal(correccion.cuerpo.superficie_ha, 2.43, "se ha perdido la superficie de la tierra");
  assert.equal(
    correccion.cuerpo.ref_sigpac,
    "37-70-0-0-503-51-1",
    "se ha perdido la referencia del SIGPAC: la tierra se quedaría sin saber cuál es",
  );
  assert.ok(
    !servidor.enviados.some((uno) => uno.metodo === "POST" && uno.ruta === "/api/parcelas"),
    "además de corregir, se ha dado de alta una tierra nueva",
  );
});

test("borrar una tierra pregunta antes, y lo que desaparece es esa tierra", async () => {
  const { entorno, servidor } = await tierrasDeMisCosasPedidas();
  const antes = servidor.enviados.length;
  await pulsar(entorno, "cosa-borrar", { tipo: "parcela", id: "1" });

  const montado = montajes[montajes.length - 1].elemento;
  assert.equal(montado.type.name, "Confirmacion", "borrar una tierra no pregunta nada");
  assert.equal(montado.props.pregunta, "¿Seguro que quieres borrarlo?");
  const filas = montado.props.contenido.props.filas;
  assert.equal(filas[0][0], "Tierra", "no dice de qué clase es lo que se va a borrar");
  assert.equal(filas[0][1], "El Prado", "no dice qué tierra se va a borrar");
  assert.ok(
    filas.some((fila) => fila[1] === "37-70-0-0-503-51-1"),
    `no enseña la referencia de la tierra que se va a borrar: ${JSON.stringify(filas)}`,
  );
  // Las tres salidas: borrarla, corregirla (que es lo que de verdad quiere quien se ha equivocado) y
  // volver. Y se vuelve **a mis tierras**, que es de donde se ha salido, no al cuaderno.
  assert.deepEqual(
    montado.props.acciones.map((accion) => accion.accion),
    ["cosa-borrar-si", "cosa-corregir", "inicio"],
  );
  assert.equal(montado.props.acciones[2].datos.ir, "mis_cosas", "se vuelve a la pantalla equivocada");
  assert.equal(
    servidor.enviados.length,
    antes,
    "se ha borrado la tierra sin esperar a que el agricultor diga que sí",
  );
});

test("decir que sí borra la tierra, en su ruta y con DELETE", async () => {
  const { entorno, servidor } = await tierrasDeMisCosasPedidas({
    "DELETE /api/parcelas/1": { borrado: true, id: 1 },
  });
  await pulsar(entorno, "cosa-borrar", { tipo: "parcela", id: "1" });
  await pulsar(entorno, "cosa-borrar-si", { tipo: "parcela", id: "1" });

  const borrado = servidor.enviados.find((uno) => uno.metodo === "DELETE");
  assert.ok(borrado, "no se ha mandado el borrado de la tierra");
  assert.equal(borrado.ruta, "/api/parcelas/1", "se ha borrado otra tierra");
  const montado = montajes[montajes.length - 1].elemento;
  assert.equal(montado.props.titulo, "Borrado");
  assert.equal(montado.props.pista, "Esa tierra ya no está en tu cuaderno.");
  // Y el botón grande devuelve a las tierras, que es donde estaba.
  assert.equal(montado.props.acciones[0].datos.ir, "mis_cosas");
});

test("si la tierra tiene apuntes, el servidor no la deja borrar y se lee su motivo", async () => {
  // **El caso que de verdad importa**: borrar una tierra con apuntes destruiría el cuaderno de campo en
  // silencio. El servidor contesta que no y explica qué hacer; la interfaz lo enseña tal cual (no
  // inventa frases) y deja salir del aviso.
  const motivo = "Esa tierra tiene 12 apuntes en el cuaderno. Bórralos o corrígelos antes.";
  const { entorno, servidor } = await tierrasDeMisCosasPedidas({
    "DELETE /api/parcelas/1": falla({ detail: motivo }),
  });
  await pulsar(entorno, "cosa-borrar", { tipo: "parcela", id: "1" });
  await pulsar(entorno, "cosa-borrar-si", { tipo: "parcela", id: "1" });

  const { texto, boton } = ultimoErrorPedido();
  assert.equal(texto, motivo, "no se dice por qué no se puede borrar la tierra");
  assert.ok(boton, "el aviso no lleva salida: el agricultor se queda encerrado");
  assert.ok(servidor.enviados.some((uno) => uno.metodo === "DELETE"), "ni siquiera se ha intentado");
});

test("cada grupo lleva sus dos botones, y corregirlo solo pregunta cómo se llama", async () => {
  const { grupos, entorno, servidor } = await gruposPedidos({
    "PUT /api/grupos/1": { id: 1, nombre: "El de mi hermano" },
  });
  const acciones = grupos[0].acciones;
  assert.equal(acciones.length, 2, "el grupo no lleva sus dos botones");
  assert.equal(acciones[0].accion, "cosa-corregir");
  assert.equal(acciones[0].datos.tipo, "grupo", "el botón no dice que esto es un grupo");
  assert.equal(acciones[1].accion, "cosa-borrar");

  await pulsar(entorno, "cosa-corregir", { tipo: "grupo", id: "1" });
  const montado = montajes[montajes.length - 1].elemento;
  assert.equal(montado.type.name, "PantallaAsistente");
  assert.equal(montado.props.titulo, "Corregir lo que apuntaste");
  // Un grupo lo junta el programa: lo único que el agricultor cambia es el nombre.
  assert.equal(montado.props.total, 1, "el formulario de un grupo tiene más de una pregunta");

  await pulsar(entorno, "asistente-seguir");
  const correccion = servidor.enviados.find((uno) => uno.metodo === "PUT");
  assert.ok(correccion, "la corrección del grupo no se ha mandado");
  assert.equal(correccion.ruta, "/api/grupos/1", "no se corrige ese grupo");
  assert.equal(correccion.cuerpo.nombre, "Cebada (3 parcelas)", "no se manda el nombre del grupo");
  // **Y las tierras siguen siendo las suyas**: el formulario no las pregunta, así que si no viajaran,
  // renombrar un grupo lo dejaría vacío.
  assert.deepEqual(
    correccion.cuerpo.parcela_ids,
    [1, 2, 3],
    "renombrar el grupo le ha quitado las tierras",
  );
});

test("un grupo se puede borrar, y se dice que las tierras no se tocan", async () => {
  const { entorno, servidor } = await gruposPedidos({
    "DELETE /api/grupos/1": { borrado: true, id: 1 },
  });
  await pulsar(entorno, "cosa-borrar", { tipo: "grupo", id: "1" });
  const montado = montajes[montajes.length - 1].elemento;
  assert.equal(montado.props.pregunta, "¿Seguro que quieres borrarlo?");
  assert.equal(montado.props.contenido.props.filas[0][0], "Grupo de tierras");
  assert.equal(montado.props.contenido.props.filas[0][1], "Cebada (3 parcelas)");

  await pulsar(entorno, "cosa-borrar-si", { tipo: "grupo", id: "1" });
  const borrado = servidor.enviados.find((uno) => uno.metodo === "DELETE");
  assert.ok(borrado, "no se ha mandado el borrado del grupo");
  assert.equal(borrado.ruta, "/api/grupos/1", "se ha borrado otro grupo");
  const fin = montajes[montajes.length - 1].elemento;
  assert.equal(fin.props.pista, "Ese grupo ya no está: las tierras siguen ahí.");
  assert.equal(fin.props.acciones[0].datos.ir, "grupos", "se vuelve a la pantalla equivocada");
});

// ---------------------------------------------------------------------------
// Y lo mismo para TODO lo demás que se da de alta (ronda 93)
//
// Las fichas de lo que se usa (un producto, un abono, quién aplica, un asesor, una máquina, una nave),
// los análisis, lo que se vende y el plan de abono. Todas se corrigen con **su propio formulario**
// (el mismo con el que se dan de alta) y se borran con la misma pantalla.
//
// Aquí se comprueba lo que se rompe en silencio: que los datos que el formulario **no pregunta** lleguen
// igualmente al servidor al corregir. Un plan que pierde su reparto previsto, un análisis que pierde sus
// nueve números o una venta que pierde de qué tierras salió son datos del cuaderno que desaparecen sin
// que salte ningún error.
// ---------------------------------------------------------------------------

test("corregir un producto que dice «no lo sé» deja marcada esa respuesta", async () => {
  // **El fallo que esto persigue** (02/10/2026, con los tres estados de A1). La autorización de un
  // producto puede valer «sí», «no» o «no lo sé», y en la base «no lo sé» es `null`. Al corregir una
  // ficha, el formulario se rellena con lo que había y **las opciones se comparan como texto**, así
  // que el `null` de la base no casaba con la opción «nulo»: no salía marcada ninguna respuesta. El
  // agricultor tenía que volver a elegir, con el riesgo de elegir lo contrario de lo que ya había
  // dicho —y esa respuesta decide si el programa le deja echar el producto—.
  const { entorno } = await tierrasDeMisCosasPedidas({
    "/api/productos": [{ ...UN_PRODUCTO[0], autorizado: null, permitido_ecologico: null }],
  });
  await pulsar(entorno, "cosa-corregir", { tipo: "producto", id: "1" });
  await avanzarHasta(entorno, "¿Está autorizado este producto?");

  const marcadas = bloquesDelMaestroPedidos()
    .find((bloque) => bloque.tipo === "opciones" && bloque.campo === "autorizado")
    .opciones.filter((opcion) => opcion.elegido)
    .map((opcion) => opcion.etiqueta);
  assert.deepEqual(
    marcadas,
    ["No lo sé"],
    `la respuesta que ya estaba guardada no sale marcada: ${JSON.stringify(marcadas)}`,
  );
});

test("cada ficha de lo que se usa lleva sus dos botones, y corregirla abre su formulario", async () => {
  const { entorno, servidor } = await tierrasDeMisCosasPedidas({
    "/api/productos": UN_PRODUCTO,
    "PUT /api/productos/1": UN_PRODUCTO[0],
  });
  const producto = montajes[montajes.length - 1].elemento.props.secciones[1];
  assert.equal(producto.tipo, "producto");
  assert.equal(producto.elementos[0].acciones[0].accion, "cosa-corregir");
  assert.equal(producto.elementos[0].acciones[0].datos.tipo, "producto");
  assert.equal(producto.elementos[0].acciones[0].datos.id, 1);
  assert.equal(producto.elementos[0].acciones[1].accion, "cosa-borrar");

  await pulsar(entorno, "cosa-corregir", { tipo: "producto", id: "1" });
  const montado = montajes[montajes.length - 1].elemento;
  assert.equal(montado.type.name, "PantallaAsistente", "corregir un producto no abre su formulario");
  assert.equal(montado.props.titulo, "Corregir lo que apuntaste");
  await irHastaElResumen(entorno);
  await pulsar(entorno, "asistente-seguir");

  const correccion = servidor.enviados.find((uno) => uno.metodo === "PUT");
  assert.ok(correccion, "la corrección del producto no se ha mandado como PUT");
  assert.equal(correccion.ruta, "/api/productos/1", "no se corrige ese producto");
  assert.equal(correccion.cuerpo.nombre_comercial, "Ejemplo 25 EC", "no se manda el nombre");
  assert.equal(correccion.cuerpo.numero_registro, "24.123", "se ha perdido el nº de la etiqueta");
  assert.equal(correccion.cuerpo.plazo_seguridad_dias, 21, "se ha perdido el plazo de seguridad");
  assert.ok(
    !servidor.enviados.some((uno) => uno.metodo === "POST" && uno.ruta === "/api/productos"),
    "además de corregir, se ha dado de alta un producto nuevo",
  );
});

test("corregir un análisis manda también sus números del boletín", async () => {
  // Los números se guardan por clave y el asistente los lee de un diccionario: si la traducción
  // fallara, corregir la fecha de un análisis **le borraría los nueve números del boletín**, que es
  // justo lo que después lee el plan de abono.
  const { entorno, servidor } = await cargarAplicacion({
    "/api/analiticas": [unAnalisis()],
    "PUT /api/analiticas/1": unAnalisis(),
  });
  await pulsar(entorno, "analisis-ver");
  const ficha = montajes[montajes.length - 1].elemento;
  const acciones = ficha.props.analisis[0].acciones;
  assert.equal(acciones[0].accion, "cosa-corregir", "el análisis no se puede corregir");
  assert.equal(acciones[0].datos.tipo, "analitica");
  assert.equal(acciones[1].accion, "cosa-borrar");

  await pulsar(entorno, "cosa-corregir", { tipo: "analitica", id: "1" });
  assert.equal(montajes[montajes.length - 1].elemento.props.titulo, "Corregir lo que apuntaste");
  await irHastaElResumen(entorno);
  await pulsar(entorno, "asistente-seguir");

  const correccion = servidor.enviados.find((uno) => uno.metodo === "PUT");
  assert.ok(correccion, "la corrección del análisis no se ha mandado");
  assert.equal(correccion.ruta, "/api/analiticas/1");
  const porClave = Object.fromEntries(
    (correccion.cuerpo.parametros || []).map((parametro) => [parametro.clave, parametro.valor]),
  );
  assert.equal(porClave.materia_organica, "1.8", "se ha perdido la materia orgánica del boletín");
  assert.equal(porClave.ph, "7.4", "se ha perdido el pH del boletín");
  assert.equal(correccion.cuerpo.laboratorio, "Laboratorio Agrario de Villamuriel");
});

test("corregir una venta no le quita de qué tierras salió", async () => {
  const conGrupo = unaVenta({ grupo_id: 3 });
  const { entorno, servidor } = await cargarAplicacion({
    "/api/ventas": [conGrupo],
    "/api/ventas/tabla": unaTablaDeVentas(),
    "PUT /api/ventas/1": conGrupo,
  });
  await pulsar(entorno, "ventas-ver");
  await pulsar(entorno, "cosa-corregir", { tipo: "venta", id: "1" });
  await irHastaElResumen(entorno);
  await pulsar(entorno, "asistente-seguir");

  const correccion = servidor.enviados.find((uno) => uno.metodo === "PUT");
  assert.ok(correccion, "la corrección de la venta no se ha mandado");
  assert.equal(correccion.ruta, "/api/ventas/1");
  assert.equal(correccion.cuerpo.producto, "Trigo blando", "se ha perdido el producto vendido");
  assert.equal(correccion.cuerpo.grupo_id, 3, "se ha perdido el grupo del que salió la partida");
});

test("corregir un plan no le quita el reparto previsto", async () => {
  // «Qué abono, cuánto y en qué momento»: la mitad del plan. El asistente no lo pregunta, así que si no
  // viajara de vuelta, ajustar los kilos previstos de un plan lo dejaría sin reparto.
  const conReparto = unPlan({
    detalle: [{ abono: "Nitrato amónico", kilos_ha: 300, momento: "fondo" }],
  });
  const { entorno, servidor } = await cargarAplicacion({
    "/api/planes": [conReparto],
    "PUT /api/planes/1": conReparto,
  });
  await pulsar(entorno, "plan-ver");
  await pulsar(entorno, "cosa-corregir", { tipo: "plan", id: "1" });
  await irHastaElResumen(entorno);
  await pulsar(entorno, "asistente-seguir");

  const correccion = servidor.enviados.find((uno) => uno.metodo === "PUT");
  assert.ok(correccion, "la corrección del plan no se ha mandado");
  assert.equal(correccion.ruta, "/api/planes/1");
  assert.equal(correccion.cuerpo.cultivo, "Trigo blando", "se ha perdido el cultivo del plan");
  assert.deepEqual(
    correccion.cuerpo.detalle,
    [{ abono: "Nitrato amónico", kilos_ha: 300, momento: "fondo" }],
    "el plan ha perdido su reparto previsto",
  );
});

test("la barra dice en qué finca se está, y deja cambiar cuando hay más de una", async () => {
  // El contexto en la cabecera (T04): con una cuenta que entra en **varias** fincas, la barra tiene que
  // decir en cuál se está y dejar cambiar. Sin esto, apuntar en la finca equivocada es cuestión de suerte.
  const { entorno, servidor } = await cargarAplicacion();
  const alArrancar = montajesDelMarco[montajesDelMarco.length - 1].elemento.props;
  assert.equal(
    alArrancar.contexto.finca,
    "David Pérez Velasco",
    "la barra no dice en qué finca se está",
  );
  assert.deepEqual(
    alArrancar.contexto.fincas,
    [],
    "ofrece cambiar de finca antes de saber en cuáles puede entrar",
  );

  // Se abre la pantalla donde se piden las fincas de la cuenta (son dos: la suya y una en la que ayuda).
  await pulsar(entorno, "inicio", { ir: "mis_datos" });
  await pulsar(entorno, "quien-entra-abrir");
  const conFincas = montajesDelMarco[montajesDelMarco.length - 1].elemento.props;
  assert.equal(conFincas.contexto.fincas.length, 2, "no ofrece las fincas en las que puede entrar");

  // Y el botón de la barra cambia de finca de verdad: es el mismo camino que el de la pantalla.
  await pulsar(entorno, "cambiar-finca", { valor: "3" });
  const enviado = servidor.enviados.find(
    (uno) => uno.metodo === "POST" && uno.ruta === "/api/fincas/cambiar",
  );
  assert.ok(enviado, "el botón de la barra no cambia de finca");
  assert.deepEqual(enviado.cuerpo, { explotacion_id: 3 }, "no dice a qué finca se cambia");
});

test("la barra no ofrece cambiar de campaña, porque cambiarla no existe", async () => {
  // **Decisión, no olvido** (T04). El servidor no tiene ninguna forma de decir «trabaja en el año 2023»
  // (`/api/campanas/actual` devuelve siempre la más nueva), así que la barra enseña la campaña —que es un
  // dato— pero **no inventa un botón que no cambiaría nada**. Los años se manejan en su pantalla.
  const { entorno } = await cargarAplicacion();
  const props = montajesDelMarco[montajesDelMarco.length - 1].elemento.props;
  assert.equal(props.campana, "2026", "la barra no dice en qué año se está apuntando");
  assert.equal(
    props.contexto.campanas,
    undefined,
    "la barra ofrece elegir campaña cuando cambiarla no es algo que el programa sepa hacer",
  );
  assert.equal(entorno.window.localStorage.getItem("cuedigital.token"), "token-de-prueba");
});

test("el botón de volver de una ficha lleva a la pantalla de la que se salió", async () => {
  // **Esto estaba roto y no se veía**: el botón decía «VOLVER A MIS TIERRAS» y llevaba a la pantalla de
  // inicio, porque el nombre de la pantalla (`mis_cosas`) no estaba en la lista de destinos de
  // `irAInicio` y un destino que no está cae en el `default`. Lo que hay que comprobar no es lo que dice
  // el `data-ir`, sino **en qué pantalla acaba**.
  const { entorno } = await tierrasDeMisCosasPedidas({
    "DELETE /api/parcelas/1": { borrado: true, id: 1 },
  });
  await pulsar(entorno, "cosa-borrar", { tipo: "parcela", id: "1" });
  await pulsar(entorno, "cosa-borrar-si", { tipo: "parcela", id: "1" });
  const fin = montajes[montajes.length - 1].elemento;
  assert.equal(fin.props.acciones[0].accion, "inicio");

  await pulsar(entorno, "inicio", { ir: fin.props.acciones[0].datos.ir });
  const donde = montajes[montajes.length - 1].elemento;
  assert.equal(
    donde.type.name,
    "PantallaMisCosas",
    "el botón de volver no lleva a mis tierras: el destino no está en `irAInicio`",
  );
});

// ---------------------------------------------------------------------------
// La dirección: abrir, recargar, atrás y adelante (T04)
//
// Lo que se comprueba aquí no es el enrutador suelto (eso está en `tests_js/rutas.test.js`, contra el
// módulo y sin navegador): es **el cableado con la aplicación**, que es donde se rompe en silencio. Y son
// los cuatro casos de la aceptación de T04: abrir una tierra por su enlace, recargar y seguir donde
// estaba, atrás y adelante, y volver al listado sin perder los filtros.
// ---------------------------------------------------------------------------

/** El nombre del componente de la última pantalla montada. */
function laPantallaDeAhora() {
  return montajes[montajes.length - 1].elemento.type.name;
}

/** La dirección que hay puesta ahora mismo. */
function laDireccion(entorno) {
  return entorno.window.location.hash;
}

/** Lo que haría el navegador al pulsar «atrás»: la dirección cambia y salta `popstate`. */
async function irAtras(entorno, direccion) {
  entorno.window.location.hash = direccion;
  await entorno.manejadores.popstate();
  await new Promise((resolver) => setTimeout(resolver, 30));
}

test("los filtros de la lista de ventas viajan en la direccion y vuelven", async () => {
  // **CRM-01, 11/10/2026**: la revisión independiente midió que los filtros de esta lista vivían solo en
  // memoria —`estado.filtroVentas`— y que **volver de una ficha los perdía**. No había ninguna prueba de
  // esto, ni para ventas ni para ninguna lista. Aquí se exige el camino entero, en dos mitades:
  //
  //   1. el agricultor pone «solo las pendientes» → **la dirección lo lleva** (y por tanto se puede mandar
  //      o recargar sin perderlo);
  //   2. y al abrir el CRM **con esa dirección**, el filtro llega al servidor en la petición de la tabla.
  const conLaTabla = {
    "/api/ventas/tabla": { columnas: [], filas: [], pie: "", total: 0 },
  };
  const { entorno } = await cargarAplicacion(conLaTabla);
  await pulsar(entorno, "ventas-abrir");
  await pulsar(entorno, "ventas-solo-pendientes");
  const direccion = laDireccion(entorno);
  assert.match(
    direccion,
    /solo=pendientes/,
    `la dirección no lleva el filtro, así que volver lo perdería: ${direccion}`,
  );

  // Y la vuelta: se abre el CRM con esa dirección y el filtro tiene que llegar al servidor.
  const { servidor } = await cargarAplicacion({ ...conLaTabla }, { direccion });
  const pedidas = servidor.llamadas.filter((ruta) => ruta.startsWith("/api/ventas/tabla"));
  assert.ok(pedidas.length >= 1, "con esa dirección no se ha pedido la tabla de ventas");
  assert.ok(
    pedidas.some((ruta) => ruta.includes("solo=pendientes")),
    `el filtro de la dirección no ha llegado a la tabla: ${JSON.stringify(pedidas)}`,
  );
});

test("abrir una tierra por su dirección deja esa tierra abierta", async () => {
  // La aceptación de T04 en una línea: `#/tierras/2` tiene que abrir **la tierra 2**, con su panel, sin
  // que nadie tenga que buscarla en la lista de 64.
  await cargarAplicacion({}, { direccion: "#/tierras/2" });

  assert.equal(laPantallaDeAhora(), "PantallaMisCosas", "la dirección de una tierra no la ha abierto");
  const tabla = tablaDeTierrasPedida();
  assert.equal(tabla.panel.elegida, true, "la tierra de la dirección no sale abierta en el panel");
  const marcadas = tabla.filas.filter((fila) => fila.elegida);
  assert.equal(marcadas.length, 1, `hay ${marcadas.length} tierras marcadas`);
  assert.equal(marcadas[0].celdas[1].texto, "La Vega", "la tierra abierta no es la de la dirección");
});

test("recargar la página deja al agricultor donde estaba", async () => {
  // Recargar es **volver a arrancar con la misma dirección**: por eso se abre la aplicación dos veces.
  const primera = await cargarAplicacion({}, { direccion: "#/tierras/2" });
  const direccion = laDireccion(primera.entorno);
  assert.match(direccion, /^#\/tierras\/2/, `la dirección no es la de la tierra abierta: ${direccion}`);
  assert.ok(
    /campana=/.test(direccion) && /finca=/.test(direccion),
    `la dirección tiene que llevar la campaña y la finca: ${direccion}`,
  );

  await cargarAplicacion({}, { direccion });
  assert.equal(laPantallaDeAhora(), "PantallaMisCosas", "al recargar no se vuelve a la tierra");
  assert.equal(tablaDeTierrasPedida().panel.elegida, true, "al recargar se pierde la tierra abierta");
});

test("la dirección se escribe al cambiar de pantalla, y sin duplicados", async () => {
  const { entorno } = await cargarAplicacion();
  // Al arrancar sin dirección, la aplicación pone la de casa (y con el contexto).
  assert.match(laDireccion(entorno), /^#\/\?/, `la dirección de inicio no se ha escrito: ${laDireccion(entorno)}`);

  const antes = entorno.historial.length;
  await pulsar(entorno, "inicio", { ir: "mi_cuaderno" });
  assert.match(laDireccion(entorno), /^#\/cuaderno\?/, `no se ha escrito la del cuaderno: ${laDireccion(entorno)}`);
  assert.equal(entorno.historial.length, antes + 1, "no ha añadido exactamente una entrada al historial");

  // Y volver a pintar la misma pantalla no añade otra entrada: si no, «atrás» daría dos pasos para
  // volver a lo mismo.
  const conEntrada = entorno.historial.length;
  await pulsar(entorno, "inicio", { ir: "mi_cuaderno" });
  assert.equal(entorno.historial.length, conEntrada, "ha añadido una entrada de historial de más");
});

test("atrás y adelante llevan a la pantalla de la dirección", async () => {
  // El navegador no avisa con `click`: al pulsar «atrás» cambia la dirección y salta `popstate`. Es lo
  // único que se puede simular aquí, y es exactamente lo que hace la aplicación.
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "inicio", { ir: "mis_cosas" });
  assert.equal(laPantallaDeAhora(), "PantallaMisCosas");

  assert.ok(entorno.historial.length >= 2, `no hay historial que recorrer: ${entorno.historial}`);
  await irAtras(entorno, entorno.historial[0]);
  assert.equal(laPantallaDeAhora(), "PantallaInicio", "«atrás» no ha vuelto al inicio");

  // Y hacia adelante: se vuelve a la dirección del cuaderno.
  await irAtras(entorno, "#/cuaderno?campana=2026&finca=1");
  assert.equal(laPantallaDeAhora(), "PantallaMiCuaderno", "no se ha abierto el cuaderno de la dirección");
});

test("al volver del detalle, el listado conserva lo buscado y el orden", async () => {
  // **Volver no puede devolver al agricultor al principio de las 64 tierras sin filtro**: sería tener que
  // volver a buscarla cada vez que mira una ficha.
  const { entorno } = await cargarAplicacion({ "/api/parcelas": TRES_TIERRAS });
  await pulsar(entorno, "inicio", { ir: "mis_cosas" });
  escribir(entorno, "buscar_tierra_mis_cosas", "vallejo");
  await pulsar(entorno, "buscar-tierra-mis-cosas");
  const direccionDelListado = laDireccion(entorno);
  assert.match(direccionDelListado, /q=vallejo/, `el filtro no viaja en la dirección: ${direccionDelListado}`);

  // Se ordena por el nombre (la primera cabecera de la tabla) y se abre una ficha.
  await pulsar(entorno, "ordenar-tabla", { tabla: "tierras", campo: "alias" });
  const conOrden = laDireccion(entorno);
  assert.match(conOrden, /orden=alias/, `el orden no viaja en la dirección: ${conOrden}`);

  // Y se vuelve con «atrás» al listado, que es lo que hace el agricultor.
  await irAtras(entorno, conOrden);
  const seccion = montajes[montajes.length - 1].elemento.props.secciones[0];
  assert.equal(
    seccion.buscar.props.valor,
    "vallejo",
    "al volver, el buscador se ha quedado sin lo que el agricultor había escrito",
  );
  const orden = seccion.tabla.columnas.find((columna) => columna.campo === "alias");
  assert.equal(orden.descendente || false, false, "al volver se ha perdido el orden de la tabla");
});

test("una dirección que no lleva a nada lo dice, y no se disimula", async () => {
  // Tres casos que no son lo mismo y que la aplicación tiene que distinguir de «no hay nada apuntado»:
  // una pantalla que no existe, y una tierra que no está en el cuaderno de este agricultor.
  const primera = await cargarAplicacion({}, { direccion: "#/lo-que-sea" });
  assert.equal(
    laPantallaDeAhora(),
    "Confirmacion",
    `una dirección que no existe tiene que decirlo, y salió: ${laPantallaDeAhora()}`,
  );
  assert.match(
    primera.entorno.window.location.hash,
    /lo-que-sea/,
    "la dirección equivocada se ha cambiado sola por la de casa: el agricultor no ve qué pasó",
  );

  // Y una tierra que no es suya (o no existe): la lista de tierras ya descargada es la que manda, igual
  // que el servidor contesta 404 sin decir si existe en otra finca.
  await cargarAplicacion({}, { direccion: "#/tierras/99" });
  assert.equal(
    laPantallaDeAhora(),
    "Confirmacion",
    "abrir una tierra que no está en el cuaderno tiene que decirlo",
  );
});

test("una dirección de otra finca cambia de finca; y si no se puede, lo dice", async () => {
  // Lo que pide el encargo: **evitar datos antiguos al cambiar de explotación**. Una dirección que nombra
  // otra finca no puede enseñar los datos de la actual «como si nada».
  const buena = await cargarAplicacion({}, { direccion: "#/tierras/1?finca=3" });
  assert.ok(
    buena.servidor.enviados.some(
      (uno) => uno.metodo === "POST" && uno.ruta === "/api/fincas/cambiar",
    ),
    "una dirección de otra finca no ha cambiado de finca",
  );
  assert.equal(laPantallaDeAhora(), "PantallaMisCosas", "no se ha abierto la tierra de la otra finca");

  const mala = await cargarAplicacion(
    { "POST /api/fincas/cambiar": falla({ detail: "Esa finca no es tuya o ya no tienes acceso a ella." }) },
    { direccion: "#/tierras/1?finca=9" },
  );
  assert.equal(
    laPantallaDeAhora(),
    "Confirmacion",
    "si la finca de la dirección no es suya, no puede quedarse callado enseñando otra cosa",
  );
  assert.ok(mala, "el servidor de mentira tiene que haber contestado");
});

// ---------------------------------------------------------------------------
// Las pantallas que todavía no tenían dirección (T04, segunda entrega, 03/10/2026)
//
// De las 13 pantallas que se quedaron fuera de la primera entrega, **siete estrenan dirección** y **seis se
// quedan sin ella a propósito** (son pasos de un formulario: el asistente, «lo he apuntado», entrar, el alta
// de un papel y la de una factura —y el paso del SIGPAC, que vive dentro del asistente—).
//
// Aquí no se prueba el módulo del enrutador (eso está en `tests_js/rutas.test.js`, sin navegador): se prueba
// **el cableado con la aplicación**, que es donde se rompe en silencio. Los dos fallos que estas pruebas
// persiguen son los que el encargo nombra: que pulsar el botón de verdad acabe en la pantalla correcta
// **con la dirección que toca**, y que un paso no le robe la dirección a la pantalla de la que salió.
// ---------------------------------------------------------------------------

/** Una factura ya guardada, con una línea, para las pruebas de su dirección. */
function unaFacturaGuardada(extra = {}) {
  return {
    id: 9,
    proveedor: "Cooperativa Agrícola",
    proveedor_nif: "F37012345",
    numero_factura: "2026/00123",
    fecha: "2026-03-02",
    base_imponible: 620.0,
    cuota_iva: 130.2,
    tipo_iva_pct: 21.0,
    total: 750.2,
    notas: "Pagada a 30 días",
    leida_por: "pdf",
    tiene_fichero: true,
    lineas: [
      {
        id: 31,
        descripcion: "GLIFOSATO 36% SL 20 L",
        cantidad: 40,
        unidad: "L",
        precio_unitario: 4.25,
        importe: 170.0,
        numero_registro: "24.123",
        lote: "L-2026-07",
        producto_id: 5,
        fertilizante_id: null,
        cuadra: true,
      },
    ],
    ...extra,
  };
}

test("decir qué hay sembrado se abre por la dirección de su tierra, y recargar la vuelve a abrir", async () => {
  // Lo que persigue: que decir el cultivo sea **de una tierra**. Sin el identificador en la dirección,
  // recargar dejaba al agricultor en la lista de lo sembrado y tenía que volver a buscar cuál de sus
  // tierras era.
  const primera = await cargarAplicacion({}, { direccion: "#/tierras/2/cultivo" });
  assert.equal(
    laPantallaDeAhora(),
    "PantallaDecirCultivo",
    "la dirección de decir el cultivo no la ha abierto",
  );
  assert.equal(
    montajes[montajes.length - 1].elemento.props.parcela.id,
    2,
    "la tierra de la pantalla no es la de la dirección",
  );
  const direccion = laDireccion(primera.entorno);
  assert.match(direccion, /^#\/tierras\/2\/cultivo/, `la dirección no es la de esa tierra: ${direccion}`);

  // Recargar es volver a arrancar con la misma dirección.
  await cargarAplicacion({}, { direccion });
  assert.equal(laPantallaDeAhora(), "PantallaDecirCultivo", "al recargar no se vuelve a la tierra");
  assert.equal(
    montajes[montajes.length - 1].elemento.props.parcela.id,
    2,
    "al recargar se pierde de qué tierra se estaba diciendo el cultivo",
  );
});

test("decir el cultivo de una tierra que no está en el cuaderno lo dice, y no abre otra cosa", async () => {
  // El mismo caso que la ficha de una tierra: el servidor contesta 404 sin decir si existe en otra finca,
  // así que lo que se comprueba aquí es que **no se abre la tierra de al lado** ni una pantalla a medias.
  await cargarAplicacion({}, { direccion: "#/tierras/99/cultivo" });
  assert.equal(
    laPantallaDeAhora(),
    "Confirmacion",
    "decir el cultivo de una tierra que no es suya tiene que decirlo",
  );
});

test("pulsar el cultivo de una tierra deja la dirección de esa tierra, no la de la lista", async () => {
  // Es el camino de verdad: la tarjeta de una tierra en «qué hay sembrado» lleva a decir su cultivo. Antes
  // la dirección se quedaba en `#/cultivos`, así que recargar devolvía a la lista y el agricultor tenía que
  // acordarse de cuál de las 51 tierras había tocado.
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "cultivo-decir", { id: "2" });
  assert.equal(laPantallaDeAhora(), "PantallaDecirCultivo", "no se ha abierto la pantalla de decir el cultivo");
  const direccion = laDireccion(entorno);
  assert.match(direccion, /^#\/tierras\/2\/cultivo/, `la dirección no es la de esa tierra: ${direccion}`);
  assert.doesNotMatch(direccion, /^#\/cultivos/, "la dirección se ha quedado en la lista de lo sembrado");
});

test("el mapa se abre por su dirección y no por la de las tierras", async () => {
  // El mapa cuelga de las tierras en el menú (es donde se miran las parcelas), pero su dirección es la suya:
  // volver a `#/tierras` no es volver al mapa, y al revés, recargar el mapa no puede dejar al agricultor en
  // una lista que no ha pedido.
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "mapa-abrir");
  assert.equal(laPantallaDeAhora(), "PantallaMapa", "el botón del mapa no abre el mapa");
  const direccion = laDireccion(entorno);
  assert.match(direccion, /^#\/mapa/, `la dirección del mapa no es la del mapa: ${direccion}`);

  await cargarAplicacion({}, { direccion });
  assert.equal(laPantallaDeAhora(), "PantallaMapa", "al recargar el mapa no se vuelve al mapa");
});

test("firmar el cuaderno tiene su dirección, y no es la de un apunte", async () => {
  // Firmar cuelga de «mi cuaderno» y es un destino, no un paso: se puede mandar el enlace y recargar. Y su
  // camino (`#/cuaderno/firmar`) no puede leerse como el apunte número «firmar».
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "firmar-abrir");
  assert.equal(laPantallaDeAhora(), "PantallaFirmar", "el botón de firmar no abre la pantalla de la firma");
  const direccion = laDireccion(entorno);
  assert.match(direccion, /^#\/cuaderno\/firmar/, `la dirección de la firma no es la suya: ${direccion}`);

  await cargarAplicacion({}, { direccion });
  assert.equal(laPantallaDeAhora(), "PantallaFirmar", "al recargar la firma no se vuelve a la firma");
});

test("quién entra en la finca se abre por su dirección y vuelve a pedir lo que enseña", async () => {
  // Es un destino de «mis datos» (dice en qué fincas puede entrar esta cuenta y quién entra en la que se
  // está usando), así que su dirección tiene que poder recargarse: al abrirla **se vuelve a preguntar al
  // servidor**, que es lo que impide enseñar la lista de la finca anterior.
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "quien-entra-abrir");
  assert.equal(laPantallaDeAhora(), "PantallaQuienEntra", "no se ha abierto quién entra");
  const direccion = laDireccion(entorno);
  assert.match(direccion, /^#\/datos\/quien-entra/, `la dirección de quién entra no es la suya: ${direccion}`);

  const otra = await cargarAplicacion({}, { direccion });
  assert.equal(laPantallaDeAhora(), "PantallaQuienEntra", "al recargar no se vuelve a quién entra");
  assert.ok(
    otra.servidor.llamadas.includes("/api/fincas/quien-entra"),
    "al abrir quién entra por su dirección no se ha preguntado quién entra",
  );
});

test("la revisión de una factura guardada se abre por su dirección, y recargarla la vuelve a abrir", async () => {
  // **Una factura concreta y su interpretación.** La misma pantalla sirve para confirmar lo que se acaba de
  // leer y para corregir una factura guardada; la guardada sí tiene dirección, porque se puede volver a
  // armar entera con lo que hay en el cuaderno (que es lo que hace que el enlace sirva para algo).
  const laFactura = unaFacturaGuardada();
  const { entorno } = await cargarAplicacion({ "/api/facturas": [laFactura] });
  await pulsar(entorno, "facturas-abrir");
  await pulsar(entorno, "cosa-corregir", { tipo: "factura", id: "9" });
  assert.equal(
    laPantallaDeAhora(),
    "PantallaInterpretacionDeLaFactura",
    "corregir una factura no abre su pantalla",
  );
  const direccion = laDireccion(entorno);
  assert.match(direccion, /^#\/facturas\/9/, `la dirección no es la de esa factura: ${direccion}`);

  const segunda = await cargarAplicacion({ "/api/facturas": [laFactura] }, { direccion });
  assert.equal(
    laPantallaDeAhora(),
    "PantallaInterpretacionDeLaFactura",
    "al recargar no se vuelve a la factura que dice la dirección",
  );
  const montado = montajes[montajes.length - 1].elemento;
  assert.equal(montado.props.corrigiendo, true, "al abrirla por su dirección no se está corrigiendo esa factura");
  const cabecera = Object.fromEntries(montado.props.leida.cabecera.map((campo) => [campo.id, campo.valor]));
  assert.equal(cabecera["factura-proveedor"], "Cooperativa Agrícola", "no llega la factura de la dirección");
  assert.ok(segunda, "el servidor de mentira tiene que haber contestado");
});

test("una factura que no está en el cuaderno no abre la revisión de otra", async () => {
  // Abrir `#/facturas/999` no puede abrir «una factura cualquiera»: se dice que esa dirección no lleva a
  // ninguna parte, igual que con una tierra que no es suya.
  await cargarAplicacion({}, { direccion: "#/facturas/999" });
  assert.equal(
    laPantallaDeAhora(),
    "Confirmacion",
    "una factura que no está en el cuaderno tiene que decirlo",
  );
});

test("una factura recién leída no tiene dirección propia: no se le roba la de la lista", async () => {
  // La otra mitad de la decisión: lo que se ha leído de una foto **no está guardado en ningún sitio**, así
  // que no hay dirección que lo reproduzca. Escribir `#/facturas/9` ahí sería inventarse un identificador
  // —y al recargar, el agricultor vería una factura que no es la que estaba revisando—.
  const { entorno } = await cargarAplicacion();
  await pulsar(entorno, "facturas-abrir");
  const laDeLaLista = laDireccion(entorno);
  assert.match(laDeLaLista, /^#\/facturas/, "no se ha abierto la lista de facturas");

  await pulsar(entorno, "factura-nueva");
  assert.equal(laPantallaDeAhora(), "PantallaNuevaFactura", "no se ha abierto el alta de una factura");
  assert.equal(
    laDireccion(entorno),
    laDeLaLista,
    "el alta de una factura se ha llevado la dirección de la lista",
  );

  elegirLaFactura(entorno);
  await pulsar(entorno, "factura-leer");
  assert.equal(
    laPantallaDeAhora(),
    "PantallaInterpretacionDeLaFactura",
    "no se ha abierto la revisión de lo leído",
  );
  assert.equal(montajes[montajes.length - 1].elemento.props.corrigiendo, false, "dice que está corrigiendo");
  assert.equal(
    laDireccion(entorno),
    laDeLaLista,
    "la revisión de una lectura sin guardar se ha inventado una dirección de factura",
  );
});

test("el dictado y su revisión tienen su dirección, y el borrador sin dictado lleva al dictado", async () => {
  // El dictado es una pantalla a la que se va (tiene su botón en la de inicio) y la revisión es lo que sale
  // de él. Abrir `#/borrador` sin haber dictado **no inventa una revisión**: lleva al dictado, que es donde
  // nace el borrador y donde el agricultor puede hacer algo.
  const { entorno } = await cargarAplicacion({
    "POST /api/borradores/desde-texto": {
      tipo: "tratamiento",
      datos: { parcela_id: 1 },
      entendido: [{ pregunta: "¿Dónde?", valor: "El Prado", campo: "parcela_id" }],
      falta: [{ pregunta: "¿Cuándo?" }],
      fuente: "reglas",
      titulo: "Lo que he entendido",
      intro: "Mira si está bien.",
      falta_intro: "Me falta esto:",
      nada_entendido: null,
    },
  });
  await pulsar(entorno, "dictado");
  assert.match(laDireccion(entorno), /^#\/dictado/, "el dictado no tiene dirección propia");
  escribir(entorno, "dictado-texto", "he echado glifosato en el prado");
  await pulsar(entorno, "dictado-entender");
  assert.equal(laPantallaDeAhora(), "PantallaBorrador", "no se ha abierto la revisión");
  assert.match(laDireccion(entorno), /^#\/borrador/, "la revisión de lo dictado no tiene dirección propia");

  // Y en frío: `#/borrador` sin nada dictado.
  const frio = await cargarAplicacion({}, { direccion: "#/borrador" });
  assert.equal(
    laPantallaDeAhora(),
    "PantallaDictado",
    "abrir la revisión sin haber dictado tiene que llevar al dictado, no a una revisión vacía",
  );
  assert.match(laDireccion(frio.entorno), /^#\/dictado/, "no se ha quedado en el dictado");
});

test("los pasos de un formulario no le roban la dirección a la pantalla anterior", async () => {
  // **Es la mitad de la decisión que casi nadie ve.** El asistente de apuntar tiene 65 pasos y lo que lleva
  // escrito vive en la memoria de la sesión: una dirección que al recargar dejara al agricultor en el paso
  // 34 no se puede construir, y una que lo dejara en el cuaderno (que es lo que hacía antes) le hacía
  // perder el sitio donde estaba. Lo mismo con «lo he apuntado», el alta de un papel, la de una factura y
  // la pantalla de entrar: **no escriben ninguna dirección**, así que la barra se queda donde estaba.
  //
  // Se empieza **en una tierra** a propósito: si la dirección de partida fuera la de la lista del módulo, el
  // paso escribiría exactamente lo mismo y esta prueba no distinguiría nada (es el fallo de una prueba que
  // da por bueno lo que no mira).
  const { entorno } = await cargarAplicacion(
    {
      "/api/tratamientos": [unTratamiento(DENTRO_DE_LA_TIERRA)],
      "PUT /api/tratamientos/7": unTratamiento(DENTRO_DE_LA_TIERRA),
    },
    { direccion: "#/tierras/2" },
  );
  const laDeLaTierra = laDireccion(entorno);
  assert.match(laDeLaTierra, /^#\/tierras\/2/, `no se ha abierto la tierra: ${laDeLaTierra}`);

  // El asistente, abierto para corregir el apunte 7 desde la tierra (donde está el botón APUNTAR del menú).
  await pulsar(entorno, "cosa-corregir", { tipo: "tratamiento", id: "7" });
  assert.equal(laPantallaDeAhora(), "PantallaAsistente", "no se ha abierto el asistente");
  assert.equal(
    laDireccion(entorno),
    laDeLaTierra,
    "el asistente se ha llevado la dirección de la pantalla de la que salió",
  );

  // Y «lo he apuntado», que sale al guardar: la dirección sigue siendo la de la tierra, que es donde estaba
  // el agricultor cuando empezó a apuntar.
  await irHastaElResumen(entorno);
  await pulsar(entorno, "asistente-seguir");
  assert.equal(laPantallaDeAhora(), "PantallaHecho", "no ha salido la pantalla de «apuntado»");
  assert.equal(
    laDireccion(entorno),
    laDeLaTierra,
    "«lo he apuntado» se ha llevado la dirección de la pantalla de la que salió",
  );

  // El alta de un papel, desde la lista de papeles, y la de una factura desde la suya: los dos formularios
  // se rellenan a mano y al recargar saldrían vacíos, así que no tocan la dirección de su lista.
  await pulsar(entorno, "papel-ver-todos");
  const laDeLosPapeles = laDireccion(entorno);
  await pulsar(entorno, "papel-nuevo");
  assert.equal(laPantallaDeAhora(), "PantallaNuevoDocumento", "no se ha abierto el alta de un papel");
  assert.equal(
    laDireccion(entorno),
    laDeLosPapeles,
    "el alta de un papel se ha llevado la dirección de la lista",
  );

  await pulsar(entorno, "facturas-abrir");
  const laDeLasFacturas = laDireccion(entorno);
  await pulsar(entorno, "factura-nueva");
  assert.equal(laPantallaDeAhora(), "PantallaNuevaFactura", "no se ha abierto el alta de una factura");
  assert.equal(
    laDireccion(entorno),
    laDeLasFacturas,
    "el alta de una factura se ha llevado la dirección de la lista",
  );

  // Y la pantalla de entrar: un estado sin sesión no es una pantalla de la aplicación, así que la dirección
  // se queda donde estaba (al volver a entrar se sigue en lo que se estaba mirando).
  await pulsar(entorno, "salir");
  assert.equal(laPantallaDeAhora(), "PantallaEntrar", "no se ha abierto la pantalla de entrar");
  assert.equal(
    laDireccion(entorno),
    laDeLasFacturas,
    "la pantalla de entrar se ha llevado la dirección de la pantalla de la que salió",
  );
});

test("recargar en mitad de un apunte no inventa una ficha a medias", async () => {
  // Lo que pidió el encargo con estas palabras: «que se puede recargar en mitad de un asistente sin que el
  // programa invente una ficha a medias». Empieza en una tierra (su dirección), abre el asistente desde
  // ella y **recarga**: lo que tiene que salir es la tierra de la que salió, no un apunte a medias ni una
  // ficha inventada.
  const primera = await cargarAplicacion({}, { direccion: "#/tierras/2" });
  const laDeLaTierra = laDireccion(primera.entorno);
  assert.match(laDeLaTierra, /^#\/tierras\/2/, `no se ha abierto la tierra: ${laDeLaTierra}`);

  await pulsar(primera.entorno, "inicio", { ir: "echar_producto" });
  assert.equal(laPantallaDeAhora(), "PantallaAsistente", "no se ha abierto el asistente de apuntar");
  assert.equal(
    laDireccion(primera.entorno),
    laDeLaTierra,
    "el asistente ha cambiado la dirección: recargar aquí dejaría al agricultor en otro sitio",
  );

  // Recargar: se vuelve a arrancar con la dirección que quedó puesta.
  await cargarAplicacion({}, { direccion: laDireccion(primera.entorno) });
  assert.equal(
    laPantallaDeAhora(),
    "PantallaMisCosas",
    "recargar en mitad de un apunte no ha devuelto a la tierra de la que se salió",
  );
  assert.equal(
    tablaDeTierrasPedida().panel.elegida,
    true,
    "al recargar no se ha abierto la tierra, que es donde estaba el agricultor",
  );
  // Y no se ha inventado una ficha: no hay ni un apunte a medias apuntado en el cuaderno.
  assert.equal(montajes[montajes.length - 1].elemento.props.secciones[0].tabla.filas.length, 2);
});

// ---------------------------------------------------------------------------
// El libro del almacén (T09, 03/10/2026)
//
// POR QUÉ ESTAS PRUEBAS VIVEN AQUÍ Y NO EN `react.test.js`
//
// Las de `react.test.js` montan un componente suelto y miran su HTML. Lo que hay que comprobar aquí es
// otra cosa, y es justo la que no se ve en un componente: que **pulsando botones de verdad** (el
// manejador de clics de `document`, como en la aplicación) se llegue a donde tiene que llegarse, que a
// lo que se manda al servidor no le falte ni le sobre nada, que el mismo albarán **no entre dos veces**,
// que un dato que no se sabe no se convierta en un cero y que enganchar una factura **proponga y no
// escriba**. Es el mismo sitio y el mismo estilo que las pruebas del cuaderno y de las facturas.
//
// Los dos finales que se persiguen en cada camino son los de la casa: **sin cobertura** (lo que se puede
// apuntar se queda en el móvil y se manda solo) y **no lo he podido comprobar** (que no es «no» ni es
// «sí»). Por eso hay una prueba para cada uno.
// ---------------------------------------------------------------------------

/** Un movimiento del libro, como lo devuelve el servidor. */
function unMovimiento(cambios = {}) {
  return {
    id: 1,
    articulo_id: 3,
    articulo: "Glifosato 36 SL",
    lote_id: 8,
    numero_lote: "4471-A",
    tipo: "entrada",
    fecha: "2026-03-20",
    cantidad: 5,
    unidad: "L",
    origen_tipo: "recepcion",
    origen_id: 5,
    motivo: null,
    usuario_id: 1,
    anulado: false,
    motivo_anulacion: null,
    creado_en: "2026-03-20T18:00:00",
    cuenta: true,
    no_cuenta_porque: null,
    ...cambios,
  };
}

/** Un envase (un lote), con lo que queda y el desglose de sus movimientos. */
function unLote(cambios = {}) {
  return {
    lote_id: 8,
    numero_lote: "4471-A",
    fecha_caducidad: "2028-05-01",
    caducado: false,
    presentacion: "garrafa 5 L",
    contenido_por_envase: 5,
    ubicacion: "La nave",
    movimientos_del_lote: [unMovimiento()],
    entradas: 5,
    salidas: 0,
    mermas: 0,
    ajustes: 0,
    unidad: "L",
    movimientos: 1,
    sin_movimientos: false,
    saldo: 5,
    motivo_codigo: "",
    motivo: "",
    movimientos_sin_cantidad: 0,
    movimientos_sin_unidad: 0,
    unidades_que_no_cuadran: [],
    ...cambios,
  };
}

/**
 * Un artículo del almacén, con sus envases.
 *
 * `producto_id: 5` **no es un número al azar**: es el producto de `unTratamiento()` (el Glifosato 36 SL de
 * los datos de prueba), que es lo que engancha el artículo con el apunte cuando se saca de un envase.
 */
function unArticuloDelAlmacen(cambios = {}) {
  return {
    articulo_id: 3,
    nombre: "Glifosato 36 SL",
    categoria: "fitosanitario",
    unidad: "L",
    producto_id: 5,
    fertilizante_id: null,
    lotes: [unLote()],
    cuantos_lotes: 1,
    caducados: 0,
    sin_caducidad_apuntada: 0,
    con_caducidad_apuntada: 1,
    entradas: 5,
    salidas: 0,
    mermas: 0,
    ajustes: 0,
    movimientos: 1,
    sin_movimientos: false,
    saldo: 5,
    motivo_codigo: "",
    motivo: "",
    movimientos_sin_cantidad: 0,
    movimientos_sin_unidad: 0,
    unidades_que_no_cuadran: [],
    facturas_sin_recibir: 0,
    ...cambios,
  };
}

/** Lo que contesta `/api/almacen/existencias`. */
function unasExistencias(cambios = {}) {
  return {
    textos: {},
    articulos: [unArticuloDelAlmacen()],
    cuantos: 1,
    cuantos_con_existencias: 1,
    sin_poder_saber: 0,
    en_negativo: 0,
    caducados: 0,
    sin_caducidad_apuntada: 0,
    comprado_sin_entrar: [],
    resumen: "En el almacén llevas 1 cosa apuntada.",
    ...cambios,
  };
}

/** Un albarán como lo devuelve el servidor, con su línea y lo que metió en el almacén. */
function unaRecepcion(cambios = {}) {
  return {
    id: 5,
    fecha: "2026-03-20",
    proveedor: "Cooperativa Agrícola de Peñaranda",
    proveedor_nif: "B37333333",
    numero_albaran: "2026/0417",
    factura_id: null,
    notas: null,
    anulada: false,
    motivo_anulacion: null,
    creada_en: "2026-03-20T18:00:00",
    lineas: [
      {
        id: 31,
        articulo_id: 3,
        lote_id: 8,
        descripcion: null,
        cantidad: 5,
        unidad: "L",
        linea_factura_id: null,
        articulo: "Glifosato 36 SL",
        numero_lote: "4471-A",
        fecha_caducidad: "2028-05-01",
      },
    ],
    entradas: 1,
    ...cambios,
  };
}

/** Una factura de compra, como la devuelve `/api/facturas`. */
function unaFactura(cambios = {}) {
  return {
    id: 9,
    proveedor: "Cooperativa Agrícola de Peñaranda",
    proveedor_nif: "B37333333",
    numero_factura: "2026/00123",
    fecha: "2026-03-25",
    base_imponible: 100,
    cuota_iva: 21,
    total: 121,
    anulada: false,
    tiene_fichero: true,
    lineas: [
      {
        id: 41,
        descripcion: "Glifosato 36 SL",
        cantidad: 5,
        unidad: "L",
        precio: 20,
        importe: 100,
        producto_id: 5,
        fertilizante_id: null,
      },
    ],
    ...cambios,
  };
}

/** La aplicación con el almacén cargado: lo que hay, lo que ha llegado y lo que ha pasado. */
async function conElAlmacen(cambios = {}, extra = {}) {
  return cargarAplicacion(
    {
      // Las de leer van **sin el método delante** (`/api/…`), que es como las busca el servidor de
      // mentira: con `"GET /api/…"` una prueba que quisiera cambiar la lista tendría que saberse esa
      // forma, y la que se escribiera sin el método **no se aplicaría** (el servidor de mentira mira
      // primero la clave con método). Costó un rato encontrarlo.
      "/api/almacen/existencias": unasExistencias(),
      "/api/almacen/recepciones": [unaRecepcion()],
      "/api/almacen/recepciones/5": unaRecepcion(),
      "/api/almacen/movimientos": [unMovimiento()],
      "POST /api/almacen/recepciones": {
        recepcion: unaRecepcion(),
        ya_estaba: false,
        como_se_reconocio: "",
        avisos: [],
        textos: {},
      },
      "POST /api/almacen/movimientos": {
        movimiento: unMovimiento(),
        ya_estaba: false,
        avisos: [],
        textos: {},
      },
      ...cambios,
    },
    extra,
  );
}

/** Cuántas veces se ha llamado a una ruta con un método (`"POST /api/…"`). */
function cuantasVeces(servidor, metodoYRuta) {
  return servidor.llamadasConMetodo.filter((una) => una === metodoYRuta).length;
}

/**
 * Dónde está `textos.py`, calculado **una vez y sin `new URL`**.
 *
 * Las pruebas de la interfaz le meten a `globalThis.URL` un objeto de mentira (el del navegador, con
 * `createObjectURL`), así que `new URL(…)` **dentro de una prueba** revienta con «URL is not a
 * constructor». Se calcula al cargar el fichero, que es antes de que nadie lo sustituya.
 */
const LA_RUTA_DE_LOS_TEXTOS = path.join(
  path.dirname(fileURLToPath(import.meta.url)),
  "..",
  "app",
  "textos.py",
);

/** El texto de `textos.py`, con las cadenas partidas en varias líneas juntadas (para poder buscar frases). */
function elFicheroDeTextos() {
  return readFileSync(LA_RUTA_DE_LOS_TEXTOS, "utf8").replace(/"\s*\n\s*"/g, "");
}

/** Lo que se ha mandado en la primera llamada a una ruta, con su método. */
function loMandado(servidor, ruta, metodo = "POST") {
  return servidor.enviados.filter((uno) => uno.metodo === metodo && uno.ruta === ruta);
}

/** Rellena la primera línea de un albarán, como lo haría el agricultor con el teclado. */
function rellenarUnaLineaDelAlbaran(entorno, cambios = {}) {
  const valores = {
    articulo: "producto:5",
    nombre: "",
    cantidad: "5",
    unidad: "L",
    lote: "4471-A",
    caducidad: "2028-05-01",
    envase: "garrafa 5 L",
    contenido: "5",
    donde: "La nave",
    ...cambios,
  };
  // Los `id` son los del componente (`albaran-0-…`), que son los que lee la aplicación: si uno cambiara,
  // el albarán se guardaría con la línea vacía sin que salte nada.
  for (const [campo, valor] of Object.entries(valores)) {
    escribir(entorno, `albaran-0-${campo}`, valor);
  }
}

test("desde el almacén se llega al libro, y llega con lo que ha llegado, lo que queda y lo que ha pasado", async () => {
  const { entorno, servidor } = await conElAlmacen();
  // Se entra por donde entra el agricultor: «lo que tengo en el almacén» y, desde ahí, el libro.
  await pulsar(entorno, "cesta-ver");
  assert.equal(ultimoMontaje().type.name, "PantallaCesta", "no se ha abierto la cesta");
  await pulsar(entorno, "libro-ver");
  const elemento = ultimoMontaje();
  assert.equal(elemento.type.name, "PantallaLibroDelAlmacen", "el libro no se le pide a React");
  const props = elemento.props;

  // Los textos llegan (el título es el que sirve el servidor, no uno escrito en el componente).
  assert.equal(props.textos.cesta.libro_titulo, "El libro del almacén", "el libro sale sin su título");
  // Las tres preguntas del libro se piden al abrirlo: sin ellas, la pantalla sería un hueco.
  for (const ruta of [
    "/api/almacen/existencias",
    "/api/almacen/recepciones",
    "/api/almacen/movimientos",
  ]) {
    assert.ok(servidor.llamadas.includes(ruta), `el libro no ha pedido ${ruta}`);
  }
  // Lo que ha llegado, con su número, su fecha y lo que trajo.
  assert.equal(props.albaranes.length, 1, "no sale el albarán que ha llegado");
  assert.equal(props.albaranes[0].titulo, "Albarán 2026/0417", "el albarán no se llama por su número");
  assert.equal(props.albaranes[0].cuando, "20/03/2026");
  assert.equal(props.albaranes[0].proveedor, "Cooperativa Agrícola de Peñaranda");
  assert.equal(props.albaranes[0].detalle, "1 línea");
  assert.equal(props.resumen_albaranes, "Tienes 1 albarán apuntado.", "la cuenta sale en plural con uno solo");
  // Lo que queda, por artículo y por envase.
  assert.equal(props.articulos.length, 1);
  assert.equal(props.articulos[0].categoria, "Productos de tratamiento", "la clase no viene con su nombre");
  assert.equal(props.articulos[0].queda, "5,00 L");
  assert.equal(props.articulos[0].lotes[0].titulo, "Lote 4471-A");
  assert.equal(props.articulos[0].lotes[0].queda, "5,00 L", "el envase no dice lo que queda");
  // Y el libro: qué pasó, de qué era y de dónde viene.
  assert.equal(props.movimientos.length, 1);
  assert.match(props.movimientos[0].titulo, /^Entró · Glifosato 36 SL$/, props.movimientos[0].titulo);
  assert.match(props.movimientos[0].detalle, /5,00 L/, props.movimientos[0].detalle);
  assert.match(props.movimientos[0].detalle, /Entró con un albarán/, props.movimientos[0].detalle);
});

test("lo comprado que todavía no ha entrado se dice, para que nadie crea que se ha perdido", async () => {
  const { entorno } = await conElAlmacen({
    "GET /api/almacen/existencias": unasExistencias({
      comprado_sin_entrar: [
        { que_es: "producto", identificador: 12, nombre: "Cobre 50 WP", unidad: "kg", lineas: 2 },
      ],
    }),
  });
  await pulsar(entorno, "libro-ver");
  const props = ultimoMontaje().props;

  assert.equal(props.compras.hay, true, "hay compras sin albarán y no se dicen");
  assert.equal(
    props.compras.texto,
    "De esto tienes 1 compra apuntada en una factura pero no ha entrado nada al almacén: apunta el albarán cuando llegue y aquí saldrá la existencia.",
    "el aviso sale en plural con uno solo",
  );
  assert.equal(props.compras.filas[0].detalle, "Cobre 50 WP · 2 líneas");
  // **Y no se suma a lo que queda**: el artículo sigue diciendo sus cinco litros, que son los que han
  // entrado de verdad. Sumarlo contaría dos veces la misma compra (una por factura y otra por entrada).
  assert.equal(props.articulos[0].queda, "5,00 L", "lo comprado sin entrar se ha sumado a las existencias");
});

test("un saldo que no se sabe se dice como que no se sabe, y nunca como un cero", async () => {
  const elMotivo =
    "De este lote hay 1 movimiento sin la cantidad apuntada, así que no se puede saber lo que queda. Apunta cuánto era.";
  const sinSaber = unLote({
    saldo: null,
    movimientos_sin_cantidad: 1,
    motivo_codigo: "AL30_falta_la_cantidad",
    motivo: elMotivo,
    movimientos_del_lote: [unMovimiento({ cantidad: null })],
  });
  const { entorno } = await conElAlmacen({
    "GET /api/almacen/existencias": unasExistencias({
      articulos: [
        unArticuloDelAlmacen({
          lotes: [sinSaber],
          saldo: null,
          motivo: elMotivo,
          movimientos_sin_cantidad: 1,
        }),
      ],
    }),
  });
  await pulsar(entorno, "libro-ver");
  const props = ultimoMontaje().props;

  assert.equal(
    props.articulos[0].lotes[0].queda,
    "No se puede saber lo que queda",
    "un saldo que no se sabe no se dice con palabras",
  );
  assert.equal(props.articulos[0].queda, "No se puede saber lo que queda");
  // Y **con su motivo**, que es lo que hace que el agricultor sepa qué le falta por apuntar.
  assert.ok(
    props.articulos[0].lotes[0].avisos.includes(elMotivo),
    `el envase no dice por qué no se sabe: ${props.articulos[0].lotes[0].avisos.join(" | ")}`,
  );
  // Lo que no puede aparecer por ningún lado: un cero que parecería un dato.
  assert.ok(
    !JSON.stringify(props).includes("0,00 L"),
    "un saldo desconocido se ha pintado como un cero",
  );
});

test("las existencias llegan por envase, con su caducidad y el desglose de cada lote", async () => {
  const anulada = unMovimiento({
    id: 2,
    tipo: "salida",
    cantidad: 2,
    origen_tipo: "tratamiento",
    origen_id: 7,
    anulado: false,
    cuenta: false,
    no_cuenta_porque: "Ese apunte está anulado, así que no gastó nada.",
  });
  const { entorno } = await conElAlmacen({
    "GET /api/almacen/existencias": unasExistencias({
      articulos: [
        unArticuloDelAlmacen({
          lotes: [
            unLote({ movimientos_del_lote: [unMovimiento(), anulada], saldo: 3 }),
            // Un envase del que no se sabe ni el número ni la caducidad: las dos cosas se dicen, y la
            // caducidad que no se ha mirado **no** se cuenta como vigente.
            unLote({
              lote_id: 9,
              numero_lote: null,
              fecha_caducidad: null,
              caducado: null,
              presentacion: null,
              ubicacion: null,
              movimientos_del_lote: [],
              movimientos: 0,
              sin_movimientos: true,
              entradas: 0,
              saldo: 0,
            }),
          ],
        }),
      ],
    }),
  });
  await pulsar(entorno, "libro-ver");
  const lotes = ultimoMontaje().props.articulos[0].lotes;

  assert.equal(lotes[0].titulo, "Lote 4471-A");
  assert.equal(lotes[0].caducidad, "01/05/2028");
  assert.equal(lotes[0].estado.texto, "En fecha");
  assert.equal(lotes[0].queda, "3,00 L");
  // El desglose: los movimientos del envase, uno debajo de otro, y el que no cuenta **con su porqué**.
  assert.equal(lotes[0].movimientos.length, 2, "el envase no lleva el desglose de sus movimientos");
  assert.match(lotes[0].movimientos[0].texto, /^20\/03\/2026 · Entró · 5,00 L$/, lotes[0].movimientos[0].texto);
  assert.match(lotes[0].movimientos[1].texto, /Salió · 2,00 L/);
  assert.equal(lotes[0].movimientos[1].no_cuenta, "Ese apunte está anulado, así que no gastó nada.");
  // El envase sin número ni caducidad: se dice, y se explica por qué importa mirarlo.
  assert.equal(lotes[1].titulo, "Sin número de lote");
  assert.equal(lotes[1].caducidad, "No se sabe cuándo caduca");
  assert.equal(lotes[1].estado.texto, "No se sabe cuándo caduca", "una caducidad sin mirar se cuenta como vigente");
  assert.ok(
    lotes[1].avisos.some((aviso) => aviso.includes("no caduque")),
    `no se explica que la caducidad no se ha mirado: ${lotes[1].avisos.join(" | ")}`,
  );
  assert.ok(lotes[1].pista.includes("El envase no lo trae"), "no se explica por qué importa el número de lote");
});

test("apuntar un albarán con sus líneas, de punta a punta", async () => {
  const { entorno, servidor } = await conElAlmacen();
  await pulsar(entorno, "libro-ver");
  await pulsar(entorno, "albaran-nuevo");
  assert.equal(ultimoMontaje().type.name, "PantallaNuevoAlbaran", "el alta del albarán no se le pide a React");
  const form = ultimoMontaje().props;
  assert.ok(form.borrador.fecha, "el albarán no sale con la fecha de hoy puesta");
  assert.equal(form.borrador.lineas.length, 1, "no sale con una línea para empezar");
  assert.equal(form.opciones[0].texto, "No está en mi lista: lo que pone el papel");

  escribir(entorno, "albaran-proveedor", "Cooperativa Agrícola de Peñaranda");
  escribir(entorno, "albaran-numero", "2026/0417");
  // La fecha viene puesta con la de hoy (lo que ya sabe el programa no se pregunta): en un navegador de
  // verdad la casilla trae ese valor, así que aquí se pone antes de guardar.
  escribir(entorno, "albaran-fecha", form.borrador.fecha);
  rellenarUnaLineaDelAlbaran(entorno);
  // **Y añadir una línea no borra lo de la primera**: es la trampa de pintar sobre un formulario sin
  // leerlo antes (la misma que el fichero del cuaderno de la Junta).
  await pulsar(entorno, "albaran-linea-mas");
  const conDos = ultimoMontaje().props.borrador.lineas;
  assert.equal(conDos.length, 2, "no se ha añadido la línea");
  assert.equal(conDos[0].cantidad, "5", "añadir una línea ha borrado lo escrito en la primera");
  assert.equal(conDos[0].numero_lote, "4471-A");
  await pulsar(entorno, "albaran-linea-menos", { indice: 1 });
  assert.equal(ultimoMontaje().props.borrador.lineas.length, 1, "no se ha quitado la línea");

  await pulsar(entorno, "albaran-guardar");
  const mandados = loMandado(servidor, "/api/almacen/recepciones");
  assert.equal(mandados.length, 1, `se ha mandado el albarán ${mandados.length} veces`);
  const cuerpo = mandados[0].cuerpo;
  assert.equal(cuerpo.proveedor, "Cooperativa Agrícola de Peñaranda");
  assert.equal(cuerpo.numero_albaran, "2026/0417");
  assert.equal(cuerpo.fecha, form.borrador.fecha, "el albarán no viaja con su fecha");
  assert.ok(cuerpo.clave_de_reenvio, "el albarán no viaja con su clave de reenvío");
  assert.equal(cuerpo.lineas.length, 1);
  assert.equal(cuerpo.lineas[0].producto_id, 5, "la línea no dice qué producto es");
  assert.equal(cuerpo.lineas[0].cantidad, 5, "la cantidad no llega como número");
  assert.equal(cuerpo.lineas[0].unidad_de_la_cantidad, "L");
  assert.equal(cuerpo.lineas[0].numero_lote, "4471-A");
  assert.equal(cuerpo.lineas[0].fecha_caducidad, "2028-05-01");
  assert.equal(cuerpo.lineas[0].presentacion, "garrafa 5 L");
  assert.equal(cuerpo.lineas[0].ubicacion, "La nave");

  // Y se dice lo que ha pasado, con lo que significa: la mercancía ya está dentro.
  const pedida = ultimoMontaje();
  assert.equal(pedida.type.name, "Confirmacion", "no se confirma que el albarán esté apuntado");
  assert.equal(pedida.props.pregunta, "El albarán está apuntado.");
  assert.equal(
    pedida.props.pista,
    "La mercancía ya está en el almacén: lo que has apuntado es lo que ha entrado. Si algo no cuadra, anula el albarán y lo apuntas otra vez.",
  );
});

test("el mismo albarán se manda con la misma clave de reenvío las dos veces", async () => {
  // **Es la defensa contra el albarán que entra dos veces**, y por eso se pide la clave al abrir el
  // formulario y no al guardar: con dos claves distintas, dos pulsaciones del mismo botón (o el reenvío
  // del móvil sin cobertura) meterían la misma mercancía dos veces en el almacén.
  const { entorno, servidor } = await conElAlmacen({
    "POST /api/almacen/recepciones": falla({ detail: "No se ha podido apuntar el albarán." }),
  });
  await pulsar(entorno, "libro-ver");
  await pulsar(entorno, "albaran-nuevo");
  escribir(entorno, "albaran-proveedor", "Cooperativa Agrícola de Peñaranda");
  escribir(entorno, "albaran-numero", "2026/0417");
  rellenarUnaLineaDelAlbaran(entorno);

  await pulsar(entorno, "albaran-guardar");
  assert.equal(ultimoMontaje().type.name, "PantallaNuevoAlbaran", "el formulario se ha cerrado sin guardarse");
  assert.equal(
    ultimoMontaje().props.error,
    "No se ha podido apuntar el albarán.",
    "el motivo del servidor no llega al agricultor",
  );
  await pulsar(entorno, "albaran-guardar");

  const mandados = loMandado(servidor, "/api/almacen/recepciones");
  assert.equal(mandados.length, 2, "las dos pulsaciones no han mandado el albarán");
  assert.ok(mandados[0].cuerpo.clave_de_reenvio, "el albarán no lleva clave de reenvío");
  assert.equal(
    mandados[1].cuerpo.clave_de_reenvio,
    mandados[0].cuerpo.clave_de_reenvio,
    "las dos pulsaciones llevan claves distintas: el mismo albarán podría entrar dos veces",
  );
  // Y un albarán **nuevo** lleva una clave nueva: si no, el segundo albarán de la mañana se reconocería
  // como el primero y no entraría.
  await pulsar(entorno, "albaran-nuevo");
  rellenarUnaLineaDelAlbaran(entorno, { lote: "9999-B" });
  await pulsar(entorno, "albaran-guardar");
  const tercera = loMandado(servidor, "/api/almacen/recepciones")[2];
  assert.notEqual(
    tercera.cuerpo.clave_de_reenvio,
    mandados[0].cuerpo.clave_de_reenvio,
    "el segundo albarán viaja con la clave del primero: no se apuntaría",
  );
});

test("un albarán que ya estaba apuntado se dice, y no se cuenta dos veces", async () => {
  const yaEstaba =
    "Ese albarán ya lo tenías apuntado (el 20/03/2026). No se ha vuelto a apuntar, así que no se ha contado dos veces. Si el que había estaba mal, anúlalo y apunta este.";
  const { entorno } = await conElAlmacen({
    "POST /api/almacen/recepciones": {
      recepcion: unaRecepcion(),
      ya_estaba: true,
      como_se_reconocio: "numero_de_albaran",
      avisos: [yaEstaba],
      textos: {},
    },
  });
  await pulsar(entorno, "libro-ver");
  await pulsar(entorno, "albaran-nuevo");
  escribir(entorno, "albaran-proveedor", "Cooperativa Agrícola de Peñaranda");
  escribir(entorno, "albaran-numero", "2026/0417");
  rellenarUnaLineaDelAlbaran(entorno);
  await pulsar(entorno, "albaran-guardar");

  const pedida = ultimoMontaje();
  assert.equal(pedida.type.name, "Confirmacion");
  assert.equal(pedida.props.pregunta, "Ese albarán ya estaba apuntado");
  assert.equal(
    pedida.props.pista,
    "No se ha vuelto a apuntar, así que no se ha contado dos veces. Si el que había estaba mal, anúlalo y apunta este.",
  );
  assert.equal(pedida.props.avisos[0].texto, yaEstaba, "no se dice que el albarán ya estaba (ni cuándo)");
  // Y el libro sigue con **un solo** albarán: el reenvío no ha apuntado nada nuevo.
  await pulsar(entorno, "libro-ver");
  assert.equal(ultimoMontaje().props.albaranes.length, 1, "el reenvío ha apuntado el albarán dos veces");
});

test("un albarán apuntado sin cobertura se queda en el móvil y se manda solo", async () => {
  const { entorno, servidor } = await conElAlmacen();
  await pulsar(entorno, "libro-ver");
  await pulsar(entorno, "albaran-nuevo");
  escribir(entorno, "albaran-proveedor", "Cooperativa Agrícola de Peñaranda");
  rellenarUnaLineaDelAlbaran(entorno);

  entorno.navigator.onLine = false;
  await pulsar(entorno, "albaran-guardar");
  assert.equal(
    cuantasVeces(servidor, "POST /api/almacen/recepciones"),
    0,
    "sin cobertura se ha intentado mandar el albarán por la red",
  );
  // Lo apuntado se queda en el móvil, con su clave de reenvío: eso es lo que hará que, cuando se mande
  // solo, el servidor no lo cuente dos veces.
  const cola = JSON.parse(entorno.window.localStorage.getItem("cuedigital.pendientes") || "[]");
  assert.equal(cola.length, 1, "el albarán sin cobertura no se ha guardado en el móvil");
  assert.equal(cola[0].ruta, "/api/almacen/recepciones");
  assert.ok(cola[0].datos.clave_de_reenvio, "lo que se guarda en el móvil no lleva su clave de reenvío");
  assert.equal(cola[0].datos.lineas.length, 1);
  // Y se dice sin alarma, diciendo lo que pasa.
  const pedida = ultimoMontaje();
  assert.equal(pedida.type.name, "Confirmacion");
  assert.equal(pedida.props.pregunta, "El albarán se ha quedado apuntado en el móvil.");
  assert.equal(pedida.props.pista, "No hay cobertura.");
  // **Y un aviso que solo se puede dar aquí**: este albarán no lleva número, así que cuando se apunte
  // de verdad no se podrá comprobar si ya estaba. Sin cobertura ese aviso no llega del servidor, así que
  // se dice ahora: es la misma verdad, dicha antes.
  assert.equal(
    pedida.props.avisos[0].texto,
    "Como este albarán no lleva número (o no dice de quién es), no se ha podido comprobar si ya estaba apuntado. Míralo en la lista y anula el que sobre.",
  );
});

test("un albarán sin número dice que no se ha podido comprobar si ya estaba", async () => {
  const noSePudo =
    "Como este albarán no lleva número (o no dice de quién es), no se ha podido comprobar si ya estaba apuntado. Míralo en la lista y anula el que sobre.";
  const { entorno, servidor } = await conElAlmacen({
    // El albarán sin número: ni en el que se acaba de apuntar ni en la lista, que es lo que el agricultor
    // mira después para comprobar qué quedó dentro.
    "/api/almacen/recepciones": [unaRecepcion({ numero_albaran: null })],
    "POST /api/almacen/recepciones": {
      recepcion: unaRecepcion({ numero_albaran: null }),
      ya_estaba: false,
      como_se_reconocio: "",
      avisos: [noSePudo],
      textos: {},
    },
  });
  await pulsar(entorno, "libro-ver");
  await pulsar(entorno, "albaran-nuevo");
  escribir(entorno, "albaran-proveedor", "Cooperativa Agrícola de Peñaranda");
  rellenarUnaLineaDelAlbaran(entorno);
  await pulsar(entorno, "albaran-guardar");

  // **«No lo he podido comprobar» no es «no estaba»**: el albarán se apunta (llegó mercancía, y eso es un
  // hecho), y el aviso se dice entero para que nadie crea que el programa lo ha mirado.
  const pedida = ultimoMontaje();
  assert.equal(pedida.props.avisos[0].texto, noSePudo, "no se dice que no se ha podido comprobar");
  assert.equal(pedida.props.pregunta, "El albarán está apuntado.");
  // Y en la lista, ese albarán sin número se llama por lo que es y lo explica.
  await pulsar(entorno, "libro-ver");
  const albaranes = ultimoMontaje().props.albaranes;
  assert.equal(albaranes[0].titulo, "Un albarán sin número", "un albarán sin número se llama por su número");
  assert.equal(albaranes[0].aviso, "Sin número no se puede comprobar si ya estaba apuntado");
});

test("una línea sin decir qué ha llegado no se manda: se dice cuál falta", async () => {
  const { entorno, servidor } = await conElAlmacen();
  await pulsar(entorno, "libro-ver");
  await pulsar(entorno, "albaran-nuevo");

  // Sin ninguna línea rellena: se dice con la frase del servidor y **no se manda nada** (mandarlo sería
  // gastar cobertura del agricultor para que el servidor conteste lo mismo).
  await pulsar(entorno, "albaran-guardar");
  assert.equal(cuantasVeces(servidor, "POST /api/almacen/recepciones"), 0, "se ha mandado un albarán vacío");
  assert.equal(
    ultimoMontaje().props.error,
    "Un albarán sin decir qué venía no apunta nada. Escribe al menos una cosa: qué producto, cuánto y de qué lote.",
  );

  // Y con una línea rellena y otra que no dice nada, se dice **cuál** es la que falta.
  rellenarUnaLineaDelAlbaran(entorno);
  await pulsar(entorno, "albaran-linea-mas");
  await pulsar(entorno, "albaran-guardar");
  assert.equal(cuantasVeces(servidor, "POST /api/almacen/recepciones"), 0, "se ha mandado una línea vacía");
  assert.equal(
    ultimoMontaje().props.error,
    "En esa línea no dices qué ha llegado. Elige el producto o el abono de tu lista, o escribe su nombre tal y como sale en el albarán.",
  );
});

test("una línea sin unidad se manda como que no se sabe, no como un cero", async () => {
  // El papel sin la unidad es «no se sabe en qué se mide», y el almacén dirá que no puede hacer la
  // cuenta. Lo que no puede pasar es que se rellene con una unidad supuesta: partiría la cuenta del
  // envase en dos, para siempre.
  const { entorno, servidor } = await conElAlmacen();
  await pulsar(entorno, "libro-ver");
  await pulsar(entorno, "albaran-nuevo");
  escribir(entorno, "albaran-proveedor", "Cooperativa Agrícola de Peñaranda");
  rellenarUnaLineaDelAlbaran(entorno, {
    articulo: "",
    nombre: "Cobre 50 WP",
    unidad: "",
    cantidad: "",
    lote: "",
    caducidad: "",
    envase: "",
    contenido: "",
    donde: "",
  });
  await pulsar(entorno, "albaran-guardar");
  const cuerpo = loMandado(servidor, "/api/almacen/recepciones")[0].cuerpo;
  assert.equal(cuerpo.lineas[0].nombre, "Cobre 50 WP", "la línea escrita a mano no dice su nombre");
  assert.equal(cuerpo.lineas[0].producto_id, undefined, "una línea escrita a mano no puede llevar producto");
  // Vacío es «no se sabe», y viaja como vacío: ni «L» ni «0».
  assert.equal(cuerpo.lineas[0].cantidad, null, "una cantidad que no pone el papel no puede ser un cero");
  assert.equal(cuerpo.lineas[0].unidad_de_la_cantidad, null);
  assert.equal(cuerpo.lineas[0].numero_lote, null);
  assert.equal(cuerpo.lineas[0].fecha_caducidad, null);
});

test("la merma pide el motivo antes de apuntar nada", async () => {
  const { entorno, servidor } = await conElAlmacen();
  await pulsar(entorno, "libro-ver");
  await pulsar(entorno, "movimiento-nuevo", { tipo: "merma", articulo: 3 });
  assert.equal(
    ultimoMontaje().type.name,
    "PantallaMovimientoDeAlmacen",
    "el formulario del movimiento no se le pide a React",
  );
  assert.equal(ultimoMontaje().props.borrador.titulo, "Apuntar que se ha perdido");

  // El artículo sale ya elegido (es el que se ha tocado en el libro): en un navegador de verdad la lista
  // trae ese valor puesto, así que aquí se pone antes de guardar.
  escribir(entorno, "movimiento-articulo", "3");
  escribir(entorno, "movimiento-cantidad", "1");
  escribir(entorno, "movimiento-unidad", "L");
  await pulsar(entorno, "movimiento-guardar");
  // **El motivo es lo único que explica una merma**: sin documento detrás, dentro de dos años nadie sabría
  // por qué faltan diez litros. Y no se manda nada hasta que esté.
  assert.equal(cuantasVeces(servidor, "POST /api/almacen/movimientos"), 0, "se ha apuntado una merma sin motivo");
  assert.equal(
    ultimoMontaje().props.error,
    "Aquí no hay ningún papel que explique esto, así que lo tiene que explicar quien lo apunta. Escribe en dos palabras qué ha pasado: se rompió, se contó distinto, me lo trajo un vecino…",
  );

  escribir(entorno, "movimiento-motivo", "Se rompió el envase");
  await pulsar(entorno, "movimiento-guardar");
  const cuerpo = loMandado(servidor, "/api/almacen/movimientos")[0].cuerpo;
  assert.equal(cuerpo.tipo, "merma");
  assert.equal(cuerpo.motivo, "Se rompió el envase");
  assert.equal(cuerpo.cantidad, 1, "la cantidad no llega como número");
  assert.equal(cuerpo.unidad, "L");
  assert.equal(cuerpo.articulo_id, 3);
  assert.ok(cuerpo.clave_de_reenvio, "el movimiento no viaja con su clave de reenvío");
  assert.equal(ultimoMontaje().props.pregunta, "Apuntado en el libro del almacén.");
});

test("una cantidad sin unidad no se resta a ciegas: se dice y no se hace la cuenta", async () => {
  const { entorno, servidor } = await conElAlmacen();
  await pulsar(entorno, "libro-ver");
  await pulsar(entorno, "movimiento-nuevo", { tipo: "ajuste", articulo: 3 });
  escribir(entorno, "movimiento-articulo", "3");
  escribir(entorno, "movimiento-cantidad", "-2");
  escribir(entorno, "movimiento-motivo", "Al contar había menos");
  await pulsar(entorno, "movimiento-guardar");
  assert.equal(cuantasVeces(servidor, "POST /api/almacen/movimientos"), 0, "se ha apuntado sin decir en qué se mide");
  assert.equal(
    ultimoMontaje().props.error,
    "Falta decir en qué se mide esa cantidad. Sin eso no se puede restar de lo que hay en el almacén: pon litros, kilos o unidades.",
  );

  // Y un ajuste sin diferencia tampoco: si sale cero, es que cuadra y no hay nada que apuntar.
  escribir(entorno, "movimiento-unidad", "L");
  escribir(entorno, "movimiento-cantidad", "0");
  await pulsar(entorno, "movimiento-guardar");
  assert.equal(cuantasVeces(servidor, "POST /api/almacen/movimientos"), 0, "se ha apuntado un ajuste de cero");
  assert.equal(
    ultimoMontaje().props.error,
    "Un conteo distinto se apunta con lo que sobra o lo que falta. Di cuánto: si hay de más, en positivo, y si hay de menos, en negativo. Si sale cero, es que cuadra y no hay nada que apuntar.",
  );
  // Con la diferencia y su unidad, sí: y la diferencia negativa viaja en negativo.
  escribir(entorno, "movimiento-cantidad", "-2");
  await pulsar(entorno, "movimiento-guardar");
  const cuerpo = loMandado(servidor, "/api/almacen/movimientos")[0].cuerpo;
  assert.equal(cuerpo.cantidad, -2, "la diferencia del conteo no viaja en negativo");
});

test("sacar de un envase desde el apunte: la cantidad la dice el apunte y salen las dos cuentas con su nombre", async () => {
  const { entorno, servidor } = await conElAlmacen({
    "/api/tratamientos": [
      unTratamiento({ ...DENTRO_DE_LA_TIERRA, cantidad_total: 2, unidad_cantidad_aplicada: "L", dosis: 0.82 }),
    ],
    "POST /api/almacen/salidas": {
      movimiento: unMovimiento({ id: 4, tipo: "salida", cantidad: 2, origen_tipo: "tratamiento", origen_id: 7 }),
      ya_estaba: false,
      avisos: [],
      cantidad_total_gastada: 2,
      unidad_de_la_cantidad: "L",
      dosis_por_hectarea: 0.82,
      superficie_ha: 2.43,
      textos: {},
    },
  });
  // **El botón vive donde vive el apunte**, que es lo que pide el encargo: una salida del almacén sale de
  // un trabajo, y el trabajo es el que sabe cuánto se gastó.
  await pulsar(entorno, "inicio", { ir: "mi_cuaderno" });
  const fila = ultimoCuadernoPedido().apuntes.filas.find((una) => una.tipo === "tratamiento");
  const boton = fila.acciones.find((una) => una.accion === "salida-de-un-lote");
  assert.ok(boton, "el apunte del cuaderno no ofrece sacar del almacén");
  assert.equal(boton.etiqueta, "SACAR DE UN LOTE");
  await pulsar(entorno, "salida-de-un-lote", boton.datos);

  const pantalla = ultimoMontaje();
  assert.equal(pantalla.type.name, "PantallaSacarDeUnLote", "la pantalla de sacar no se le pide a React");
  assert.equal(pantalla.props.articulos.length, 1, "no salen los envases de ese producto");
  assert.equal(pantalla.props.articulos[0].lotes[0].titulo, "Lote 4471-A");
  assert.equal(pantalla.props.articulos[0].lotes[0].queda, "5,00 L");

  await pulsar(entorno, "salida-guardar", { lote: 8 });
  const cuerpo = loMandado(servidor, "/api/almacen/salidas")[0].cuerpo;
  assert.equal(cuerpo.apunte_tipo, "tratamiento");
  assert.equal(cuerpo.apunte_id, 7);
  assert.equal(cuerpo.lote_id, 8);
  assert.ok(cuerpo.clave_de_reenvio, "la salida no viaja con su clave de reenvío");
  // **La cantidad no se teclea**: la dice el apunte. Si la pantalla la mandara por su cuenta, un día
  // dirían cosas distintas el apunte y el almacén.
  assert.equal("cantidad" in cuerpo, false, "la pantalla manda la cantidad cuando la dice el apunte");

  // Y las dos cuentas salen **cada una con su nombre**, que es lo que evita el error de diez veces.
  const props = ultimoMontaje().props;
  assert.equal(props.resultado.total, "2,00 L");
  const etiquetas = props.resultado.filas.map((fila) => fila.etiqueta);
  assert.deepEqual(etiquetas, ["Cuánto por hectárea", "Hectáreas del apunte"], "las dos cuentas no van con su nombre");
  assert.equal(props.resultado.filas[0].valor, "0,82 L/ha");
  assert.equal(props.resultado.filas[1].valor, "2,43 ha");
  assert.equal(props.textos.cesta.libro_salida_total, "Lo que se ha sacado del envase");
});

test("el apunte que solo trae lo de cada hectárea pide el total en vez de multiplicarlo", async () => {
  // **La confusión de diez veces**: dos litros por hectárea no son dos litros gastados. Cuando el apunte
  // solo trae la dosis, el programa pide el total; no lo multiplica por la superficie por su cuenta.
  const { entorno, servidor } = await conElAlmacen({
    "/api/tratamientos": [
      unTratamiento({
        ...DENTRO_DE_LA_TIERRA,
        cantidad_total: null,
        unidad_cantidad_aplicada: null,
        dosis: 0.8,
      }),
    ],
    "POST /api/almacen/salidas": {
      movimiento: unMovimiento({ id: 4, tipo: "salida", cantidad: 2.5, origen_tipo: "tratamiento", origen_id: 7 }),
      ya_estaba: false,
      avisos: [],
      cantidad_total_gastada: 2.5,
      unidad_de_la_cantidad: "L",
      dosis_por_hectarea: 0.8,
      superficie_ha: 2.43,
      textos: {},
    },
  });
  await pulsar(entorno, "inicio", { ir: "mi_cuaderno" });
  await pulsar(entorno, "salida-de-un-lote", { tipo: "tratamiento", id: 7 });
  await pulsar(entorno, "salida-guardar", { lote: 8 });

  assert.equal(
    cuantasVeces(servidor, "POST /api/almacen/salidas"),
    0,
    "se ha llamado al servidor sin saber el total que se gastó",
  );
  const props = ultimoMontaje().props;
  assert.equal(props.pidiendo_cantidad, 8, "no se pide el total ni se dice de qué envase era");
  assert.equal(
    props.error,
    "Ese apunte solo tiene la dosis por hectárea, y eso no es lo que se gastó: la dosis es lo que se echa en cada hectárea. Escribe cuánto has sacado del lote en total, o completa el apunte con la cantidad total.",
  );
  // Se escribe el total (con coma, como se escribe en castellano) y se manda.
  escribir(entorno, "salida-cantidad", "2,5");
  await pulsar(entorno, "salida-guardar", { lote: 8 });
  const cuerpo = loMandado(servidor, "/api/almacen/salidas")[0].cuerpo;
  assert.equal(cuerpo.cantidad, 2.5, "el total escrito a mano no llega bien");
});

test("si lo que sale deja el envase en negativo, se avisa y hay que decir que la diferencia es de verdad", async () => {
  const aviso =
    "De este lote quedan 3,00 L y vas a sacar 5,00 L. Puedes corregir la cantidad, apuntar la entrada que falta, o marcar que la diferencia es de verdad y seguir: lo que no se hace es apuntarlo a escondidas.";
  const { entorno, servidor } = await conElAlmacen({
    "/api/tratamientos": [
      unTratamiento({ ...DENTRO_DE_LA_TIERRA, cantidad_total: 5, unidad_cantidad_aplicada: "L" }),
    ],
    "POST /api/almacen/salidas": falla({ detail: aviso }, 409),
  });
  await pulsar(entorno, "inicio", { ir: "mi_cuaderno" });
  await pulsar(entorno, "salida-de-un-lote", { tipo: "tratamiento", id: 7 });
  await pulsar(entorno, "salida-guardar", { lote: 8 });

  const props = ultimoMontaje().props;
  assert.equal(props.descuadre, aviso, "no se avisa de lo que queda y de lo que se saca");
  assert.equal(props.lote_del_descuadre, 8, "no se sabe de qué envase era el descuadre");
  // Y el agricultor decide: se pulsa «sí, la diferencia es de verdad» y **eso viaja** al servidor.
  await pulsar(entorno, "salida-descuadre-si", { lote: 8 });
  const cuerpo = loMandado(servidor, "/api/almacen/salidas")[1].cuerpo;
  assert.equal(cuerpo.aceptar_descuadre, true, "no se ha dicho al servidor que la diferencia es de verdad");
  assert.equal(cuerpo.lote_id, 8);
});

test("enganchar la factura propone y no escribe: solo se engancha cuando el agricultor dice que sí", async () => {
  const { entorno, servidor } = await conElAlmacen({
    "/api/facturas": [unaFactura()],
    "GET /api/almacen/facturas/9/posibles-recepciones": {
      factura_id: 9,
      ya_enganchadas: [],
      propuestas: [
        {
          recepcion_id: 5,
          numero_albaran: "2026/0417",
          fecha: "2026-03-20",
          proveedor: "Cooperativa Agrícola de Peñaranda",
          lineas_casadas: [
            { linea_de_recepcion_id: 31, linea_de_factura_id: 41, como: "es el mismo producto" },
          ],
          como_se_propone: "por el proveedor",
        },
      ],
      textos: {},
    },
    "GET /api/almacen/recepciones/5": unaRecepcion(),
    "POST /api/almacen/recepciones/5/factura": unaRecepcion({ factura_id: 9 }),
  });
  const elEnganche = "POST /api/almacen/recepciones/5/factura";

  await pulsar(entorno, "libro-ver");
  await pulsar(entorno, "albaran-abrir", { id: 5 });
  assert.equal(ultimoMontaje().type.name, "PantallaRecepcion", "la ficha del albarán no se le pide a React");
  assert.equal(ultimoMontaje().props.factura.hay, false, "un albarán sin factura dice que la tiene");
  assert.equal(ultimoMontaje().props.recepcion.titulo, "Albarán 2026/0417");
  assert.equal(ultimoMontaje().props.recepcion.lineas[0].lote, "4471-A");

  // 1. Abrir la pantalla de enganchar **no escribe nada**.
  await pulsar(entorno, "factura-enganchar", { id: 5 });
  assert.equal(ultimoMontaje().type.name, "PantallaEngancharLaFactura");
  assert.equal(cuantasVeces(servidor, elEnganche), 0, "abrir la pantalla ya ha enganchado la factura");

  // 2. Elegir la factura **tampoco**: solo pregunta al servidor si puede ser la de este albarán.
  await pulsar(entorno, "factura-proponer", { id: 9 });
  assert.equal(cuantasVeces(servidor, "GET /api/almacen/facturas/9/posibles-recepciones"), 1);
  assert.equal(cuantasVeces(servidor, elEnganche), 0, "elegir la factura ya ha enganchado algo");
  const eleccion = ultimoMontaje().props.eleccion;
  assert.equal(eleccion.propuesta, true, "no se enseña la propuesta del servidor");
  assert.equal(eleccion.como, "por el proveedor", "no se dice por qué se propone");
  assert.equal(
    eleccion.lineas[0].texto,
    "Glifosato 36 SL · Glifosato 36 SL · es el mismo producto",
    "no se enseñan las líneas que se casan",
  );
  assert.equal(
    ultimoMontaje().props.textos.cesta.libro_factura_propuesta,
    "El programa cree que esta factura es la de este albarán. Míralo y dilo tú: todavía no está apuntado nada.",
    "la pantalla no dice que la propuesta todavía no está apuntada",
  );

  // 3. Y solo cuando el agricultor dice que sí se engancha: sin cantidades y con las líneas casadas.
  await pulsar(entorno, "factura-enganchar-si", { id: 9 });
  const mandados = loMandado(servidor, "/api/almacen/recepciones/5/factura");
  assert.equal(mandados.length, 1, "el enganche no se ha mandado");
  assert.deepEqual(mandados[0].cuerpo, {
    factura_id: 9,
    lineas: [{ linea_de_recepcion_id: 31, linea_de_factura_id: 41 }],
  });
  // **Ni una cantidad**: la mercancía entró una vez, el día del albarán. Si este enganche metiera
  // cantidades, el almacén contaría la misma compra dos veces.
  assert.equal(
    JSON.stringify(mandados[0].cuerpo).includes("cantidad"),
    false,
    "el enganche de la factura lleva cantidades",
  );
  // Y el albarán queda diciendo de qué factura es, con el aviso del servidor sobre lo que eso significa.
  assert.equal(ultimoMontaje().type.name, "PantallaRecepcion");
  assert.equal(ultimoMontaje().props.factura.hay, true, "el albarán no queda con su factura");
  assert.equal(
    ultimoMontaje().props.textos.cesta.libro_factura_enganchada,
    "Esta factura ya está enganchada a su albarán. La mercancía no se cuenta otra vez: entró una vez, el día que llegó.",
  );
});

test("las cuentas de un artículo solo se enseñan cuando se pueden sumar enteras", async () => {
  // **Un «Entró 0,00» con una entrada de la que no se sabe la cantidad parecería que no entró nada.** Lo
  // que el servidor devuelve en `entradas` es la suma **de las que tienen cantidad**, así que cuando hay
  // alguna sin ella la cuenta es solo de una parte y se calla: lo que se enseña es el motivo, que es la
  // verdad. Se vio en la captura del libro con un albarán que traía una línea sin cantidad.
  const elMotivo =
    "De este lote hay 1 movimiento sin la cantidad apuntada, así que no se puede saber lo que queda. Apunta cuánto era.";
  const { entorno } = await conElAlmacen({
    "/api/almacen/existencias": unasExistencias({
      articulos: [
        unArticuloDelAlmacen({
          lotes: [unLote({ saldo: null, motivo: elMotivo, movimientos_sin_cantidad: 1 })],
          saldo: null,
          motivo: elMotivo,
          movimientos_sin_cantidad: 1,
          entradas: 0,
        }),
      ],
    }),
  });
  await pulsar(entorno, "libro-ver");
  const articulo = ultimoMontaje().props.articulos[0];

  assert.deepEqual(
    articulo.filas.map((fila) => fila.etiqueta),
    [],
    "se enseñan cuentas que solo son de una parte de lo que hay",
  );
  assert.equal(articulo.queda, "No se puede saber lo que queda");
  assert.equal(articulo.motivo, elMotivo);

  // Y cuando todo tiene cantidad y unidad, **sí** se enseñan: es lo que explica el saldo.
  const { entorno: otro } = await conElAlmacen();
  await pulsar(otro, "libro-ver");
  const conCuentas = ultimoMontaje().props.articulos[0];
  assert.deepEqual(
    conCuentas.filas.map((fila) => fila.etiqueta),
    ["Entró"],
    "un artículo con su cuenta entera no enseña lo que entró",
  );
  assert.equal(conCuentas.filas[0].valor, "5,00 L");
});

test("el libro y la ficha de un albarán tienen su dirección, y recargar las abre", async () => {
  const primera = await conElAlmacen({}, { direccion: "#/almacen/libro" });
  assert.equal(
    laPantallaDeAhora(),
    "PantallaLibroDelAlmacen",
    "la dirección del libro de almacén no lo ha abierto",
  );
  assert.match(laDireccion(primera.entorno), /^#\/almacen\/libro/, laDireccion(primera.entorno));

  await pulsar(primera.entorno, "albaran-abrir", { id: 5 });
  const laDelAlbaran = laDireccion(primera.entorno);
  assert.match(laDelAlbaran, /^#\/almacen\/recepcion\/5/, `la dirección no es la del albarán: ${laDelAlbaran}`);
  // Recargar: se vuelve a arrancar con la dirección que quedó puesta.
  await conElAlmacen({ "GET /api/almacen/recepciones/5": unaRecepcion() }, { direccion: laDelAlbaran });
  assert.equal(laPantallaDeAhora(), "PantallaRecepcion", "recargar no vuelve a abrir el albarán");
  assert.equal(ultimoMontaje().props.recepcion.titulo, "Albarán 2026/0417");

  // Un albarán que no es suyo: se dice, y **no se cambia la dirección sola** (ponerla en la de casa daría
  // a entender que el agricultor está donde no está).
  const tercera = await conElAlmacen({}, { direccion: "#/almacen/recepcion/99" });
  assert.equal(
    tercera.entorno.window.location.hash,
    "#/almacen/recepcion/99",
    "la dirección equivocada se ha cambiado sola por la de casa",
  );
  assert.equal(laPantallaDeAhora(), "Confirmacion", "un albarán que no existe no lleva a ninguna pantalla");
});

test("la copia de los textos del almacén dice lo mismo que el servidor", () => {
  // **La copia que se queda vieja deja la prueba pasando en blanco**: comprobaría una pantalla que el
  // agricultor no tiene. Esto se comprueba leyendo `textos.py`, que es lo que el servidor sirve de verdad.
  //
  // Los textos largos de `textos.py` están escritos en varias líneas (cadenas pegadas: `"una parte "` y
  // `"la otra"`), así que se juntan antes de comparar: si no, **todas las frases largas** darían un falso
  // suspenso diciendo que la copia está vieja cuando está bien.
  const fuente = elFicheroDeTextos();
  const copia = RESPUESTAS["/api/interfaz"].cesta;
  const mias = Object.entries(copia).filter(([clave]) => clave.startsWith("libro_"));
  assert.ok(mias.length > 100, `la copia solo tiene ${mias.length} textos del almacén: ¿se han perdido?`);

  const cambiados = mias.filter(([, valor]) => !fuente.includes(valor)).map(([clave]) => clave);
  assert.deepEqual(
    cambiados,
    [],
    `estos textos de la copia ya no dicen lo que dice el servidor: ${cambiados.join(", ")}`,
  );
  const inventados = mias.filter(([clave]) => !fuente.includes(`"${clave}":`)).map(([clave]) => clave);
  assert.deepEqual(
    inventados,
    [],
    `estas claves de la copia no están en textos.py: ${inventados.join(", ")}`,
  );

  // Y al revés: **ningún texto del servidor se queda sin copia**, o las pruebas lo pintarían en blanco.
  const enElServidor = [...fuente.matchAll(/^\s+"(libro_[a-z_0-9]+)":/gm)].map((encontrado) => encontrado[1]);
  assert.ok(
    enElServidor.length > 100,
    `solo se han encontrado ${enElServidor.length} claves del almacén en textos.py: el lector se ha roto`,
  );
  const sinCopia = enElServidor.filter((clave) => !(clave in copia));
  assert.deepEqual(
    sinCopia,
    [],
    `estos textos del servidor no están en la copia de las pruebas, así que las pruebas los pintarían en blanco: ${sinCopia.join(", ")}`,
  );
});

test("el lector de la copia de textos del almacén funciona (si no, la prueba de arriba pasaría sin comprobar nada)", () => {
  const fuente = elFicheroDeTextos();
  assert.ok(fuente.includes('"libro_titulo":'), "el lector no encuentra una clave que sí está en textos.py");
  assert.ok(!fuente.includes("Un texto que no está en textos.py"), "el lector da por bueno cualquier texto");
  // Y el juntador de cadenas tampoco se pasa de listo: una frase que está partida en dos líneas se
  // encuentra entera, y una que no está, no.
  assert.ok(
    fuente.includes("Lo que mete mercancía en el almacén es el albarán, no la factura."),
    "el juntador de cadenas no encuentra una frase larga que sí está en textos.py",
  );
  assert.ok(!fuente.includes("Lo que mete mercancía en el almacén es la factura"));
});

// ---------------------------------------------------------------------------
// T06 (03/10/2026): las tierras en el mapa y en la tabla, y lo que ha sido una tierra
//
// **Qué se comprueba aquí y qué no.** Lo que se mira en el componente (los filtros, el grupo «sin
// forma», la selección múltiple, el vínculo fila ↔ polígono, los cuatro estados de la comparación y
// el ensayo) está en `tests_js/tierras_y_versiones.test.js`, que es donde se puede leer el HTML que
// dibuja React. Aquí se comprueba **el cableado**, que es lo que solo se ve desde `app.js`: que la
// dirección abra la pantalla, que el toque en un trozo enfoque su fila, y —esto es lo que más
// importa— que **ensayar no escriba**: que el camino del ensayo no tenga ninguna forma de mandar el
// lote a la ruta que guarda.
// ---------------------------------------------------------------------------

/** Los textos de T06, tal y como los sirve `/api/parcelas/vista` (recortados a lo que se usa). */
const TEXTOS_DE_T06 = {
  titulo: "Mis tierras, en el mapa y en la tabla",
  explica: "Aquí están todas tus tierras a la vez.",
  buscar: "Buscar por su nombre o por su referencia del SIGPAC",
  buscar_boton: "BUSCAR",
  filtros_titulo: "Filtros",
  filtro_cultivo: "Qué tienen sembrado",
  filtro_municipio: "El pueblo",
  filtro_revision: "Si lo has revisado",
  filtro_pac: "Lo que puedes declarar",
  filtro_todas: "TODAS",
  quitar_filtros: "QUITAR LOS FILTROS",
  agrupar_titulo: "Agrupar la lista",
  agrupar_no: "Sin agrupar",
  agrupar_cultivo: "Por lo que tienen sembrado",
  agrupar_municipio: "Por pueblo",
  agrupar_forma: "Por si se les ha medido la forma",
  grupo_con_forma: "Con su forma medida",
  grupo_sin_forma: "Sin forma",
  sin_forma: "SIN FORMA",
  con_forma: "Medida",
  sin_cultivo: "Sin decir qué tiene",
  sin_hectareas: "Sin hectáreas dichas",
  sin_pueblo: "Sin pueblo dicho",
  revision_sin_version: "Sin ninguna versión de este año",
  col_marcar: "Marcar",
  marcar_todas: "MARCAR LAS QUE SE VEN",
  desmarcar_todas: "QUITAR LA SELECCIÓN",
  marcadas_uno: "Has marcado 1 tierra",
  marcadas_varios: "Has marcado {cuantas} tierras",
  ninguna_marcada: "No has marcado ninguna tierra.",
  marcar_esta: "Marcar esta tierra",
  col_numero: "N.º",
  col_nombre: "Nombre",
  col_referencia: "Referencia SIGPAC",
  col_hectareas: "Hectáreas",
  col_cultivo: "Qué tiene este año",
  col_pueblo: "Pueblo",
  col_revision: "Revisión",
  col_forma: "Forma",
  col_acciones: "Acciones",
  tabla_etiqueta: "Tus tierras",
  ver_versiones: "VER LO QUE HA SIDO",
  abrir_en_el_mapa: "VERLA EN EL MAPA",
  pie_filtrado: "Ves {cuantas} de {total} tierras",
  pie_todas: "{cuantas} tierras",
  pie_sin_forma: "Sin forma: {cuantas}",
  pie_sin_cultivo: "Sin decir qué tienen este año: {cuantas}",
  pie_sin_hectareas: "Sin hectáreas dichas: {cuantas}",
  mapa_titulo: "El mapa de la finca",
  mapa_explica: "Debajo están tus trozos.",
  encajar: "ENCAJAR TODA LA FINCA",
  acercar: "ACERCAR",
  alejar: "ALEJAR",
  ver_mis_tierras: "QUITAR LOS LINDEROS DE MIS TIERRAS",
  ocultar_mis_tierras: "VER LOS LINDEROS DE MIS TIERRAS",
  cambiar_capa: "Qué se ve debajo",
  leyenda: "Leyenda",
  lo_da: "Lo da: {servicio}",
  fecha_de_la_imagen: "De cuándo es la imagen: {cuando}",
  fecha_sin_saber: "No se sabe: el servicio que da la imagen no dice de qué día es.",
  sin_forma_que_ensenar: "No hay ninguna tierra con su forma medida.",
  imagen_no_llega: "No se ha podido traer la imagen del mapa. Tus linderos siguen dibujados.",
  capa_avisos_no_esta: "La capa de avisos no está puesta porque el SIGPAC no publica ese servicio.",
};

/** Las palabras de la ficha de una tierra, tal y como las sirve el mismo endpoint. */
const TEXTOS_DE_LAS_VERSIONES_EN_T06 = {
  titulo: "Lo que ha sido esta tierra",
  explica: "Una tierra no es siempre la misma.",
  sin_versiones: "De esta tierra todavía no hay ninguna versión guardada.",
  cuando_se_miro: "Cuándo se miró",
  sin_fecha_de_consulta: "No se apuntó cuándo se miró.",
  referencia: "La referencia",
  sin_referencia_numeros: "No vinieron los números de la referencia.",
  le_falta_el_recinto: "Le falta el número de recinto",
  como_esta: "Cómo está",
  el_area_de_la_forma: "Lo que mide la forma que vino",
  el_area_del_sigpac: "Lo que dice el SIGPAC",
  el_area_declarada: "Las hectáreas que declaras",
  no_se_sabe: "No se sabe",
  comparar_titulo: "Comparar dos años",
  comparar_explica: "Elige un año y otro.",
  comparar_antes: "El año de antes",
  comparar_despues: "El año de ahora",
  comparar_boton: "COMPARAR",
  comparar_falta: "Elige los dos años y vuelve a pulsar.",
  comparar_sin_datos: "Todavía no hay versiones de dos años distintos.",
  que_cambio: "Qué cambió",
  no_cambio_nada: "No cambió nada",
  cuenta_iguales: "Iguales",
  cuenta_cambiados: "Cambiados",
  cuenta_desaparecidos: "Desaparecidos",
  cuenta_nuevos: "Nuevos",
  traer_titulo: "Traer lo de otro año",
  traer_explica: "Primero se enseña lo que cambiaría y no se apunta nada.",
  traer_de_anio: "Lo que esta tierra tenía en {anio}, según {fuente}",
  ensayar: "ENSAYARLO SIN APUNTAR NADA",
  ensayando: "Mirando qué cambiaría…",
  recintos_que_trae: "Recintos que trae",
  tierras_nuevas: "Tierras que se darían de alta",
  no_se_ha_apuntado: "Esto es solo un ensayo: no se ha apuntado nada de nada.",
  apuntarlo: "SÍ, APUNTARLO",
  apuntando_el_lote: "Apuntándolo…",
  apuntado_el_lote: "Ya está apuntado: {creadas} versiones nuevas.",
  lo_que_no_se_pudo: "Lo que no se ha podido tener en cuenta",
  trozos_que_se_pisan: "Trozos que se pisan",
  superficies_que_no_cuadran: "Superficies que no cuadran",
  volver_a_las_tierras: "VOLVER A MIS TIERRAS",
};

/**
 * **La copia del servidor de mentira tiene que decir lo mismo que el de verdad.** `/api/interfaz`
 * sirve los dos bloques de textos de T06 (se añadieron ahí porque la ficha de una tierra **se puede
 * abrir por su dirección** sin pasar por la pantalla del mapa, y entonces no hay ninguna vista
 * descargada de la que sacar las palabras). Sin esto en la copia, la pantalla saldría sin sus textos y
 * las pruebas darían por bueno un hueco.
 */
RESPUESTAS["/api/interfaz"].tierras = TEXTOS_DE_T06;
RESPUESTAS["/api/interfaz"].versiones = TEXTOS_DE_LAS_VERSIONES_EN_T06;

/** La vista de las tierras, como la sirve `/api/parcelas/vista`. */
function laVistaDeLasTierras(cambios = {}) {  return {
    textos: TEXTOS_DE_T06,
    textos_de_las_versiones: TEXTOS_DE_LAS_VERSIONES_EN_T06,
    campana_id: 1,
    campana_anio: 2026,
    tierras: [
      {
        id: 1,
        numero: 1,
        alias: "El Prado",
        referencia: "37-70-0-0-503-51-1",
        provincia: "Salamanca",
        municipio: "Calvarrasa de Arriba",
        sistema: "secano",
        superficie_ha: 2.43,
        superficie_sigpac_ha: 2.79,
        tiene_forma: true,
        forma: null,
        anillos: [
          [
            [-5.56, 40.9],
            [-5.55, 40.9],
            [-5.55, 40.91],
            [-5.56, 40.91],
          ],
        ],
        cultivo: "Trigo · secano",
        cultivo_clave: "Trigo",
        estado_revision: "revisado",
        estado_revision_texto: "Revisado",
        anio_de_la_version: 2026,
        fuente_texto: "SIGPAC",
        tiene_referencia_completa: true,
        area_declarada_ha: 2.4,
        tiene_hectareas_dichas: true,
      },
      {
        // **Sin forma**: la tierra a la que no le ha llegado el polígono. Sigue en la tabla.
        id: 2,
        numero: 2,
        alias: "La Vega",
        referencia: "37-70-0-0-112-4-2",
        provincia: "Salamanca",
        municipio: "Peñaranda de Bracamonte",
        sistema: "regadío",
        superficie_ha: 5.0,
        superficie_sigpac_ha: null,
        tiene_forma: false,
        forma: null,
        anillos: [],
        cultivo: "",
        cultivo_clave: "",
        estado_revision: null,
        estado_revision_texto: null,
        anio_de_la_version: null,
        fuente_texto: null,
        tiene_referencia_completa: true,
        area_declarada_ha: null,
        tiene_hectareas_dichas: true,
      },
    ],
    totales: {
      tierras: 2,
      con_forma: 1,
      sin_forma: 1,
      sin_cultivo: 1,
      sin_hectareas: 0,
      sin_revision: 1,
    },
    mapa: {
      hay_forma: true,
      tierras_con_forma: 1,
      caja: { oeste: -5.56, sur: 40.9, este: -5.55, norte: 40.91 },
    },
    filtros: {
      cultivos: [{ valor: "Trigo", texto: "Trigo", cuantas: 1 }],
      municipios: [{ valor: "Peñaranda de Bracamonte", texto: "Peñaranda de Bracamonte", cuantas: 1 }],
      revisiones: [{ valor: "revisado", texto: "Revisado", cuantas: 1 }],
      pac: [{ valor: "con_referencia", texto: "Con los tres números de la referencia", cuantas: 2 }],
    },
    ...cambios,
  };
}

/** Lo que dice `/api/mapa/estado` de sus capas. */
function elEstadoDelMapa() {
  return {
    capas: {
      foto: {
        titulo: "La foto del campo",
        servicio: "IGN (PNOA)",
        leyenda: "La foto del campo vista desde el aire.",
        fecha: null,
        fecha_texto: TEXTOS_DE_T06.fecha_sin_saber,
        se_puede_ocultar: true,
      },
      linderos: {
        titulo: "Los linderos",
        servicio: "SIGPAC (FEGA)",
        leyenda: "Las rayas que separan los trozos.",
        fecha: null,
        fecha_texto: TEXTOS_DE_T06.fecha_sin_saber,
        se_puede_ocultar: true,
      },
      cultivo: {
        titulo: "Lo que se declaró",
        servicio: "SIGPAC (FEGA)",
        leyenda: "Lo que se declaró que hay sembrado.",
        fecha: null,
        fecha_texto: TEXTOS_DE_T06.fecha_sin_saber,
        se_puede_ocultar: true,
      },
    },
    leyenda_de_mis_tierras: "Las rayas gruesas son tus tierras.",
    capa_avisos_no_esta: TEXTOS_DE_T06.capa_avisos_no_esta,
    si_no_llega_una_imagen: TEXTOS_DE_T06.imagen_no_llega,
  };
}

/** Una versión de la tierra 2, de otro año, para poder ensayar traerla. */
function unaVersionDeOtroAno() {
  return {
    id: 9,
    parcela_id: 2,
    tierra: "La Vega",
    campana_id: 3,
    anio: 2025,
    fuente: "sigpac",
    fuente_texto: "SIGPAC",
    fecha_consulta: null,
    clave: "37-70-0-0-112-4-2",
    referencia: "37-70-0-0-112-4-2",
    provincia: "37",
    municipio: "70",
    agregado: 0,
    zona: 0,
    poligono: 112,
    numero_parcela: 4,
    numero_recinto: 2,
    poligono_valido: true,
    geometria: null,
    tiene_forma: false,
    area_geometria_ha: null,
    area_sigpac_ha: 5.0,
    area_declarada_ha: null,
    uso_sigpac: "TA",
    pendiente_pct: null,
    estado_revision: "sin_revisar",
    estado_texto: "Sin revisar",
    como_esta: "Sin forma: no ha venido el polígono",
    creada_en: "2025-10-01T10:00:00",
  };
}

/** El plan que devuelve la previsualización: los cuatro números y ningún recinto que apuntar. */
function unPlanDeEnsayo(cambios = {}) {
  return {
    campana_id: 1,
    anio: 2026,
    fuente: "sigpac",
    fuente_texto: "SIGPAC",
    recintos_en_el_lote: 1,
    nuevos: 0,
    cambiados: 1,
    iguales: 0,
    sin_forma: 1,
    tierras_nuevas: 0,
    detalle: [],
    solapes: [],
    diferencias_de_superficie: [],
    problemas: [],
    aplicada: false,
    versiones_creadas: 0,
    versiones_actualizadas: 0,
    tierras_creadas: [],
    ...cambios,
  };
}

test("la dirección de las tierras abre la pantalla con su tabla y su mapa, y pide la vista", async () => {
  const { entorno, servidor } = await cargarAplicacion(
    {
      "/api/parcelas/vista": laVistaDeLasTierras(),
      "/api/mapa/estado": elEstadoDelMapa(),
    },
    { direccion: "#/tierras/mapa" },
  );

  assert.equal(laPantallaDeAhora(), "PantallaTierrasDeLaExplotacion", "la dirección no abre la pantalla");
  assert.ok(servidor.llamadas.includes("/api/parcelas/vista"), "no ha pedido la vista de las tierras");
  const montado = montajes[montajes.length - 1].elemento;
  assert.equal(montado.props.vista.tierras.length, 2, "la tabla no lleva las tierras");
  // La caja del mapa sale del servidor, no de un centro escrito a mano.
  assert.deepEqual(montado.props.mapa.caja, { oeste: -5.56, sur: 40.9, este: -5.55, norte: 40.91 });
  // Y la dirección queda escrita con el contexto, como todas.
  assert.match(
    laDireccion(entorno),
    /^#\/tierras\/mapa\?/,
    `la dirección no es la de la pantalla: ${laDireccion(entorno)}`,
  );
});

test("los filtros viajan en la dirección, y volver a abrirla los deja puestos", async () => {
  // Es la aceptación de T04 aplicada a esta pantalla: lo que el agricultor tiene filtrado se puede
  // recargar y mandar a quien le ayuda.
  const { entorno } = await cargarAplicacion(
    {
      "/api/parcelas/vista": laVistaDeLasTierras(),
      "/api/mapa/estado": elEstadoDelMapa(),
    },
    { direccion: "#/tierras/mapa?cultivo=Trigo&grupo=forma" },
  );

  const montado = montajes[montajes.length - 1].elemento;
  assert.equal(montado.props.filtro.cultivo, "Trigo", "el filtro de la dirección no se ha aplicado");
  assert.equal(montado.props.grupo, "forma", "la agrupación de la dirección no se ha aplicado");
  assert.match(
    laDireccion(entorno),
    /cultivo=Trigo/,
    `el filtro no viaja en la dirección: ${laDireccion(entorno)}`,
  );
  assert.match(laDireccion(entorno), /grupo=forma/);
});

test("tocar una fila la enfoca, y tocar un trozo del mapa enfoca **su** fila", async () => {
  // **El vínculo de las dos vistas**, que es la mitad del contrato: los dos caminos llevan la misma
  // acción (`t06-elegir-fila`) con el identificador de la tierra, así que el manejador de clics
  // enfoca la tierra por el mismo sitio. Aquí se comprueba desde `app.js`, que es donde vive el
  // manejador; que la fila y el trozo se enciendan se comprueba en el componente.
  const { entorno } = await cargarAplicacion(
    {
      "/api/parcelas/vista": laVistaDeLasTierras(),
      "/api/mapa/estado": elEstadoDelMapa(),
    },
    { direccion: "#/tierras/mapa" },
  );

  await pulsar(entorno, "t06-elegir-fila", { id: "2" });

  const montado = montajes[montajes.length - 1].elemento;
  assert.equal(montado.type.name, "PantallaTierrasDeLaExplotacion", "no se ha vuelto a pintar la pantalla");
  assert.equal(montado.props.elegida, 2, "la tierra tocada no se ha enfocado");
  // Y la dirección lleva la tierra enfocada, para poder enlazarla.
  assert.match(
    laDireccion(entorno),
    /id=2/,
    `la tierra enfocada no viaja en la dirección: ${laDireccion(entorno)}`,
  );
  // Y como esa tierra **no tiene forma**, el mapa no se mueve a buscarla: la caja sigue siendo la
  // misma. Mover el mapa buscando un polígono que no existe sería enseñar otro sitio.
  assert.equal(montado.props.mapa.caja.oeste, -5.56, "el mapa se ha movido a un trozo que no existe");
});

test("ensayar una importación **no escribe nada**: manda el lote solo a la ruta que lee", async () => {
  // **Esta es la prueba que más importa de T06**, y solo se puede hacer aquí: el ensayo se pide desde
  // `app.js`. Lo que persigue es que el camino de mirar no tenga, ni por descuido, una forma de
  // guardar: `previsualizar` sí se llama, `aplicar` **no**.
  const { entorno, servidor } = await cargarAplicacion(
    {
      "/api/parcelas/vista": laVistaDeLasTierras(),
      "/api/mapa/estado": elEstadoDelMapa(),
      "/api/versiones?parcela_id=2": [unaVersionDeOtroAno()],
      "POST /api/versiones/previsualizar": unPlanDeEnsayo(),
    },
    { direccion: "#/tierras/2/versiones" },
  );

  assert.equal(laPantallaDeAhora(), "PantallaVersionesDeUnaTierra", "la ficha de la tierra no se ha abierto");
  assert.ok(servidor.llamadas.includes("/api/versiones?parcela_id=2"), "no ha pedido las versiones");

  await pulsar(entorno, "t06-ensayar", { fuente: "sigpac", campana: "3" });

  const ensayado = servidor.enviados.find((uno) => uno.metodo === "POST");
  assert.ok(ensayado, "no se ha pedido ningún ensayo");
  assert.equal(ensayado.ruta, "/api/versiones/previsualizar", "el ensayo ha ido a la ruta que guarda");
  assert.ok(
    !servidor.llamadasConMetodo.includes("POST /api/versiones/aplicar"),
    "ensayar ha apuntado algo: previsualizar no puede escribir nunca",
  );
  // Y el lote que se manda lleva lo que había, sin inventarse ningún número de la referencia.
  assert.equal(ensayado.cuerpo.campana_id, 1, "el lote no va al año que se está llevando");
  assert.equal(ensayado.cuerpo.fuente, "sigpac");
  assert.equal(ensayado.cuerpo.recintos[0].parcela_id, 2, "el lote no dice de qué tierra es");
  assert.ok(
    !("area_declarada_ha" in ensayado.cuerpo.recintos[0]),
    "se manda la superficie declarada vacía, y eso podría borrar la que el agricultor puso",
  );
  // Y la pantalla lo dice: el ensayo no ha apuntado nada, y ofrece el botón de apuntarlo.
  const montado = montajes[montajes.length - 1].elemento;
  assert.equal(
    montado.props.ensayo.sin_apuntar,
    TEXTOS_DE_LAS_VERSIONES_EN_T06.no_se_ha_apuntado,
    `el ensayo tiene que decir que no ha apuntado nada: ${JSON.stringify(montado.props.ensayo)}`,
  );
  assert.equal(montado.props.ensayo.apuntado, "", "dice que se ha apuntado algo que solo se ha ensayado");
});

test("apuntar el lote es lo único que escribe, y solo cuando el agricultor lo pide", async () => {
  const { entorno, servidor } = await cargarAplicacion(
    {
      "/api/parcelas/vista": laVistaDeLasTierras(),
      "/api/mapa/estado": elEstadoDelMapa(),
      "/api/versiones?parcela_id=2": [unaVersionDeOtroAno()],
      "POST /api/versiones/previsualizar": unPlanDeEnsayo(),
      "POST /api/versiones/aplicar": unPlanDeEnsayo({
        aplicada: true,
        versiones_creadas: 1,
        versiones_actualizadas: 0,
      }),
    },
    { direccion: "#/tierras/2/versiones" },
  );

  await pulsar(entorno, "t06-ensayar", { fuente: "sigpac", campana: "3" });
  assert.ok(
    !servidor.llamadasConMetodo.includes("POST /api/versiones/aplicar"),
    "el ensayo ya ha escrito: no se puede apuntar sin que lo pida el agricultor",
  );

  await pulsar(entorno, "t06-apuntar-lote");

  assert.ok(
    servidor.llamadasConMetodo.includes("POST /api/versiones/aplicar"),
    "el botón de apuntar no ha apuntado nada",
  );
  const montado = montajes[montajes.length - 1].elemento;
  assert.match(montado.props.ensayo.apuntado, /Ya está apuntado/);
});

test("si la vista de las tierras no llega, se dice en la pantalla y no se queda en blanco", async () => {
  const { entorno } = await cargarAplicacion(
    { "/api/parcelas/vista": falla({ detail: "No se ha podido leer tus tierras." }) },
    { direccion: "#/tierras/mapa" },
  );

  const montado = montajes[montajes.length - 1].elemento;
  assert.equal(montado.type.name, "PantallaTierrasDeLaExplotacion");
  assert.equal(montado.props.aviso, "No se ha podido leer tus tierras.", "el motivo no llega al agricultor");
  assert.ok(entorno, "el entorno tiene que existir");
});

// ---------------------------------------------------------------------------
// T10 · Las semillas y las siembras: **el camino de guardar**, pulsando los botones
//
// POR QUÉ ESTE APARTADO EXISTE, Y ES UNA CORRECCIÓN DE LA REVISIÓN. Las pruebas de
// `tests_js/semillas.test.js` pintan las cuatro pantallas con `renderToStaticMarkup` y comprueban
// los `id` de los campos, los textos y las opciones… pero **ninguna pulsaba `semilla-guardar`,
// `siembra-guardar` ni `siembra-anular`**: el camino por el que el agricultor guarda de verdad no lo
// miraba nadie. Ahí estaba el defecto 8 (la cuenta que hace el servidor se tiraba antes de pintar).
// Aquí se pulsan, con el DOM de mentira y el servidor de mentira de este fichero, y se mira **lo que
// llega al servidor** — que es lo único que dice si lo escrito se guarda bien.
//
// Y de escribir esto salió un defecto más: **ninguna pantalla pintaba el botón `siembra-nueva`**, así
// que no había forma de llegar al formulario de la siembra. Por eso la primera prueba recorre el
// camino entero, empezando por la lista de semillas.
// ---------------------------------------------------------------------------

/**
 * Los textos de las semillas, los mismos que sirve `/api/interfaz`.
 *
 * Es una copia recortada: solo las claves que estas pruebas leen o comprueban (el guardián de que no
 * falte ninguna vive en Python, `tests/test_que_no_falte_ningun_texto.py`, y mira el servidor de
 * verdad). Si una clave no estuviera, el texto saldría en blanco en la comprobación y se vería.
 */
const TEXTOS_DE_LAS_SEMILLAS = {
  titulo: "Mis semillas",
  explica: "Aquí tienes las semillas que usas, con lo que pone su etiqueta y lo que te queda de cada una.",
  vacia: "Todavía no has dado de alta ninguna semilla.",
  cuantas: "Tienes {cuantas} semillas dadas de alta.",
  cuantas_una: "Tienes 1 semilla dada de alta.",
  buscando: "Buscando…",
  que_se_puede_hacer: "¿Qué quieres hacer?",
  anadir: "AÑADIR UNA SEMILLA",
  anadir_pista: "Escribe lo que pone la etiqueta del envase",
  volver_al_inicio: "VOLVER AL INICIO",
  ver_las_siembras: "VER LO QUE HE SEMBRADO",
  leer_etiqueta: "HACERLE UNA FOTO A LA ETIQUETA",
  leer_lo_que_pone: "LEER LO QUE PONE (NO SE GUARDA NADA)",
  leer_etiqueta_pista: "Hazle una foto a la etiqueta del envase.",
  ficha_titulo: "Una semilla nueva",
  ficha_titulo_corregir: "Corregir esta semilla",
  ficha_explica: "Escribe lo que pone la etiqueta. Lo que no venga en el papel, déjalo en blanco.",
  ficha_explica_propuesta: "Esto es lo que he leído de la foto. Míralo y corrígelo.",
  articulo_del_almacen: "¿Es algo que ya tienes en el almacén?",
  articulo_del_almacen_pista: "Si la semilla ya entró con un albarán, elígela aquí.",
  articulo_nuevo: "No, es nueva: la apunto ahora",
  nombre_del_articulo: "Cómo la llamas tú",
  nombre_del_articulo_pista: "El nombre con el que la reconoces en el almacén.",
  especie: "Qué semilla es",
  especie_pista: "La especie, como viene en la etiqueta.",
  variedad: "La variedad",
  variedad_pista: "El nombre de la variedad, si el papel lo dice.",
  casa_comercial: "La casa que la vende",
  casa_comercial_pista: "Quien la produce o la envasa.",
  proveedor: "A quién se la compraste",
  proveedor_pista: "El proveedor o la cooperativa.",
  numero_lote_proveedor: "El número de lote del envase",
  numero_lote_proveedor_pista: "El número que va impreso en el saco.",
  dosis_recomendada: "Cuánto recomienda sembrar por hectárea",
  dosis_recomendada_pista: "Lo que dice la etiqueta, no lo que tú siembras.",
  unidad_de_la_dosis: "En qué se mide",
  sin_decir: "Sin decir",
  fecha_envasado: "Cuándo se envasó",
  fecha_caducidad: "Hasta cuándo vale",
  fecha_caducidad_pista: "Si el papel no lo dice, déjalo en blanco.",
  poder_germinativo: "Poder germinativo",
  poder_germinativo_pista: "El porcentaje del papel.",
  pureza: "Pureza",
  pureza_pista: "El porcentaje del papel.",
  no_lo_dice: "La etiqueta no lo dice",
  tratada: "¿Viene tratada?",
  tratada_pista: "Si el envase dice que viene tratada, márcalo aquí.",
  tratada_si: "Sí viene tratada",
  tratada_no: "No viene tratada",
  tratada_no_se: "No lo sé",
  guardar: "GUARDAR LA SEMILLA",
  guardando: "Guardando…",
  subir_la_foto: "SUBIR LA FOTO",
  ver_la_foto: "VER LA FOTO DE LA ETIQUETA",
  la_foto_se_guarda: "La foto se guarda con la semilla.",
  no_confirmada: "Esto es solo lo que he leído. Hasta que no pulses GUARDAR LA SEMILLA, no hay ninguna semilla apuntada.",
  lo_que_dice_el_papel: "Lo que dice el papel y no he podido apuntar",
  lo_que_dice_el_papel_explica: "Esto lo he leído, pero tal y como está escrito no se puede apuntar.",
  leido_a_mano: "Lo has escrito tú",
  leido_de_foto: "Leído de la foto de la etiqueta",
  campos_leidos: "He podido leer {cuantos} datos de la etiqueta.",
  campos_leidos_uno: "He podido leer 1 dato de la etiqueta.",
  idioma_de_la_lectura: "Leído con el idioma {idioma}",
  volver_a_las_semillas: "VOLVER A MIS SEMILLAS",
  lo_que_queda: "Lo que te queda",
  sin_saber_lo_que_queda: "No se puede saber lo que queda",
  sin_semillas: "Todavía no tienes ninguna semilla dada de alta, así que no hay de dónde descontar lo que siembres.",
  siembras_titulo: "Lo que he sembrado",
  siembras_explica: "Cada siembra dice en qué tierra, de qué semilla y cuánto.",
  siembras_vacia: "Todavía no has apuntado ninguna siembra.",
  cuantas_siembras: "Tienes {cuantas} siembras apuntadas.",
  cuantas_siembras_uno: "Tienes 1 siembra apuntada.",
  sembrar_esta: "SEMBRAR ESTA SEMILLA",
  sembrar_esta_pista: "Apunta en qué tierra la has sembrado y sale del almacén",
  siembra_titulo: "Sembrar una semilla",
  siembra_titulo_corregir: "Corregir esta siembra",
  siembra_explica: "Dime en qué tierra la has sembrado y cuánto.",
  siembra_semilla: "¿Qué semilla?",
  siembra_tierra: "¿En qué tierra?",
  siembra_elige_la_tierra: "Elige la tierra",
  siembra_fecha: "¿Cuándo?",
  siembra_superficie: "¿Cuántas hectáreas has sembrado?",
  siembra_superficie_pista: "Las hectáreas que has sembrado.",
  siembra_dosis: "Cuánto se siembra en cada hectárea",
  siembra_dosis_pista: "Lo que siembras en cada hectárea. No es lo que has gastado en total: son cosas distintas.",
  siembra_cantidad_total: "Cuánto se ha gastado en total",
  siembra_cantidad_total_pista: "Lo que has gastado en la tierra entera. Es lo que sale del almacén.",
  siembra_unidad_total: "En qué se mide el total",
  siembra_envase: "De qué envase sale",
  siembra_envase_pista: "De qué saco sale la semilla.",
  siembra_sin_envase: "No sé de qué envase sale",
  siembra_notas: "Lo que quieras apuntar",
  guardar_siembra: "GUARDAR LA SIEMBRA",
  guardando_siembra: "Guardando…",
  calculado: "Lo ha calculado el programa",
  calculado_pista: "Este número no lo has escrito tú: sale de la dosis por las hectáreas. Míralo, y si no es así, cámbialo.",
  siembra_anular: "ANULAR ESTA SIEMBRA",
  siembra_motivo_anulacion: "Por qué la anulas",
  siembra_motivo_anulacion_pista: "Una siembra no se borra: se anula y queda dicho por qué.",
  siembra_anulada: "Siembra anulada. Lo que había salido del almacén vuelve a contar.",
  siembra_no_descuenta: "Esta siembra no ha descontado nada del almacén",
  siembra_no_descuenta_pista: "Falta saber cuánto se sembró o de qué envase sale.",
  volver_a_las_siembras: "VOLVER A LO QUE HE SEMBRADO",
};

/** Los mensajes que la pantalla enseña tal cual, los mismos que sirve `/api/interfaz`. */
const MENSAJES_DE_LAS_SEMILLAS = {
  SM13_falta_el_nombre: "Falta cómo llamas a esta semilla. Escribe el nombre con el que la reconoces.",
  SM14_falta_la_unidad_de_la_dosis: "Has puesto cuánto se siembra por hectárea, pero no en qué se mide.",
  SM16_no_se_puede_sacar_sin_cantidad: "No se ha sacado nada del almacén porque no se sabe cuánto se sembró.",
  SM17_no_se_puede_sacar_sin_envase: "No se ha sacado nada del almacén porque no se sabe de qué envase sale.",
  SM22_falta_la_tierra: "Falta decir en qué tierra la has sembrado. Toca la tierra y vuelve a guardar.",
  SM24_falta_el_motivo_para_anular: "Para anular una siembra hace falta decir por qué. Escríbelo y vuelve a pulsar.",
  SM34_la_semilla_no_se_cambia: "La semilla de una siembra apuntada no se cambia.",
};

RESPUESTAS["/api/interfaz"].semillas = TEXTOS_DE_LAS_SEMILLAS;
RESPUESTAS["/api/interfaz"].mensajes = {
  ...RESPUESTAS["/api/interfaz"].mensajes,
  ...MENSAJES_DE_LAS_SEMILLAS,
};
RESPUESTAS["/api/interfaz"].unidades_dosis_semilla = ["kg/ha", "g/ha", "ud/ha", "L/ha"];
RESPUESTAS["/api/interfaz"].unidades_cantidad_semilla = ["kg", "g", "ud", "L"];

// ---------------------------------------------------------------------------
// Las personas y las empresas (T11, 03/10/2026)
//
// **Aquí va solo lo que este fichero necesita para no pintar un hueco**: el nombre del renglón del menú
// y los papeles. La **copia entera** de los textos de las cuatro pantallas de contactos vive en
// `tests_js/contactos.test.js`, que es donde se prueban sus componentes, y hay una prueba de Python
// (`tests/test_contactos.py::TestLaCopiaDeLosTextosNoSeQuedaVieja`) que comprueba, clave por clave, que
// esa copia dice lo mismo que el servidor. Se reparte así por el mismo motivo que las semillas: este
// fichero prueba el cableado de la aplicación entera y no puede permitirse que una pantalla nueva le
// deje un renglón en blanco; la copia palabra por palabra es de quien prueba la pantalla.
const TEXTOS_DE_LOS_CONTACTOS = {
  titulo: "Las personas y las empresas",
  explica:
    "Aquí apuntas una vez a quien te vende, a quien te compra, a quien te asesora o a quien te lleva la mercancía. Después, en cada factura y en cada venta, solo tienes que decir cuál de ellos es: su nombre ya no hay que volver a escribirlo.",
  vacia:
    "Todavía no tienes ninguna ficha apuntada. Puedes empezar por los nombres que ya has escrito en tus facturas y en tus ventas: el programa te los enseña y tú dices cuáles son la misma persona.",
  cuantas: "Tienes {cuantas} fichas apuntadas.",
  cuantas_una: "Tienes 1 ficha apuntada.",
  cuantos_escritos: "Su nombre está escrito en {cuantas} papeles.",
  cuantos_escritos_uno: "Su nombre está escrito en 1 papel.",
  buscando: "Buscando…",
  buscar: "Buscar por el nombre",
  buscar_pista: "Escribe unas letras del nombre. No hacen falta las tildes.",
  buscar_boton: "BUSCAR",
  buscar_limpiar: "VERLAS TODAS",
  que_se_puede_hacer: "¿Qué quieres hacer?",
  anadir: "AÑADIR UNA FICHA",
  anadir_pista: "Una persona o una empresa que trate con tu finca",
  traer_los_nombres: "TRAER LOS NOMBRES QUE YA TENGO ESCRITOS",
  traer_los_nombres_pista:
    "El programa mira los nombres que ya están escritos en tus facturas, tus ventas y tus análisis, y te propone una ficha por cada uno. Tú decides cuáles se apuntan.",
  volver_al_inicio: "VOLVER AL INICIO",
  donde_aparece: "Dónde está escrito su nombre",
  sin_enlaces: "Su nombre todavía no está enlazado con ningún papel.",
  papeles: {
    proveedor: "Quien te vende el producto",
    proveedor_semilla: "Quien te vende la semilla",
    proveedor_abono: "Quien te vende el abono",
    comprador: "Quien te compra la cosecha",
    asesor: "El técnico que te asesora",
    aplicador: "Quien echa el producto",
    transportista: "Quien te lleva la mercancía",
    taller: "El taller donde arreglas las máquinas",
    laboratorio: "El laboratorio donde mandas las muestras",
    veterinario: "El veterinario",
    arrendador: "Quien te alquila la tierra",
    otro: "Otra cosa",
  },
  revision_titulo: "Los nombres que ya tienes escritos",
  revision_nada: "No hay ningún nombre escrito sin dueño. Todo lo que tienes apuntado ya tiene su ficha.",
  revision_volver: "VOLVER A LAS FICHAS",
};

RESPUESTAS["/api/interfaz"].contactos = TEXTOS_DE_LOS_CONTACTOS;
// **La lista de papeles, con su orden y con su nombre**, tal y como la sirve el servidor: la ficha los
// pinta en este orden, y un cuestionario cuyas preguntas cambian de sitio se contesta mal.
RESPUESTAS["/api/interfaz"].papeles_de_un_contacto = Object.entries(
  TEXTOS_DE_LOS_CONTACTOS.papeles,
).map(([valor, texto]) => ({ valor, texto }));


/** Una semilla ya dada de alta, con lo que pone su etiqueta y lo que queda en el almacén. */
function unaSemillaDeVerdad(cambios = {}) {
  return {
    id: 4,
    articulo_id: 9,
    nombre: "Veza común Villalobos",
    unidad: "kg",
    categoria: "semilla",
    especie: "Veza común",
    variedad: "Villalobos",
    casa_comercial: "Semillas del Duero",
    proveedor: "Cooperativa Agrícola de Peñaranda",
    numero_lote_proveedor: "4471-A",
    dosis_recomendada_por_ha: 120.0,
    unidad_dosis: "kg/ha",
    fecha_envasado: "2026-01-12",
    fecha_caducidad: "2028-01-12",
    poder_germinativo_pct: 92.0,
    pureza_pct: null,
    tratada: false,
    leida_de: "mano",
    idioma_del_lector: null,
    tiene_foto: false,
    creada_en: "2026-01-20T10:00:00",
    queda: { saldo: 500.0, unidad: "kg", motivo: "", motivo_codigo: "", cuantos_lotes: 1 },
    envases: [
      { lote_id: 8, numero_lote: "4471-A", fecha_caducidad: "2028-01-12", caducado: false, presentacion: "saco", saldo: 500.0, unidad: "kg", motivo: "" },
    ],
    siembras: 0,
    ...cambios,
  };
}

/** Una siembra ya apuntada, como la devuelve `/api/siembras`. */
function unaSiembraDeVerdad(cambios = {}) {
  return {
    id: 7,
    semilla_id: 4,
    parcela_id: 1,
    lote_id: 8,
    fecha: "2026-03-01",
    superficie_ha: 1.0,
    dosis_por_ha: 200.0,
    unidad_dosis: "kg/ha",
    cantidad_total: 200.0,
    unidad_cantidad: "kg",
    dosis_calculada: false,
    cantidad_total_calculada: false,
    notas: null,
    anulada: false,
    motivo_anulacion: null,
    creada_en: "2026-03-01T09:00:00",
    semilla: "Veza común Villoblos",
    tierra: "El Prado",
    numero_lote: "4471-A",
    descuenta: true,
    no_descuenta_porque: null,
    movimiento_id: 3,
    avisos: [],
    ...cambios,
  };
}

/** La aplicación con las semillas y las siembras cargadas. */
async function conLasSemillas(cambios = {}) {
  return cargarAplicacion({
    "/api/semillas": [unaSemillaDeVerdad()],
    "/api/siembras": [],
    "/api/almacen/articulos": [],
    "POST /api/siembras": unaSiembraDeVerdad(),
    ...cambios,
  });
}

/** Rellena el formulario de una siembra, como lo haría el agricultor con el teclado y el dedo. */
function rellenarLaSiembra(entorno, cambios = {}) {
  const valores = {
    "siembra-tierra": "1",
    "siembra-fecha": "2026-03-01",
    "siembra-superficie": "2,5",
    "siembra-dosis": "120",
    "siembra-unidad-dosis": "kg/ha",
    "siembra-cantidad": "300",
    "siembra-unidad-cantidad": "kg",
    "siembra-envase": "8",
    "siembra-notas": "A mano en el lindero",
    ...cambios,
  };
  for (const [id, valor] of Object.entries(valores)) escribir(entorno, id, valor);
}

test("desde una semilla se llega a sembrarla (la puerta que faltaba), y lo escrito llega al servidor", async () => {
  // **Esta prueba salió de la revisión, y por dos motivos.** El primero: el camino de guardar no lo
  // pulsaba nadie. El segundo, que se descubrió al escribirla: **ninguna pantalla pintaba el botón
  // `siembra-nueva`**, así que el formulario de sembrar existía y no había forma de llegar a él.
  const { entorno, servidor } = await conLasSemillas();

  await pulsar(entorno, "semillas-ver");
  assert.equal(ultimoMontaje().type.name, "PantallaDeLasSemillas", "no se abre la lista de semillas");
  assert.equal(ultimoMontaje().props.tarjetas[0].etiqueta, "Veza común Villalobos");

  await pulsar(entorno, "semilla-abrir", { id: 4 });
  const ficha = ultimoMontaje();
  assert.equal(ficha.type.name, "PantallaDeUnaSemilla", "no se abre la ficha de la semilla");
  assert.equal(ficha.props.semillaId, 4, "la ficha no sabe de qué semilla es: sin eso no sale el botón de sembrarla");

  await pulsar(entorno, "siembra-nueva", { id: 4 });
  assert.equal(ultimoMontaje().type.name, "PantallaDeUnaSiembra", "no se abre el formulario de la siembra");
  assert.equal(ultimoMontaje().props.semilla, "Veza común Villalobos");
  assert.equal(ultimoMontaje().props.quedar.saldo, 500.0, "el formulario no dice lo que queda");

  rellenarLaSiembra(entorno);
  await pulsar(entorno, "siembra-guardar");

  const cuerpo = loMandado(servidor, "/api/siembras")[0].cuerpo;
  // **La dosis y el total van cada uno en su campo y con su unidad**, que es lo que impide el error de
  // diez veces. Y el total que el agricultor ha escrito (300) no se copia en el campo de la dosis.
  assert.equal(cuerpo.dosis_por_ha, 120, "la dosis por hectárea no llega como número");
  assert.equal(cuerpo.unidad_dosis, "kg/ha");
  assert.equal(cuerpo.cantidad_total, 300, "la cantidad total no llega como número");
  assert.equal(cuerpo.unidad_cantidad, "kg");
  assert.equal(cuerpo.superficie_ha, 2.5, "la coma del móvil no se entiende");
  assert.equal(cuerpo.lote_id, 8, "el envase del que sale no llega");
  assert.equal(cuerpo.parcela_id, 1);
  assert.equal(cuerpo.fecha, "2026-03-01");
  assert.equal(cuerpo.notas, "A mano en el lindero");
  // La marca de reenvío es lo que impide que un reintento del móvil descuente dos veces.
  assert.ok(cuerpo.clave_de_reenvio, "la siembra no viaja con su marca de reenvío");
  // Y la confirmación del descuadre no se manda si el agricultor no la ha dado.
  assert.equal(cuerpo.aceptar_descuadre, false, "se está aceptando un descuadre que nadie ha confirmado");
});

test("al guardar la siembra, la cuenta que ha hecho el servidor se lee en la lista (defecto 8)", async () => {
  // **El defecto 8, con su prueba de verdad.** El servidor dice la cuenta en el aviso de la respuesta
  // de guardar (y solo ahí: al volver a leer la siembra ya no viene). La pantalla la guardaba y la
  // ponía a nulo antes de pintar, así que el agricultor leía un total que no había escrito él como si
  // lo hubiera escrito él. Aquí se comprueba que **llega a la pantalla que se queda delante**.
  const laCuenta =
    "La cantidad total la he calculado yo: 120,00 kg/ha por 2,50 hectáreas son 300,00 kg. Míralo, y si no es así, cámbialo.";
  const { entorno } = await conLasSemillas({
    "POST /api/siembras": unaSiembraDeVerdad({
      dosis_por_ha: 120.0,
      cantidad_total: 300.0,
      cantidad_total_calculada: true,
      avisos: [laCuenta],
    }),
    // Y la lista, al volver a leerla, trae la siembra que se acaba de guardar —sin el aviso: el aviso
    // solo vive en la respuesta de guardar, que es justo por lo que hay que enseñarlo al guardar—.
    "/api/siembras": [
      unaSiembraDeVerdad({
        dosis_por_ha: 120.0,
        cantidad_total: 300.0,
        cantidad_total_calculada: true,
      }),
    ],
  });
  await pulsar(entorno, "semillas-ver");
  await pulsar(entorno, "semilla-abrir", { id: 4 });
  await pulsar(entorno, "siembra-nueva", { id: 4 });
  rellenarLaSiembra(entorno, { "siembra-cantidad": "" });
  await pulsar(entorno, "siembra-guardar");

  const lista = ultimoMontaje();
  assert.equal(lista.type.name, "PantallaDeLasSiembras", "después de guardar no se enseña la lista");
  assert.ok(lista.props.calculado, "la cuenta que ha hecho el servidor no llega a la pantalla");
  assert.equal(lista.props.calculado.cantidad_total, true);
  assert.equal(lista.props.calculado.total_en_palabras, laCuenta, "la cuenta entera no se lee");
  assert.ok(
    (lista.props.avisos || []).includes(laCuenta),
    "los avisos del servidor no se guardan para enseñarlos",
  );
  // Y la tarjeta que se ve es la de la siembra que se acaba de guardar.
  assert.equal(lista.props.tarjetas.length, 1);
  assert.equal(lista.props.avisos.length, 1);
});

test("una siembra sin tierra no se manda, y se dice cuál falta", async () => {
  const { entorno, servidor } = await conLasSemillas();
  await pulsar(entorno, "semillas-ver");
  await pulsar(entorno, "semilla-abrir", { id: 4 });
  await pulsar(entorno, "siembra-nueva", { id: 4 });
  rellenarLaSiembra(entorno, { "siembra-tierra": "" });
  await pulsar(entorno, "siembra-guardar");

  assert.equal(cuantasVeces(servidor, "POST /api/siembras"), 0, "se ha mandado una siembra sin tierra");
  assert.equal(
    ultimoMontaje().props.error,
    MENSAJES_DE_LAS_SEMILLAS.SM22_falta_la_tierra,
    "no se dice qué falta",
  );
});

test("anular una siembra pide el motivo, y solo llama al servidor si lo hay", async () => {
  const { entorno, servidor } = await conLasSemillas({
    "/api/siembras": [unaSiembraDeVerdad()],
    "POST /api/siembras/7/anular": unaSiembraDeVerdad({
      anulada: true,
      motivo_anulacion: "Me equivoqué de tierra",
      descuenta: false,
    }),
  });
  await pulsar(entorno, "semillas-ver");
  await pulsar(entorno, "siembras-ver");
  assert.equal(ultimoMontaje().type.name, "PantallaDeLasSiembras");
  assert.equal(ultimoMontaje().props.tarjetas[0].etiqueta, "El Prado");

  await pulsar(entorno, "siembra-abrir", { id: 7 });
  assert.equal(ultimoMontaje().type.name, "PantallaDeUnaSiembra", "no se abre la siembra apuntada");
  assert.equal(ultimoMontaje().props.corrigiendo, true, "no se está corrigiendo");

  // Sin motivo no se llama y se dice por qué: una siembra no se borra, se anula con su motivo.
  await pulsar(entorno, "siembra-anular");
  assert.equal(cuantasVeces(servidor, "POST /api/siembras/7/anular"), 0, "se ha anulado sin motivo");
  assert.equal(
    ultimoMontaje().props.error,
    MENSAJES_DE_LAS_SEMILLAS.SM24_falta_el_motivo_para_anular,
    "no se dice que falta el motivo",
  );

  escribir(entorno, "siembra-motivo", "Me equivoqué de tierra");
  await pulsar(entorno, "siembra-anular");
  const cuerpo = loMandado(servidor, "/api/siembras/7/anular")[0].cuerpo;
  assert.equal(cuerpo.motivo, "Me equivoqué de tierra", "el motivo no llega al servidor");
  assert.equal(ultimoMontaje().type.name, "PantallaDeLasSiembras", "después de anular no se vuelve a la lista");
});

test("la semilla se guarda con lo que pone el formulario, y lo que no se sabe va vacío", async () => {
  const { entorno, servidor } = await conLasSemillas({
    "POST /api/semillas": unaSemillaDeVerdad(),
  });
  await pulsar(entorno, "semillas-ver");
  await pulsar(entorno, "semilla-nueva");
  assert.equal(ultimoMontaje().type.name, "PantallaDeUnaSemilla");

  escribir(entorno, "semilla-nombre", "Veza común Villalobos");
  escribir(entorno, "semilla-especie", "Veza común");
  escribir(entorno, "semilla-variedad", "Villalobos");
  escribir(entorno, "semilla-dosis", "120");
  escribir(entorno, "semilla-unidad-dosis", "kg/ha");
  escribir(entorno, "semilla-pureza", "");          // el papel no la trae: se queda vacía
  escribir(entorno, "semilla-tratada", "no_se");    // y «viene tratada» no se sabe
  await pulsar(entorno, "semilla-guardar");

  const cuerpo = loMandado(servidor, "/api/semillas")[0].cuerpo;
  assert.equal(cuerpo.nombre, "Veza común Villalobos");
  assert.equal(cuerpo.especie, "Veza común");
  assert.equal(cuerpo.dosis_recomendada_por_ha, 120, "la dosis no llega como número");
  assert.equal(cuerpo.unidad_dosis, "kg/ha");
  // **Lo que no se sabe no se convierte en cero ni en «no»**: los tres campos van a nulo.
  assert.equal(cuerpo.pureza_pct, null, "un hueco se está guardando como un número");
  assert.equal(cuerpo.tratada, null, "«no lo sé» se está guardando como «no viene tratada»");
  assert.equal(cuerpo.poder_germinativo_pct, null);
  // Y se dice de dónde salieron los datos: los ha escrito una persona.
  assert.equal(cuerpo.leida_de, "mano");
});

test("guardar una semilla sin nombre no se manda, y se dice qué falta", async () => {
  const { entorno, servidor } = await conLasSemillas();
  await pulsar(entorno, "semillas-ver");
  await pulsar(entorno, "semilla-nueva");
  await pulsar(entorno, "semilla-guardar");

  assert.equal(cuantasVeces(servidor, "POST /api/semillas"), 0, "se ha mandado una semilla sin nombre");
  assert.equal(
    ultimoMontaje().props.error,
    MENSAJES_DE_LAS_SEMILLAS.SM13_falta_el_nombre,
    "no se dice qué falta",
  );
});

test("leer la etiqueta sin haber elegido la foto no manda nada al servidor", async () => {
  // **La lectura no guarda nada, y sin foto no hay nada que leer.** Lo que se comprueba aquí es que la
  // pantalla no manda una petición vacía (y que no se queda sin decir nada, que es peor).
  const { entorno, servidor } = await conLasSemillas();
  await pulsar(entorno, "semillas-ver");
  await pulsar(entorno, "semilla-nueva");
  await pulsar(entorno, "semilla-leer-foto");

  assert.equal(
    cuantasVeces(servidor, "POST /api/semillas/etiqueta"),
    0,
    "se ha ido al servidor a leer una foto que no se ha elegido",
  );
  assert.ok(ultimoMontaje().props.error, "y no se dice nada, que deja al agricultor sin saber qué pasa");
});

// ---------------------------------------------------------------------------
// El banco y los papeles (T20, E11, 05/10/2026)
//
// **Lo que se comprueba aquí, y por qué aquí.** La pantalla tiene sus 42 pruebas
// (`tests_js/bancos.test.js`) y el servidor las suyas, pero **el cableado no lo probaba nadie** —y en
// este proyecto eso ya ha costado dos pantallas muertas: la de las cuentas llamaba a un ayudante que no
// existía (`campanaActual`) y su botón de guardar mandaba un GET sin datos—. Así que aquí se pulsa la
// puerta de entrada: abrir la dirección de los movimientos tiene que montar la pantalla **con los datos
// del servidor**, y abrir la de un movimiento tiene que montar su ficha **con su identificador**.
// ---------------------------------------------------------------------------

/** Un extracto con una cuenta, un movimiento y un papel pendiente. */
function conElBanco(cambios = {}) {
  return cargarAplicacion({
    "/api/bancos/cuentas": [{ id: 1, nombre: "Cuenta de la casa", ultimos_digitos: "4321" }],
    "/api/bancos/perfiles": [{ id: 2, nombre: "El de mi banco" }],
    // **La ruta con su cuenta, tal y como la pide la pantalla**: los movimientos son de una cuenta (la
    // primera que trae el servidor), y `recargarLosBancos` la pone en la consulta. Si la ruta no casara,
    // el servidor de mentira contestaría vacío y la prueba daría por bueno un hueco.
    "/api/bancos/movimientos?cuenta_id=1": {
      items: [
        {
          id: 5,
          fecha: "2026-06-15",
          concepto: "TRANSFERENCIA RECIBIDA COOPERATIVA",
          importe: "1205.40",
          texto_importe: "1.205,40 €",
          estado: "sin_conciliar",
          cuenta_id: 1,
        },
      ],
      agregados: { entradas: "1205.40", texto_entradas: "1.205,40 €", salidas: "0.00", texto_salidas: "0,00 €" },
      total: 1,
    },
    "/api/bancos/pendientes": [],
    "/api/bancos/movimientos/5/propuestas": {
      movimiento: {
        id: 5,
        fecha: "2026-06-15",
        concepto: "TRANSFERENCIA RECIBIDA COOPERATIVA",
        importe: "1205.40",
        texto_importe: "1.205,40 €",
        estado: "sin_conciliar",
      },
      pendientes: [],
      propuestas: [],
    },
    ...cambios,
  });
}

test("la dirección de los movimientos del banco abre la pantalla con sus datos", async () => {
  const { entorno, servidor } = await conElBanco();
  entorno.window.location.hash = "#/cuentas/bancos";
  await entorno.manejadores.popstate();
  await new Promise((resolver) => setTimeout(resolver, 80));

  const elemento = ultimoMontaje();
  assert.equal(elemento.type.name, "PantallaDeLosBancos");
  assert.ok(
    servidor.llamadas.some((ruta) => ruta.includes("/api/bancos/movimientos")),
    "no se han pedido los movimientos al abrir la pantalla",
  );
  assert.equal(elemento.props.cuentas.length, 1, "no le llegan las cuentas del servidor");
  assert.equal(elemento.props.cuentas[0].texto, "Cuenta de la casa ·4321");
  assert.equal(elemento.props.movimientos.length, 1, "no le llega el movimiento apuntado");
  assert.ok(elemento.props.textos.bancos, "no le llegan las palabras de la pantalla");
});

test("conciliar enseña a qué papel ha ido el dinero, y no borra el aviso al recargar la ficha", async () => {
  // **El fallo que esto fija, que se encontró pulsando.** Al conciliar, `app.js` guardaba la respuesta
  // del servidor y **después** recargaba la ficha; la recarga limpia lo anterior a propósito (al abrir un
  // movimiento de cero no hay nada que contar), así que se llevaba por delante el «lo que ha quedado
  // apuntado». El agricultor apuntaba el dinero y no veía **a qué papel** había ido: justo lo que hay que
  // poder comprobar para no apuntar dos veces el mismo pago. Por eso esta prueba no mira la pantalla: mira
  // lo que se le pide a React después de pulsar, que es donde estaba el hueco.
  const { entorno, servidor } = await conElBanco({
    // La propuesta que se va a pulsar: con su índice y sus imputaciones, tal y como las manda el servidor.
    "/api/bancos/movimientos/5/propuestas": {
      movimiento: {
        id: 5,
        fecha: "2026-06-15",
        concepto: "TRANSFERENCIA RECIBIDA COOPERATIVA",
        importe: "1205.40",
        texto_importe: "1.205,40 €",
        estado: "sin_conciliar",
        por_conciliar: "1205.40",
        texto_por_conciliar: "1.205,40 €",
      },
      pendientes: [
        {
          clase: "factura_emitida",
          documento_id: 3,
          etiqueta: "factura_emitida:3",
          contraparte: "Cooperativa del Sur",
          referencia: "F-2026-12",
          que_es: "Una factura tuya, de lo que has vendido",
          pendiente: "1205.40",
          texto_pendiente: "1.205,40 €",
        },
      ],
      propuestas: [
        {
          tipo: "exacta",
          total: "1205.40",
          texto_total: "1.205,40 €",
          sobrante: "0.00",
          texto_sobrante: "0,00 €",
          porque: ["el importe cuadra exacto"],
          imputaciones: [
            { clase: "factura_emitida", documento_id: 3, importe: "1205.40", texto_importe: "1.205,40 €" },
          ],
        },
      ],
    },
    "POST /api/bancos/movimientos/5/conciliar": {
      movimiento: {
        id: 5,
        fecha: "2026-06-15",
        concepto: "TRANSFERENCIA RECIBIDA COOPERATIVA",
        importe: "1205.40",
        texto_importe: "1.205,40 €",
        estado: "conciliado",
        imputado: "1205.40",
        texto_imputado: "1.205,40 €",
        por_conciliar: "0.00",
        texto_por_conciliar: "0,00 €",
      },
      conciliaciones: [
        { clase: "factura_emitida", documento_id: 3, importe: "1205.40", texto_importe: "1.205,40 €" },
      ],
      avisos: ["Apuntados 1.205,40 € de este movimiento a 1 papel(es)."],
    },
  });
  entorno.window.location.hash = "#/cuentas/bancos/5";
  await entorno.manejadores.popstate();
  await new Promise((resolver) => setTimeout(resolver, 80));

  await pulsar(entorno, "banco-conciliar-propuesta", { indice: "0" });
  await new Promise((resolver) => setTimeout(resolver, 80));

  assert.equal(
    cuantasVeces(servidor, "POST /api/bancos/movimientos/5/conciliar"),
    1,
    "no se ha ido a conciliar al servidor",
  );
  const montado = ultimoMontaje();
  assert.equal(montado.type.name, "PantallaDeUnMovimiento", "la conciliación no deja la ficha del movimiento");
  assert.ok(
    montado.props.resultado,
    "la respuesta de la conciliación se pierde: el agricultor no ve a qué papel ha ido el dinero",
  );
  assert.equal(
    montado.props.resultado.conciliaciones.length,
    1,
    "el papel al que se ha apuntado no llega a la pantalla",
  );
  assert.equal(montado.props.resultado.conciliaciones[0].documento_id, 3);
  assert.deepEqual(
    montado.props.resultado.avisos,
    ["Apuntados 1.205,40 € de este movimiento a 1 papel(es)."],
    "el aviso del servidor no se enseña",
  );
  // Y la ficha se ha recargado de verdad: no se queda con lo que había antes de conciliar.
  assert.ok(
    cuantasVeces(servidor, "GET /api/bancos/movimientos/5/propuestas") >= 2,
    "tras conciliar no se ha vuelto a pedir la ficha del movimiento",
  );
  assert.equal(montado.props.movimiento.id, 5, "la ficha recargada no es la del movimiento que se estaba viendo");
});

test("la frase del movimiento ya apuntado del todo llega a la pantalla", async () => {
  // La otra mitad del cableado: la frase **la manda el servidor** (no se escribe en la pantalla) y tiene
  // que llegar hasta la ficha, o la pantalla no podría decir por qué no ofrece nada que apuntar.
  const { entorno } = await conElBanco({
    "/api/bancos/movimientos/5/propuestas": {
      movimiento: {
        id: 5,
        fecha: "2026-06-15",
        concepto: "TRANSFERENCIA RECIBIDA COOPERATIVA",
        importe: "1205.40",
        texto_importe: "1.205,40 €",
        estado: "conciliado",
        imputado: "1205.40",
        texto_imputado: "1.205,40 €",
        por_conciliar: "0.00",
        texto_por_conciliar: "0,00 €",
      },
      pendientes: [],
      propuestas: [],
      ya_apuntado: true,
      texto_ya_apuntado: "Este movimiento ya está apuntado entero a sus papeles, así que no queda nada que repartir.",
    },
  });
  entorno.window.location.hash = "#/cuentas/bancos/5";
  await entorno.manejadores.popstate();
  await new Promise((resolver) => setTimeout(resolver, 80));

  const montado = ultimoMontaje();
  assert.equal(montado.type.name, "PantallaDeUnMovimiento");
  assert.match(
    montado.props.yaApuntado || "",
    /ya está apuntado entero/,
    "la frase del servidor no llega a la ficha: la pantalla no puede decir por qué no hay nada que apuntar",
  );
});

test("la dirección de un movimiento abre su ficha con su identificador", async () => {
  const { entorno, servidor } = await conElBanco();
  entorno.window.location.hash = "#/cuentas/bancos/5";
  await entorno.manejadores.popstate();
  await new Promise((resolver) => setTimeout(resolver, 80));

  const elemento = ultimoMontaje();
  assert.equal(elemento.type.name, "PantallaDeUnMovimiento");
  assert.ok(
    servidor.llamadas.some((ruta) => ruta.includes("/api/bancos/movimientos/5/propuestas")),
    "no se han pedido las propuestas de ese movimiento",
  );
  assert.equal(elemento.props.movimiento.id, 5, "no le llega el movimiento que se está mirando");
});


//
// **Lo que se comprueba aquí, y por qué aquí.** Las dos pantallas tienen sus propias pruebas
// (`tests_js/trabajos.test.js` con 24 y `tests_js/gastos.test.js` con 26) y sus servidores tienen las
// suyas, pero **el cableado de `app.js` no lo probaba nadie**: que el renglón del menú abra la pantalla,
// que le lleguen los datos del servidor y que guardar llame a la puerta que toca. Eso lo escribió el
// coordinador al integrarlas, y es lo que se prueba en este bloque.
//
// En el caso de los trabajos hay algo más: la pantalla espera cada línea **ya escrita** y el servidor
// devuelve los trabajos en crudo, así que la costura (montar las frases) es de `app.js` y se prueba
// aquí: que las líneas salgan con sus palabras, que lo previsto y lo hecho no se mezclen, y que un dato
// que no se sabe se lea como un hueco.
// ---------------------------------------------------------------------------

test("las cuentas se abren desde su renglón del menú y les llegan los gastos del servidor", async () => {
  const { entorno, servidor } = await cargarAplicacion({
    // **La ruta con su campaña, tal y como la pide la pantalla**: las cuentas son las de un año, y
    // `abrirLasCuentas` pregunta por el que se está llevando (el 1 en esta copia del servidor). Si la
    // ruta no casara, el servidor de mentira contestaría vacío y la prueba daría por bueno un hueco.
    "GET /api/gastos?campana_id=1": {
      gastos: [
        {
          id: 7,
          concepto: "Abono 15-15-15",
          categoria: "abono",
          importe: "663.00",
          texto_importe: "663,00 €",
          pagado: "0.00",
          pendiente: "663.00",
          estado: "sin_pagar",
          esta_sin_repartir: true,
          anulado: false,
          repartos: [],
          cuadre: { cuadra: true },
        },
      ],
      pagos: [],
      inversiones: [],
      subvenciones: [],
      cuenta: { gastos: 1 },
      caja: {},
      margenes: {},
      coste_por_clase: {},
      por_pagar: {},
      que_falta: [],
    },
  });
  await pulsar(entorno, "gastos-ver");

  const elemento = ultimoMontaje();
  assert.equal(elemento.type.name, "PantallaDeLasCuentas");
  assert.ok(
    servidor.llamadas.some((ruta) => ruta.includes("/api/gastos")),
    "no se ha pedido la lista de gastos al abrir la pantalla",
  );
  assert.equal(elemento.props.cuentas.gastos.length, 1, "no le llega el gasto del servidor");
  assert.equal(elemento.props.cuentas.gastos[0].concepto, "Abono 15-15-15");
  // **El resumen lo monta `app.js` con las dos formas del servidor**: «Tienes 1 gastos» es lo primero
  // que hace desconfiar de un programa.
  assert.ok(elemento.props.resumen, "no se dice cuántos gastos hay");
  assert.ok(!/1 gastos/.test(elemento.props.resumen), `el singular está mal: «${elemento.props.resumen}»`);
  // Y la tabla del ordenador se prepara aquí, con sus columnas del servidor.
  assert.ok(elemento.props.tabla, "no le llega la tabla del ordenador");
  assert.equal(elemento.props.tabla.columnas.length, 7);

  // **Y guardar un gasto manda de verdad lo que se ha escrito.** Esta comprobación existe porque el
  // botón de guardar **no guardaba nada**: la llamada al servidor decía `{ metodo, cuerpo }` y `api`
  // pasa sus opciones tal cual a `fetch`, que solo entiende `method` y `body`, así que salía un GET sin
  // datos y **no saltaba ningún error**. Lo encontró el subagente de los extractos leyendo el fichero,
  // y esta prueba es la que impide que vuelva: si el cuerpo no viaja, aquí se ve.
  await pulsar(entorno, "gasto-nuevo");
  escribir(entorno, "gasto-concepto", "Gasóleo de la sembradora");
  escribir(entorno, "gasto-importe", "121.00");
  // **El botón de guardar lleva su clase en el `data-*`** (`datos: {clase, id}`), y la prueba se lo pasa
  // igual que lo hace la pantalla: sin él, `guardarLasCuentas` no sabría qué formulario está guardando.
  await pulsar(entorno, "gasto-guardar", { clase: "gasto" });
  const guardado = servidor.enviados.find(
    (envio) => envio.metodo === "POST" && envio.ruta === "/api/gastos",
  );
  assert.ok(guardado, "el botón de guardar de las cuentas no ha mandado nada al servidor");
  assert.equal(
    guardado.cuerpo.concepto,
    "Gasóleo de la sembradora",
    `no viaja lo que se ha escrito: ${JSON.stringify(guardado.cuerpo)}`,
  );
  assert.equal(guardado.cuerpo.importe, "121.00");
});

test("repartir un gasto manda las tierras marcadas y lo que le toca a cada una", async () => {
  // **Lo que faltaba para poder repartir de verdad** (06/10/2026): la pantalla ofrecía los cuatro
  // métodos, mandaba `parcela_ids: []` y el servidor contestaba —con razón— que no se puede repartir lo
  // que no dice entre qué. El gasto se quedaba sin asignar y el recorrido 2 no se podía completar.
  // Aquí se comprueba el cableado entero: marcar una tierra, marcar todas, escribir lo de cada una y
  // que **eso** sea lo que sale hacia la puerta del reparto.
  const { entorno, servidor } = await cargarAplicacion({
    "/api/parcelas": [
      { id: 3, alias: "El Prado", ref_sigpac: "37-70-0-0-503-51", superficie_ha: 4.9 },
      { id: 4, alias: "Las Suertes de Arriba", ref_sigpac: "37-70-0-0-112-4-2", superficie_ha: 3.2 },
    ],
    "GET /api/gastos?campana_id=1": {
      gastos: [
        {
          id: 7,
          concepto: "Gasóleo de la sembradora",
          categoria: "gasoleo",
          importe: "121.00",
          texto_importe: "121,00 €",
          pagado: "0.00",
          texto_pagado: "0,00 €",
          pendiente: "121.00",
          texto_pendiente: "121,00 €",
          estado: "sin_pagar",
          esta_sin_repartir: true,
          anulado: false,
          repartos: [],
          cuadre: { cuadra: true },
        },
      ],
      pagos: [],
      inversiones: [],
      subvenciones: [],
      cuenta: { gastos: 1 },
      caja: {},
      margenes: {},
      coste_por_clase: {},
      por_pagar: {},
      que_falta: [],
    },
    "GET /api/gastos/7": {
      id: 7,
      concepto: "Gasóleo de la sembradora",
      importe: "121.00",
      texto_importe: "121,00 €",
      pagado: "0.00",
      texto_pagado: "0,00 €",
      pendiente: "121.00",
      texto_pendiente: "121,00 €",
      estado: "sin_pagar",
      anulado: false,
      repartos: [],
      cuadre_del_reparto: { repartido: "0.00", texto_repartido: "0,00 €", cuadra: false },
    },
  });
  await pulsar(entorno, "gastos-ver");
  await pulsar(entorno, "gasto-abrir", { id: "7" });
  await pulsar(entorno, "gasto-repartir", { id: "7" });

  // Las tierras tienen que estar ahí para poder marcarlas: son las que ya están descargadas.
  const repartiendo = ultimoMontaje().props.repartiendo;
  assert.ok(repartiendo, "no se ha abierto el formulario de repartir");
  const marcas = (repartiendo.bloques || []).find((bloque) => bloque.tipo === "marcas");
  assert.ok(marcas, `no hay tierras que marcar: ${JSON.stringify(repartiendo.bloques.map((b) => b.tipo))}`);
  assert.deepEqual(
    marcas.opciones.map((opcion) => opcion.texto),
    ["El Prado", "Las Suertes de Arriba"],
    "las tierras del reparto no son las de la finca",
  );
  assert.ok(marcas.todas, "no hay forma de marcar todas las tierras");

  // Se elige «por hectáreas» y se marcan las dos: el servidor repartirá entre ellas por su superficie.
  await pulsar(entorno, "gasto-elegir", { campo: "metodo", valor: "area" });
  await pulsar(entorno, "gasto-marcar-todas");
  const conLasDos = ultimoMontaje().props.repartiendo;
  const pesos = (conLasDos.bloques || []).filter((bloque) =>
    String(bloque.id || "").startsWith("gasto-peso-"),
  );
  assert.deepEqual(
    pesos.map((bloque) => bloque.id),
    ["gasto-peso-3", "gasto-peso-4"],
    "no hay un campo por tierra marcada",
  );

  await pulsar(entorno, "gasto-guardar", { clase: "reparto", id: "7" });
  const reparto = servidor.enviados.find(
    (envio) => envio.metodo === "POST" && envio.ruta === "/api/gastos/7/repartos",
  );
  assert.ok(reparto, "el botón de repartir no ha llamado a la puerta del reparto");
  assert.deepEqual(
    reparto.cuerpo.parcela_ids,
    ["3", "4"],
    `el reparto no dice entre qué tierras: ${JSON.stringify(reparto.cuerpo)}`,
  );
  assert.equal(reparto.cuerpo.metodo, "area");
  assert.equal(reparto.cuerpo.destino_tipo, "tierra");
  assert.equal(reparto.cuerpo.confirmado, true);
});

test("el reparto por horas manda las horas de cada tierra, sin perder las que ya estaban escritas", async () => {
  // La otra mitad: elegir «por horas» y escribir las horas de cada tierra. Y con la trampa de pintar:
  // marcar una tierra **repinta** el formulario, así que las horas ya escritas en las otras tienen que
  // sobrevivir (es la misma trampa que con la categoría de un gasto).
  const { entorno, servidor } = await cargarAplicacion({
    "/api/parcelas": [
      { id: 3, alias: "El Prado", ref_sigpac: "37-70-0-0-503-51", superficie_ha: 4.9 },
      { id: 4, alias: "Las Suertes de Arriba", ref_sigpac: "37-70-0-0-112-4-2", superficie_ha: 3.2 },
    ],
    "GET /api/gastos?campana_id=1": {
      gastos: [],
      pagos: [],
      inversiones: [],
      subvenciones: [],
      cuenta: { gastos: 0 },
      caja: {},
      margenes: {},
      coste_por_clase: {},
      por_pagar: {},
      que_falta: [],
    },
    "GET /api/gastos/7": {
      id: 7,
      concepto: "El gasóleo",
      importe: "121.00",
      texto_importe: "121,00 €",
      pagado: "0.00",
      texto_pagado: "0,00 €",
      pendiente: "121.00",
      texto_pendiente: "121,00 €",
      estado: "sin_pagar",
      anulado: false,
      repartos: [],
      cuadre_del_reparto: { repartido: "0.00", texto_repartido: "0,00 €", cuadra: false },
    },
  });
  await pulsar(entorno, "gastos-ver");
  await pulsar(entorno, "gasto-abrir", { id: "7" });
  await pulsar(entorno, "gasto-repartir", { id: "7" });
  await pulsar(entorno, "gasto-elegir", { campo: "metodo", valor: "horas" });

  await pulsar(entorno, "gasto-marcar", { clave: "3" });
  escribir(entorno, "gasto-peso-3", "4");
  // Al marcar la segunda, el formulario se repinta: las horas de la primera tienen que seguir ahí.
  await pulsar(entorno, "gasto-marcar", { clave: "4" });
  escribir(entorno, "gasto-peso-4", "2");
  await pulsar(entorno, "gasto-guardar", { clase: "reparto", id: "7" });

  const reparto = servidor.enviados.find(
    (envio) => envio.metodo === "POST" && envio.ruta === "/api/gastos/7/repartos",
  );
  assert.ok(reparto, "el botón de repartir no ha llamado a la puerta");
  assert.deepEqual(reparto.cuerpo.parcela_ids, ["3", "4"]);
  assert.equal(reparto.cuerpo.metodo, "horas");
  assert.deepEqual(
    reparto.cuerpo.pesos,
    { 3: "4", 4: "2" },
    `las horas de cada tierra no viajan, o se perdió una al marcar la siguiente: ${JSON.stringify(
      reparto.cuerpo.pesos,
    )}`,
  );
  // Y por horas **no** se mandan trozos: los trozos son del reparto a mano.
  assert.deepEqual(reparto.cuerpo.trozos, []);
});

test("repartir un gasto entre máquinas manda las máquinas, y no las tierras", async () => {
  // **La otra mitad del defecto del reparto por clases.** El formulario ofrecía «entre tierras, entre
  // cultivos o entre máquinas», pero lo que se podía marcar era siempre la lista de tierras: eligiendo
  // «máquina» se mandaban tierras con la etiqueta «máquina» y el servidor guardaba una fila que decía
  // una cosa falsa (ahora lo rechaza, y hay su prueba). Aquí se comprueba el cableado bueno: elegir
  // «máquina» cambia **lo que se marca**, quita de en medio el método de las hectáreas (una máquina no
  // tiene superficie) y lo que sale hacia el servidor son nombres de máquinas.
  const { entorno, servidor } = await cargarAplicacion({
    "/api/parcelas": [
      { id: 3, alias: "El Prado", ref_sigpac: "37-70-0-0-503-51", superficie_ha: 4.9 },
    ],
    "GET /api/maquinaria": {
      maquinas: [
        { id: 5, nombre: "El Landini" },
        { id: 6, nombre: "La cosechadora" },
      ],
    },
    "GET /api/cultivos": {
      campana_id: 1,
      parcelas: [
        // **La forma de verdad de `GET /api/cultivos`**: el cultivo de este año va dentro de `actual`, y
        // ahí se llama `especie`. La tierra que todavía no lo ha dicho trae `actual: null` (y
        // `falta_decirlo: true`), que es el caso que no puede salir como destino.
        { parcela_id: 3, alias: "El Prado", actual: { especie: "TRIGO BLANDO" } },
        { parcela_id: 4, alias: "Las Suertes de Arriba", actual: { especie: "CEBADA" } },
        { parcela_id: 5, alias: "El quiñón", actual: { especie: "TRIGO BLANDO" } },
        { parcela_id: 6, alias: "La era", actual: null, falta_decirlo: true },
      ],
    },
    "GET /api/gastos?campana_id=1": {
      gastos: [
        {
          id: 7,
          concepto: "El seguro del tractor",
          categoria: "seguro",
          importe: "320.00",
          texto_importe: "320,00 €",
          pagado: "0.00",
          pendiente: "320.00",
          estado: "sin_pagar",
          esta_sin_repartir: true,
          anulado: false,
          repartos: [],
          cuadre: { cuadra: true },
        },
      ],
      pagos: [],
      inversiones: [],
      subvenciones: [],
      cuenta: { gastos: 1 },
      caja: {},
      margenes: {},
      coste_por_clase: {},
      por_pagar: {},
      que_falta: [],
    },
    "GET /api/gastos/7": {
      id: 7,
      concepto: "El seguro del tractor",
      importe: "320.00",
      texto_importe: "320,00 €",
      pagado: "0.00",
      pendiente: "320.00",
      estado: "sin_pagar",
      anulado: false,
      repartos: [],
      cuadre_del_reparto: { repartido: "0.00", texto_repartido: "0,00 €", cuadra: false },
    },
  });
  await pulsar(entorno, "gastos-ver");
  await pulsar(entorno, "gasto-abrir", { id: "7" });
  await pulsar(entorno, "gasto-repartir", { id: "7" });

  // Nace en tierras: eso no cambia.
  let repartiendo = ultimoMontaje().props.repartiendo;
  const marcasIniciales = repartiendo.bloques.find((bloque) => bloque.tipo === "marcas");
  assert.deepEqual(marcasIniciales.opciones.map((uno) => uno.texto), ["El Prado"]);

  // Se elige repartir **entre máquinas**: la lista de lo que se marca pasa a ser sus máquinas.
  await pulsar(entorno, "gasto-elegir", { campo: "destino_tipo", valor: "maquina" });
  repartiendo = ultimoMontaje().props.repartiendo;
  const marcas = repartiendo.bloques.find((bloque) => bloque.tipo === "marcas");
  assert.deepEqual(
    marcas.opciones.map((uno) => uno.texto),
    ["El Landini", "La cosechadora"],
    `lo que se marca no son las máquinas: ${JSON.stringify(marcas.opciones)}`,
  );
  assert.deepEqual(marcas.marcadas, [], "al cambiar de destino siguen marcadas las tierras");
  // Y el método de las hectáreas no se ofrece: una máquina no tiene superficie.
  const metodo = repartiendo.bloques.find((bloque) => bloque.campo === "metodo");
  assert.ok(
    !metodo.opciones.some((uno) => uno.valor === "area"),
    "se ofrece repartir por hectáreas entre máquinas, y el servidor lo va a rechazar",
  );

  // Por horas, con las dos máquinas marcadas y sus horas.
  await pulsar(entorno, "gasto-elegir", { campo: "metodo", valor: "horas" });
  await pulsar(entorno, "gasto-marcar-todas");
  escribir(entorno, "gasto-peso-El_Landini", "6");
  escribir(entorno, "gasto-peso-La_cosechadora", "2");
  await pulsar(entorno, "gasto-guardar", { clase: "reparto", id: "7" });

  const reparto = servidor.enviados.find(
    (envio) => envio.metodo === "POST" && envio.ruta === "/api/gastos/7/repartos",
  );
  assert.ok(reparto, "el botón de repartir no ha llamado a la puerta");
  assert.equal(reparto.cuerpo.destino_tipo, "maquina");
  assert.deepEqual(
    reparto.cuerpo.parcela_ids,
    [],
    "se mandan tierras en un reparto entre máquinas: es el defecto que afirmaba algo falso",
  );
  assert.deepEqual(
    reparto.cuerpo.pesos,
    { "El Landini": "6", "La cosechadora": "2" },
    `lo que viaja no son las máquinas con sus horas: ${JSON.stringify(reparto.cuerpo.pesos)}`,
  );
});

test("repartir un gasto entre cultivos marca los cultivos que tiene sembrados", async () => {
  // Y la tercera clase: los cultivos. Salen de lo que el agricultor tiene sembrado este año —los mismos
  // que lee en «qué hay sembrado»—, por su nombre, y **sin colar el que no dice nada**: repartir «a lo
  // que no se sabe» sería inventarse el sitio.
  const { entorno, servidor } = await cargarAplicacion({
    "/api/parcelas": [{ id: 3, alias: "El Prado", superficie_ha: 4.9 }],
    "GET /api/cultivos": {
      campana_id: 1,
      parcelas: [
        // La forma de verdad: el cultivo del año va en `actual.especie`.
        { parcela_id: 3, alias: "El Prado", actual: { especie: "TRIGO BLANDO" } },
        { parcela_id: 4, alias: "Las Suertes de Arriba", actual: { especie: "CEBADA" } },
        { parcela_id: 5, alias: "El quiñón", actual: { especie: "TRIGO BLANDO" } },
        { parcela_id: 6, alias: "La era", actual: null, falta_decirlo: true },
      ],
    },
    "GET /api/gastos?campana_id=1": {
      gastos: [
        {
          id: 7,
          concepto: "El gasóleo de la siega",
          categoria: "gasoleo",
          importe: "254.10",
          texto_importe: "254,10 €",
          pagado: "0.00",
          pendiente: "254.10",
          estado: "sin_pagar",
          esta_sin_repartir: true,
          anulado: false,
          repartos: [],
          cuadre: { cuadra: true },
        },
      ],
      pagos: [],
      inversiones: [],
      subvenciones: [],
      cuenta: { gastos: 1 },
      caja: {},
      margenes: {},
      coste_por_clase: {},
      por_pagar: {},
      que_falta: [],
    },
    "GET /api/gastos/7": {
      id: 7,
      concepto: "El gasóleo de la siega",
      importe: "254.10",
      pagado: "0.00",
      pendiente: "254.10",
      estado: "sin_pagar",
      anulado: false,
      repartos: [],
      cuadre_del_reparto: { repartido: "0.00", cuadra: false },
    },
  });
  await pulsar(entorno, "gastos-ver");
  await pulsar(entorno, "gasto-abrir", { id: "7" });
  await pulsar(entorno, "gasto-repartir", { id: "7" });
  await pulsar(entorno, "gasto-elegir", { campo: "destino_tipo", valor: "cultivo" });

  const repartiendo = ultimoMontaje().props.repartiendo;
  const marcas = repartiendo.bloques.find((bloque) => bloque.tipo === "marcas");
  assert.deepEqual(
    marcas.opciones.map((uno) => uno.texto),
    ["TRIGO BLANDO", "CEBADA"],
    `los cultivos del reparto no son los que tiene sembrados: ${JSON.stringify(marcas.opciones)}`,
  );

  // A mano, un importe a cada cultivo: lo que viaja son los nombres de los cultivos.
  await pulsar(entorno, "gasto-elegir", { campo: "metodo", valor: "manual" });
  await pulsar(entorno, "gasto-marcar-todas");
  escribir(entorno, "gasto-peso-TRIGO_BLANDO", "150,00");
  escribir(entorno, "gasto-peso-CEBADA", "104,10");
  await pulsar(entorno, "gasto-guardar", { clase: "reparto", id: "7" });

  const reparto = servidor.enviados.find(
    (envio) => envio.metodo === "POST" && envio.ruta === "/api/gastos/7/repartos",
  );
  assert.ok(reparto, "el botón de repartir no ha llamado a la puerta");
  assert.equal(reparto.cuerpo.destino_tipo, "cultivo");
  assert.deepEqual(reparto.cuerpo.parcela_ids, [], "se mandan tierras en un reparto entre cultivos");
  assert.deepEqual(
    reparto.cuerpo.trozos,
    [
      { destino_tipo: "cultivo", destino: "TRIGO BLANDO", importe: "150,00" },
      { destino_tipo: "cultivo", destino: "CEBADA", importe: "104,10" },
    ],
    `lo que viaja no son los cultivos con su importe: ${JSON.stringify(reparto.cuerpo.trozos)}`,
  );
});

/** Una explotación con dos tierras, un plan, un trabajo hecho y una máquina. */
function conLosTrabajos(cambios = {}) {
  return cargarAplicacion({
    "GET /api/trabajos": {
      hechos: [
        {
          id: 34,
          de_donde: "hecho",
          tipo: "siembra",
          subtipo: null,
          fecha: "2026-03-01",
          parcela_id: 1,
          superficie_ha: 3.0,
          horas: null,
          equipo_id: 5,
          anulado: false,
          observaciones: null,
          insumos: [],
        },
      ],
      previstos: [
        {
          id: 12,
          de_donde: "previsto",
          tipo: "laboreo",
          subtipo: "cultivador",
          fecha_prevista: "2026-04-20",
          dias_que_faltan: 19,
          parcela_id: 2,
          superficie_ha: null,
          horas_previstas: 4,
          anulado: false,
          insumos: [],
        },
        {
          // **Sin día**: el plan del que no se sabe cuándo. Tiene que decirse así, y no con un día
          // inventado ni con el de hoy.
          id: 13,
          de_donde: "previsto",
          tipo: "laboreo",
          subtipo: "rodillo",
          fecha_prevista: null,
          dias_que_faltan: null,
          parcela_id: 1,
          anulado: false,
          insumos: [],
        },
      ],
      reenviados: 0,
      no_se_pudo_comprobar_si_ya_estaba: 0,
      aviso_codigo: "",
      lo_previsto_y_lo_hecho: [],
      hoy: "2026-04-01",
      textos: {},
    },
    "GET /api/trabajos/que-falta": {
      tipos: ["siembra", "laboreo", "riego"],
      subtipos_de_laboreo: ["rodillo", "cultivador", "arado"],
    },
    "GET /api/maquinaria": { maquinas: [{ id: 5, nombre: "El Landini" }] },
    "GET /api/almacen/existencias": { articulos: [] },
    ...cambios,
  });
}

test("un plan que ya se cumplió llega a la pantalla con su día y sin su botón", async () => {
  // **La costura que faltaba del defecto del 409.** La agenda trae los planes cumplidos, y el vínculo con
  // el hecho que salió de ellos lo puso el servidor en la **labor** (`previsto_id`). Si `app.js` no cruza
  // las dos listas, la pantalla no puede saber cuál está cumplido y le pinta «YA LO HE HECHO» otra vez:
  // ese botón lleva a un 409 y se queda ahí. Aquí se comprueba la costura entera —el cruce y la frase— y
  // que el botón no llega a la pantalla.
  const { entorno } = await conLosTrabajos({
    "GET /api/trabajos": {
      hechos: [
        {
          id: 34,
          de_donde: "hecho",
          tipo: "laboreo",
          subtipo: "cultivador",
          fecha: "2026-04-25",
          previsto_id: 12,
          parcela_id: 2,
          superficie_ha: 3.0,
          horas: 5,
          equipo_id: null,
          anulado: false,
          observaciones: null,
          insumos: [],
        },
      ],
      previstos: [
        {
          id: 12,
          de_donde: "previsto",
          tipo: "laboreo",
          subtipo: "cultivador",
          estado: "realizado",
          fecha_prevista: "2026-04-20",
          dias_que_faltan: 19,
          parcela_id: 2,
          superficie_ha: null,
          anulado: false,
          insumos: [],
        },
        {
          id: 13,
          de_donde: "previsto",
          tipo: "siembra",
          subtipo: null,
          estado: "previsto",
          fecha_prevista: "2026-03-10",
          dias_que_faltan: null,
          parcela_id: 1,
          superficie_ha: null,
          anulado: false,
          insumos: [],
        },
      ],
      reenviados: 0,
      no_se_pudo_comprobar_si_ya_estaba: 0,
      aviso_codigo: "",
      lo_previsto_y_lo_hecho: [],
      hoy: "2026-04-01",
      textos: {},
    },
  });
  await pulsar(entorno, "trabajos-ver");

  const props = ultimoMontaje().props;
  const cumplido = props.previstos.find((uno) => uno.id === 12);
  const pendiente = props.previstos.find((uno) => uno.id === 13);
  assert.match(
    cumplido.cuando_lo_hice || "",
    /25\/04\/2026/,
    `el plan cumplido no dice cuándo se hizo: «${cumplido.cuando_lo_hice}»`,
  );
  assert.equal(pendiente.cuando_lo_hice, "", "un plan sin cumplir se ha marcado como cumplido");
});

test("la agenda monta lo previsto y lo hecho, en dos listas y con sus frases", async () => {
  const { entorno } = await conLosTrabajos();
  await pulsar(entorno, "trabajos-ver");

  const elemento = ultimoMontaje();
  assert.equal(elemento.type.name, "PantallaDeLosTrabajos");
  const props = elemento.props;
  assert.equal(props.previstos.length, 2, "no llegan los dos planes");
  assert.equal(props.hechos.length, 1, "no llega el trabajo hecho");

  // **Lo previsto y lo hecho no se mezclan**: es la mitad del ticket. Un plan nunca sale como hecho.
  const idsPrevistos = props.previstos.map((uno) => uno.id);
  const idsHechos = props.hechos.map((uno) => uno.id);
  assert.deepEqual(idsPrevistos, [12, 13]);
  assert.deepEqual(idsHechos, [34]);

  // La línea del plan: su tipo y su apero, su día **y los días que faltan**, con la frase del servidor.
  const plan = props.previstos[0];
  assert.match(plan.titulo, /LABRADO/, `el título del plan no dice qué trabajo es: «${plan.titulo}»`);
  assert.match(plan.titulo, /cultivador/, "no dice con qué apero");
  assert.match(plan.cuando, /20\/04\/2026/, `el día del plan no está: «${plan.cuando}»`);
  assert.match(plan.cuando, /19 días/, `no dice cuántos días faltan: «${plan.cuando}»`);
  // Y la frase que impide el malentendido: esto no ha gastado nada.
  assert.ok(plan.no_gasta, "no se dice que lo previsto no ha gastado nada");

  // **Un plan sin día lo dice**, y no se le pone el de hoy: «sin decir» es la respuesta del programa.
  assert.equal(props.previstos[1].cuando, "Sin decir", "un plan sin día se ha rellenado con algo");

  // El trabajo hecho: su día y **lo que le falta decir**, que es un dato y no un cero.
  const hecho = props.hechos[0];
  assert.match(hecho.cuando, /01\/03\/2026/);
  assert.ok(
    hecho.faltan.some((linea) => /horas/i.test(linea)),
    `no se dice que al trabajo le faltan las horas: ${JSON.stringify(hecho.faltan)}`,
  );
  assert.ok(hecho.faltan.every((linea) => /Sin decir/.test(linea)), "un hueco no se dice como hueco");
});

test("marcar lo hecho enseña al lado lo que se había pensado", async () => {
  const { entorno } = await conLosTrabajos();
  await pulsar(entorno, "trabajos-ver");
  await pulsar(entorno, "trabajo-hecho", { id: "12" });

  const elemento = ultimoMontaje();
  assert.equal(elemento.type.name, "PantallaDeUnTrabajo");
  assert.equal(elemento.props.modo, "hecho", "no se ha abierto la ficha en modo de apuntar lo hecho");
  assert.ok(elemento.props.previsto, "no se enseña lo que se había pensado al lado de lo que pasó");
  assert.ok(
    elemento.props.previsto.filas.some((fila) => /cultivador/.test(fila.valor)),
    "lo que se había pensado no dice qué trabajo era",
  );
});

test("al marcar lo hecho se puede decir de qué envase salió el producto", async () => {
  // **El defecto que esto fija, encontrado recorriendo el recorrido 4 en un navegador.** `app.js` leía
  // `articulo.envases` de lo que contesta `/api/almacen/existencias`, y ese campo **no existe**: los
  // envases de un artículo vienen en `articulo.lotes` (es lo que pinta el libro del almacén). Con el
  // nombre equivocado la lista salía siempre vacía, así que el desplegable de insumos no tenía ni una
  // opción y **no se podía decir de qué envase se gastó el producto**: esa mitad del recorrido era
  // imposible desde la pantalla. Ninguna prueba lo cazaba porque las de aquí mandaban `articulos: []`.
  const { entorno } = await conLosTrabajos({
    "GET /api/almacen/existencias": unasExistencias(),
  });
  await pulsar(entorno, "trabajos-ver");
  await pulsar(entorno, "trabajo-hecho", { id: "12" });

  const elemento = ultimoMontaje();
  assert.equal(elemento.type.name, "PantallaDeUnTrabajo", "no se ha abierto la ficha de lo hecho");
  const insumos = elemento.props.insumos || [];
  assert.equal(insumos.length, 1, `el desplegable de insumos sale vacío: ${JSON.stringify(insumos)}`);
  assert.equal(insumos[0].valor, 8, "la opción no lleva el envase del que sale el producto");
  assert.match(
    insumos[0].texto,
    /Glifosato 36 SL/,
    `la opción no dice qué producto es: «${insumos[0].texto}»`,
  );
  assert.match(insumos[0].texto, /4471-A/, `la opción no dice de qué envase se trata: «${insumos[0].texto}»`);
});

test("guardar un trabajo llama a la puerta que le toca, según lo que se esté haciendo", async () => {
  // **Cinco modos, cinco puertas.** Es lo que impide que apuntar lo hecho se guarde como un plan (o al
  // revés), que es justo lo que el ticket viene a separar: lo previsto no gasta y lo hecho sí.
  const casos = [
    {
      que: "planificar",
      pulsaciones: [["trabajo-planificar"], ["trabajo-previsto-guardar"]],
      comprobacion: (envio) => {
        assert.equal(envio.metodo, "POST");
        assert.equal(envio.ruta, "/api/trabajos/previstos");
      },
    },
    {
      que: "marcar lo hecho",
      pulsaciones: [["trabajo-hecho", { id: "12" }], ["trabajo-hecho-guardar"]],
      comprobacion: (envio) => {
        assert.equal(envio.metodo, "POST");
        assert.equal(envio.ruta, "/api/trabajos/previstos/12/hecho");
      },
    },
    {
      que: "corregir",
      pulsaciones: [["trabajo-corregir", { id: "34" }], ["trabajo-guardar"]],
      comprobacion: (envio) => {
        assert.equal(envio.metodo, "PUT");
        assert.equal(envio.ruta, "/api/trabajos/34");
      },
    },
    {
      que: "anular un trabajo hecho",
      pulsaciones: [["trabajo-anular", { id: "34" }], ["trabajo-anular-confirmar"]],
      comprobacion: (envio) => {
        assert.equal(envio.metodo, "POST");
        assert.equal(envio.ruta, "/api/trabajos/34/anular");
      },
    },
    {
      que: "cancelar un plan",
      pulsaciones: [["trabajo-cancelar", { id: "12" }], ["trabajo-anular-confirmar"]],
      comprobacion: (envio) => {
        assert.equal(envio.metodo, "POST");
        assert.equal(
          envio.ruta,
          "/api/trabajos/previstos/12/cancelar",
          "un plan se cancela, no se anula: son dos puertas distintas",
        );
      },
    },
  ];
  for (const caso of casos) {
    const { entorno, servidor } = await conLosTrabajos();
    await pulsar(entorno, "trabajos-ver");
    for (const [accion, datos] of caso.pulsaciones) await pulsar(entorno, accion, datos || {});
    // El motivo de anular y de cancelar hace falta: sin él la pantalla no manda nada (y lo dice).
    if (caso.que.startsWith("anular") || caso.que.startsWith("cancelar")) {
      escribir(entorno, "trabajo-motivo", "Se rompió el apero");
      await pulsar(entorno, caso.pulsaciones[caso.pulsaciones.length - 1][0]);
    }
    const envio = servidor.enviados.find(
      (uno) => uno.ruta.startsWith("/api/trabajos") && uno.metodo !== "GET",
    );
    assert.ok(envio, `«${caso.que}» no ha mandado nada al servidor`);
    caso.comprobacion(envio);
  }
});

test("la historia de una tierra se abre por su dirección y enseña todo lo que ha pasado", async () => {
  const { entorno, servidor } = await conLosTrabajos({
    "GET /api/trabajos/tierra/1": {
      tierra: { id: 1, alias: "El Prado", superficie_ha: 3.0 },
      historial: {
        lineas: [
          {
            id: 34,
            trabajo: {
              id: 34,
              tipo: "siembra",
              fecha: "2026-03-01",
              superficie_ha: 3.0,
              horas: null,
              equipo_id: 5,
              insumos: [],
            },
            anulado: false,
            revisado: false,
            firmado: false,
            motivo_anulacion: null,
          },
          {
            id: 35,
            trabajo: {
              id: 35,
              tipo: "laboreo",
              subtipo: "rodillo",
              fecha: "2026-03-10",
              superficie_ha: 3.0,
              horas: 2.0,
              equipo_id: 5,
              insumos: [],
            },
            anulado: true,
            motivo_anulacion: "Se pasó dos veces",
            revisado: false,
            firmado: false,
          },
        ],
      },
      estado: {
        cultivo_declarado: { cultivo: "Trigo blando", variedad: "Meseta", fecha: "2026-03-01" },
        // El nombre del campo es el que devuelve el servidor (`trabajos.py`, con su `un_` delante).
        un_apero_no_cambia_lo_sembrado_codigo: "TJ8_un_rodillo_no_cambia_lo_sembrado",
        ultima_labor: { tipo: "laboreo", subtipo: "rodillo", fecha: "2026-03-10" },
        que_queda_previsto: [{ id: 12, tipo: "laboreo", subtipo: "cultivador", fecha_prevista: "2026-04-20" }],
      },
      lo_que_no_se_sabe: {},
    },
    // **Lo que ha costado esa tierra** (T13 + T15): se pide a la puerta de las cuentas, con el año que
    // se está llevando. La pantalla de la historia junta los dos hechos —los trabajos y el dinero— y
    // esta prueba comprueba que el de las cuentas llega de verdad (si no llegara, el bloque no saldría
    // y nadie se enteraría: la pantalla se enseña igual, a propósito).
    "GET /api/gastos/de-una-tierra/1?campana_id=1": {
      parcela_id: 1,
      tierra: "El Prado",
      directos: "250.00",
      texto_directos: "250,00 €",
      repartidos: "60.00",
      texto_repartidos: "60,00 €",
      total_conocido: "310.00",
      texto_total: "310,00 €",
      sin_importe: 1,
      cuantos: 2,
      filas: [
        {
          gasto_id: 7,
          que_es: "Gasóleo",
          fecha: "2026-03-04",
          importe: "250.00",
          texto_importe: "250,00 €",
          de_donde: "directo",
        },
        {
          gasto_id: 9,
          que_es: "Seguro de la finca",
          fecha: null,
          importe: "60.00",
          texto_importe: "60,00 €",
          de_donde: "repartido",
        },
      ],
    },
  });
  // **La dirección manda**: se abre la historia de una tierra poniendo su dirección, que es como llega
  // desde un enlace o al recargar. Se lee de la barra con `laDireccion` como en las demás pruebas de T04.
  entorno.window.location.hash = "#/tierras/1/historial";
  await entorno.manejadores.popstate();
  await new Promise((resolver) => setTimeout(resolver, 60));

  const elemento = ultimoMontaje();
  assert.equal(elemento.type.name, "PantallaDeLaTierra");
  const props = elemento.props;
  assert.ok(
    servidor.llamadas.some((r) => r.includes("/api/trabajos/tierra/1")),
    "no se ha pedido la historia de esa tierra",
  );
  assert.equal(props.tierra.nombre, "El Prado");
  assert.equal(props.historial.length, 2, "no sale todo lo que ha pasado");
  // **Lo anulado sale dentro, con su motivo**: esconderlo haría que el agricultor no pudiera explicar su
  // cuaderno, que es la regla del ticket.
  const anulada = props.historial.find((linea) => linea.anulado);
  assert.ok(anulada, "lo anulado se ha escondido");
  assert.equal(anulada.motivo_anulacion, "Se pasó dos veces");
  assert.match(anulada.titulo, /rodillo/, "la línea anulada no dice qué trabajo era");
  // Y las horas que no constan se leen como «sin decir», nunca como un cero.
  const sembrada = props.historial.find((linea) => /SEMBRADO/.test(linea.titulo));
  assert.ok(sembrada, `no sale la siembra en el historial: ${JSON.stringify(props.historial.map((l) => l.titulo))}`);
  assert.ok(
    sembrada.filas.some((fila) => /horas/i.test(fila.etiqueta) && fila.valor === "Sin decir"),
    "las horas que no constan no se dicen como un hueco",
  );
  // El estado: qué hay sembrado, el apero que no cambia nada y lo que queda previsto, aparte de lo hecho.
  assert.equal(props.estado.cultivo_declarado.cultivo, "Trigo blando");
  assert.ok(props.estado.apero_no_cambia, "no se dice que el rodillo no borra lo sembrado");
  assert.equal(props.estado.previstos.length, 1);
  assert.match(props.estado.previstos[0].cuando, /20\/04\/2026/);

  // **Y lo que ha costado la tierra** (T13 + T15): los dos hechos juntos, que es el recorrido 5 del
  // encargo («qué cultivo tiene, qué trabajos se han hecho, qué queda previsto y qué costes conocidos
  // tiene»). Si esta puerta no se pidiera, el bloque no saldría y la pantalla se vería igual.
  assert.ok(props.costes, "no se ha pedido lo que ha costado la tierra");
  assert.ok(
    servidor.llamadas.some((r) => r.includes("/api/gastos/de-una-tierra/1")),
    "no se ha ido a la puerta de las cuentas a por el coste de esa tierra",
  );
  assert.equal(props.costes.texto_total, "310,00 €");
  assert.equal(props.costes.sin_importe, 1, "no se dice que un gasto de esa tierra no trae importe");
});

test("la historia de una tierra se abre desde el botón de la ficha de la tierra", async () => {
  // **Esta prueba existe por un defecto de verdad** (05/10/2026): la pantalla de la historia de una
  // tierra existía, su dirección funcionaba y **no había ningún botón en toda la aplicación que
  // llevara a ella**. El recorrido 5 del encargo («abrir tierra → qué cultivo tiene, qué trabajos se han
  // hecho, qué queda previsto y qué costes conocidos») solo se podía hacer escribiendo la dirección a
  // mano, que para el agricultor es no poder hacerlo.
  //
  // Se mira lo que solo se puede mirar aquí: que el botón que se pinta en la ficha de la tierra lleva
  // **una acción con dueño** (si nadie la atiende, pulsarla no hace nada y la pantalla se ve igual).
  const { entorno, servidor } = await conLosTrabajos({
    "/api/parcelas": TRES_TIERRAS,
    // La puerta de la historia de esa tierra, con lo mínimo para que conteste: es lo que hace que el
    // botón tenga a dónde ir y que la pantalla se pinte con datos.
    "GET /api/trabajos/tierra/1": {
      tierra: { id: 1, alias: "El Prado", superficie_ha: 3.0 },
      historial: { lineas: [] },
      estado: { cultivo_declarado: null, previstos: [] },
      trabajos_sin_hectareas: 0,
      lo_que_no_se_sabe: {},
      falta: {},
      textos: {},
    },
  });
  await pulsar(entorno, "mis-cosas");

  // Primero, que el botón **está** en la ficha de la tierra, con la acción que después se pulsa.
  const seccion = montajes[montajes.length - 1].elemento.props.secciones[0];
  const acciones = seccion.elementos[0].acciones || [];
  const elBoton = acciones.find((una) => una.accion === "tierra-historia");
  assert.ok(
    elBoton,
    `la ficha de la tierra no tiene el botón de su historia: ${JSON.stringify(acciones.map((a) => a.accion))}`,
  );
  assert.equal(elBoton.datos.id, 1, "el botón no dice de qué tierra es la historia");
  assert.match(elBoton.etiqueta, /LO QUE HA PASADO/, `la etiqueta del botón es «${elBoton.etiqueta}»`);

  await pulsar(entorno, "tierra-historia", elBoton.datos);
  // La pantalla se pinta **dos veces**: primero en blanco (para no hacer esperar al agricultor) y otra
  // vez con lo que contesta el servidor. La dirección se escribe en la segunda, así que hay que dejar
  // que llegue, como en la prueba de arriba.
  await new Promise((resolver) => setTimeout(resolver, 60));
  const elemento = ultimoMontaje();
  assert.equal(
    elemento.type.name,
    "PantallaDeLaTierra",
    "pulsar el botón no abre la historia de la tierra",
  );
  assert.ok(
    servidor.llamadas.some((r) => r.includes("/api/trabajos/tierra/1")),
    "no se ha pedido la historia de esa tierra",
  );
  // Y la dirección pasa a ser la suya: recargar deja al agricultor en la historia que estaba mirando.
  assert.equal(
    entorno.window.location.hash.split("?")[0],
    "#/tierras/1/historial",
    `la dirección no es la de la historia: ${entorno.window.location.hash}`,
  );
});

test("la misma tierra se dice igual en el panel y en su ficha", async () => {
  // **Una tierra, una ficha** (07/10/2026, del encargo del rediseño). Hoy la tierra se puede mirar en
  // cuatro sitios —el panel de la fila, su historia, sus versiones y su cultivo—, y **nadie comprobaba
  // que dijeran lo mismo**: la revisión del recorrido avisó de que el panel usa su propia fuente de datos
  // y de que ninguna prueba exigía que coincidieran. Esta es la primera: **el nombre y la superficie de
  // la tierra son los mismos** se mire por donde se mire. Si un día se separan, se verá aquí antes que en
  // la pantalla del agricultor.
  const { entorno } = await conLosTrabajos({
    "/api/parcelas": TRES_TIERRAS,
    // **Las dos puertas tienen que decir las mismas hectáreas** porque en el servidor salen de la misma
    // columna (`parcela.superficie_ha`): el panel las lee de `/api/parcelas` y la ficha, de
    // `/api/trabajos/tierra/<id>`. Aquí se copia el valor de `TRES_TIERRAS` a propósito: si se pusiera
    // otro, la prueba estaría comprobando una diferencia que el servidor no puede producir.
    "GET /api/trabajos/tierra/1": {
      tierra: { id: 1, alias: "El Prado", superficie_ha: 4.9 },
      historial: { lineas: [] },
      estado: { cultivo_declarado: null, previstos: [] },
      trabajos_sin_hectareas: 0,
      lo_que_no_se_sabe: {},
      falta: {},
      textos: {},
    },
  });
  await pulsar(entorno, "mis-cosas");

  // Lo que dice la lista de la tierra (es lo que el agricultor acaba de leer al tocarla).
  const seccion = montajes[montajes.length - 1].elemento.props.secciones[0];
  const enLaLista = seccion.elementos[0];

  // Lo que dice el **panel** de esa tierra, al elegirla. (El panel viaja dentro de la sección de la
  // lista: `seccion.tabla.panel`, que es lo que usa la prueba de «elegir una tierra…».)
  await pulsar(entorno, "elegir-fila", { tabla: "tierras", id: "1" });
  const panel = tablaDeTierrasPedida().panel;
  const superficieEnElPanel = (panel.filas || []).find((fila) => /hect[áa]reas/i.test(fila.etiqueta));

  // Y lo que dice su **ficha**.
  await pulsar(entorno, "tierra-historia", { id: 1 });
  await new Promise((resolver) => setTimeout(resolver, 60));
  const ficha = ultimoMontaje();
  assert.equal(ficha.type.name, "PantallaDeLaTierra", "la ficha no se ha abierto");

  const nombreEnLaFicha = ficha.props.tierra.nombre;
  const superficieEnLaFicha = ficha.props.tierra.superficie;
  assert.ok(nombreEnLaFicha, "la ficha no dice el nombre de la tierra");
  assert.equal(
    nombreEnLaFicha,
    enLaLista.etiqueta,
    `la lista y la ficha dicen cosas distintas de la misma tierra: «${enLaLista.etiqueta}» y «${nombreEnLaFicha}»`,
  );
  assert.ok(superficieEnElPanel, "el panel no dice las hectáreas de la tierra");
  // Se comparan los dígitos y no el texto entero: el panel puede escribir «3 ha» y la ficha «3 ha» o
  // «3,00», y lo que importa —que es el mismo número— es lo que se está comprobando.
  const digitos = (texto) => String(texto).replace(/[^0-9]/g, "");
  assert.equal(
    digitos(superficieEnLaFicha),
    digitos(superficieEnElPanel.valor),
    "el panel y la ficha dicen superficies distintas de la misma tierra: "
      + `«${superficieEnElPanel.valor}» y «${superficieEnLaFicha}»`,
  );
});

// ---------------------------------------------------------------------------
// El borrador de un formulario (CRM-08, 17/10/2026)
//
// El ticket lo pide asi: *«borrador **por usuario/finca**, guardar local, cierre/reapertura, respuesta
// perdida…»*. Y aqui se prueba **lo que importa del cierre/reapertura**: que lo que quedo a medias
// **vuelve al formulario** cuando se abre la aplicacion otra vez.
//
// ***Se arranca con el borrador ya en el almacen*** -`extra.almacen`-, que es lo que pasa de verdad: al
// cerrar la pestana la memoria se va y el almacen se queda. *Comprobar solo la memoria no probaria nada,
// porque eso ya funcionaba antes.*

test("un borrador de factura a medias vuelve al formulario al abrir la aplicacion", async () => {
  // ***La clave lleva la cuenta (1) y la finca (1)***, que son las de las pruebas: por eso el borrador de
  // una cuenta **no sale en el formulario de otra**.
  const { entorno } = await cargarAplicacion(
    // ***Y hay que decirle quien es***: al arrancar, la aplicacion pregunta a `/api/cuenta/yo` **antes de
    // pintar nada**, y el borrador no puede ser de nadie si esa respuesta no llega.
    { "GET /api/cuenta/yo": { id: 1, explotacion: { id: 1 }, puede_modificar: true, puede_ver_lo_economico: true } },
    {
      almacen: {
        "cuedigital.borrador.1.1.factura": {
          datos: {
            numero: "2026/00123",
            fecha: "2026-03-15",
            cliente: "COOPERATIVA AGRICOLA DE PENARANDA",
          },
          cuando: "2026-03-15T10:00:00.000Z",
        },
      },
    },
  );
  await pulsar(entorno, "inicio", { ir: "ventas" });
  // ***Y facturar se abre pulsando***, no por su clave: la ruta de `facturar_entregas` es
  // `["ventas", "facturar"]`, y `inicio` navega por el **patron entero**. *Asi es como llega el agricultor:
  // entrando en lo vendido y pulsando FACTURAR.*
  await pulsar(entorno, "ventas-facturar");

  // ***Y se mira DONDE ESTA***: la pantalla de facturar es React
  // (`react/pantallas/facturar_entregas.js`), y lo suyo **no se ve en el DOM de mentira**. *Se comprueba
  // por las propiedades que recibe, que es como lo hacen las demas pruebas de pantallas de React.*
  const elemento = ultimoMontaje();
  assert.equal(
    elemento.type.name,
    "PantallaFacturarEntregas",
    "no se ha abierto la pantalla de facturar",
  );
  const borrador = elemento.props.borrador || {};
  assert.equal(
    borrador.numero,
    "2026/00123",
    "***el borrador que quedo a medias no vuelve al formulario***",
  );
  assert.equal(
    borrador.cliente,
    "COOPERATIVA AGRICOLA DE PENARANDA",
    "el cliente del borrador tampoco vuelve",
  );
});

test("y sin borrador, el formulario sale limpio", async () => {
  // ***La otra mitad***: que no se invente nada. *Un formulario con el numero de una factura anterior seria
  // peor que uno vacio: se guardaria una factura con datos que no son.*
  const { entorno } = await cargarAplicacion({
    "GET /api/cuenta/yo": { id: 1, explotacion: { id: 1 } },
  });
  await pulsar(entorno, "inicio", { ir: "ventas" });
  // ***Y facturar se abre pulsando***, no por su clave: la ruta de `facturar_entregas` es
  // `["ventas", "facturar"]`, y `inicio` navega por el **patron entero**. *Asi es como llega el agricultor:
  // entrando en lo vendido y pulsando FACTURAR.*
  await pulsar(entorno, "ventas-facturar");

  const elemento = ultimoMontaje();
  assert.equal(elemento.type.name, "PantallaFacturarEntregas");
  const borrador = elemento.props.borrador || {};
  assert.ok(
    !borrador.numero,
    `sin borrador el numero tiene que salir vacio, y sale ${JSON.stringify(borrador.numero)}`,
  );
});


test("rectificar un papel manda el identificador elegido al servidor", async () => {
  const papel = { id: 5, titulo: "La factura corregida", campos: {}, vinculos: [], rectificada_por: [] };
  const { entorno, servidor } = await cargarAplicacion({
    "/api/bandeja/5": papel,
    "/api/bandeja/5/rectificar": { papel, avisos: [] },
    "/api/bandeja": { papeles: [papel] },
  });
  await pulsar(entorno, "bandeja-abrir", { id: "5" });
  escribir(entorno, "bandeja-rectifica-a", "2");
  await pulsar(entorno, "bandeja-rectificar", { id: "5" });
  const enviado = servidor.enviados.find((e) => e.ruta === "/api/bandeja/5/rectificar");
  assert.ok(enviado, "el botón debe enviar la rectificación");
  assert.deepEqual(enviado.cuerpo, { rectifica_a_id: 2 });
});

test("subir el papel de una factura sin elegir fichero muestra el aviso y conserva la lista", async () => {
  const { entorno, servidor } = await cargarAplicacion();
  await pulsar(entorno, "facturas-abrir");
  await pulsar(entorno, "factura-papel-subir", { id: "7" });
  assert.equal(ultimoMontaje().props.error, RESPUESTAS["/api/interfaz"].facturas.que_fichero);
  assert.ok(!servidor.enviados.some((e) => e.ruta === "/api/facturas/7/fichero"));
});

// ---------------------------------------------------------------------------
// ***Lo local tiene dueño: los rechazos de una cuenta no los ve otra*** (21/10/2026)
// ---------------------------------------------------------------------------

test("los rechazos de una cuenta no los ve otra", async () => {
  // *`CLAVE_RECHAZADOS` y `CLAVE_ULTIMO` eran **globales**: en el mismo móvil, **un rechazo de A se le enseñaba a
  // B**. Es el mismo fallo que se cerró en los pendientes, y el encargo pide cerrarlo «completo, no solo el filtrado
  // de pendientes».*
  //
  // *La regresión reproduce lo de antes: se guarda un rechazo de A bajo su clave -con dueño-, y se carga la
  // aplicación **como B**. Si las claves fueran globales, B leería el rechazo de A y lo enseñaría.*
  const unVale = (uid, eid) =>
    `${Buffer.from(JSON.stringify({ uid, eid })).toString("base64url")}.firma`;

  const elRechazoDeA = [{ id_local: "p1", motivo: "EL RECHAZO DE LA CUENTA A", estado: 422 }];

  // *A: ve su rechazo.*
  const comoA = await cargarAplicacion(
    {},
    {
      almacen: {
        "cuedigital.rechazados.1:1": elRechazoDeA,
      },
      almacenCrudo: {
        "cuedigital.token": unVale(1, 1),
      },
    },
  );
  await new Promise((resolver) => setTimeout(resolver, 60));
  // ***Se mira el HTML y el texto***: *la rama de rechazados pinta con `innerHTML` —para poder poner el motivo en
  // negrita—, y el nodo de mentira del arnés **no sincroniza** `innerHTML` con `textContent`. Mirar solo uno
  // hacia que la prueba fallara por el andamio y no por la aplicación.*
  const elAvisoDeA = comoA.entorno.nodos.get("aviso-pendientes");
  assert.match(
    `${elAvisoDeA.innerHTML || ""} ${elAvisoDeA.textContent || ""}`,
    /EL RECHAZO DE LA CUENTA A/,
    "***A tiene que ver su propio rechazo***",
  );

  // *B: el mismo móvil, otra cuenta. **No puede verlo.***
  const comoB = await cargarAplicacion(
    {},
    {
      almacen: {
        "cuedigital.rechazados.1:1": elRechazoDeA,
      },
      almacenCrudo: {
        "cuedigital.token": unVale(2, 2),
      },
    },
  );
  await new Promise((resolver) => setTimeout(resolver, 60));
  const elAvisoDeB = comoB.entorno.nodos.get("aviso-pendientes");
  const loDeB = `${elAvisoDeB.innerHTML || ""} ${elAvisoDeB.textContent || ""}`;
  assert.ok(
    !loDeB.includes("CUENTA A"),
    `***B no puede ver el rechazo de A***: ${loDeB}`,
  );
});

// ---------------------------------------------------------------------------
// ***D03: un fallo no es un cero*** (21/10/2026)
// ---------------------------------------------------------------------------

test("un fallo de facturas no es cero facturas", async () => {
  // *`cargarDatos` pedia 32 secciones con `.catch(() => [])`: **un fallo se convertia en «no hay datos»**. El
  // encargo lo dice con estas palabras: «un fallo de facturas no implica cero facturas».*
  //
  // *Ahora cada seccion **apunta como fue**, y esto lo comprueba: con el servidor fallando en `/api/facturas`, la
  // seccion queda **como fallo** -no desaparece en silencio-, y con el servidor bien, **no figura como fallo**.*
  const elQueFalla = await cargarAplicacion({
    "/api/facturas": falla({ detail: "El servidor se ha caido." }, 500),
  });
  const loQueFallo = elQueFalla.app.loQueNoSePudoCargar();
  assert.ok(
    loQueFallo.facturas,
    `***un fallo de facturas NO es «no hay facturas»***: ${JSON.stringify(loQueFallo).slice(0, 300)}`,
  );

  // *Y el control positivo: cuando el servidor va bien, la seccion no figura como fallo.*
  const elQueVaBien = await cargarAplicacion({});
  assert.equal(
    elQueVaBien.app.loQueNoSePudoCargar().facturas,
    undefined,
    "***una carga buena no puede apuntarse como fallo***",
  );
});

test("y un fallo de las tierras tampoco es «no hay tierras»", async () => {
  // *La misma trampa en otra seccion: si `/api/parcelas` falla, la pantalla no puede decir que la finca no tiene
  // tierras -que es una afirmacion sobre la finca, no sobre la red-.*
  const elQueFalla = await cargarAplicacion({
    "/api/parcelas": falla({ detail: "El servidor se ha caido." }, 500),
  });
  const loQueFallo = elQueFalla.app.loQueNoSePudoCargar();
  assert.ok(loQueFallo.parcelas, `***un fallo de tierras no es una finca sin tierras***: ${JSON.stringify(loQueFallo).slice(0, 300)}`);
});

test("lo que no se pudo cargar se DICE en pantalla, con su reintento", async () => {
  // *Que `estado.cargas` lo apunte no sirve de nada si **el agricultor sigue leyendo «0 facturas»**. Esto
  // comprueba que **se enseña**, que **dice qué** falló y que **ofrece reintentar**.*
  const elQueFalla = await cargarAplicacion({
    "/api/facturas": falla({ detail: "El servidor se ha caido." }, 500),
  });
  const elAviso = elQueFalla.entorno.nodos.get("aviso-cargas");
  const loQueDice = `${elAviso.innerHTML || ""} ${elAviso.textContent || ""}`;
  assert.match(loQueDice, /facturas/, `***tiene que decir que fallo facturas***: ${loQueDice}`);
  assert.match(
    loQueDice,
    /reintentar-lo-que-fallo/,
    `***y ofrecer reintentar***: ${loQueDice}`,
  );

  // *Y el reintento vuelve a pedirlo: **sin perder nada**, porque lo unico que hace es repetir la carga.*
  const lasDeAntes = elQueFalla.servidor.llamadas.filter((ruta) => ruta === "/api/facturas").length;
  await pulsar(elQueFalla.entorno, "reintentar-lo-que-fallo");
  const lasDeAhora = elQueFalla.servidor.llamadas.filter((ruta) => ruta === "/api/facturas").length;
  assert.ok(
    lasDeAhora > lasDeAntes,
    `***reintentar tiene que volver a pedirlo***: ${lasDeAntes} -> ${lasDeAhora}`,
  );

  // ***Y el control positivo: sin fallos, el aviso NO se enseña.***
  const elQueVaBien = await cargarAplicacion({});
  const elOtro = elQueVaBien.entorno.nodos.get("aviso-cargas");
  assert.match(
    elOtro.className || "",
    /oculto/,
    `***sin fallos no se ensena nada***: ${elOtro.className} · fallaron: ${JSON.stringify(elQueVaBien.app.loQueNoSePudoCargar())}`,
  );
});

test("un 403 no aparta una orden valida: se queda en la cola", async () => {
  // ***«Si falta permiso o caduca el acceso, no descartar como rechazado definitivo una orden valida pendiente»***
  // (encargo, D01) y ***«un 403 no se reintenta como alta sin cobertura»*** (D03). *Son las dos caras del mismo
  // caso: un 403 **no dice que el apunte este mal**, dice que **ahora no se puede**. Se queda esperando a que el
  // permiso vuelva; apartarlo seria tirar una orden valida del agricultor.*
  const unVale = `₹{Buffer.from(JSON.stringify({ uid: 1, eid: 1 })).toString("base64url")}.firma`.replace("₹", "$");
  const elApunte = [
    {
      id_local: "p-del-403",
      ruta: "/api/trabajos",
      datos: { tipo: "laboreo", clave_de_reenvio: "p-del-403" },
      cuenta: "1:1",
      apuntado_en: "2026-10-21T08:00:00.000Z",
    },
  ];

  const { entorno } = await cargarAplicacion(
    { "/api/trabajos": falla({ detail: "No puedes apuntar eso." }, 403) },
    {
      almacen: { "cuedigital.pendientes": elApunte },
      almacenCrudo: { "cuedigital.token": unVale },
    },
  );
  // *Se le da tiempo al vaciado, que arranca cuando se sabe quien esta dentro.*
  await new Promise((resolver) => setTimeout(resolver, 120));

  const laCola = entorno.window.localStorage.getItem("cuedigital.pendientes") || "";
  assert.ok(
    laCola.includes("p-del-403"),
    `***un 403 NO puede apartar una orden valida: tiene que quedarse en la cola***: ${laCola}`,
  );
  const losApartados = Object.keys(entorno.window.localStorage)
    .filter((clave) => clave.indexOf("cuedigital.rechazados") === 0)
    .map((clave) => entorno.window.localStorage.getItem(clave) || "")
    .join("");
  assert.ok(
    !losApartados.includes("p-del-403"),
    `***ni apartarlo como rechazo definitivo***: ${losApartados}`,
  );
});

