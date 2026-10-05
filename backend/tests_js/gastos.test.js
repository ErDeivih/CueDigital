/*
 * gastos.test.js — las pruebas de la pantalla de las cuentas (T13, E7, 05/10/2026).
 *
 * QUÉ SE COMPRUEBA AQUÍ, Y POR QUÉ ESTAS COSAS
 *
 * El componente es **puro**: recibe todo por propiedades, así que se puede montar sin navegador y sin
 * servidor (el arnés es el mismo que el de las demás pantallas: React y htm de `vendor/`, y
 * `renderToStaticMarkup`). Y lo que se comprueba es la mitad visible de las cuatro reglas del ticket:
 *
 *  1. **Las tres columnas del coste van separadas** (directos, repartidos y sin asignar), con su
 *     nombre y su total. Es lo primero que pide el contrato en S13.
 *  2. **Un importe que no consta se enseña en blanco y con la palabra que lo dice**, nunca como
 *     `0,00 €`. Es la prueba que muerde: si alguien «arregla» la pantalla pintando un cero donde no
 *     se sabe el importe, aquí se pone roja.
 *  3. **El margen de un cultivo al que le falta un coste NO se enseña como un número**: sale la frase
 *     que dice que está incompleto. Un margen calculado con datos que faltan sale más alto que el
 *     verdadero, y con él se toman decisiones.
 *  4. **La caja y el margen son dos tarjetas distintas** y las dos se ven, porque la respuesta a
 *     «¿gano dinero?» y a «¿puedo pagar el gasóleo?» no es la misma.
 *  5. **Las ayudas tienen sus tres cifras separadas** y la previsión lleva su frase: no se suma al
 *     ingreso cobrado.
 *  6. **Los botones llevan su acción y sus datos**, y los campos del formulario su `id`: un botón sin
 *     `data-accion` es un botón que no hace nada, y un campo sin `id` es un campo que se rellena y se
 *     guarda vacío sin decir nada.
 *
 * Y la de siempre: **ni una frase escrita a mano**. Todo lo que se lee sale de las propiedades, que es
 * lo que garantiza que el vocabulario siga viviendo en `textos.py` (donde el test de jerga lo revisa).
 */

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import vm from "node:vm";

// El arnés: React y htm, como los deja `index.html` (ver `react.test.js`, que lo cuenta entero).
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
// Los textos: los mismos que sirve `/api/interfaz` (los de `textos.GASTOS`)
// ---------------------------------------------------------------------------

