/*
 * bancos.test.js — las pruebas de la pantalla del extracto del banco (S14, T20 / E11, 06/10/2026).
 *
 * POR QUÉ ESTÁN AQUÍ Y NO EN `interfaz.test.js`
 *
 * Las dos pantallas están escritas en React (`web/react/pantallas/bancos.js`) y en el DOM de mentira de
 * `interfaz.test.js` React no se puede montar. Así que se prueban **contra el componente**: se le dan las
 * propiedades y se mira el HTML que produce con `renderToStaticMarkup`, igual que con las demás pantallas
 * migradas. No hay `jsdom` ni ninguna dependencia nueva.
 *
 * QUÉ SE COMPRUEBA, Y POR QUÉ ESAS COSAS
 *
 *  1. **Que la vista previa enseñe las líneas que no se han entendido con su motivo Y con su número de
 *     línea del fichero.** Sin el número, el agricultor tendría que abrir el CSV y contar renglones a
 *     mano: es la mitad del ticket.
 *  2. **Que nada se apunte hasta que el agricultor lo diga.** Leer es una puerta que no guarda, y el
 *     botón de apuntar **solo existe cuando hay una propuesta delante**. Si ese botón estuviera en el
 *     formulario de subir el fichero, importar dos veces el mismo extracto dejaría de ser una decisión.
 *  3. **Que un importe que no consta se enseñe como hueco y nunca como cero.** Se comprueba de la manera
 *     que muerde: se le pasa al movimiento un `texto_importe` de `0,00 €` **con el importe a nulo**, y la
 *     pantalla tiene que enseñar su palabra («No consta») y **no** el cero. Un cero ahí diría que el banco
 *     movió cero euros.
 *  4. **Que conciliar mande las imputaciones que el agricultor ha elegido.** El botón de una propuesta
 *     lleva su **índice**, y `app.js` manda las imputaciones de **esa** propuesta; por eso la prueba
 *     comprueba que cada índice está **en el bloque de su propuesta y en el orden del servidor**: si la
 *     pantalla las ordenara, el botón apuntaría a otro papel, que es el peor fallo posible de aquí.
 *  5. **Que deshacer no borre el movimiento.** Después de deshacer, el movimiento sigue entero en la
 *     pantalla, con su importe y su estado, y lo que sale es lo que ha vuelto a quedar pendiente.
 *  6. **Que un traspaso entre cuentas propias se pueda atar y desatar**, y que se diga que ese dinero no
 *     cuenta como ingreso ni como gasto (A07).
 *  7. **Que las cuatro familias de claves compuestas estén enteras en los textos** (`estado_…`,
 *     `falta_…`, `por_que_no_…` y `propuesta_…`): el servidor las manda como **claves**, no como frases, y
 *     la que falte sale en blanco sin que salte nada.
 *  8. **Que ninguna frase esté escrita dentro del componente**: todas salen de la copia de los textos del
 *     servidor que hay aquí abajo, y hay una prueba que comprueba que **no se lee ni una clave que no
 *     esté** y que **no sobra ninguna frase**.
 *
 * LA COPIA DE LOS TEXTOS (`BANCOS`, aquí abajo) son **las claves que esta pantalla lee**, y su bloque
 * completo para `app/textos.py` está en `docs/T20_PANTALLA.md`. Va aparte, con una clave por línea, para
 * que la prueba de Python del ticket pueda leerla y compararla con lo que sirve el servidor. Lo que
 * `app.js` lee para montar los formularios (los rótulos del alta de una cuenta y de la forma de escribir
 * del banco) y la tabla del ordenador no está aquí: eso no lo lee la pantalla, y por eso no se cuenta.
 */

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import vm from "node:vm";

// ---------------------------------------------------------------------------
// El arnés: React y htm, como los deja `index.html`
// ---------------------------------------------------------------------------

globalThis.self = globalThis;

function cargarDeVendor(nombre) {
  const codigo = readFileSync(new URL(`../web/vendor/${nombre}`, import.meta.url), "utf8");
  vm.runInThisContext(codigo, { filename: nombre });
}

cargarDeVendor("react.production.min.js");
cargarDeVendor("htm.umd.js");
cargarDeVendor("react-dom-server-legacy.browser.production.min.js");

const React = globalThis.React;

// ---------------------------------------------------------------------------
// La copia de los textos que lee esta pantalla
// ---------------------------------------------------------------------------

/**
 * El bloque `BANCOS` de `textos.py`, con **las claves que la pantalla lee**.
 *
 * Las cuatro familias compuestas (`estado_…`, `falta_…`, `por_que_no_…`, `propuesta_…`) van enteras: el
 * servidor manda la clave y la pantalla compone la frase, así que la que falte deja el hueco en blanco.
 */
const BANCOS = {
  titulo: "El banco y los papeles",
  explica:
    "Aquí subes el extracto que has descargado de tu banca y lo cuadras con las facturas y los cobros. El programa no se conecta a ningún banco: solo lee el fichero que le das tú.",
  buscando: "Buscando…",
  volver_a_los_movimientos: "VOLVER A LOS MOVIMIENTOS",
  // --- subir el fichero ---
  subir_titulo: "Subir el extracto",
  subir_explica:
    "Elige el fichero que has descargado de tu banca. El programa lo lee y te enseña lo que ha entendido, sin apuntar nada todavía.",
  nada_se_apunta: "Leer no apunta nada: primero lo miras y después decides.",
  fichero: "El fichero del extracto",
  fichero_pista: "Es el fichero que te has descargado de tu banca.",
  fichero_elegido: "El fichero que has elegido es",
  cuenta: "De qué cuenta es",
  cuenta_pista: "La cuenta de la que has descargado el extracto.",
  elige_la_cuenta: "Elige la cuenta",
  perfil: "Cómo escribe tu banco",
  perfil_pista: "Si ya nos dijiste cómo escribe las fechas y los importes, elígelo aquí.",
  sin_perfil: "Todavía no lo he dicho",
  leer_el_extracto: "LEER EL EXTRACTO",
  leyendo: "Leyendo el extracto…",
  anadir_una_cuenta: "AÑADIR UNA CUENTA",
  anadir_un_perfil: "DECIR CÓMO ESCRIBE MI BANCO",
  sin_cuentas: "Para subir un extracto hace falta decir antes de qué cuenta es.",
  // --- la vista previa ---
  vista_titulo: "Lo que he entendido del fichero",
  vista_nada_apuntado: "Esto todavía no está apuntado. Míralo y, si está bien, apúntalo.",
  ya_estaba_el_fichero: "Este mismo fichero ya lo subiste antes.",
  cuenta_detectada: "En el fichero pone que es la cuenta",
  cuenta_no_detectada: "En el fichero no se lee de qué cuenta es.",
  lineas_leidas: "Líneas leídas",
  movimientos_leidos: "Movimientos entendidos",
  se_apuntaran: "Se van a apuntar",
  ya_estaban: "Ya estaban apuntados",
  ya_estaban_explica: "Estos no se apuntan otra vez: ya los tenías.",
  rechazadas_cuantas: "Líneas que no se han entendido",
  entradas: "Dinero que entra",
  salidas: "Dinero que sale",
  sin_importe: "Líneas sin importe",
  sin_importe_explica: "De esas no se sabe cuánto, y no cuentan en los totales. Escribe el importe a mano.",
  formato_de_fecha: "Las fechas del fichero",
  formato_no_dicho: "No nos has dicho cómo son",
  saldo_final: "El saldo que queda",
  no_consta: "No consta",
  no_se_sabe: "No lo sé",
  avisos_titulo: "Lo que hay que mirar de esta lectura",
  rechazadas_titulo: "Líneas que no se han podido leer",
  rechazadas_explica: "Estas líneas no se van a apuntar. Cada una dice qué le pasa y en qué línea está.",
  linea_numero: "Línea",
  se_van_a_apuntar: "Lo que se va a apuntar",
  no_hay_ninguno_nuevo: "De este fichero no hay ningún movimiento nuevo que apuntar.",
  ya_estaba_esta_linea: "Esta línea ya estaba apuntada.",
  apuntar_los_movimientos: "APUNTAR ESTOS MOVIMIENTOS",
  importando: "Apuntando…",
  descartar: "NO APUNTAR NADA",
  apuntado_titulo: "Lo que se ha apuntado",
  apuntados: "Movimientos apuntados",
  repetidos: "Que ya estaban",
  repetidos_explica: "No se han repetido: ya los tenías apuntados.",
  // --- los traspasos ---
  traspasos_titulo: "Dinero que ha cambiado de cuenta",
  traspasos_explica: "Parece el mismo dinero pasado de una cuenta tuya a otra.",
  traspaso_sale_de: "Sale de",
  traspaso_entra_en: "Entra en",
  traspaso_dias: "Días de diferencia",
  traspaso_donde: "Márcalo abriendo uno de los dos movimientos y diciendo cuál es el otro.",
  // --- la lista de movimientos ---
  movimientos_titulo: "Los movimientos del banco",
  movimientos_explica: "Cada línea del extracto, con lo que le queda por cuadrar.",
  movimientos_vacio: "Todavía no has apuntado ningún movimiento. Sube el extracto de tu banca para empezar.",
  sin_resultados: "Ningún movimiento coincide con lo que buscas. Prueba con otras letras o pulsa VER TODO.",
  buscar: "Buscar en los movimientos",
  buscar_pista: "Escribe parte del concepto o de la referencia.",
  buscar_boton: "BUSCAR",
  ver_todo: "VER TODO",
  exportar: "DESCARGAR EL EXTRACTO",
  exportar_pista: "Se descarga en un fichero, con el importe en blanco donde no consta.",
  estado: "Cuáles ver",
  todos_los_estados: "Todos",
  fecha: "El día",
  referencia: "La referencia",
  importe: "El importe",
  saldo: "El saldo que quedó",
  su_cuenta: "La cuenta",
  como_esta: "Cómo está",
  imputado: "Ya apuntado a papeles",
  por_conciliar: "Le queda por cuadrar",
  abrir: "¿CONTRA QUÉ PAPEL VA?",
  es_traspaso: "Es un traspaso entre cuentas tuyas: ese dinero solo ha cambiado de sitio.",
  corregido_a_mano: "Este importe lo escribiste tú.",
  sin_importe_aviso:
    "De este movimiento no consta el importe, así que no se puede cuadrar con ningún papel. Escríbelo a mano.",
  // --- los dos lados de lo que queda por cuadrar ---
  pendientes_titulo: "Lo que queda por cuadrar",
  pendientes_explica:
    "De un lado, el dinero del banco que todavía no está apuntado a ningún papel. Del otro, las facturas y los cobros a los que les falta dinero.",
  dinero_sin_papel: "Dinero del banco sin papel",
  sin_conciliar_cuantos: "Movimientos sin cuadrar",
  papeles_sin_dinero: "Papeles sin dinero",
  de_quien: "Quién",
  le_falta: "Le falta",
  sin_pendientes: "No queda nada por cuadrar: todo el dinero apuntado está en su papel.",
  como_se_cuadra: "Para cuadrar algo, abre el movimiento del banco y dile contra qué papel va.",
  // --- los formularios ---
  ficha_titulo: "Este movimiento del banco",
  // --- la conciliación ---
  propuestas_titulo: "Contra qué papel va",
  propuestas_explica:
    "Estas son las cuentas que cuadran con este movimiento, y por qué. Elige una y el dinero queda apuntado a ese papel.",
  propuestas_vacio: "Con este movimiento no cuadra ninguna factura ni ningún cobro. Puedes apuntarlo a mano.",
  porque_titulo: "Por qué te lo propongo",
  a_que_papeles: "A estos papeles",
  se_apuntaria: "Se apuntarían",
  quedaria_sin_apuntar: "Quedaría sin apuntar",
  apuntar_esta: "APUNTAR ESTA",
  papel_desconocido: "De este papel no se sabe cómo se llama. Míralo antes de apuntar nada aquí.",
  a_mano_titulo: "Apuntarlo a mano",
  a_mano_explica:
    "Elige el papel y, si solo le vas a apuntar una parte, escribe cuánto. Si lo dejas en blanco, se apunta lo que quepa, del papel más antiguo al más nuevo.",
  papel: "A qué papel",
  elige_el_papel: "Elige el papel",
  cantidad: "Cuánto de este movimiento",
  cantidad_pista: "Déjalo en blanco para apuntar todo lo que quepa.",
  apuntar: "APUNTAR ESTE DINERO",
  sin_papeles: "No tienes ninguna factura ni ningún cobro al que apuntar este dinero. Apúntalo antes.",
  lo_conciliado_titulo: "Lo que ha quedado apuntado",
  lo_devuelto_titulo: "Lo que ha vuelto a quedar pendiente",
  deshacer_titulo: "Deshacer lo apuntado",
  deshacer_explica:
    "Deshacer no borra el movimiento del banco: el banco ya movió ese dinero. Lo que se deshace es a qué papeles estaba apuntado, y queda dicho quién lo deshizo y cuándo.",
  deshacer: "DESHACERLO",
  nada_que_deshacer: "De este movimiento no hay nada apuntado a ningún papel.",
  // --- el traspaso, en la ficha ---
  traspaso_titulo: "Es un traspaso entre cuentas tuyas",
  traspaso_explica: "Si este dinero solo ha cambiado de cuenta, dilo: así no cuenta como ingreso ni como gasto.",
  traspaso_ya_esta: "Este movimiento está atado a otro: ese dinero solo ha cambiado de cuenta.",
  traspaso_el_otro: "La otra parte del traspaso",
  traspaso_pista: "Tiene que ser de otra cuenta tuya, del mismo importe y al revés.",
  traspaso_elige: "Elige el otro movimiento",
  traspaso_atar: "ATAR EL TRASPASO",
  traspaso_quitar: "QUITAR EL TRASPASO",
  sin_parejas: "No hay ningún movimiento de otra cuenta tuya al que atarlo.",
  // --- corregir el importe que no consta ---
  corregir: "CORREGIR EL IMPORTE A MANO",
  // --- cómo está un movimiento (el servidor manda la clave, no la frase) ---
  estado_sin_conciliar: "Sin cuadrar",
  estado_conciliado_en_parte: "A medias",
  estado_conciliado: "Cuadrado",
  estado_no_se_puede_conciliar: "No consta el importe",
  // --- lo que no consta de una línea ---
  falta_importe_no_consta: "No consta el importe",
  falta_saldo_no_consta: "No consta el saldo",
  falta_referencia_no_consta: "No trae referencia",
  falta_concepto_no_consta: "No trae concepto",
  falta_importe_ilegible_en_la_fila: "El importe no se ha podido leer",
  falta_saldo_ilegible: "El saldo no se ha podido leer",
  // --- por qué no se puede cuadrar ---
  por_que_no_no_consta_el_importe:
    "En este movimiento no consta el importe, así que no se sabe cuánto se puede apuntar a un papel. Escríbelo y vuelve a intentarlo.",
  por_que_no_es_un_traspaso_entre_cuentas_tuyas:
    "Este movimiento es un traspaso entre cuentas tuyas: ese dinero solo ha cambiado de sitio y no salda ninguna factura.",
  // --- cómo cuadra una propuesta ---
  propuesta_exacta: "Cuadra exacto con este papel",
  propuesta_agrupada: "Cuadra con varios papeles a la vez",
  propuesta_parcial: "Es una parte de lo que le falta",
};