const GASTO = {
  // **Copia literal de `textos.GASTOS`.** La prueba del backend que compara las dos listas exigirá
  // que diga lo mismo que el servidor; aquí se copia para que esta prueba se pueda leer sola.
  titulo: "Mis cuentas",
  explica:
    "Aquí está lo que te ha costado y lo que has ingresado. Cada gasto dice cuánto costó, a qué tierra o cultivo va y cuánto queda por pagar.",
  cuantas: "Tienes {cuantos} gastos apuntados.",
  cuantas_uno: "Tienes 1 gasto apuntado.",
  sin_gastos: "Todavía no has apuntado ningún gasto. Empieza por el que tengas el papel a mano: el abono, el gasóleo o la reparación.",
  sin_resultados: "Ningún gasto coincide con lo que buscas. Prueba con otras letras o pulsa VER TODAS.",
  nuevo: "APUNTAR UN GASTO",
  nuevo_pago: "APUNTAR UN PAGO",
  nueva_inversion: "APUNTAR UNA INVERSIÓN",
  nueva_ayuda: "APUNTAR UNA AYUDA",
  buscar: "BUSCAR",
  buscar_pista: "Escribe las primeras letras del concepto o del proveedor",
  ver_todas: "VER TODAS",
  abrir: "VER ESTE GASTO",
  corregir: "CORREGIR",
  anular: "ANULAR",
  anular_motivo: "¿Por qué lo anulas?",
  rellenar: "RELLENAR EL IMPORTE",
  importe: "Lo que costó",
  pagado: "Pagado",
  pendiente: "Falta por pagar",
  como_esta: "Cómo está",
  proveedor: "Proveedor:",
  su_tierra: "Va a",
  su_cuenta: "La cuenta de este gasto",
  no_se_sabe: "No lo sé",
  sin_asignar_corto: "Sin asignar",
  sin_asignar_explica:
    "Lo que está sin asignar es un coste que ya sabes que existe pero todavía no está en ninguna tierra. Sigue contando en tus cuentas: solo falta decir a dónde va.",
  estado_sin_importe: "Falta saber lo que costó",
  estado_sin_pagar: "Sin pagar",
  estado_pagado_en_parte: "Pagado a medias",
  estado_pagado: "Pagado",
  estado_vencido: "Vencido",
  estado_anulado: "Anulado",
  esta_anulado: "Esto está anulado, con su motivo. Sigue aquí para que sepas que estuvo.",
  esta_anulada: "Esta compra está anulada.",
  cuadre_titulo: "Las cuentas de este gasto",
  cuadre_entero: "Lo que costó",
  cuadre_repartido: "En tierras, cultivos o máquinas",
  cuadre_sin_asignar: "Sin asignar",
  cuadre_no_cierra:
    "Estas cuentas no cierran: hay una parte del gasto que no está ni en un sitio ni en el otro.",
  todavia_sin_reparto: "Todavía no has dicho a qué tierra o cultivo va este gasto.",
  reparto_metodo: "Se repartió",
  reparto_quitar: "QUITARLO DE AQUÍ",
  repartir: "REPARTIRLO",
  dejarlo_sin_asignar: "DEJARLO SIN ASIGNAR",
  metodo_area: "por hectáreas",
  metodo_horas: "por horas",
  metodo_consumo: "por lo que se gastó en cada sitio",
  metodo_manual: "a mano",
  coste_titulo: "Lo que te ha costado",
  coste_explica:
    "Lo directo es lo que dice el papel de un gasto de esa tierra. Lo repartido lo has repartido tú. Y lo sin asignar es un coste que existe y todavía no va a ningún sitio.",
  coste_directo: "Directo",
  coste_repartido: "Repartido",
  coste_sin_asignar: "Sin asignar",
  coste_total_conocido: "Total conocido",
  cuantos_sin_importe: "Gastos de los que no sabes el importe",
  sin_importe_explica: "De esos no se puede hacer la cuenta hasta que apuntes lo que costaron",
  caja_titulo: "La caja",
  caja_explica:
    "Esto es el dinero que ha entrado y salido de verdad. No es lo mismo que el margen: puedes haber vendido mucho y no haber cobrado nada todavía.",
  caja_entrado: "Ha entrado",
  caja_salido: "Ha salido",
  caja_saldo: "Queda",
  caja_por_pagar: "Falta por pagar",
  ayudas_cobradas: "Ayudas cobradas",
  ayudas_previstas: "Ayudas pedidas o concedidas, sin cobrar",
  prevision_no_es_ingreso: "Esto no se suma a lo que ha entrado: todavía no es dinero tuyo",
  margen_titulo: "El margen de cada cultivo",
  margen_explica:
    "Lo que has ingresado menos lo que te ha costado. Si falta el importe de un gasto, el margen no se puede calcular y aquí se dice por qué.",
  ingresos: "Has ingresado",
  coste_conocido: "Te ha costado",
  margen: "Margen",
  margen_incompleto:
    "De este cultivo no se puede calcular el margen: falta el importe de algún gasto o de algún ingreso. Apunta lo que falta y vuelve a mirarlo.",
  inversiones_titulo: "Las inversiones",
  inversiones_explica:
    "Un tractor o una nave no son un gasto del año: duran años. Lo que de ellos le toca a esta campaña lo dices tú, y lo que no digas se queda sin asignar.",
  inversion_en_la_campana: "De esto le toca a esta campaña",
  ayudas_titulo: "Las ayudas",
  ayudas_explica:
    "Lo que has pedido, lo que te han concedido y lo que has cobrado son tres cosas distintas, y aquí van separadas.",
  ayuda_prevista: "Pedido",
  ayuda_concedida: "Concedido",
  ayuda_cobrada: "Cobrado",
  ayuda_estado_prevista: "Pedida, sin resolver",
  ayuda_estado_concedida: "Concedida, sin cobrar",
  ayuda_estado_cobrada: "Cobrada",
  pagos_titulo: "Los pagos",
  pagos_explica: "El dinero que ha salido, y a qué gastos va.",
  sin_pagos: "Todavía no has apuntado ningún pago.",
  pago_aplicado: "Va a gastos por",
  pago_sin_conciliar: "Sin saber a qué va",
  pago_conciliar: "DECIR A QUÉ VA",
  pago_deshacer: "DESHACER ESTO",
  sin_conciliar_titulo: "Dinero que salió y todavía no sabes a qué va",
  sin_conciliar_explica:
    "Ese dinero está apuntado y no se ha perdido: solo falta decir contra qué gasto va.",
  sus_pagos: "Los pagos de este gasto",
  que_falta_titulo: "Lo que este programa todavía no calcula",
  que_falta_explica:
    "Se dice para que no te fíes de una cifra que no está: cuando el programa no tiene el dato, no se lo inventa.",
  que_falta_para_que: "Para qué haría falta",
  que_falta_depende: "De quién depende",
  form_nuevo_titulo: "Apuntar un gasto",
  form_nuevo_pista:
    "Con el concepto y lo que costó ya queda apuntado. Lo que no sepas se deja en blanco: un hueco se queda en blanco y no se escribe un cero.",
  form_repartir_titulo: "Repartir este gasto",
  form_repartir_pista: "Elige cómo lo repartes. Si no lo sabes, déjalo sin asignar y dilo.",
  guardar: "GUARDAR",
  cancelar: "VOLVER SIN GUARDAR",
  guardando: "Guardando…",
  campo_concepto: "¿Qué fue?",
  campo_concepto_pista: "«Gasóleo», «abono del trigo», «reparación del remolque»",
  campo_categoria: "¿De qué es?",
  campo_importe: "¿Cuánto costó?",
  campo_importe_pista: "Si no lo sabes, déjalo en blanco",
  campo_metodo: "¿Cómo lo reparto?",
  campo_destino: "¿A qué se reparte?",
};

/**
 * Las dos frases que **compone el servidor** contando cosas (`textos.mensaje_con_cuenta`), que no
 * viven en `textos.GASTOS` porque son mensajes: llegan dentro de `coste_por_clase`, ya escritas.
 */
const FRASES_CONTADAS = {
  texto_sin_asignar_cuantos: "1 gasto sin saber a dónde va",
  texto_sin_importe: "Faltan 2 importes por saber",
};

const ACCIONES = { volver: "VOLVER" };

const TEXTOS = { gasto: GASTO, acciones: ACCIONES };

// ---------------------------------------------------------------------------
// Los datos: lo que devuelve `GET /api/gastos` (ya calculado por el servidor)
// ---------------------------------------------------------------------------

function elGasto(cambios = {}) {
  return {
    id: 7,
    campana_id: 1,
    fecha: "2026-03-04",
    vencimiento: "2026-04-03",
    concepto: "Abono 15-15-15",
    categoria: "abono",
    etiqueta_categoria: "Abono",
    proveedor: "Cooperativa Agrícola de Peñaranda",
    proveedor_nif: "B37000000",
    contacto_id: null,
    factura_id: 3,
    maquina_id: null,
    averia_id: null,
    parcela_id: null,
    cultivo: null,
    base_imponible: "600.00",
    cuota_iva: "63.00",
    tipo_iva_pct: 21,
    importe: "663.00",
    texto_importe: "663,00 €",
    pagado: "200.00",
    texto_pagado: "200,00 €",
    pendiente: "463.00",
    texto_pendiente: "463,00 €",
    estado: "pagado_en_parte",
    cuadre: { cuadra: true, se_puede_comprobar: true },
    repartos: [
      {
        id: 11,
        destino_tipo: "tierra",
        destino: "El Prado",
        etiqueta_destino: "El Prado",
        parcela_id: null,
        campana_id: null,
        maquina_id: null,
        importe: "463.00",
        texto_importe: "463,00 €",
        metodo: "area",
        confirmado_por_el_agricultor: true,
      },
      {
        id: 12,
        destino_tipo: "sin_asignar",
        destino: "",
        etiqueta_destino: "",
        parcela_id: null,
        campana_id: null,
        maquina_id: null,
        importe: "200.00",
        texto_importe: "200,00 €",
        metodo: "manual",
        confirmado_por_el_agricultor: false,
      },
    ],
    cuadre_del_reparto: {
      entero: "663.00",
      repartido: "463.00",
      sin_asignar: "200.00",
      total_conocido: "663.00",
      falta: "0.00",
      cuadra: true,
      trozos_sin_importe: 0,
      no_se_reparte: "",
      texto_entero: "663,00 €",
      texto_repartido: "463,00 €",
      texto_sin_asignar: "200,00 €",
      texto_falta: "0,00 €",
    },
    anulado: false,
    motivo_anulacion: null,
    notas: null,
    le_falta_el_importe: false,
    esta_sin_repartir: true,
    no_cuadra: false,
    ...cambios,
  };
}

function elGastoQueNoSeSabeLoQueCosto(cambios = {}) {
  return elGasto({
    id: 8,
    concepto: "Reparación del remolque",
    importe: null,
    texto_importe: null,
    base_imponible: null,
    cuota_iva: null,
    pagado: "0.00",
    texto_pagado: "0,00 €",
    pendiente: null,
    texto_pendiente: "",
    estado: "sin_importe",
    repartos: [],
    cuadre_del_reparto: {
      entero: null,
      repartido: "0.00",
      sin_asignar: "0.00",
      total_conocido: "0.00",
      falta: null,
      cuadra: false,
      trozos_sin_importe: 0,
      no_se_reparte: "no_se_el_importe",
      texto_entero: "",
      texto_repartido: "0,00 €",
      texto_sin_asignar: "0,00 €",
      texto_falta: "",
    },
    le_falta_el_importe: true,
    ...cambios,
  });
}