const TEXTOS = { bancos: BANCOS, acciones: { volver: "VOLVER" } };

// Las dos listas que la pantalla ofrece para elegir (la cuenta y la forma de escribir del banco). Van aquí,
// y no dentro de cada prueba, porque **sus textos son datos del servidor**: la prueba de las frases a mano
// tiene que saber que esas frases vienen de las propiedades y no del componente.
const CUENTAS = [{ valor: 1, texto: "La del día a día · ·1234" }];
const PERFILES = [{ valor: 4, texto: "El extracto de siempre" }];

// ---------------------------------------------------------------------------
// Los datos, tal y como los prepara `app.js`
// ---------------------------------------------------------------------------

/**
 * Un movimiento del banco, con sus `texto_*` ya escritos.
 *
 * Los `texto_*` los añade `app.js` con `enEuros`, que devuelve **vacío** cuando el dato no consta: así el
 * formateo del dinero vive en un solo sitio (`enEuros`, en `app.js`) y la pantalla no hace ninguna cuenta.
 */
function unMovimiento(cambios = {}) {
  return {
    id: 5,
    cuenta_id: 1,
    cuenta: "La del día a día · ·1234",
    fecha: "2026-10-01",
    texto_fecha: "01/10/2026",
    concepto: "TRANSFERENCIA RECIBIDA DE LA COOPERATIVA",
    referencia: "F-2026-12",
    importe: "500.00",
    texto_importe: "500,00 €",
    signo: "entra",
    saldo: "1500.00",
    texto_saldo: "1.500,00 €",
    estado: "sin_conciliar",
    imputado: "0.00",
    texto_imputado: "0,00 €",
    por_conciliar: "500.00",
    texto_por_conciliar: "500,00 €",
    es_traspaso_propio: false,
    pareja_de_traspaso_id: null,
    lo_que_falta: [],
    se_puede_conciliar: true,
    por_que_no: null,
    corregido: false,
    ...cambios,
  };
}

/** Un movimiento **sin importe**: es «no lo sé», y el `texto_importe` que llega está vacío. */
function unMovimientoSinImporte(cambios = {}) {
  return unMovimiento({
    importe: null,
    texto_importe: "",
    signo: null,
    por_conciliar: null,
    texto_por_conciliar: "",
    estado: "no_se_puede_conciliar",
    se_puede_conciliar: false,
    por_que_no: "no_consta_el_importe",
    lo_que_falta: ["importe_no_consta"],
    ...cambios,
  });
}

/** Un papel pendiente (una factura nuestra, un cobro o una factura de compra). */
function unPendiente(cambios = {}) {
  return {
    clase: "factura_emitida",
    documento_id: 3,
    etiqueta: "factura_emitida:3",
    contraparte: "Cooperativa del Sur",
    referencia: "F-2026-12",
    fecha: "2026-09-01",
    texto_fecha: "01/09/2026",
    vencimiento: "2026-10-01",
    texto_vencimiento: "01/10/2026",
    importe: "121.00",
    texto_importe: "121,00 €",
    pendiente: "121.00",
    texto_pendiente: "121,00 €",
    que_es: "Una factura tuya, de lo que has vendido",
    ...cambios,
  };
}

/** Un segundo papel, de otra clase y otro número, para las pruebas que necesitan más de uno. */
function otroPendiente(cambios = {}) {
  return unPendiente({
    clase: "cobro",
    documento_id: 8,
    etiqueta: "cobro:8",
    contraparte: "",
    referencia: "Ingreso del 20 de septiembre",
    importe: "81.00",
    texto_importe: "81,00 €",
    pendiente: "81.00",
    texto_pendiente: "81,00 €",
    que_es: "Un dinero que entró y todavía no sabes de qué factura es",
    ...cambios,
  });
}

/** Una propuesta de conciliación: cómo cuadra, por qué, y a qué papeles y cuánto. */
function unaPropuesta(cambios = {}) {
  return {
    tipo: "exacta",
    total: "500.00",
    texto_total: "500,00 €",
    sobrante: "0.00",
    texto_sobrante: "0,00 €",
    puntuacion: 90,
    porque: ["la referencia está en el concepto del movimiento", "el importe cuadra exacto"],
    imputaciones: [
      { clase: "factura_emitida", documento_id: 3, importe: "500.00", texto_importe: "500,00 €" },
    ],
    ...cambios,
  };
}

/** La vista previa, tal y como la devuelve `POST /api/bancos/extractos/vista-previa`. */
function laVistaPrevia(cambios = {}) {
  return {
    cuenta_detectada: "La del día a día",
    ultimos_digitos: "1234",
    saldo_final: "1500.00",
    texto_saldo_final: "1.500,00 €",
    formato_de_fecha: "d/m/Y",
    sin_signo_quiere_decir: null,
    movimientos: [
      {
        numero_de_linea: 2,
        fecha: "2026-10-01",
        texto_fecha: "01/10/2026",
        concepto: "TRANSFERENCIA RECIBIDA",
        importe: "500.00",
        texto_importe: "500,00 €",
        signo: "entra",
        saldo: "1500.00",
        texto_saldo: "1.500,00 €",
        referencia: "F-2026-12",
        clave_de_duplicado: "c1#1",
        ya_estaba: false,
        lo_que_falta: [],
      },
    ],
    ya_estaban: 0,
    nuevas: 1,
    rechazadas: [],
    avisos: [],
    traspasos: [],
    resumen: {
      entradas: "500.00",
      salidas: "0.00",
      texto_entradas: "500,00 €",
      texto_salidas: "0,00 €",
      sin_importe: 0,
      lineas_leidas: 2,
      movimientos: 1,
      rechazadas: 0,
    },
    el_fichero_ya_estaba: false,
    ...cambios,
  };
}