function lasCuentas(cambios = {}) {
  return {
    campana_id: 1,
    cuantos: 1,
    gastos: [elGasto()],
    inversiones: [
      {
        id: 2,
        campana_id: 1,
        concepto: "Tractor usado",
        categoria: "maquinaria",
        etiqueta_categoria: "Maquinaria",
        importe: "24000.00",
        texto_importe: "24.000,00 €",
        valor_residual: null,
        repartido_a_la_campana: "1200.00",
        texto_repartido: "1.200,00 €",
        sin_asignar: "22800.00",
        texto_sin_asignar: "22.800,00 €",
        es_un_gasto_completo_del_cultivo: false,
        anulada: false,
        motivo_anulacion: null,
        notas: null,
        le_falta_el_importe: false,
      },
    ],
    pagos: [
      {
        id: 5,
        fecha: "2026-03-20",
        importe: "200.00",
        texto_importe: "200,00 €",
        proveedor: "Cooperativa Agrícola de Peñaranda",
        forma: "transferencia",
        etiqueta_forma: "Transferencia",
        referencia: "TRANSF 2026/4471",
        anulado: false,
        texto_aplicado: "200,00 €",
        texto_sin_conciliar: "0,00 €",
        aplicaciones: [{ id: 31, gasto_id: 7, concepto: "Abono 15-15-15", importe: "200.00" }],
        estan_sin_conciliar: false,
      },
    ],
    subvenciones: [
      {
        id: 1,
        concepto: "Ayuda a la cosecha de cereal",
        organismo: "Junta de Castilla y León",
        importe_previsto: "3000.00",
        importe_concedido: "2500.00",
        importe_cobrado: null,
        texto_previsto: "3.000,00 €",
        texto_concedido: "2.500,00 €",
        texto_cobrado: "",
        estado: "concedida",
        etiqueta_estado: "Concedida, sin cobrar",
        cuenta_como_ingreso: false,
        anulada: false,
      },
    ],
    sin_conciliar: [],
    cuenta: {
      gastos: 1,
      gastos_sin_importe: 0,
      coste_conocido: "663.00",
      pagado: "200.00",
      pendiente: "463.00",
      sin_asignar: "200.00",
      margen: null,
      margen_completo: false,
    },
    caja: {
      entrado: "500.00",
      salido: "200.00",
      saldo: "300.00",
      texto_entrado: "500,00 €",
      texto_salido: "200,00 €",
      texto_saldo: "300,00 €",
      por_pagar: "463.00",
      texto_por_pagar: "463,00 €",
      ayudas_cobradas: "0.00",
      texto_ayudas_cobradas: "0,00 €",
      ayudas_previstas: "2500.00",
      texto_ayudas_previstas: "2.500,00 €",
      importes_que_no_se: 0,
    },
    margenes: {
      Trigo: {
        concepto: "Trigo",
        directos: "663.00",
        repartidos: "0.00",
        sin_asignar: "200.00",
        texto_coste_conocido: "663,00 €",
        ingresos: "2000.00",
        texto_ingresos: "2.000,00 €",
        cobrado: "500.00",
        texto_margen: "1.337,00 €",
        margen: "1337.00",
        completo: true,
        costes_que_no_se: 0,
        ingresos_que_no_se: 0,
      },
      Cebada: {
        concepto: "Cebada",
        directos: "400.00",
        repartidos: "0.00",
        sin_asignar: "0.00",
        texto_coste_conocido: "400,00 €",
        ingresos: null,
        texto_ingresos: null,
        cobrado: "0.00",
        texto_margen: null,
        margen: null,
        completo: false,
        costes_que_no_se: 1,
        ingresos_que_no_se: 0,
      },
    },
    coste_por_clase: {
      directos: "1063.00",
      repartidos: "463.00",
      sin_asignar: "200.00",
      texto_directos: "1.063,00 €",
      texto_repartidos: "463,00 €",
      texto_sin_asignar: "200,00 €",
      total_conocido: "1726.00",
      texto_total_conocido: "1.726,00 €",
      sin_asignar_cuantos: 1,
      sin_importe: 2,
      texto_sin_asignar_cuantos: FRASES_CONTADAS.texto_sin_asignar_cuantos,
      texto_sin_importe: FRASES_CONTADAS.texto_sin_importe,
    },
    por_pagar: { importe: "463.00", texto: "463,00 €", cuantos: 1, sin_importe: 0 },
    que_falta: [
      {
        que: "Los años de vida útil de un bien y su cuota de amortización.",
        para_que: "Poder llevar a cada campaña la parte del tractor que le toca sin preguntártelo.",
        de_quien_depende: "De que este programa tenga una tabla de amortización con su fuente.",
      },
    ],
    ...cambios,
  };
}

function laTabla() {
  return {
    clave: "gastos",
    etiqueta: "Mis cuentas",
    resumen: "1 gasto · 1.726,00 €",
    columnas: [
      { texto: "Concepto", campo: "concepto" },
      { texto: "Lo que costó" },
      { texto: "Va a" },
      { texto: "Falta por pagar" },
      { texto: "Cómo está" },
      { texto: "Acciones" },
    ],
    filas: [
      {
        celdas: [
          { texto: "Abono 15-15-15", accion: "gasto-abrir", datos: { id: 7 } },
          { texto: "663,00 €" },
          { texto: "El Prado" },
          { texto: "463,00 €" },
          { texto: "Pagado a medias" },
        ],
        acciones: [],
      },
    ],
    panel: null,
  };
}

// ---------------------------------------------------------------------------
// El arnés
// ---------------------------------------------------------------------------

async function cargarLaPantalla() {
  // El `?prueba=` con un número al azar es obligatorio: sin él, Node devuelve el módulo ya cargado por
  // otra prueba y la caché de módulos hace que las pruebas se pisen.
  return import(`../web/react/pantallas/gastos.js?prueba=${Math.random()}`);
}