/** Lo que contesta el servidor al apuntar los movimientos. */
function elResultadoDeLaImportacion(cambios = {}) {
  return {
    importacion_id: 1,
    cuenta_id: 1,
    creados: 7,
    repetidos: 0,
    filas_rechazadas: 0,
    sin_importe: 0,
    el_fichero_ya_estaba: false,
    ya_estaba: false,
    avisos: [],
    traspasos: [],
    ...cambios,
  };
}

/** Un formulario de escribir, tal y como lo monta `app.js` (el alta de una cuenta, aquí como ejemplo). */
function unFormulario(cambios = {}) {
  return {
    titulo: "Añadir una cuenta",
    pista: "No se pide ninguna clave ni el número entero de la cuenta.",
    guardar: "GUARDAR",
    cancelar: "DEJARLO",
    guardando: "Guardando…",
    datos: { clase: "cuenta" },
    bloques: [
      { tipo: "texto", id: "banco-cuenta-nombre", etiqueta: "Cómo llamas a esta cuenta", valor: "" },
      { tipo: "texto", id: "banco-cuenta-ultimos", etiqueta: "Los cuatro últimos números", valor: "" },
    ],
    ...cambios,
  };
}

/** Y uno con un bloque de **elegir**, que es el que pinta los botones de una opción (`banco-elegir`). */
function unFormularioConOpciones(cambios = {}) {
  return unFormulario({
    titulo: "Cómo escribe tu banco",
    datos: { clase: "perfil" },
    bloques: [
      { tipo: "texto", id: "banco-perfil-nombre", etiqueta: "Cómo llamas a esta forma de escribir", valor: "" },
      {
        tipo: "opciones",
        campo: "formato_de_fecha",
        etiqueta: "Cómo escribe las fechas",
        elegido: "",
        opciones: [
          { valor: "d/m/Y", texto: "Día/mes/año" },
          { valor: "m/d/Y", texto: "Mes/día/año" },
        ],
      },
      {
        tipo: "opciones",
        campo: "sin_signo_quiere_decir",
        etiqueta: "Cuando un importe no trae signo, ¿qué quiere decir?",
        elegido: "",
        opciones: [
          { valor: "entra", texto: "Que el dinero entra" },
          { valor: "sale", texto: "Que el dinero sale" },
        ],
      },
    ],
    ...cambios,
  });
}

// ---------------------------------------------------------------------------
// Utilidades
// ---------------------------------------------------------------------------

async function cargarLaPantallaModulo() {
  // El `?prueba=` con un número al azar es obligatorio: sin él, Node devuelve el módulo ya cargado por otra
  // prueba y la caché de módulos hace que las pruebas se pisen.
  return import(`../web/react/pantallas/bancos.js?prueba=${Math.random()}`);
}

async function htmlDe(componente, propiedades) {
  const modulo = await cargarLaPantallaModulo();
  return globalThis.ReactDOMServer.renderToStaticMarkup(
    React.createElement(modulo[componente], propiedades),
  );
}

const htmlDeLosBancos = (cambios = {}) =>
  htmlDe("PantallaDeLosBancos", {
    textos: structuredClone(TEXTOS),
    cuentas: structuredClone(CUENTAS),
    perfiles: structuredClone(PERFILES),
    cuentaElegida: "1",
    perfilElegido: "",
    ficheroElegido: "",
    leyendo: false,
    importando: false,
    guardando: false,
    vistaPrevia: null,
    resultado: null,
    movimientos: [],
    agregados: {},
    resumen: "",
    tabla: null,
    filtro: "",
    estado: "",
    pendientes: [],
    formulario: null,
    error: "",
    aviso: "",
    ...cambios,
  });

const htmlDeUnMovimiento = (cambios = {}) =>
  htmlDe("PantallaDeUnMovimiento", {
    textos: structuredClone(TEXTOS),
    movimiento: unMovimiento(),
    propuestas: [],
    pendientes: [],
    papeles: [],
    parejas: [],
    formulario: null,
    resultado: null,
    deshecho: false,
    guardando: false,
    cargando: false,
    error: "",
    aviso: "",
    ...cambios,
  });

/** Los `data-accion` que salen pintados, en el orden en que salen. */
function accionesDe(html) {
  return [...html.matchAll(/data-accion="([a-z0-9_-]+)"/g)].map((encontrado) => encontrado[1]);
}

/** Los botones del HTML: su acción y todos sus `data-*`. */
function botonesDe(html) {
  return [...html.matchAll(/<button[^>]*>/g)].map((encontrado) => {
    const etiqueta = encontrado[0];
    const accion = (etiqueta.match(/data-accion="([^"]*)"/) || [])[1] || "";
    const datos = {};
    for (const dato of etiqueta.matchAll(/data-(?!accion)[a-z-]+="([^"]*)"/g)) {
      datos[dato[0].split("=")[0].replace("data-", "")] = dato[1];
    }
    return { accion, ...datos };
  });
}

/** Los `id` de los campos que salen pintados, en el orden en que salen. */
function idsDe(html) {
  return [...html.matchAll(/(?<![\w-])id="([^"]+)"/g)].map((encontrado) => encontrado[1]);
}

/**
 * Todos los textos de una estructura anidada, **incluidos los números**.
 *
 * Los números entran porque la pantalla enseña algunos tal cual llegan del servidor (cuántas líneas trae el
 * fichero, cuántos movimientos ya estaban): un número no es una frase escrita a mano, y sin esto la prueba
 * de las frases a mano los tomaría por frases inventadas.
 */
function todosLosTextos(valor) {
  if (typeof valor === "string") return [valor];
  if (typeof valor === "number") return [String(valor)];
  if (Array.isArray(valor)) return valor.flatMap(todosLosTextos);
  if (valor && typeof valor === "object") return Object.values(valor).flatMap(todosLosTextos);
  return [];
}

/** Lo que de verdad se lee: el texto que hay entre las etiquetas. */
function frasesVisibles(html) {
  return html
    .replace(/<span class="icono"[^>]*>[^<]*<\/span>/g, "")
    .replace(/<span class="flecha"[^>]*>[^<]*<\/span>/g, "")
    .replace(/<[^>]*>/g, "\u0000")
    .split("\u0000")
    .map((trozo) => trozo.trim())
    .filter(Boolean);
}

// ===========================================================================
// 1. Subir el extracto: leer no guarda nada
// ===========================================================================

test("el formulario de subir lleva su campo de fichero, su cuenta y su perfil, y no apunta nada", async () => {
  // **La prueba que impide que importar dos veces sea un descuido.** Al leer todavía no hay ninguna
  // propuesta delante, así que el único botón que apunta movimientos (`banco-importar`) **no puede estar
  // aquí**: si estuviera, el agricultor apuntaría el extracto sin haberlo mirado.
  const html = await htmlDeLosBancos();

  for (const campo of ["banco-fichero", "banco-cuenta", "banco-perfil"]) {
    assert.ok(idsDe(html).includes(campo), `falta el campo «${campo}» de la subida`);
  }
  assert.match(html, /type="file"/, "no hay dónde elegir el fichero del extracto");
  assert.match(html, /accept="\.csv,text\/csv"/, "el campo no dice que lo que se sube es un CSV");

  const acciones = accionesDe(html);
  assert.ok(acciones.includes("banco-leer"), "no hay forma de leer el extracto");
  assert.ok(!acciones.includes("banco-importar"), "se puede apuntar el extracto sin haberlo mirado antes");
  assert.ok(!acciones.includes("banco-descartar"), "se ofrece descartar algo que todavía no se ha leído");

  // Y se dice que leer no guarda nada, que es lo que hay que saber antes de empezar.
  assert.match(html, /Leer no apunta nada/);
});

test("sin ninguna cuenta dada de alta se dice, y el aviso trae el botón que lo arregla", async () => {
  // Regla de la casa: al agricultor no se le deja sin salida. Sin cuenta no se puede decir de cuál es el
  // extracto, así que el aviso lleva el botón que da de alta una.
  const html = await htmlDeLosBancos({ cuentas: [] });
  assert.match(html, /Para subir un extracto hace falta decir antes de qué cuenta es/);
  const acciones = accionesDe(html);
  assert.ok(acciones.includes("banco-cuenta-nueva"), "el aviso no lleva a donde se arregla");
  assert.ok(!acciones.includes("banco-leer"), "se puede leer un extracto sin decir de qué cuenta es");
});

test("no hay ni una credencial que pedir: la pantalla solo lee el fichero que se sube", async () => {
  // Lo prohíbe el encargo del T20. Se comprueba en el código de la pantalla, que es lo único que la suite
  // de JavaScript puede leer: no hay campos de clave, ni de usuario, ni direcciones de banco.
  const fuente = readFileSync(new URL("../web/react/pantallas/bancos.js", import.meta.url), "utf8");
  for (const prohibido of ["clave de acceso", "contraseña", "password", "usuario del banco", "http://", "https://"]) {
    assert.ok(!fuente.toLowerCase().includes(prohibido), `la pantalla lleva «${prohibido}»`);
  }
});

// ===========================================================================
// 2. La vista previa: lo que no se ha entendido, con su motivo y su línea
// ===========================================================================

test("la vista previa enseña cada línea rechazada con su motivo y con su número de línea", async () => {
  // **La prueba central del recorrido.** Una línea que no se ha entendido tiene que poder buscarse en el
  // fichero del banco: para eso van su número de línea y lo que pone esa línea. Sin el número, el
  // agricultor tendría que abrir el CSV y contar renglones a mano.
  const html = await htmlDeLosBancos({
    vistaPrevia: laVistaPrevia({
      rechazadas: [
        {
          numero_de_linea: 7,
          motivo: "fecha_ambigua",
          que_pasa:
            "La fecha de una línea se puede leer de dos maneras (día/mes o mes/día) y no se ha adivinado. Dinos cómo escribe las fechas tu banco y vuelve a subir el extracto.",
          texto: "03/04/2026;PAGO DE EJEMPLO;40,00",
          lo_que_dice: null,
        },
      ],
      resumen: { ...laVistaPrevia().resumen, rechazadas: 1 },
    }),
  });

  assert.match(html, /Líneas que no se han podido leer/);
  assert.match(html, /Línea/, "no se dice que lo que sigue es un número de línea");
  assert.match(html, />7</, "no sale el número de línea del fichero");
  assert.match(html, /se puede leer de dos maneras/, "no sale el motivo de la línea rechazada");
  assert.match(html, /03\/04\/2026;PAGO DE EJEMPLO;40,00/, "no sale la línea tal y como está en el fichero");
});

test("la vista previa dice cuántas líneas ya estaban apuntadas, para que no se dupliquen", async () => {
  // Subir dos veces el mismo fichero no puede apuntar nada dos veces, y eso se dice **antes** de apuntar:
  // es lo que permite decidir sin miedo.
  const html = await htmlDeLosBancos({
    vistaPrevia: laVistaPrevia({ ya_estaban: 7, nuevas: 0, movimientos: [] }),
  });
  assert.match(html, /Ya estaban apuntados/);
  assert.match(html, />7</, "no sale cuántas líneas ya estaban");
  assert.match(html, /no se apuntan otra vez/);
  assert.match(html, /no hay ningún movimiento nuevo que apuntar/i);
});

test("la vista previa enseña los avisos, el formato deducido y el saldo final", async () => {
  const html = await htmlDeLosBancos({
    vistaPrevia: laVistaPrevia({
      avisos: [
        {
          codigo: "el_formato_de_la_fecha_se_ha_deducido_del_fichero",
          que_pasa: "Las fechas se han leído como d/m/Y porque las líneas 6, 7, 8 lo demuestran.",
          lineas: [6, 7, 8],
        },
      ],
      traspasos: [
        {
          sale_de: "c1#1",
          entra_en: "c2#1",
          importe: "500.00",
          texto_importe: "500,00 €",
          dias_de_diferencia: 1,
          cuentas: ["La del día a día", "La del gasóleo"],
          que_pasa: "Estos dos movimientos parecen el mismo dinero pasado de una cuenta tuya a otra.",
        },
      ],
    }),
  });
  assert.match(html, /Las fechas se han leído como d\/m\/Y porque las líneas 6, 7, 8 lo demuestran/);
  assert.match(html, /d\/m\/Y/, "no sale cómo se han leído las fechas");
  assert.match(html, /1\.500,00 €/, "no sale el saldo que queda");
  // Y el traspaso propuesto, con las dos cuentas y los días de diferencia.
  assert.match(html, /La del gasóleo/);
  assert.match(html, /el mismo dinero pasado de una cuenta tuya a otra/);
  assert.match(html, /Márcalo abriendo uno de los dos movimientos/);
});

test("la vista previa ofrece las dos salidas, y solo las dos", async () => {
  const html = await htmlDeLosBancos({ vistaPrevia: laVistaPrevia() });
  const acciones = accionesDe(html);
  assert.ok(acciones.includes("banco-importar"), "no hay forma de apuntar lo que se ha leído");
  assert.ok(acciones.includes("banco-descartar"), "no hay forma de decir que no se apunte nada");
  assert.match(html, /APUNTAR ESTOS MOVIMIENTOS/);
  assert.match(html, /NO APUNTAR NADA/);
  // Y se dice que nada de esto está apuntado todavía.
  assert.match(html, /Esto todavía no está apuntado/);
});

test("al apuntar se dice lo que entró, lo que ya estaba y lo que no traía importe", async () => {
  const html = await htmlDeLosBancos({
    resultado: elResultadoDeLaImportacion({
      creados: 7,
      repetidos: 2,
      sin_importe: 1,
      avisos: ["En las líneas 9 no consta el importe: se apuntan sin él y no cuentan en los totales."],
    }),
  });
  assert.match(html, /Lo que se ha apuntado/);
  assert.match(html, />7</, "no sale cuántos movimientos se han apuntado");
  assert.match(html, />2</, "no sale cuántos ya estaban");
  assert.match(html, /En las líneas 9 no consta el importe/);
});

test("la pantalla del banco dice cuántos importes no constan, aparte de los totales", async () => {
  // Un total que calla que le faltan datos es un total que miente: por eso lo que no consta se cuenta
  // **aparte** y con su nombre.
  const html = await htmlDeLosBancos({
    vistaPrevia: laVistaPrevia({
      movimientos: [
        {
          numero_de_linea: 3,
          fecha: "2026-10-02",
          texto_fecha: "02/10/2026",
          concepto: "RECIBO SIN IMPORTE",
          importe: null,
          texto_importe: "",
          signo: null,
          saldo: "1500.00",
          texto_saldo: "1.500,00 €",
          referencia: null,
          clave_de_duplicado: "c1#2",
          ya_estaba: false,
          lo_que_falta: ["importe_no_consta", "referencia_no_consta"],
        },
      ],
      resumen: { ...laVistaPrevia().resumen, sin_importe: 1, movimientos: 1 },
    }),
  });
  assert.match(html, /Líneas sin importe/);
  assert.match(html, /no cuentan en los totales/);
  // Y de la línea se dice **qué no consta**, uno por uno.
  assert.match(html, /No consta el importe/);
  assert.match(html, /No trae referencia/);
});

// ===========================================================================
// 3. Un importe que no consta es un hueco, y nunca un cero
// ===========================================================================

test("un movimiento sin importe se enseña como hueco: ni un cero, ni un total inventado", async () => {
  // **Esta prueba muerde a propósito.** Al movimiento se le pasa un `texto_importe` de `0,00 €` **con el
  // importe a nulo**: si la pantalla se fiara del texto en vez de mirar el dato, enseñaría un cero y el
  // agricultor leería que el banco movió cero euros. Lo que tiene que salir es su palabra, y el cero no
  // puede aparecer por ningún lado.
  const sinImporte = unMovimientoSinImporte({
    texto_importe: "0,00 €",
    por_conciliar: null,
    texto_por_conciliar: "0,00 €",
    // Y el importe ya apuntado tampoco trae cifra: aquí lo que importa es que **sus `texto_*` dicen cero
    // y el dato dice que no consta**, así que la pantalla no puede creerse ninguno de los dos.
    texto_imputado: "",
    // El saldo se pone sin ceros para que la prueba pueda exigir que **no aparezca un `0,00` por ningún
    // lado**: con un saldo de «1.500,00 €» el cero saldría del propio saldo y la prueba no diría nada.
    saldo: "1234.56",
    texto_saldo: "1.234,56 €",
  });
  const html = await htmlDeLosBancos({ movimientos: [sinImporte] });

  assert.match(html, /No consta/, "no se dice que el importe no consta");
  assert.doesNotMatch(html, /0,00 €/, "la pantalla ha enseñado un cero donde el importe no consta");
  assert.doesNotMatch(html, /0,00/, "la pantalla ha enseñado un cero donde el importe no consta");
  // Y se dice qué hacer, que es lo que convierte el hueco en algo que se puede arreglar.
  assert.match(html, /Escríbelo a mano/);
  // Lo que le queda por cuadrar tampoco se sabe: es «no lo sé», no un cero.
  assert.match(html, /No lo sé/);
});

test("en la ficha, un movimiento sin importe dice por qué no se puede cuadrar", async () => {
  const html = await htmlDeUnMovimiento({ movimiento: unMovimientoSinImporte() });
  assert.match(html, /No consta el importe/);
  assert.match(html, /no se sabe cuánto se puede apuntar a un papel/);
  // Y **no** se ofrece apuntarlo a mano: sin importe no se puede cuadrar con nada.
  assert.ok(
    !accionesDe(html).includes("banco-conciliar-a-mano"),
    "se puede cuadrar un movimiento del que no consta el importe",
  );
  assert.ok(!idsDe(html).includes("banco-papel"), "se ofrece elegir papel para un movimiento sin importe");
});

// ===========================================================================
// 4. Conciliar: se manda lo que el agricultor ha elegido
// ===========================================================================

test("cada propuesta lleva su porqué, sus papeles y su importe antes de apuntar nada", async () => {
  const html = await htmlDeUnMovimiento({
    propuestas: [unaPropuesta({ porque: ["la referencia está en el concepto del movimiento"] })],
    pendientes: [unPendiente()],
    papeles: [{ valor: "factura_emitida:3", texto: "Una factura tuya, de lo que has vendido" }],
  });
  assert.match(html, /la referencia está en el concepto del movimiento/, "una propuesta sin porqué no se puede revisar");
  assert.match(html, /Cuadra exacto con este papel/);
  // A qué papel y cuánto: el nombre del papel sale de la lista de pendientes, no del identificador.
  assert.match(html, /Cooperativa del Sur/);
  assert.match(html, /F-2026-12/);
  assert.match(html, /500,00 €/);
  assert.match(html, /Se apuntarían/);
});

test("el botón de una propuesta lleva el índice de **esa** propuesta, en el orden del servidor", async () => {
  // **El fallo que se persigue aquí.** El botón no lleva los papeles: lleva el índice, y `app.js` manda las
  // imputaciones de la propuesta que pidió al servidor. Si la pantalla ordenara las propuestas —o las
  // pintara en otro orden—, pulsar «APUNTAR ESTA» apuntaría el dinero **a otro papel**, y eso no se nota
  // hasta que una factura está pagada dos veces. Por eso se comprueba que cada índice está dentro del
  // bloque de su propuesta, y en el mismo orden en que llegan.
  const propuestas = [
    unaPropuesta({
      tipo: "exacta",
      imputaciones: [
        { clase: "factura_emitida", documento_id: 3, importe: "500.00", texto_importe: "500,00 €" },
      ],
    }),
    unaPropuesta({
      tipo: "parcial",
      total: "40.00",
      texto_total: "40,00 €",
      sobrante: "460.00",
      texto_sobrante: "460,00 €",
      imputaciones: [{ clase: "cobro", documento_id: 8, importe: "40.00", texto_importe: "40,00 €" }],
    }),
  ];
  const html = await htmlDeUnMovimiento({
    propuestas,
    pendientes: [unPendiente(), otroPendiente()],
  });

  const botones = botonesDe(html).filter((boton) => boton.accion === "banco-conciliar-propuesta");
  assert.deepEqual(
    botones.map((boton) => boton.indice),
    ["0", "1"],
    "no hay un botón por propuesta, con el índice de la suya",
  );

  // Y en el HTML, el papel de la propuesta 0 va antes que su botón, y su botón antes del papel de la 1.
  const papelDeLaPrimera = html.indexOf("Cooperativa del Sur");
  const botonDeLaPrimera = html.indexOf('data-indice="0"');
  const papelDeLaSegunda = html.indexOf("Ingreso del 20 de septiembre");
  const botonDeLaSegunda = html.indexOf('data-indice="1"');
  for (const [nombre, posicion] of [
    ["el papel de la primera propuesta", papelDeLaPrimera],
    ["el botón de la primera", botonDeLaPrimera],
    ["el papel de la segunda", papelDeLaSegunda],
    ["el botón de la segunda", botonDeLaSegunda],
  ]) {
    assert.ok(posicion > 0, `no sale ${nombre}`);
  }
  assert.ok(
    papelDeLaPrimera < botonDeLaPrimera && botonDeLaPrimera < papelDeLaSegunda && papelDeLaSegunda < botonDeLaSegunda,
    "las propuestas no se pintan en el orden del servidor: el índice apuntaría a otro papel",
  );
  // Y cada propuesta dice **cómo** cuadra, que es lo que la hace entendible (exacta, parcial o agrupada).
  assert.match(html, /Cuadra exacto con este papel/);
  assert.match(html, /Es una parte de lo que le falta/);
});