async function htmlDeLasCuentas(cambios = {}) {
  const { PantallaDeLasCuentas } = await cargarLaPantalla();
  return globalThis.ReactDOMServer.renderToStaticMarkup(
    React.createElement(PantallaDeLasCuentas, {
      textos: structuredClone(TEXTOS),
      cuentas: lasCuentas(),
      tabla: laTabla(),
      resumen: GASTO.cuantas,
      filtro: "",
      formulario: null,
      anulando: null,
      guardando: false,
      error: "",
      aviso: "",
      ...cambios,
    }),
  );
}

async function htmlDeUnGasto(cambios = {}) {
  const { PantallaDeUnGasto } = await cargarLaPantalla();
  return globalThis.ReactDOMServer.renderToStaticMarkup(
    React.createElement(PantallaDeUnGasto, {
      textos: structuredClone(TEXTOS),
      gasto: elGasto(),
      pagos: [],
      formulario: null,
      repartiendo: null,
      anulando: null,
      guardando: false,
      error: "",
      aviso: "",
      ...cambios,
    }),
  );
}

/** Los botones del HTML: su acción y sus datos, en el orden en que salen. */
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

/** Los `id` de los campos de un formulario, en el orden en que salen. */
function idsDe(html) {
  return [...html.matchAll(/(?<![\w-])id="([^"]+)"/g)].map((encontrado) => encontrado[1]);
}