test("apuntar a mano: se elige el papel de la lista y el importe se puede dejar en blanco", async () => {
  const html = await htmlDeUnMovimiento({
    pendientes: [unPendiente(), otroPendiente()],
    papeles: [
      { valor: "factura_emitida:3", texto: "Una factura tuya, de lo que has vendido · Cooperativa del Sur" },
      { valor: "cobro:8", texto: "Un dinero que entró y todavía no sabes de qué factura es" },
    ],
  });
  assert.ok(idsDe(html).includes("banco-papel"), "no se puede elegir el papel a mano");
  assert.ok(idsDe(html).includes("banco-cantidad"), "no se puede decir cuánto se apunta");
  assert.match(html, /factura_emitida:3/, "no sale el papel de la factura entre las opciones");
  assert.match(html, /cobro:8/, "no sale el cobro entre las opciones");
  // **Y dejarlo en blanco reparte lo que quepa**, que es lo que evita un reparto a ojo.
  assert.match(html, /se apunta lo que quepa, del papel más antiguo al más nuevo/);
  assert.ok(accionesDe(html).includes("banco-conciliar-a-mano"));
});

test("sin ningún papel al que apuntar se dice qué hacer, y no se enseña un desplegable vacío", async () => {
  const html = await htmlDeUnMovimiento({ papeles: [] });
  assert.match(html, /No tienes ninguna factura ni ningún cobro al que apuntar este dinero/);
  assert.ok(!idsDe(html).includes("banco-papel"), "se ofrece elegir papel cuando no hay ninguno");
  assert.ok(!accionesDe(html).includes("banco-conciliar-a-mano"), "se puede apuntar dinero sin papeles");
});

test("una propuesta de un papel que no está en la lista se dice, en vez de enseñar un identificador", async () => {
  const html = await htmlDeUnMovimiento({
    propuestas: [unaPropuesta({ imputaciones: [{ clase: "factura_emitida", documento_id: 99, importe: "500.00", texto_importe: "500,00 €" }] })],
    pendientes: [unPendiente()],
  });
  assert.match(html, /De este papel no se sabe cómo se llama/);
  assert.doesNotMatch(html, /factura_emitida:99/, "la pantalla enseña el identificador del papel al agricultor");
});

// ===========================================================================
// 5. Deshacer no borra el movimiento
// ===========================================================================

test("deshacer dice que no borra nada, y el movimiento sigue entero después", async () => {
  // La regla del contrato, y la prueba que la ata: **el banco ya movió ese dinero**. Después de deshacer el
  // movimiento tiene que seguir en la pantalla, con su importe y su estado, y lo que sale es lo que ha
  // vuelto a quedar pendiente.
  const html = await htmlDeUnMovimiento({
    movimiento: unMovimiento({
      estado: "conciliado",
      imputado: "500.00",
      texto_imputado: "500,00 €",
      por_conciliar: "0.00",
      texto_por_conciliar: "0,00 €",
    }),
    resultado: {
      movimiento: unMovimiento({ estado: "sin_conciliar" }),
      conciliaciones: [
        { documento: "factura_emitida:3", clase: "factura_emitida", documento_id: 3, importe: "500.00", texto_importe: "500,00 €" },
      ],
      avisos: ["Deshecho: 500,00 € vuelven a estar pendientes. El movimiento del banco sigue apuntado igual."],
    },
    deshecho: true,
    pendientes: [unPendiente()],
  });

  assert.match(html, /Deshacer no borra el movimiento del banco/, "no se avisa de que deshacer no borra nada");
  assert.match(html, /queda dicho quién lo deshizo y cuándo/);
  assert.ok(accionesDe(html).includes("banco-deshacer"), "no hay forma de deshacer lo apuntado");
  // Lo que ha vuelto a quedar pendiente, con su papel y su fecha.
  assert.match(html, /Lo que ha vuelto a quedar pendiente/);
  assert.match(html, /vuelven a estar pendientes/);
  // Y **el movimiento sigue ahí**: su fecha, su concepto y su importe.
  assert.match(html, /01\/10\/2026/);
  assert.match(html, /TRANSFERENCIA RECIBIDA DE LA COOPERATIVA/);
  assert.match(html, /500,00 €/);
});

test("un movimiento sin nada apuntado dice que no hay nada que deshacer", async () => {
  const html = await htmlDeUnMovimiento();
  assert.match(html, /no hay nada apuntado a ningún papel/);
  assert.ok(!accionesDe(html).includes("banco-deshacer"), "se ofrece deshacer algo que no está apuntado");
});

// ===========================================================================
// 6. El traspaso entre cuentas propias (A07)
// ===========================================================================

test("un traspaso se puede atar y se dice que ese dinero no es ingreso ni gasto", async () => {
  const html = await htmlDeUnMovimiento({
    movimiento: unMovimiento({ estado: "sin_conciliar" }),
    parejas: [{ valor: 9, texto: "30/09/2026 · TRASPASO A LA DEL GASÓLEO · 500,00 €" }],
  });
  assert.match(html, /Si este dinero solo ha cambiado de cuenta/);
  assert.ok(idsDe(html).includes("banco-pareja"), "no se puede elegir la otra parte del traspaso");
  assert.match(html, /TRASPASO A LA DEL GASÓLEO/, "no sale la otra parte del traspaso");
  const acciones = accionesDe(html);
  assert.ok(acciones.includes("banco-traspaso-atar"), "no hay forma de atar el traspaso");
  assert.ok(!acciones.includes("banco-traspaso-quitar"), "se puede quitar un traspaso que no está atado");
});

test("un movimiento ya atado se puede desatar, y se dice que no cuenta como ingreso ni como gasto", async () => {
  const html = await htmlDeUnMovimiento({
    // Un traspaso **no se puede conciliar**: ese dinero solo ha cambiado de sitio.
    movimiento: unMovimiento({
      es_traspaso_propio: true,
      pareja_de_traspaso_id: 9,
      se_puede_conciliar: false,
      por_que_no: "es_un_traspaso_entre_cuentas_tuyas",
    }),
    propuestas: [],
  });
  const acciones = accionesDe(html);
  assert.ok(acciones.includes("banco-traspaso-quitar"), "no hay forma de quitar el traspaso");
  assert.ok(!acciones.includes("banco-traspaso-atar"), "se puede atar un traspaso ya atado");
  assert.ok(!acciones.includes("banco-conciliar-a-mano"), "se puede cuadrar un traspaso con un papel");
  assert.match(html, /solo ha cambiado de sitio y no salda ninguna factura/);
  assert.match(html, /este dinero ya no cuenta como ingreso ni como gasto|solo ha cambiado de cuenta/);
});

test("sin otra cuenta a la que atarlo se dice, en vez de dejar el traspaso a medias", async () => {
  const html = await htmlDeUnMovimiento({ parejas: [] });
  assert.match(html, /No hay ningún movimiento de otra cuenta tuya al que atarlo/);
  assert.ok(!idsDe(html).includes("banco-pareja"));
});

// ===========================================================================
// 7. Corregir a mano el importe que no consta
// ===========================================================================

test("la ficha ofrece escribir a mano el importe, que es la puerta que existe para eso", async () => {
  const html = await htmlDeUnMovimiento();
  assert.ok(accionesDe(html).includes("banco-corregir"), "no hay dónde escribir el importe a mano");
});

test("el formulario de corregir sale con sus campos y con qué se está guardando", async () => {
  const html = await htmlDeUnMovimiento({
    formulario: unFormulario({
      titulo: "Corregir este movimiento",
      datos: { clase: "correccion", id: 5 },
      bloques: [
        { tipo: "numero", id: "banco-importe", etiqueta: "El importe", valor: "" },
        {
          tipo: "opciones",
          campo: "signo",
          etiqueta: "Si el dinero entra o sale",
          elegido: "",
          opciones: [
            { valor: "entra", texto: "Entra" },
            { valor: "sale", texto: "Sale" },
          ],
        },
        { tipo: "texto", id: "banco-motivo", etiqueta: "Por qué lo corriges", valor: "" },
      ],
    }),
  });
  assert.match(html, /Corregir este movimiento/);
  assert.deepEqual(
    idsDe(html).filter((id) => id.startsWith("banco-")),
    ["banco-importe", "banco-motivo"],
  );
  // Las opciones de un bloque de elegir salen **sin ninguna elegida**: la pantalla no contesta por nadie.
  assert.doesNotMatch(html, /data-elegido="1"/);
  assert.match(html, /data-accion="banco-elegir" data-campo="signo" data-valor="entra"/);
  // Y el botón de guardar dice **qué** se está guardando.
  const guardar = botonesDe(html).filter((boton) => boton.accion === "banco-guardar");
  assert.deepEqual(guardar.map((boton) => boton.clase), ["correccion"]);
  assert.deepEqual(guardar.map((boton) => boton.id), ["5"]);
});

// ===========================================================================
// 8. Lo que queda por cuadrar, de los dos lados
// ===========================================================================

test("los pendientes se enseñan de los dos lados: dinero sin papel y papeles sin dinero", async () => {
  const html = await htmlDeLosBancos({
    movimientos: [unMovimiento()],
    agregados: {
      entradas: "1708.65",
      texto_entradas: "1.708,65 €",
      salidas: "1126.15",
      texto_salidas: "1.126,15 €",
      sin_importe: 1,
      sin_conciliar: 3,
      conciliados: 4,
      a_medias: 1,
      importes_que_no_constan: 1,
    },
    pendientes: [unPendiente(), otroPendiente()],
  });

  assert.match(html, /Lo que queda por cuadrar/);
  assert.match(html, /Dinero del banco sin papel/);
  assert.match(html, />3</, "no sale cuántos movimientos están sin cuadrar");
  assert.match(html, /1\.708,65 €/, "no sale lo que ha entrado");
  assert.match(html, /1\.126,15 €/, "no sale lo que ha salido");
  assert.match(html, /Papeles sin dinero/);
  // Del papel: qué es, de quién, su referencia y lo que le falta.
  assert.match(html, /Una factura tuya, de lo que has vendido/);
  assert.match(html, /Cooperativa del Sur/);
  assert.match(html, /F-2026-12/);
  assert.match(html, /121,00 €/);
  assert.match(html, /Le falta/);
  // Y se dice cómo se cuadra, para que la lista no sea un callejón sin salida.
  assert.match(html, /abre el movimiento del banco y dile contra qué papel va/);
});

test("sin nada pendiente se dice, y sin movimientos se dice qué hacer", async () => {
  const html = await htmlDeLosBancos();
  assert.match(html, /No queda nada por cuadrar/);
  assert.match(html, /Sube el extracto de tu banca para empezar/);
});

test("si el buscador o el estado no encuentran nada se dice, y se puede volver a ver todo", async () => {
  const html = await htmlDeLosBancos({ filtro: "pepito" });
  assert.match(html, /Ningún movimiento coincide con lo que buscas/);
  assert.ok(accionesDe(html).includes("banco-ver-todos"), "no hay forma de quitar el filtro");
  // Y con el estado puesto también se dice, en vez de dejar la lista en blanco.
  const conEstado = await htmlDeLosBancos({ estado: "sin_conciliar" });
  assert.match(conEstado, /Ningún movimiento coincide con lo que buscas/);
});

test("el desplegable del estado lleva las cuatro palabras del servidor y ninguna inventada", async () => {
  const html = await htmlDeLosBancos();
  for (const palabra of ["Sin cuadrar", "A medias", "Cuadrado", "No consta el importe", "Todos"]) {
    assert.ok(html.includes(palabra), `no sale «${palabra}» en el desplegable del estado`);
  }
  assert.match(html, /id="banco-estado"/);
});

test("la lista lleva el enlace de descarga y la tabla del ordenador", async () => {
  const html = await htmlDeLosBancos({
    movimientos: [unMovimiento()],
    tabla: {
      clave: "bancos",
      etiqueta: "Los movimientos del banco, en una tabla",
      columnas: [{ texto: "El día" }, { texto: "Qué fue" }],
      filas: [{ celdas: [{ texto: "01/10/2026" }], acciones: [] }],
      resumen: "1 movimiento",
    },
    resumen: "Tienes 1 movimiento",
  });
  assert.ok(accionesDe(html).includes("banco-exportar"), "no hay forma de sacar el extracto en un fichero");
  assert.ok(html.includes("solo-escritorio tabla-scroll"), "no sale la tabla del ordenador");
  assert.ok(html.includes('class="lista solo-movil"'), "no sale la lista del móvil");
  // Las dos son la misma lista: la del ordenador y la del móvil salen en el mismo HTML.
  assert.match(html, /TRANSFERENCIA RECIBIDA DE LA COOPERATIVA/);
});

test("el buscador y el filtro del estado llevan su campo con su id", async () => {
  const html = await htmlDeLosBancos();
  assert.ok(idsDe(html).includes("banco-buscar"), "no hay dónde buscar");
  assert.ok(idsDe(html).includes("banco-estado"), "no se puede elegir qué estados ver");
  assert.equal(idsDe(html).filter((id) => id === "banco-buscar").length, 1, "hay dos buscadores");
});

// ===========================================================================
// 9. Las claves compuestas: la que falte sale en blanco
// ===========================================================================

test("las cuatro familias de claves compuestas están enteras en los textos", async () => {
  // El servidor manda `estado`, `lo_que_falta`, `por_que_no` y el tipo de una propuesta **como claves**, y
  // la pantalla compone la frase. La que falte **no revienta: sale en blanco**, y un renglón en blanco en
  // medio de una pantalla de dinero es lo peor que puede pasar aquí. Por eso se recorren las cuatro
  // familias enteras, sacadas de `app/extractos.py` (no de una lista escrita a mano aquí).
  const familias = {
    estado: ["sin_conciliar", "conciliado_en_parte", "conciliado", "no_se_puede_conciliar"],
    falta: [
      "importe_no_consta",
      "saldo_no_consta",
      "referencia_no_consta",
      "concepto_no_consta",
      "importe_ilegible_en_la_fila",
      "saldo_ilegible",
    ],
    por_que_no: ["no_consta_el_importe", "es_un_traspaso_entre_cuentas_tuyas"],
    propuesta: ["exacta", "agrupada", "parcial"],
  };
  for (const [familia, claves] of Object.entries(familias)) {
    for (const clave of claves) {
      const nombre = `${familia}_${clave}`;
      assert.ok(
        Object.prototype.hasOwnProperty.call(BANCOS, nombre),
        `falta «${nombre}» en los textos: esa frase saldría en blanco en la pantalla`,
      );
      assert.ok(BANCOS[nombre].length > 0, `«${nombre}» está vacía`);
    }
  }
  // Y los estados no se confunden: «sin cuadrar» (se puede y no lo has hecho) no es «no consta el importe».
  assert.notEqual(BANCOS.estado_sin_conciliar, BANCOS.estado_no_se_puede_conciliar);
});

test("las cuatro familias salen de verdad pintadas en la pantalla", async () => {
  // Que estén en los textos no basta: tienen que llegar a la pantalla. Se recorren los cuatro estados, los
  // seis motivos de lo que no consta, los dos porqués y los tres tipos de propuesta.
  const estados = ["sin_conciliar", "conciliado_en_parte", "conciliado", "no_se_puede_conciliar"];
  const vistos = new Set();
  let todo = "";
  for (const estado of estados) {
    const html = await htmlDeLosBancos({
      movimientos: [
        unMovimiento({
          estado,
          importe: estado === "no_se_puede_conciliar" ? null : "500.00",
          texto_importe: estado === "no_se_puede_conciliar" ? "" : "500,00 €",
          se_puede_conciliar: estado !== "no_se_puede_conciliar",
          por_que_no: estado === "no_se_puede_conciliar" ? "no_consta_el_importe" : null,
        }),
      ],
    });
    todo += html;
    vistos.add(BANCOS[`estado_${estado}`]);
    if (estado === "no_se_puede_conciliar") vistos.add(BANCOS.por_que_no_no_consta_el_importe);
  }
  todo += await htmlDeLosBancos({
    movimientos: [
      unMovimiento({
        lo_que_falta: [
          "importe_no_consta",
          "saldo_no_consta",
          "referencia_no_consta",
          "concepto_no_consta",
          "importe_ilegible_en_la_fila",
          "saldo_ilegible",
        ],
      }),
    ],
  });
  for (const falta of [
    "importe_no_consta",
    "saldo_no_consta",
    "referencia_no_consta",
    "concepto_no_consta",
    "importe_ilegible_en_la_fila",
    "saldo_ilegible",
  ]) {
    vistos.add(BANCOS[`falta_${falta}`]);
  }
  todo += await htmlDeUnMovimiento({
    propuestas: [
      unaPropuesta({ tipo: "exacta" }),
      unaPropuesta({ tipo: "agrupada" }),
      unaPropuesta({ tipo: "parcial" }),
    ],
  });
  for (const tipo of ["exacta", "agrupada", "parcial"]) vistos.add(BANCOS[`propuesta_${tipo}`]);
  todo += await htmlDeUnMovimiento({
    movimiento: unMovimiento({
      es_traspaso_propio: true,
      se_puede_conciliar: false,
      por_que_no: "es_un_traspaso_entre_cuentas_tuyas",
    }),
  });
  vistos.add(BANCOS.por_que_no_es_un_traspaso_entre_cuentas_tuyas);

  for (const frase of vistos) {
    assert.ok(todo.includes(frase), `«${frase}» no sale pintada en ninguna rama de la pantalla`);
  }
});

// ===========================================================================
// 10. Las acciones: la lista entera, y ninguna de más
// ===========================================================================

test("las acciones que pinta la pantalla son las del informe, y ninguna más", async () => {
  // **Esta prueba fija la lista.** El manejador de clics de `app.js` es uno solo: una acción que se pinte y
  // nadie atienda es un botón que se pulsa y no hace nada. La lista con lo que hace cada una está en
  // `docs/T20_PANTALLA.md`, y si alguien inventa una acción nueva, aquí se ve.
  const esperadas = new Set([
    "banco-leer",
    "banco-importar",
    "banco-descartar",
    "banco-abrir",
    "banco-buscar",
    "banco-ver-todos",
    "banco-cuenta-nueva",
    "banco-perfil-nuevo",
    "banco-guardar",
    "banco-cancelar",
    "banco-elegir",
    "banco-exportar",
    "banco-conciliar-propuesta",
    "banco-conciliar-a-mano",
    "banco-deshacer",
    "banco-traspaso-atar",
    "banco-traspaso-quitar",
    "banco-corregir",
    "banco-ver",
    "ir-inicio",
  ]);

  const vistas = new Set();
  // Todas las ramas que pueden pintar un botón: la lista llena, la vacía, sin cuentas, con vista previa,
  // con resultado, con un formulario de escribir y con uno de elegir, y la ficha en sus cuatro estados.
  const ramas = [
    await htmlDeLosBancos(),
    await htmlDeLosBancos({ cuentas: [] }),
    await htmlDeLosBancos({ movimientos: [unMovimiento()], pendientes: [unPendiente()] }),
    await htmlDeLosBancos({ vistaPrevia: laVistaPrevia(), importando: true }),
    await htmlDeLosBancos({ resultado: elResultadoDeLaImportacion() }),
    await htmlDeLosBancos({ formulario: unFormularioConOpciones() }),
    await htmlDeLosBancos({ filtro: "pepito" }),
    await htmlDeUnMovimiento(),
    await htmlDeUnMovimiento({
      movimiento: unMovimiento({ estado: "conciliado", imputado: "500.00", texto_imputado: "500,00 €" }),
      propuestas: [unaPropuesta()],
      pendientes: [unPendiente()],
      papeles: [{ valor: "factura_emitida:3", texto: "Una factura tuya" }],
      parejas: [{ valor: 9, texto: "La otra pata" }],
    }),
    await htmlDeUnMovimiento({ movimiento: unMovimiento({ es_traspaso_propio: true }) }),
    await htmlDeUnMovimiento({ movimiento: unMovimientoSinImporte() }),
    await htmlDeUnMovimiento({ formulario: unFormularioConOpciones({ datos: { clase: "correccion", id: 5 } }) }),
  ];
  for (const html of ramas) for (const accion of accionesDe(html)) vistas.add(accion);

  const de_mas = [...vistas].filter((accion) => !esperadas.has(accion));
  const de_menos = [...esperadas].filter((accion) => !vistas.has(accion));
  assert.deepEqual(de_mas, [], "hay acciones que nadie ha decidido y que el manejador de clics no atiende");
  assert.deepEqual(de_menos, [], "hay acciones del informe que la pantalla no pinta");
});