/** Todos los textos de una estructura anidada. */
function todosLosTextos(valor) {
  if (typeof valor === "string") return [valor];
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

// ---------------------------------------------------------------------------
// 1. Las tres columnas del coste, separadas y con su nombre
// ---------------------------------------------------------------------------

test("el coste enseña lo directo, lo repartido y lo sin asignar por separado", async () => {
  const html = await htmlDeLasCuentas();
  for (const rotulo of ["Directo", "Repartido", "Sin asignar", "Total conocido"]) {
    assert.match(html, new RegExp(rotulo), `no se enseña «${rotulo}»`);
  }
  assert.match(html, /1\.063,00 €/);
  assert.match(html, /463,00 €/);
  assert.match(html, /200,00 €/);
  assert.match(html, /1\.726,00 €/);
});

test("el coste dice cuántos importes no se saben, para que el total no parezca completo", async () => {
  const html = await htmlDeLasCuentas();
  assert.match(html, /Gastos de los que no sabes el importe/);
  assert.match(html, /Faltan 2 importes por saber/);
  assert.match(html, /De esos no se puede hacer la cuenta hasta que apuntes lo que costaron/);
  assert.match(html, /1 gasto sin saber a dónde va/);
});

// ---------------------------------------------------------------------------
// 2. Un importe que no consta no es cero
// ---------------------------------------------------------------------------

test("un gasto sin importe se enseña en blanco y con la palabra que lo dice, no como cero", async () => {
  // **La prueba que muerde.** Si alguien «arregla» la pantalla pintando `0,00 €` donde no se sabe el
  // importe, el agricultor lee que esa reparación salió gratis y el total deja de ser verdad.
  const html = await htmlDeLasCuentas({
    cuentas: lasCuentas({
      gastos: [elGastoQueNoSeSabeLoQueCosto()],
      coste_por_clase: {
        directos: "0.00",
        repartidos: "0.00",
        sin_asignar: "0.00",
        texto_directos: "0,00 €",
        texto_repartidos: "0,00 €",
        texto_sin_asignar: "0,00 €",
        total_conocido: "0.00",
        texto_total_conocido: "0,00 €",
        sin_asignar_cuantos: 1,
        sin_importe: 1,
      },
    }),
  });
  assert.match(html, /Reparación del remolque/);
  assert.match(html, /No lo sé/);
  assert.match(html, /Falta saber lo que costó/);
  // Y el hueco del importe **no** lleva un cero: se busca el renglón del importe y se mira qué pone.
  const renglon = html.split("Lo que costó")[1] || "";
  assert.doesNotMatch(renglon.slice(0, 200), /0,00 €\s*<\/dd>/, "el importe que no consta sale como 0,00 €");
});

test("las cuentas de un gasto sin importe dicen que no se pueden cerrar", async () => {
  const html = await htmlDeUnGasto({ gasto: elGastoQueNoSeSabeLoQueCosto() });
  assert.match(html, /Las cuentas de este gasto/);
  assert.match(html, /Estas cuentas no cierran/);
  assert.match(html, /Todavía no has dicho a qué tierra o cultivo va este gasto/);
});

// ---------------------------------------------------------------------------
// 3. El margen incompleto
// ---------------------------------------------------------------------------

test("un cultivo al que le falta un coste NO enseña un margen: enseña por qué no se puede", async () => {
  // **La prueba que muerde.** Un margen calculado con datos que faltan sale más alto que el
  // verdadero, y con él se decide qué sembrar el año que viene.
  const html = await htmlDeLasCuentas();
  assert.match(html, /Cebada/);
  assert.match(html, /De este cultivo no se puede calcular el margen/);
  const trozo = html.split("Cebada")[1].split("</li>")[0];
  assert.doesNotMatch(trozo, /Margen 0,00 €/, "el margen incompleto sale como un número");
});

test("un cultivo completo sí enseña su margen", async () => {
  const html = await htmlDeLasCuentas();
  assert.match(html, /Trigo/);
  assert.match(html, /1\.337,00 €/);
});

// ---------------------------------------------------------------------------
// 4. La caja y el margen: dos tarjetas distintas
// ---------------------------------------------------------------------------

test("la caja y el margen son dos tarjetas distintas y las dos se ven", async () => {
  const html = await htmlDeLasCuentas();
  assert.match(html, /La caja/);
  assert.match(html, /El margen de cada cultivo/);
  // La caja enseña el dinero de verdad: lo que entra, lo que sale y lo que queda.
  assert.match(html, /Ha entrado/);
  assert.match(html, /Ha salido/);
  assert.match(html, /Queda/);
  assert.match(html, /300,00 €/);
  // Y el margen va por cultivo, que es otra cosa.
  assert.match(html, /Has ingresado/);
  assert.match(html, /Te ha costado/);
});

// ---------------------------------------------------------------------------
// 5. Las ayudas: tres cifras y la previsión fuera del ingreso
// ---------------------------------------------------------------------------

test("las ayudas enseñan sus tres cifras separadas y la previsión con su aviso", async () => {
  const html = await htmlDeLasCuentas();
  assert.match(html, /Pedido/);
  assert.match(html, /Concedido/);
  assert.match(html, /Cobrado/);
  assert.match(html, /3\.000,00 €/);
  assert.match(html, /2\.500,00 €/);
  assert.match(html, /Concedida, sin cobrar/);
  // **Y la previsión no se suma a lo que ha entrado**: se dice con esa frase al lado.
  assert.match(html, /Esto no se suma a lo que ha entrado/);
  assert.match(html, /2\.500,00 €/);
});

// ---------------------------------------------------------------------------
// 6. La inversión: su tarjeta, y no es un gasto del año
// ---------------------------------------------------------------------------

test("la inversión va en su tarjeta, con lo que le toca a la campaña y lo que queda sin asignar", async () => {
  const html = await htmlDeLasCuentas();
  assert.match(html, /Las inversiones/);
  assert.match(html, /Tractor usado/);
  assert.match(html, /24\.000,00 €/);
  assert.match(html, /De esto le toca a esta campaña/);
  assert.match(html, /1\.200,00 €/);
  assert.match(html, /22\.800,00 €/);
  assert.match(html, /Un tractor o una nave no son un gasto del año/);
});

// ---------------------------------------------------------------------------
// 7. El reparto de un gasto, trozo a trozo, y su cuadre
// ---------------------------------------------------------------------------

test("la ficha del gasto enseña sus trozos, el método de cada uno y el botón de quitarlo", async () => {
  const html = await htmlDeUnGasto();
  assert.match(html, /El Prado/);
  assert.match(html, /463,00 €/);
  assert.match(html, /por hectáreas/);
  assert.match(html, /a mano/);
  const quitar = botonesDe(html).filter((boton) => boton.accion === "gasto-reparto-quitar");
  assert.deepEqual(
    quitar.map((boton) => [boton.id, boton.reparto]),
    [
      ["7", "11"],
      ["7", "12"],
    ],
  );
});

test("el cuadre del reparto enseña sus cuatro números y, si no cierra, la cifra que falta", async () => {
  const html = await htmlDeUnGasto();
  assert.match(html, /Las cuentas de este gasto/);
  assert.match(html, /En tierras, cultivos o máquinas/);
  assert.match(html, /Sin asignar/);
  // Y cuando no cierra, se dice con la cifra exacta que falta.
  const roto = await htmlDeUnGasto({
    gasto: elGasto({
      cuadre_del_reparto: {
        entero: "100.00",
        repartido: "60.00",
        sin_asignar: "0.00",
        total_conocido: "60.00",
        falta: "40.00",
        cuadra: false,
        trozos_sin_importe: 0,
        no_se_reparte: "",
        texto_entero: "100,00 €",
        texto_repartido: "60,00 €",
        texto_sin_asignar: "0,00 €",
        texto_falta: "40,00 €",
      },
    }),
  });
  assert.match(roto, /Estas cuentas no cierran/);
  assert.match(roto, /40,00 €/);
});

test("un gasto sin reparto lo dice, en vez de dejar el hueco en blanco", async () => {
  const html = await htmlDeUnGasto({ gasto: elGasto({ repartos: [] }) });
  assert.match(html, /Todavía no has dicho a qué tierra o cultivo va este gasto/);
  // Y ofrece las dos salidas: repartirlo o dejarlo sin asignar diciéndolo.
  const acciones = botonesDe(html).map((boton) => boton.accion);
  assert.ok(acciones.includes("gasto-repartir"));
  assert.ok(acciones.includes("gasto-sin-asignar"));
});

// ---------------------------------------------------------------------------
// 8. Los pagos y el dinero sin conciliar
// ---------------------------------------------------------------------------

test("los pagos enseñan lo aplicado y lo que no se sabe a qué va", async () => {
  const html = await htmlDeLasCuentas();
  assert.match(html, /Los pagos/);
  assert.match(html, /Va a gastos por/);
  assert.match(html, /Sin saber a qué va/);
  const acciones = botonesDe(html).map((boton) => boton.accion);
  assert.ok(acciones.includes("gasto-pago-conciliar"));
});

test("el dinero que salió y no se sabe a qué va tiene su lista aparte, con su explicación", async () => {
  const html = await htmlDeLasCuentas({
    cuentas: lasCuentas({ sin_conciliar: [{ id: 9, texto_importe: "379,00 €" }] }),
  });
  assert.match(html, /Dinero que salió y todavía no sabes a qué va/);
  assert.match(html, /Ese dinero está apuntado y no se ha perdido/);
});

// ---------------------------------------------------------------------------
// 9. Los botones llevan su acción y sus datos
// ---------------------------------------------------------------------------

test("cada botón de la lista lleva su acción y sus datos", async () => {
  const html = await htmlDeLasCuentas();
  const acciones = botonesDe(html).map((boton) => boton.accion);
  for (const esperada of [
    "gasto-nuevo",
    "gasto-pago-nuevo",
    "gasto-inversion-nueva",
    "gasto-ayuda-nueva",
    "gastos-ver-todas",
    "gasto-abrir",
  ]) {
    assert.ok(acciones.includes(esperada), `a la lista le falta el botón ${esperada}`);
  }
  const abrir = botonesDe(html).filter((boton) => boton.accion === "gasto-abrir");
  // El mismo gasto se puede abrir desde la lista del móvil y desde el botón de la tabla del
  // ordenador (`.solo-escritorio`), y las dos llevan el identificador del gasto.
  assert.ok(abrir.length >= 1, "no hay ningún botón para abrir el gasto");
  assert.deepEqual([...new Set(abrir.map((boton) => boton.id))], ["7"]);
});

test("el botón de anular dice **qué** se anula, y no solo que se anula", async () => {
  // En la lista, el botón de anular es el de un **pago** (un gasto se anula desde su ficha, que es
  // donde el agricultor lo está mirando). Y lleva su clase, para que `app.js` sepa qué anular.
  const html = await htmlDeLasCuentas();
  const anular = botonesDe(html).filter((boton) => boton.accion === "gasto-anular");
  assert.ok(anular.length >= 1, "no está el botón de anular un pago");
  assert.deepEqual([...new Set(anular.map((boton) => boton.clase))], ["pago"]);
  assert.deepEqual([...new Set(anular.map((boton) => boton.id))], ["5"]);

  // Y en la ficha de un gasto, el suyo dice que es un gasto.
  const ficha = await htmlDeUnGasto();
  const enLaFicha = botonesDe(ficha).filter((boton) => boton.accion === "gasto-anular");
  assert.deepEqual(enLaFicha.map((boton) => boton.clase), ["gasto"]);
});

// ---------------------------------------------------------------------------
// 10. Los formularios: sus campos con `id` y las preguntas sin contestar
// ---------------------------------------------------------------------------

test("el formulario de un gasto lleva los campos con su id y no contesta nada por su cuenta", async () => {
  const formulario = {
    titulo: GASTO.form_nuevo_titulo,
    pista: GASTO.form_nuevo_pista,
    guardar: GASTO.guardar,
    cancelar: GASTO.cancelar,
    guardando: GASTO.guardando,
    datos: { clase: "gasto" },
    bloques: [
      {
        tipo: "texto",
        id: "gasto-concepto",
        etiqueta: GASTO.campo_concepto,
        pista: GASTO.campo_concepto_pista,
        valor: "",
      },
      {
        tipo: "opciones",
        campo: "categoria",
        etiqueta: GASTO.campo_categoria,
        elegido: "",
        opciones: [
          { valor: "abono", texto: "Abono" },
          { valor: "gasoleo", texto: "Gasóleo" },
        ],
      },
      { tipo: "numero", id: "gasto-importe", etiqueta: GASTO.campo_importe, pista: GASTO.campo_importe_pista, valor: "" },
    ],
  };
  const html = await htmlDeLasCuentas({ formulario });
  assert.match(html, /Apuntar un gasto/);
  assert.deepEqual(
    idsDe(html).filter((id) => id.startsWith("gasto-")),
    ["gasto-concepto", "gasto-importe"],
  );
  // **Las preguntas que no nacen contestadas**: ninguna opción sale marcada como elegida.
  assert.doesNotMatch(html, /data-elegido="1"/);
  assert.match(html, /data-accion="gasto-elegir" data-campo="categoria" data-valor="abono"/);
  // Y el botón de guardar dice **qué se está guardando**.
  const guardar = botonesDe(html).filter((boton) => boton.accion === "gasto-guardar");
  assert.deepEqual(guardar.map((boton) => boton.clase), ["gasto"]);
});

test("el formulario de repartir pregunta el método y el destino, y se puede volver sin guardar", async () => {
  const repartiendo = {
    titulo: GASTO.form_repartir_titulo,
    pista: GASTO.form_repartir_pista,
    guardar: GASTO.guardar,
    cancelar: GASTO.cancelar,
    guardando: GASTO.guardando,
    datos: { id: 7 },
    bloques: [
      {
        tipo: "opciones",
        campo: "metodo",
        etiqueta: GASTO.campo_metodo,
        elegido: "",
        opciones: [
          { valor: "area", texto: "Por hectáreas" },
          { valor: "horas", texto: "Por horas" },
          { valor: "consumo", texto: "Por lo que se gastó en cada sitio" },
          { valor: "manual", texto: "A mano" },
        ],
      },
    ],
  };
  const html = await htmlDeUnGasto({ repartiendo });
  assert.match(html, /Repartir este gasto/);
  assert.match(html, /Por hectáreas/);
  assert.match(html, /A mano/);
  assert.match(html, /data-accion="gasto-elegir" data-campo="metodo" data-valor="manual"/);
  const acciones = botonesDe(html).map((boton) => boton.accion);
  assert.ok(acciones.includes("gasto-cancelar"));
});

test("la pantalla de anular pide el motivo, porque sin motivo el rastro no sirve", async () => {
  const html = await htmlDeLasCuentas({
    anulando: {
      titulo: GASTO.anular,
      pista: GASTO.explica,
      id: "gasto-motivo-anulacion",
      confirmar: GASTO.anular,
      cancelar: GASTO.cancelar,
      datos: { id: 7, clase: "gasto" },
      error: "",
    },
  });
  assert.match(html, /¿Por qué lo anulas\?/);
  assert.match(html, /id="gasto-motivo-anulacion"/);
  const confirmar = botonesDe(html).filter((boton) => boton.accion === "gasto-anular-confirmar");
  assert.deepEqual(confirmar.map((boton) => boton.id), ["7"]);
});

// ---------------------------------------------------------------------------
// 11. Lo que el programa todavía no calcula, y las dos vistas de la lista
// ---------------------------------------------------------------------------

test("la lista dice lo que el programa no calcula, para que no parezca un olvido", async () => {
  const html = await htmlDeLasCuentas();
  assert.match(html, /Lo que este programa todavía no calcula/);
  assert.match(html, /Los años de vida útil de un bien/);
  assert.match(html, /De quién depende/);
});

test("la misma lista se pinta para el móvil y para la tabla del ordenador", async () => {
  const html = await htmlDeLasCuentas();
  assert.match(html, /solo-escritorio tabla-scroll/);
  assert.match(html, /class="lista solo-movil"/);
  assert.match(html, /Abono 15-15-15/);
});

test("sin gastos se dice qué hacer, y el botón de apuntar uno está siempre", async () => {
  const html = await htmlDeLasCuentas({
    cuentas: lasCuentas({ gastos: [] }),
    tabla: null,
    resumen: "",
  });
  assert.match(html, /Todavía no has apuntado ningún gasto/);
  assert.match(html, /data-accion="gasto-nuevo"/);
});

test("si el buscador no encuentra nada se dice, y se pueden volver a ver todos", async () => {
  const html = await htmlDeLasCuentas({
    cuentas: lasCuentas({ gastos: [] }),
    tabla: null,
    filtro: "pepito",
  });
  assert.match(html, /Ningún gasto coincide con lo que buscas/);
  assert.match(html, /data-accion="gastos-ver-todas"/);
});

// ---------------------------------------------------------------------------
// 12. Ni una frase escrita a mano
// ---------------------------------------------------------------------------

test("la lista no lleva ni una frase escrita a mano", async () => {
  const html = await htmlDeLasCuentas();
  const delServidor = new Set([
    ...todosLosTextos(TEXTOS),
    ...todosLosTextos(lasCuentas()),
    ...todosLosTextos(laTabla()),
    ...todosLosTextos(FRASES_CONTADAS),
    GASTO.cuantas,
  ]);
  for (const frase of frasesVisibles(html)) {
    assert.ok(delServidor.has(frase), `frase escrita a mano: «${frase}»`);
  }
});

test("la ficha del gasto no lleva ni una frase escrita a mano", async () => {
  const html = await htmlDeUnGasto();
  const delServidor = new Set([...todosLosTextos(TEXTOS), ...todosLosTextos(elGasto())]);
  for (const frase of frasesVisibles(html)) {
    assert.ok(delServidor.has(frase), `frase escrita a mano: «${frase}»`);
  }
});

// ---------------------------------------------------------------------------
// 13. La pantalla no hace cuentas de dinero
// ---------------------------------------------------------------------------

test("la pantalla no hace cuentas de dinero: los números llegan hechos del servidor", async () => {
  // **Esta prueba mide una decisión, no un descuido.** En el navegador todo número es de coma
  // flotante: si la pantalla sumara importes, el total de la pantalla y el de la base dejarían de
  // coincidir por céntimos y el agricultor dejaría de fiarse de los dos. Por eso el componente no
  // tiene ni una suma, ni una resta, ni un `parseFloat`.
  const fuente = readFileSync(new URL("../web/react/pantallas/gastos.js", import.meta.url), "utf8");
  for (const prohibido of ["parseFloat", "parseInt", "toFixed", "Number("]) {
    assert.ok(!fuente.includes(prohibido), `la pantalla usa «${prohibido}» para hacer cuentas`);
  }
  assert.ok(!/\+\s*[a-zA-Z_$][\w.$]*\.importe/.test(fuente), "la pantalla suma importes");
});