test("ninguna acción va puesta por variable, para que el guardián pueda leerlas", async () => {
  // `tests/test_los_botones_hacen_algo.py` lee las acciones del código: una puesta por variable **no se
  // puede leer**, y un botón que no hiciera nada pasaría desapercibido. Esta pantalla es nueva, así que no
  // está en la lista de los ficheros que sí pueden hacerlo.
  //
  // Se quitan los comentarios antes de mirar, y no es un detalle: el comentario de cabecera del propio
  // fichero **nombra la forma prohibida** para explicarla, y sin quitarlo la prueba se pondría roja por el
  // texto que la documenta.
  const fuente = readFileSync(new URL("../web/react/pantallas/bancos.js", import.meta.url), "utf8")
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/^\s*\/\/.*$/gm, "");
  const dinamicas = [...fuente.matchAll(/data-accion=\$\{/g), ...fuente.matchAll(/\baccion=\$\{/g)];
  assert.deepEqual(dinamicas, [], "hay acciones puestas por variable en la pantalla del banco");
  assert.ok(fuente.includes('accion: "banco-abrir"'), "el quitador se ha comido el fichero");
});

test("los campos del formulario son los que lee app.js", async () => {
  // Si un `id` cambia, `app.js` recoge vacío y el extracto se apunta sin lo que el agricultor escribió, sin
  // que salte nada.
  const deLaLista = idsDe(await htmlDeLosBancos({ vistaPrevia: laVistaPrevia() }));
  for (const campo of ["banco-fichero", "banco-cuenta", "banco-perfil", "banco-buscar", "banco-estado"]) {
    assert.ok(deLaLista.includes(campo), `falta el campo «${campo}», y app.js lo busca`);
  }
  const deLaFicha = idsDe(
    await htmlDeUnMovimiento({
      propuestas: [unaPropuesta()],
      pendientes: [unPendiente()],
      papeles: [{ valor: "factura_emitida:3", texto: "Una factura tuya" }],
      parejas: [{ valor: 9, texto: "La otra pata" }],
    }),
  );
  for (const campo of ["banco-papel", "banco-cantidad", "banco-pareja"]) {
    assert.ok(deLaFicha.includes(campo), `falta el campo «${campo}», y app.js lo busca`);
  }
});

test("cada botón lleva los datos que necesita, y no solo su nombre", async () => {
  // Un botón con su acción y sin su dato es un botón que no sabe sobre qué actuar.
  const deLaLista = botonesDe(
    await htmlDeLosBancos({ movimientos: [unMovimiento({ id: 5 })] }),
  );
  const abrir = deLaLista.filter((boton) => boton.accion === "banco-abrir");
  assert.ok(abrir.length >= 1, "no hay forma de abrir un movimiento");
  assert.deepEqual([...new Set(abrir.map((boton) => boton.id))], ["5"]);

  const deLaFicha = botonesDe(
    await htmlDeUnMovimiento({
      movimiento: unMovimiento({
        id: 5,
        estado: "conciliado",
        imputado: "500.00",
        texto_imputado: "500,00 €",
        es_traspaso_propio: true,
      }),
      propuestas: [unaPropuesta()],
      papeles: [{ valor: "factura_emitida:3", texto: "Una factura tuya" }],
    }),
  );
  for (const accion of ["banco-deshacer", "banco-corregir", "banco-traspaso-quitar"]) {
    const suyos = deLaFicha.filter((boton) => boton.accion === accion);
    assert.ok(suyos.length >= 1, `no sale el botón «${accion}»`);
    assert.deepEqual([...new Set(suyos.map((boton) => boton.id))], ["5"], `«${accion}» no dice sobre qué actúa`);
  }
  const propuesta = deLaFicha.filter((boton) => boton.accion === "banco-conciliar-propuesta");
  assert.deepEqual(propuesta.map((boton) => boton.indice), ["0"], "el botón de la propuesta no dice cuál es");
});

test("al guardar se dice qué se está guardando, para que el manejador sepa a qué puerta ir", async () => {
  const html = await htmlDeLosBancos({ formulario: unFormulario({ datos: { clase: "perfil" } }) });
  const guardar = botonesDe(html).filter((boton) => boton.accion === "banco-guardar");
  assert.deepEqual(guardar.map((boton) => boton.clase), ["perfil"]);
});

// ===========================================================================
// 11. Ni una frase escrita a mano, y ninguna clave en blanco
// ===========================================================================

/**
 * Un vocabulario de mentira que **apunta qué claves se leen**.
 *
 * Es la forma de comprobar dos cosas de una vez, y las dos son el mismo defecto: una clave que la pantalla
 * lee y no está en los textos **sale en blanco en la pantalla** (y no revienta nada, así que ningún test se
 * entera), y una frase que está y no la lee nadie es una frase que se queda vieja.
 */
function vocabularioQueApuntaLasClaves(usadas) {
  return new Proxy(
    {},
    {
      get(_destino, clave) {
        if (typeof clave !== "string") return undefined;
        usadas.add(clave);
        // El valor es la clave entre comillas angulares: así se ve en el HTML y se puede comprobar.
        return `«${clave}»`;
      },
    },
  );
}

test("la pantalla no lee ninguna frase que no esté en los textos, y no le sobra ninguna", async () => {
  const usadas = new Set();
  const textos = {
    bancos: vocabularioQueApuntaLasClaves(usadas),
    acciones: vocabularioQueApuntaLasClaves(new Set()),
  };

  // Se recorren **todas** las ramas de las dos pantallas: la lista con movimientos y vacía, sin cuentas,
  // con la vista previa (con líneas rechazadas, avisos y traspasos), con el resultado de apuntar, con el
  // formulario abierto, con filtro, y la ficha con los cuatro estados, con propuestas de los tres tipos,
  // con papeles y sin ellos, con la otra pata del traspaso y sin ella, y deshecha. Si una clave solo se lee
  // en una de esas ramas y nadie la recorre, esta prueba no la vería: por eso están todas.
  await htmlDeLosBancos({ textos });
  await htmlDeLosBancos({ textos, cuentas: [], perfiles: [] });
  await htmlDeLosBancos({ textos, formulario: unFormularioConOpciones(), guardando: true });
  await htmlDeLosBancos({ textos, filtro: "x", estado: "sin_conciliar", resumen: "Tienes 3" });
  await htmlDeLosBancos({ textos, ficheroElegido: "extracto.csv", leyendo: true });
  await htmlDeLosBancos({ textos, vistaPrevia: laVistaPrevia({ movimientos: [] }), importando: true });
  await htmlDeLosBancos({ textos, vistaPrevia: laVistaPrevia({ el_fichero_ya_estaba: true, ya_estaban: 2 }) });
  await htmlDeLosBancos({
    textos,
    movimientos: [
      unMovimiento(),
      unMovimiento({
        estado: "conciliado_en_parte",
        es_traspaso_propio: true,
        corregido: true,
        lo_que_falta: [
          "importe_no_consta",
          "saldo_no_consta",
          "referencia_no_consta",
          "concepto_no_consta",
          "importe_ilegible_en_la_fila",
          "saldo_ilegible",
        ],
      }),
      unMovimiento({ estado: "conciliado" }),
      unMovimientoSinImporte(),
    ],
    pendientes: [unPendiente(), otroPendiente({ contraparte: "", referencia: "" })],
    agregados: { sin_conciliar: 1, texto_entradas: "", texto_salidas: "", importes_que_no_constan: 1 },
  });
  await htmlDeLosBancos({
    textos,
    vistaPrevia: laVistaPrevia({
      cuenta_detectada: null,
      formato_de_fecha: null,
      texto_saldo_final: "",
      rechazadas: [{ numero_de_linea: 7, motivo: "sin_signo", que_pasa: "Algo", texto: "x;y", lo_que_dice: null }],
      avisos: [{ codigo: "x", que_pasa: "Un aviso", lineas: [6] }],
      traspasos: [
        { sale_de: "c1", entra_en: "c2", importe: "500.00", texto_importe: "500,00 €", dias_de_diferencia: 1, cuentas: ["a", "b"], que_pasa: "Algo" },
      ],
      movimientos: [
        {
          numero_de_linea: 2,
          texto_fecha: "01/10/2026",
          concepto: "Algo",
          importe: null,
          texto_importe: "",
          saldo: null,
          texto_saldo: "",
          referencia: null,
          clave_de_duplicado: "c#1",
          ya_estaba: true,
          lo_que_falta: ["importe_no_consta"],
        },
      ],
      resumen: { ...laVistaPrevia().resumen, sin_importe: 1, texto_entradas: "", texto_salidas: "" },
    }),
  });
  await htmlDeLosBancos({ textos, resultado: elResultadoDeLaImportacion({ repetidos: 2, sin_importe: 1, avisos: ["Un aviso"], traspasos: [{ cuentas: ["a", "b"], texto_importe: "", dias_de_diferencia: 2, que_pasa: "Algo" }] }) });

  for (const estado of ["sin_conciliar", "conciliado_en_parte", "conciliado", "no_se_puede_conciliar"]) {
    await htmlDeUnMovimiento({
      textos,
      movimiento: unMovimiento({
        estado,
        es_traspaso_propio: estado === "conciliado",
        corregido: true,
        lo_que_falta: ["importe_no_consta"],
        por_que_no: estado === "no_se_puede_conciliar" ? "no_consta_el_importe" : "es_un_traspaso_entre_cuentas_tuyas",
        se_puede_conciliar: estado !== "no_se_puede_conciliar",
      }),
      propuestas: [
        unaPropuesta({ tipo: "exacta" }),
        unaPropuesta({ tipo: "agrupada", imputaciones: [{ clase: "cobro", documento_id: 99, importe: "40.00", texto_importe: "40,00 €" }] }),
        unaPropuesta({ tipo: "parcial" }),
      ],
      pendientes: [unPendiente()],
      papeles: [{ valor: "factura_emitida:3", texto: "Una factura tuya" }],
      parejas: [{ valor: 9, texto: "La otra pata" }],
      formulario: unFormulario(),
      cargando: true,
      guardando: true,
      error: "Algo ha fallado",
      aviso: "Un aviso",
      resultado: { conciliaciones: [], avisos: ["Un aviso"] },
    });
  }
  await htmlDeUnMovimiento({ textos });
  await htmlDeUnMovimiento({ textos, movimiento: unMovimientoSinImporte() });
  await htmlDeUnMovimiento({
    textos,
    // Un movimiento que no se puede cuadrar **porque es un traspaso tuyo**: es la otra clave de
    // `por_que_no`, y sin esta rama la frase no se leería en ninguna prueba.
    movimiento: unMovimiento({
      es_traspaso_propio: true,
      se_puede_conciliar: false,
      por_que_no: "es_un_traspaso_entre_cuentas_tuyas",
    }),
  });
  await htmlDeUnMovimiento({ textos, movimiento: unMovimiento({ estado: "conciliado", imputado: "1.00", texto_imputado: "1,00 €" }), resultado: { conciliaciones: [{ clase: "factura_emitida", documento_id: 3, importe: "1.00", texto_importe: "1,00 €" }], avisos: ["Un aviso"] }, deshecho: true, pendientes: [unPendiente()] });
  await htmlDeUnMovimiento({ textos, parejas: [] });

  const sin_frase = [...usadas].filter((clave) => !(clave in BANCOS) && clave !== "volver");
  assert.deepEqual(
    sin_frase.sort(),
    [],
    "estas claves las lee la pantalla y no están en la copia de los textos: saldrían en blanco",
  );
  const sin_usar = Object.keys(BANCOS).filter((clave) => !usadas.has(clave));
  assert.deepEqual(sin_usar.sort(), [], "estas frases están escritas y no las lee nadie");
});

test("la lista no lleva ni una frase escrita a mano", async () => {
  // Todo lo que se lee tiene que ser un texto del servidor o un dato que viene en las propiedades. Se
  // incluyen **los datos** en la lista de lo permitido porque la pantalla enseña frases que vienen del
  // servidor (el porqué de una propuesta, lo que pone una línea del fichero, el nombre de un papel): lo
  // que esta prueba caza es una frase **escrita dentro del componente**.
  const props = {
    movimientos: [unMovimiento(), unMovimientoSinImporte()],
    pendientes: [unPendiente(), otroPendiente()],
    agregados: {
      sin_conciliar: 3,
      texto_entradas: "1.708,65 €",
      texto_salidas: "1.126,15 €",
      importes_que_no_constan: 1,
    },
    vistaPrevia: laVistaPrevia({
      rechazadas: [{ numero_de_linea: 7, motivo: "m", que_pasa: "Un motivo", texto: "x;y", lo_que_dice: null }],
      traspasos: [
        {
          sale_de: "c1",
          entra_en: "c2",
          importe: "1.00",
          texto_importe: "1,00 €",
          dias_de_diferencia: 1,
          cuentas: ["a", "b"],
          que_pasa: "Un traspaso",
        },
      ],
    }),
    resultado: elResultadoDeLaImportacion({ avisos: ["Un aviso"] }),
    formulario: unFormularioConOpciones(),
    resumen: "Tienes 2 movimientos",
  };
  const html = await htmlDeLosBancos(props);
  const delServidor = new Set([
    ...todosLosTextos(TEXTOS),
    ...todosLosTextos(CUENTAS),
    ...todosLosTextos(PERFILES),
    ...todosLosTextos(props),
  ]);
  for (const frase of frasesVisibles(html)) {
    assert.ok(delServidor.has(frase), `frase escrita a mano: «${frase}»`);
  }
});

test("la ficha no lleva ni una frase escrita a mano", async () => {
  const props = {
    movimiento: unMovimiento({ estado: "conciliado", imputado: "500.00", texto_imputado: "500,00 €" }),
    propuestas: [
      unaPropuesta({
        tipo: "agrupada",
        imputaciones: [{ clase: "cobro", documento_id: 8, importe: "40.00", texto_importe: "40,00 €" }],
      }),
      unaPropuesta({
        tipo: "parcial",
        imputaciones: [{ clase: "factura_emitida", documento_id: 99, importe: "10.00", texto_importe: "10,00 €" }],
      }),
    ],
    pendientes: [unPendiente(), otroPendiente()],
    papeles: [{ valor: "factura_emitida:3", texto: "Una factura tuya" }],
    parejas: [{ valor: 9, texto: "La otra pata" }],
    formulario: unFormularioConOpciones(),
    resultado: {
      conciliaciones: [
        { clase: "factura_emitida", documento_id: 3, importe: "500.00", texto_importe: "500,00 €" },
      ],
      avisos: ["Un aviso"],
    },
    deshecho: true,
  };
  const html = await htmlDeUnMovimiento(props);
  const delServidor = new Set([...todosLosTextos(TEXTOS), ...todosLosTextos(props)]);
  for (const frase of frasesVisibles(html)) {
    assert.ok(delServidor.has(frase), `frase escrita a mano: «${frase}»`);
  }
});

test("un movimiento ya apuntado entero lo dice, y no ofrece apuntar nada más", async () => {
  // **El fallo que esto fija.** El servidor proponía con el importe entero del movimiento aunque ya
  // estuviera apuntado: la pantalla enseñaba «APUNTAR ESTA», se pulsaba y salía un error, porque ese
  // dinero ya estaba apuntado. Ahora el servidor no propone nada en ese caso y manda la frase; la
  // pantalla tiene que enseñarla **y no dejar ninguna puerta abierta** que no pueda funcionar.
  const frase = "Este movimiento ya está apuntado entero a sus papeles. Deshaz lo apuntado y vuelve a repartirlo.";
  const props = {
    yaApuntado: frase,
    movimiento: unMovimiento({ estado: "conciliado", imputado: "500.00", texto_imputado: "500,00 €", por_conciliar: "0.00" }),
    propuestas: [unaPropuesta()],
    pendientes: [unPendiente()],
    papeles: [{ valor: "factura_emitida:3", texto: "Una factura tuya" }],
  };
  const html = await htmlDeUnMovimiento(props);

  assert.match(html, /ya está apuntado entero/, "no se dice que ya está apuntado");
  assert.ok(!accionesDe(html).includes("banco-conciliar-propuesta"), "se ofrece apuntar otra vez lo ya apuntado");
  assert.ok(!accionesDe(html).includes("banco-conciliar-a-mano"), "se ofrece apuntarlo a mano cuando no queda nada");
  assert.ok(!idsDe(html).includes("banco-papel"), "el desplegable de papeles sigue ahí sin nada que repartir");
  // Y la frase del servidor no se ha inventado aquí dentro: llega como propiedad.
  assert.ok(props.yaApuntado.includes("Deshaz"), "la frase tiene que decir qué hacer para arreglarlo");

  // El contraste, que es lo que impide que esta prueba pase por haber escondido todo: con dinero que
  // queda, la propuesta **sí** se ofrece.
  const conDinero = await htmlDeUnMovimiento({
    movimiento: unMovimiento({ estado: "sin_conciliar", por_conciliar: "500.00" }),
    propuestas: [unaPropuesta()],
    pendientes: [unPendiente()],
    papeles: [{ valor: "factura_emitida:3", texto: "Una factura tuya" }],
  });
  assert.ok(
    accionesDe(conDinero).includes("banco-conciliar-propuesta"),
    "con propuestas delante tiene que estar el botón de apuntarlas",
  );
});

test("ninguna frase de la copia lleva jerga", async () => {
  // La regla de la casa, comprobada en la copia que usan estas pruebas: si una frase lleva una palabra
  // prohibida, el test de jerga de Python la cazaría al entrar en `textos.py`… si alguien se acuerda de
  // meterla. Aquí se caza antes.
  const prohibidas = [
    "error",
    "validación",
    "cumplimentar",
    "epígrafe",
    "dosificación",
    "trazabilidad",
    "interfaz",
    "sincronizar",
    "sesión",
    "campo obligatorio",
    "operación cultural",
    "fitosanitario",
    "dgc",
    "uhc",
  ];
  for (const [clave, frase] of Object.entries(BANCOS)) {
    for (const prohibida of prohibidas) {
      assert.ok(!frase.toLowerCase().includes(prohibida), `«${clave}» lleva «${prohibida}»`);
    }
  }
});

test("la pantalla no toca el navegador y no hace cuentas de dinero", async () => {
  // El componente es **puro**: recibe propiedades y devuelve un elemento. Si tocara el navegador no se
  // podría probar sin uno; y si sumara o formateara importes, el total de la pantalla y el de la base
  // dejarían de coincidir por céntimos, que es justo lo que este proyecto no puede permitirse.
  const codigo = readFileSync(new URL("../web/react/pantallas/bancos.js", import.meta.url), "utf8")
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/^\s*\/\/.*$/gm, "");
  for (const prohibida of ["fetch(", "localStorage", "sessionStorage", "document.", "window."]) {
    assert.ok(!codigo.includes(prohibida), `bancos.js usa «${prohibida}»`);
  }
  for (const prohibido of ["parseFloat", "parseInt", "toFixed", "Number(", "Math."]) {
    assert.ok(!codigo.includes(prohibido), `la pantalla usa «${prohibido}» para hacer cuentas`);
  }
  assert.ok(!/\+\s*[a-zA-Z_$][\w.$]*\.importe/.test(codigo), "la pantalla suma importes");
  assert.ok(codigo.includes("export function PantallaDeLosBancos"), "el quitador se ha comido el fichero");
  assert.ok(codigo.includes("export function pantallaDeUnMovimiento"), "falta el elemento montado de la ficha");
});

test("un fallo del servidor se enseña con su motivo, y no deja la pantalla en blanco", async () => {
  const html = await htmlDeLosBancos({ error: "No se ha podido leer el fichero. Prueba con otro." });
  assert.match(html, /No se ha podido leer el fichero/, "el motivo del servidor no llega al agricultor");
  assert.match(html, /role="alert"/, "el aviso no se anuncia solo");
  // Y la pantalla sigue estando: se puede volver a intentarlo.
  assert.ok(accionesDe(html).includes("banco-leer"), "un fallo deja al agricultor sin poder reintentar");
});
