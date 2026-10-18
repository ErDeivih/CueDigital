/*
 * maquinaria.test.js — las pruebas de la pantalla de la maquinaria (T14, E8, 03/10/2026).
 *
 * QUÉ SE COMPRUEBA AQUÍ, Y POR QUÉ ESTAS COSAS
 *
 * El componente es puro: recibe todo por propiedades, así que se puede montar sin navegador y sin
 * servidor (el arnés es el mismo que el de las demás pantallas: React y htm de `vendor/`, y
 * `renderToStaticMarkup`). Lo que se comprueba aquí es **lo que se ve y lo que se pulsa**:
 *
 *  1. **La ficha separa las cinco obligaciones** y las enseña en su orden, cada una con lo suyo. Es lo
 *     primero que pide el contrato, y es lo que impide que la ITV y la ITEAF se confundan (el documento de
 *     la casa lo avisa por su nombre).
 *  2. **No se enseña ninguna fecha inventada.** Con una obligación que aplica y sin inspección apuntada, la
 *     ficha dice «No hay ninguna apuntada» y pide la clasificación técnica: es la trampa del ticket
 *     —«No calcular plazo solo por "tractor" o "sulfatadora"»—, y aquí se ve en pantalla.
 *  3. **Una inspección sin papel se apunta y se dice que no lo trae.**
 *  4. **Los botones llevan su acción y sus datos**: `app.js` los atiende en el manejador de clics, y un
 *     botón sin `data-accion` es un botón que no hace nada.
 *  5. **Los campos del formulario llevan su `id`**: es lo único que `app.js` tiene para leer lo que el
 *     agricultor ha escrito. Si se renombra uno, el formulario se rellena y se guarda vacío sin decir nada.
 *
 * Y la de siempre: **ni una frase escrita a mano**. Todo lo que se lee sale de las propiedades, que es lo
 * que garantiza que el vocabulario siga viviendo en `textos.py` (donde el test de jerga lo revisa).
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
// Los textos: los mismos que sirve `/api/interfaz` (los de `textos.MAQUINARIA_DE_LA_FINCA`)
// ---------------------------------------------------------------------------

const MAQUINARIA = {
  // **Copia literal de `textos.MAQUINARIA_DE_LA_FINCA`.** Se rehace con
  // `backend/scripts/copiar_textos_t14.py`, y la prueba de la revisión
  // (`tests/test_revision_t14.py`) exige que diga lo mismo que el servidor.
  titulo: "Mi maquinaria",
  explica: "Aquí están tus máquinas: el tractor, el remolque, los aperos y los equipos con los que echas el producto. De cada una se apunta qué le toca pasar y cuándo, con el papel que lo demuestra.",
  cuantas: "Tienes {cuantos} máquinas apuntadas.",
  cuantas_uno: "Tienes 1 máquina apuntada.",
  sin_maquinas: "Todavía no has apuntado ninguna máquina. Empieza por la que más uses: el tractor. Apúntala y después le dices qué le toca pasar.",
  nueva: "APUNTAR UNA MÁQUINA",
  equipo_traido: "Ya está en la lista, con lo que ya tenías apuntado del cuaderno. Mírale la clasificación técnica y contesta lo que le toca.",
  buscar: "BUSCAR",
  buscar_pista: "Escribe las primeras letras de su nombre",
  ver_todas: "VER TODAS",
  sin_decir: "Falta decirlo",
  // *** Si anades una palabra al servidor, ANADELA AQUI ***: este objeto es lo que el guardian
  // («ni una frase escrita a mano») usa para saber que un texto viene del servidor. Si falta, el
  // guardian **no puede** distinguir una palabra de verdad de una inventada, y deja pasar las dos.
  taller_de_la_averia: "Taller",
  campo_papel: "¿Con qué papel lo apuntas?",
  // ***LAS FRASES DEL SERVIDOR, LITERALES***: `tests/test_revision_t14.py` compara esta copia con lo
  // que sirve `/api/interfaz`, palabra por palabra. Acortarlas aqui deja al guardian de «ni una frase
  // escrita a mano» sin poder distinguir una palabra de verdad de una inventada.
  campo_papel_pista: "El parte del taller, la factura de la reparación o el presupuesto. Si no hay papel, déjalo como está.",
  sin_papel: "Sin papel apuntado",
  papel_de_la_averia: "Papel",
  seccion_contador: "El cuenta-horas",
  apuntar_lectura: "Apunta lo que marca",
  corregir_lectura: "Corregir",
  anular_lectura_boton: "Anular",
  contador_sin_lecturas: "De este cuenta-horas no hay ninguna lectura apuntada, así que no se sabe lo que ha trabajado. Apunta lo que marca hoy y, cuando tengas otra, el programa dirá lo que ha subido.",
  contador_marca: "Marca ahora",
  contador_ha_subido: "Ha subido desde la primera lectura",
  contador_ha_subido_parcial: "Ha subido, de lo que se puede afirmar",
  contador_no_se_sabe_cuanto: "Todavía no se sabe cuánto ha subido: hace falta otra lectura para poder comparar.",
  contador_tramos_sin_decir_uno: "y hay 1 tramo que no se puede medir, porque falta alguna lectura",
  contador_tramos_sin_decir_varios: "y hay {cuantos} tramos que no se pueden medir, porque faltan lecturas",
  contador_sustitucion: "contador nuevo",
  contador_anulada: "anulada",
  coste_de_la_maquina: "Lo que ha costado tenerla parada",
  coste_no_se_pudo: "No se ha podido traer lo que ha costado. Vuelve a abrir la ficha y, si sigue, avisa.",
  // ***LAS FRASES DEL SERVIDOR, LITERALES***: este objeto es una COPIA de lo que sirve `/api/interfaz`,
  // y `tests/test_revision_t14.py` compara las dos cosas palabra por palabra. Acortarlas aqui hace que
  // el guardian de «ni una frase escrita a mano» deje de valer: el compara contra ESTA copia.
  coste_de_la_maquina_sin_gastos: "De sus averías no hay ningún gasto apuntado, así que no se sabe lo que ha costado.",
  coste_de_una_averia: "Costó",
  coste_de_una_averia_sin_constar: "No consta lo que costó",
  coste_sin_importe_uno: "y 1 de esos gastos no tiene importe",
  coste_sin_importe_varios: "y {cuantos} de esos gastos no tienen importe",
  sin_resultados: "Ninguna de tus máquinas se llama así. Prueba con otras letras o pulsa VER TODAS para verlas todas otra vez.",
  abrir: "VER ESTA MÁQUINA",
  situacion: "Cómo está:",
  anular: "ANULAR",
  motivo_anulacion: "¿Por qué lo anulas?",
  anular_confirmar: "ANULARLO CON ESTE MOTIVO",
  anular_inspeccion: "Anular esta inspección",
  anular_averia: "Anular esta avería",
  anular_pista: "Lo que anulas se queda en tu cuaderno, tachado y con el motivo escrito, pero deja de contar: no se mira para saber cuándo le toca la próxima. Si lo que quieres es quitarlo del todo, se borra.",
  anular_necesita_motivo: "Para anularlo hace falta el motivo: dentro de un año, ese motivo es lo único que explicará por qué está tachado. Escríbelo y vuelve a pulsar el botón.",
  anulada: "Ya está anulado, con su motivo.",
  equipos_sin_ficha: "Equipos de echar producto que todavía no están en esta lista",
  equipos_explica: "Estos equipos los apuntaste para el cuaderno de la Junta. Aquí no están todavía porque esta lista es más nueva y sirve para todo, no solo para los equipos de echar producto. Si son los mismos, tráelos: no se pierde nada de lo que ya estaba escrito.",
  traer_equipo: "TRAERLO A LA LISTA",
  que_falta_titulo: "Lo que este programa todavía no calcula",
  que_falta_explica: "Se dice para que no te fíes de una fecha que no está: cuando el programa no tiene la fuente de un plazo, no se la inventa. Las fechas que ves son las que traen tus papeles.",
  que_falta_para_que: "Para qué haría falta",
  que_falta_depende: "De quién depende",
  horas_corto: "h",
  proxima_revision_texto: "{obligacion} el {fecha}",
  sin_fecha_corto: "Falta el dato",
  faltan_por_saber_uno: "1 más sin fecha",
  faltan_por_saber_varios: "{cuantas} más sin fecha",
  papeles_uno: "1 papel",
  papeles_varios: "{cuantas} papeles",
  sin_papel_apuntado_uno: "1 sin papel",
  sin_papel_apuntado_varios: "{cuantas} sin papel",
  sin_inspecciones_corto: "Sin inspecciones",
  avisos_uno: "1 cosa que mirar",
  avisos_varios: "{cuantas} cosas que mirar",
  avisos_corto_uno: "1 aviso",
  avisos_corto_varios: "{cuantas} avisos",
  ver_corto: "VER",
  vencida_corto: "Vencida",
  al_caer_corto: "Caduca pronto",
  no_favorable_corto: "Desfavorable",
  ultima_inspeccion_texto: "La última: {fecha}",
  averia_de_texto: "Avería del {fecha}",
  arreglada_texto: "Arreglada el {fecha}",
  sigue_sin_arreglar: "Sigue sin arreglar",
  no_se_si_arreglada: "No sé si está arreglada",
  form_nueva_titulo: "Apuntar una máquina",
  form_nueva_pista: "Con el nombre y las tres preguntas de abajo ya queda apuntada. Lo demás se puede dejar en blanco y ponerse otro día: en un hueco no se escribe nada.",
  form_corregir_titulo: "Corregir esta máquina",
  form_corregir_pista: "Está puesto lo que apuntaste. Cambia lo que esté mal: lo que había antes queda guardado en el historial del cuaderno.",
  form_inspeccion_titulo: "Apuntar una inspección",
  form_inspeccion_pista: "Copia las fechas del papel. El programa no las calcula: si el papel no trae la de la próxima, se deja en blanco y la ficha dirá que no se sabe cuándo toca.",
  form_averia_titulo: "Apuntar una avería",
  form_averia_pista: "Qué pasó, cuándo y si ya está arreglada. Si la máquina no está para trabajar, se cambia aparte, en sus datos: son dos cosas distintas.",
  form_guardando: "Guardando…",
  campo_tipo_inspeccion: "¿Qué le han pasado?",
  campo_fecha: "¿Cuándo fue?",
  campo_fecha_pista: "La fecha que trae el papel",
  campo_proxima_fecha: "¿Cuándo toca la próxima?",
  campo_proxima_fecha_pista: "Si el papel la trae, cópiala. Si no, déjala en blanco: el programa no la calcula.",
  campo_documento: "¿Con qué papel?",
  campo_documento_pista: "Si lo tienes guardado en «los papeles», elígelo. Sin papel también se puede apuntar, y la ficha dirá que no lo trae.",
  sin_papeles_guardados: "No tienes ningún papel guardado. Puedes apuntar la inspección igual y guardar el papel después en «los papeles».",
  campo_notas: "Notas",
  campo_fecha_averia: "¿Cuándo pasó?",
  campo_que_paso: "¿Qué pasó?",
  seccion_datos: "Los datos de la máquina",
  clase_tractor: "Tractor",
  clase_remolque: "Remolque",
  clase_apero: "Apero",
  clase_cosechadora: "Cosechadora",
  clase_equipo_de_aplicacion: "Equipo de echar producto",
  clase_otro: "Otra cosa",
  clase: "¿Qué es?",
  clase_pista: "Para leer tu lista de un vistazo. No decide qué inspecciones le tocan: eso depende de la clasificación técnica, que se pregunta más abajo.",
  nombre: "¿Cómo la llamas?",
  nombre_pista: "Como la llamas tú: «el Landini», «el remolque grande»",
  marca: "Marca",
  modelo: "Modelo",
  anio: "Año",
  matricula: "Matrícula",
  matricula_pista: "Si la tiene: los tractores, los remolques y las cosechadoras",
  numero_serie: "Número de serie",
  numero_serie_pista: "Lo traen los aperos que no llevan matrícula",
  numero_roma: "Número del ROMA",
  numero_roma_pista: "El número de inscripción en el registro de maquinaria, si lo tiene. No lo pongas si no lo sabes: un número inventado es peor que un hueco.",
  clasificacion: "¿Cómo clasifica el papel a esta máquina?",
  clasificacion_pista: "Lo pone en la ficha del ROMA o en el papel de la última inspección, con sus palabras: por ejemplo, «pulverizador arrastrado». No lo deduzcas por el nombre: de esto depende qué inspecciones le tocan. Si no lo sabes, déjalo en blanco.",
  sin_clasificacion: "Sin decir la clasificación",
  clasificacion_falta: "Falta la clasificación técnica de esta máquina, que es lo que dice qué inspecciones le tocan. Mírala en la ficha del ROMA o en el papel de la última inspección y escríbela aquí.",
  horas: "Horas del cuenta-horas",
  horas_pista: "Si la máquina lo tiene y lo has mirado. Déjalo en blanco si no lo sabes",
  notas: "Notas",
  notas_pista: "Lo que quieras apuntar: dónde duerme, quién la lleva…",
  propiedad: "¿Es tuya o alquilada?",
  propiedad_propia: "Es mía",
  propiedad_alquilada: "Es alquilada",
  propiedad_no_se: "No lo sé",
  disponibilidad: "¿Puedes contar con ella para trabajar?",
  disponibilidad_disponible: "Sí puedo",
  disponibilidad_no_disponible: "No puedo",
  disponibilidad_no_se: "No lo he mirado",
  disponibilidad_pista: "No se adivina por las averías ni por las fechas: una máquina con una avería apuntada puede estar trabajando igual, y quien lo sabe eres tú.",
  seccion_obligaciones: "Lo que tiene que pasar esta máquina",
  seccion_obligaciones_explica: "Se pregunta una por una porque no son lo mismo. Y de algunas no se puede saber por el nombre de la máquina: depende de su clasificación técnica, que es la que está en el papel.",
  obligacion_itv: "ITV",
  obligacion_iteaf: "ITEAF",
  obligacion_mantenimiento: "Mantenimiento",
  obligacion_seguro: "Seguro",
  obligacion_roma: "ROMA",
  que_es_itv: "La inspección técnica del vehículo, como la del coche.",
  que_es_iteaf: "La inspección de las máquinas con las que se echa el producto. No es la ITV.",
  que_es_mantenimiento: "El repaso que le das tú: el aceite, los filtros, las cuchillas.",
  que_es_seguro: "La póliza de la máquina. La del coche y la de la cosecha no son la misma.",
  que_es_roma: "Su número en el registro de maquinaria, que es lo que pide el cuaderno.",
  aplicabilidad: "¿Le toca?",
  aplicabilidad_si: "Sí le toca",
  aplicabilidad_no: "No le toca",
  aplicabilidad_no_se: "No lo sé",
  de_donde_sale: "¿De dónde sale eso?",
  de_donde_sale_pista: "Es lo que te van a preguntar: no es lo mismo que lo diga un papel que que lo digas tú.",
  origen_documento: "Lo dice el papel",
  origen_el_agricultor: "Lo digo yo",
  origen_no_se: "No lo sé",
  lo_que_dice_la_norma: "De dónde sale esta obligación",
  guarda_el_papel: "Los papeles de las inspecciones hay que poder enseñarlos tres años. Si los guardas en «los papeles», deja aquí apuntado cuál es.",
  situacion_no_se_si_toca: "No se sabe si le toca",
  situacion_no_aplica: "No le toca",
  situacion_sin_inspeccion: "No hay ninguna apuntada",
  situacion_sin_la_ultima: "Toca el {fecha}, pero no se sabe cuándo fue la última",
  situacion_no_favorable: "La última salió desfavorable",
  situacion_sin_fecha: "No se sabe cuándo toca la próxima",
  situacion_vencida: "Vencida el {fecha}",
  situacion_proxima: "Caduca el {fecha}",
  situacion_vigente: "Hasta el {fecha}",
  sin_fecha_apuntada: "Falta la fecha",
  resultado: "¿Cómo salió?",
  resultado_favorable: "Favorable",
  resultado_desfavorable: "Desfavorable",
  resultado_no_consta: "No lo pone el papel",
  proxima_fecha: "¿Cuándo toca la próxima?",
  ultima_inspeccion: "La última fue el {fecha}",
  documento: "¿Con qué papel lo apuntas?",
  con_papel: "Con su papel",
  sin_papel: "Sin papel apuntado",
  ver_papel: "VER EL PAPEL",
  papel_sin_nombre: "El papel que tienes guardado",
  sin_papel_pista: "De esta inspección no has apuntado ningún papel. Cuando lo tengas, guárdalo en «los papeles» y dilo aquí: en una inspección es lo que te van a pedir.",
  seccion_inspecciones: "Lo que le han pasado, con su fecha",
  sin_inspecciones: "De esta máquina no hay ninguna inspección apuntada. Lo que le toque lo dice su clasificación técnica: mírala en el papel y apunta la última que le hayan pasado.",
  apuntar_inspeccion: "APUNTAR UNA INSPECCIÓN",
  inspeccion_de: "Inspección de {obligacion}",
  seccion_averias: "Averías",
  sin_averias: "No has apuntado ninguna avería.",
  apuntar_averia: "APUNTAR UNA AVERÍA",
  que_paso: "¿Qué pasó?",
  que_paso_pista: "En dos palabras: «se rompió el eje del ventilador»",
  resuelta: "¿Ya está arreglada?",
  resuelta_si: "Ya está arreglada",
  resuelta_no: "Sigue sin arreglar",
  resuelta_no_se: "No lo sé",
  papeles_titulo: "Los papeles de las inspecciones",
  fecha_resuelta: "¿Cuándo se arregló?",
  horas_de_la_averia: "Horas del cuenta-horas cuando pasó",
  avisos_titulo: "Antes de contar con ella",
  sin_avisos: "De esta máquina no hay nada que mirar ahora mismo.",
  urgente: "Míralo antes de usarla",
  mirar_cuando_puedas: "Míralo cuando puedas",
  guardar: "GUARDAR LA MÁQUINA",
  guardado: "Ya está guardada.",
  corregida: "Ya está corregido. Lo que había antes queda guardado en el historial.",
  que_es_equipo: "Una máquina",
  es_el_equipo_del_cuaderno: "¿Es uno de los equipos que apuntaste para el cuaderno?",
  es_el_equipo_del_cuaderno_pista: "Si esta máquina es la misma que ya tenías apuntada como equipo para echar producto, elígela aquí: así no se escribe dos veces.",
  ningun_equipo: "No es ninguno de esos",
  el_equipo_que_ya_estaba: "El equipo que ya estaba enlazado",

  // ── Las reservas (CRM-07 #9, 17/10/2026) ──
  // ***La copia dice LO MISMO que el servidor***: hay una prueba que lo comprueba
  // (`test_la_copia_de_los_textos_del_test_del_movil_dice_lo_que_sirve_el_servidor`).
  seccion_reservas: "Reservas",
  sin_reservas: "No has reservado esta máquina para nada.",
  apuntar_reserva: "RESERVAR ESTA MÁQUINA",
  corregir_reserva: "Corregir",
  anular_reserva: "Anular",
  reserva_no_gasta: "Reservar no gasta nada: solo dice que la vas a coger.",
  reserva_anulada: "anulada",
  // ***Los tres estados viven en el bloque de la PANTALLA***, no en `MENSAJES`: los usan **el servidor**
  // -para escribir `estado_texto`- y **el formulario** -para sus tres opciones-. *Con dos copias, un dia
  // dirian cosas distintas.*
  reserva_estado_pedida: "Pedida",
  reserva_estado_en_curso: "En curso",
  reserva_estado_hecha: "Hecha",
  anular_reserva: "Anular la reserva",
};

const ACCIONES = { volver: "VOLVER", guardar: "GUARDAR" };
const CORREGIR = { boton: "CORREGIR", borrar: "BORRAR" };

const TEXTOS = { maquinaria: MAQUINARIA, acciones: ACCIONES, corregir: CORREGIR.boton, borrar: CORREGIR.borrar };

// ---------------------------------------------------------------------------
// Los datos, tal y como los prepara `app.js`
// ---------------------------------------------------------------------------

/** La ficha de un tractor **sin clasificación técnica y sin ninguna inspección apuntada**: el caso duro. */
function fichaSinNada() {
  return {
    maquina: {
      id: 1,
      nombre: "El Landini",
      clase_texto: "Tractor",
      clasificacion: "",
      clasificacion_falta: true,
      matricula: "1234 ABC",
      numero_serie: "",
      numero_roma: "",
      marca: "Landini",
      modelo: "",
      anio_texto: "1998",
      horas_texto: "2.400 h",
      propiedad_texto: "Es mía",
      disponibilidad_texto: "Sí puedo",
      es_el_equipo_del_cuaderno: false,
      notas: "",
      que_falta: [
        {
          que: "Cada cuánto toca pasar la ITV y la ITEAF, por clasificación técnica.",
          para_que: "Poder calcular la próxima fecha en vez de copiarla del papel.",
          de_quien_depende: "Es el trabajo legal L07 de la matriz normativa.",
        },
      ],
    },
    avisos: [],
    obligaciones: [
      {
        tipo: "itv",
        nombre: "ITV",
        que_es: "La inspección técnica del vehículo, como la del coche.",
        situacion_texto: "No se sabe si le toca",
        opciones_aplicabilidad: {
          etiqueta: "¿Le toca?",
          campo: "aplicabilidad",
          datos: { tipo: "itv" },
          opciones: [
            { valor: "si", texto: "Sí le toca", elegido: false },
            { valor: "no", texto: "No le toca", elegido: false },
            { valor: "no_se", texto: "No lo sé", elegido: true },
          ],
        },
        opciones_origen: {
          etiqueta: "¿De dónde sale eso?",
          pista: "Es lo que te van a preguntar.",
          campo: "origen",
          datos: { tipo: "itv" },
          opciones: [{ valor: "no_se", texto: "No lo sé", elegido: true }],
        },
        ultima_texto: "",
        resultado_texto: "No lo pone el papel",
        proxima_texto: "",
        papel: "",
        fuente: {
          norma: "Real Decreto 920/2017, la inspección técnica de los vehículos agrícolas",
          url: "https://www.boe.es/buscar/act.php?id=BOE-A-2017-12841",
          que_falta: "Cada cuánto toca la ITV depende de la clasificación técnica de la máquina.",
        },
        clasificacion_falta: true,
      },
      ...["iteaf", "mantenimiento", "seguro", "roma"].map((tipo) => ({
        tipo,
        nombre: { iteaf: "ITEAF", mantenimiento: "Mantenimiento", seguro: "Seguro", roma: "ROMA" }[tipo],
        que_es: { iteaf: "La inspección de las máquinas con las que se echa el producto. No es la ITV." }[tipo] || "Lo que sea.",
        situacion_texto: "No se sabe si le toca",
        opciones_aplicabilidad: {
          etiqueta: "¿Le toca?",
          campo: "aplicabilidad",
          datos: { tipo },
          opciones: [{ valor: "no_se", texto: "No lo sé", elegido: true }],
        },
        opciones_origen: {
          etiqueta: "¿De dónde sale eso?",
          pista: "Es lo que te van a preguntar.",
          campo: "origen",
          datos: { tipo },
          opciones: [{ valor: "no_se", texto: "No lo sé", elegido: true }],
        },
        ultima_texto: "",
        resultado_texto: "No lo pone el papel",
        proxima_texto: "",
        papel: "",
        fuente: { norma: null, url: null, que_falta: "No tenemos ninguna norma transcrita." },
        clasificacion_falta: true,
      })),
    ],
    inspecciones: [],
    averias: [],
  };
}

/** La misma máquina, con la ITEAF declarada, dos inspecciones (una sin papel) y una avería. */
function fichaConCosas() {
  const ficha = fichaSinNada();
  ficha.obligaciones = ficha.obligaciones.map((obligacion) => {
    if (obligacion.tipo !== "iteaf") return obligacion;
    return {
      ...obligacion,
      situacion_texto: "Vencida el 12/05/2026",
      ultima_texto: "La última: 10/05/2021",
      resultado_texto: "Favorable",
      proxima_texto: "12/05/2026",
      // El papel, **con su nombre y con su identificador**: así la ficha dice cuál es y se puede abrir
      // (antes decía solo «Con su papel», y la revisión del ticket lo cazó).
      papel: "Certificado de la ITEAF",
      papel_id: 4,
      clasificacion_falta: false,
      opciones_aplicabilidad: {
        ...obligacion.opciones_aplicabilidad,
        opciones: [
          { valor: "si", texto: "Sí le toca", elegido: true },
          { valor: "no", texto: "No le toca", elegido: false },
          { valor: "no_se", texto: "No lo sé", elegido: false },
        ],
      },
      opciones_origen: {
        ...obligacion.opciones_origen,
        opciones: [{ valor: "documento", texto: "Lo dice el papel", elegido: true }],
      },
    };
  });
  // **Lo que ha costado tenerla parada** (CRM-07 #7). Con **un gasto sin importe**, que es el caso que
  // importa: el total tiene que salir y el aviso tambien, porque un total que solo suma la mitad y no lo
  // dice parece el total entero.
  // **El cuenta-horas** (CRM-07 #8): dos lecturas -una de ellas con el contador cambiado- y la cuenta ya
  // hecha, con un tramo sin poder medir. Es el caso que la pantalla tiene que saber decir.
  ficha.contador = {
    subido: 250,
    cuantas: 2,
    sin_decir: 1,
    unidad: "horas",
    marca: 1250,
    tramos: [],
    lo_que_falta: ["hay_tramos_sin_lectura_al_final"],
    sinLecturas: false,
    marca_texto: "Marca ahora: 1.250 h",
    subido_texto: "Ha subido desde la primera lectura: 250 h",
    noSeSabeTexto: "",
    aviso: "y hay 1 tramo que no se puede medir.",
  };
  ficha.lecturas = [
    { id: 1, fecha_texto: "01/03/2026", valor: 1000, unidad: "horas", anulado: false,
      es_sustitucion: false, texto: "01/03/2026 · 1.000 h" },
    { id: 2, fecha_texto: "01/06/2026", valor: 1250, unidad: "horas", anulado: false,
      es_sustitucion: false, texto: "01/06/2026 · 1.250 h" },
  ];
  ficha.coste = {
    texto: "1.100,00 €",
    gastos: 2,
    sin_importe: 1,
    completo: false,
    frase: "Lo que ha costado tenerla parada: 1.100,00 € y 1 de esos gastos no tiene importe",
  };
  ficha.avisos = [
    { texto: "La ITEAF de «El Landini» venció el 12/05/2026. Pide cita antes de usarla.", urgente: true, tipo: "iteaf" },
    { texto: "De «El Landini» no has dicho si puedes contar con ella.", urgente: false, tipo: "disponibilidad" },
  ];
  ficha.inspecciones = [
    {
      id: 7,
      titulo: "Inspección de ITEAF",
      fecha_texto: "La última: 10/05/2021",
      resultado_texto: "Favorable",
      proxima_texto: "¿Cuándo toca la próxima?: 12/05/2026",
      papel_texto: "Con su papel: Certificado de la ITEAF",
      papel_id: 4,
      anulado: false,
      motivo_anulacion: "",
    },
    {
      id: 8,
      titulo: "Inspección de ITV",
      fecha_texto: "La última: 01/03/2024",
      resultado_texto: "No lo pone el papel",
      proxima_texto: "¿Cuándo toca la próxima?: Falta la fecha",
      // **El caso del contrato**: sin papel se apunta igual, y aquí se dice que no lo trae.
      papel_texto: "De esta inspección no has apuntado ningún papel.",
      anulado: false,
      motivo_anulacion: "",
    },
  ];
  ficha.averias = [
    {
      id: 3,
      titulo: "Avería del 04/01/2026",
      fecha_texto: "Se rompió el eje del ventilador",
      resuelta_texto: "Sigue sin arreglar",
      notas: "",
      // **El taller y el coste** (CRM-07 #7): los dos campos que la ficha ya sabe ensenar. Faltaban en el
      // fixture porque es **anterior** a las dos entregas, y sin ellos el guardian no puede distinguir
      // sus frases compuestas («Taller: …», «Costo: …») de una escrita a mano: se queda ciego.
      taller: "Talleres El Camino",
      taller_texto: "Taller: Talleres El Camino",
      papel_texto: "Papel: Factura del taller",
      coste_texto: "900,00 €",
      coste_frase: "Costó: 900,00 €",
      anulado: false,
    },
  ];
  return ficha;
}

/** La lista, tal y como la prepara `app.js` (la tabla y las tarjetas del móvil). */
function tablaDeEjemplo() {
  return {
    clave: "maquinaria",
    etiqueta: "Tu maquinaria, en una tabla",
    columnas: [
      { texto: "Máquina", campo: "nombre", ordenada: true, descendente: false, orden: "Ordenar por: Máquina" },
      { texto: "Tipo", campo: "clase_texto" },
      { texto: "Matrícula o serie", campo: "matricula_o_serie" },
      { texto: "Tuya o alquilada", campo: "propiedad_texto" },
      { texto: "Horas", campo: "horas_numero", clase: "tabla-numero" },
      { texto: "Próxima revisión", campo: "proxima_orden", clase: "tabla-numero" },
      { texto: "Papeles" },
      { texto: "Disponibilidad", campo: "disponibilidad_texto" },
      { texto: "Acciones" },
    ],
    filas: [
      {
        celdas: [
          { texto: "El Landini" },
          { texto: "Tractor" },
          { texto: "1234 ABC" },
          { texto: "Es mía" },
          { texto: "2.400 h", clase: "tabla-numero" },
          {
            texto: "ITV el 12/05/2026",
            clase: "tabla-numero",
            // **Lo que falta por saber va en su renglón**, no pegado a la fecha: la celda no puede ensancharse.
            pista: "4 más sin fecha",
            estado: { texto: "Vencida", tipo: "vencida" },
          },
          { texto: "1 papel", pista: "1 papel" },
          { texto: "Sí puedo", estado: { texto: "1 aviso", tipo: "" } },
        ],
        acciones: [
          { etiqueta: "VER", accion: "maquina-ver", datos: { id: 1 }, clase: "boton-claro" },
        ],
      },
    ],
    resumen: "1 máquina",
  };
}

/** Una máquina de la lista del móvil, ya preparada. */
function maquinaDeLaLista() {
  return {
    id: 1,
    nombre: "El Landini",
    detalle: "Tractor · 1234 ABC · Es mía",
    proxima: "Próxima revisión: ITV el 12/05/2026",
    papeles: "Papeles: 1 papel",
    disponibilidad: "Disponibilidad: Sí puedo",
    avisos: [{ texto: "La ITV de «El Landini» venció el 12/05/2026.", urgente: true }],
  };
}

// ---------------------------------------------------------------------------
// El arnés
// ---------------------------------------------------------------------------

async function cargarLaPantalla() {
  // El `?prueba=` con un número al azar es obligatorio: sin él, Node devuelve el módulo ya cargado por
  // otra prueba y la caché de módulos hace que las pruebas se pisen.
  return import(`../web/react/pantallas/maquinaria.js?prueba=${Math.random()}`);
}

async function htmlDeLaLista(cambios = {}) {
  const { PantallaDeLaMaquinaria } = await cargarLaPantalla();
  return globalThis.ReactDOMServer.renderToStaticMarkup(
    React.createElement(PantallaDeLaMaquinaria, {
      textos: structuredClone(TEXTOS),
      cuantas: MAQUINARIA.cuantas,
      filtro: "",
      tabla: tablaDeEjemplo(),
      maquinas: [maquinaDeLaLista()],
      equipos: [],
      queFalta: [],
      formulario: null,
      guardando: false,
      error: "",
      aviso: "",
      ...cambios,
    }),
  );
}

async function htmlDeLaFicha(cambios = {}) {
  const { PantallaDeUnaMaquina } = await cargarLaPantalla();
  const ficha = fichaConCosas();
  return globalThis.ReactDOMServer.renderToStaticMarkup(
    React.createElement(PantallaDeUnaMaquina, {
      textos: structuredClone(TEXTOS),
      maquina: ficha.maquina,
      avisos: ficha.avisos,
      obligaciones: ficha.obligaciones,
      inspecciones: ficha.inspecciones,
      averias: ficha.averias,
      formulario: null,
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
// 1. La ficha separa las cinco obligaciones
// ---------------------------------------------------------------------------

test("la ficha enseña las cinco obligaciones separadas, cada una con su nombre y su explicación", async () => {
  const html = await htmlDeLaFicha();
  const posiciones = ["ITV", "ITEAF", "Mantenimiento", "Seguro", "ROMA"].map((nombre) => {
    const sitio = html.indexOf(`<h3>${nombre}</h3>`);
    assert.ok(sitio >= 0, `la ficha no enseña «${nombre}» con su nombre`);
    return sitio;
  });
  assert.deepEqual([...posiciones].sort((a, b) => a - b), posiciones, "las cinco no salen en su orden");
  // Y cada una dice qué es: sin eso, ITV e ITEAF se leen como lo mismo.
  assert.match(html, /La inspección técnica del vehículo, como la del coche\./);
  assert.match(html, /La inspección de las máquinas con las que se echa el producto\. No es la ITV\./);
});

test("la ficha no llama ITV a la ITEAF, ni al revés", async () => {
  const html = await htmlDeLaFicha();
  // El documento de la casa lo avisa por su nombre: «No llamar a ITEAF "ITV" en las etiquetas». Aquí se
  // comprueba que la explicación de la ITV no es la de la ITEAF y que cada una lleva la suya.
  assert.doesNotMatch(html, /<h3>ITEAF<\/h3>[\s\S]{0,200}La inspección técnica del vehículo/);
  assert.match(html, /<h3>ITV<\/h3>[\s\S]{0,200}La inspección técnica del vehículo/);
});

test("cada obligación lleva sus tres respuestas y la pregunta de de dónde sale", async () => {
  const html = await htmlDeLaFicha();
  const acciones = botonesDe(html).filter((boton) => boton.accion === "maquina-declarar");
  assert.ok(acciones.length >= 5, `solo hay ${acciones.length} botones de declarar`);
  // Los tres estados de la aplicabilidad, y que se manda **el campo y su valor**, que es lo que lee `app.js`.
  const deITV = acciones.filter((boton) => boton.tipo === "itv" && boton.campo === "aplicabilidad");
  assert.deepEqual(
    deITV.map((boton) => boton.valor).sort(),
    ["no", "no_se", "si"],
    "la ITV no lleva sus tres respuestas",
  );
  assert.deepEqual(
    deITV.map((boton) => boton.campo),
    ["aplicabilidad", "aplicabilidad", "aplicabilidad"],
  );
  // Y el de dónde sale: «no le toca» sin decir quién lo dice es media respuesta.
  const origenes = acciones.filter((boton) => boton.campo === "origen" && boton.tipo === "iteaf");
  assert.deepEqual(origenes.map((boton) => boton.valor), ["documento"]);
});

// ---------------------------------------------------------------------------
// 2. La trampa del ticket: sin saberlo, se dice y se pregunta
// ---------------------------------------------------------------------------

test("sin clasificación técnica la ficha lo pide y no enseña ninguna fecha inventada", async () => {
  const ficha = fichaSinNada();
  const html = await htmlDeLaFicha({
    maquina: ficha.maquina,
    obligaciones: ficha.obligaciones,
    inspecciones: [],
    averias: [],
    avisos: [],
  });
  // El aviso que pide el dato…
  assert.match(html, /Falta la clasificación técnica de esta máquina/);
  // …y **ni una fecha**: ni un formato español ni un año suelto. Es lo que el contrato prohíbe calcular.
  assert.doesNotMatch(html, /\d{2}\/\d{2}\/\d{4}/, "hay una fecha donde no se sabe ninguna");
  // Y se dice que no se sabe, con palabras y no con un hueco en blanco.
  assert.match(html, /No se sabe si le toca/);
  assert.match(html, /Sin decir la clasificación/);
});

test("una obligación que aplica y sin inspección dice que no hay ninguna, no una fecha", async () => {
  const ficha = fichaSinNada();
  ficha.obligaciones[0].situacion_texto = "No hay ninguna apuntada";
  ficha.obligaciones[0].clasificacion_falta = false;
  const html = await htmlDeLaFicha({
    maquina: { ...ficha.maquina, clasificacion: "Tractor agrícola de ruedas", clasificacion_falta: false },
    obligaciones: ficha.obligaciones,
    inspecciones: [],
    averias: [],
    avisos: [],
  });
  assert.match(html, /No hay ninguna apuntada/);
  assert.doesNotMatch(html, /\d{2}\/\d{2}\/\d{4}/);
  // Y en la próxima fecha se dice que falta el dato, que es distinto de enseñar una.
  assert.match(html, /Falta la fecha/);
});

test("lo que el programa no calcula se dice, con lo que es y de quién depende", async () => {
  const html = await htmlDeLaFicha();
  assert.match(html, /Lo que este programa todavía no calcula/);
  assert.match(html, /Es el trabajo legal L07 de la matriz normativa\./);
});

// ---------------------------------------------------------------------------
// 3. Los avisos y las averías
// ---------------------------------------------------------------------------

test("los avisos dicen qué hay que mirar, con su palabra de urgencia y sin depender del color", async () => {
  const html = await htmlDeLaFicha();
  assert.match(html, /Míralo antes de usarla/);
  assert.match(html, /Míralo cuando puedas/);
  assert.match(html, /La ITEAF de «El Landini» venció el 12\/05\/2026\./);
});

test("sin nada que mirar se dice, en vez de dejar el hueco en blanco", async () => {
  const html = await htmlDeLaFicha({ avisos: [] });
  assert.match(html, /De esta máquina no hay nada que mirar ahora mismo\./);
});

test("la avería dice lo que pasó, cuándo y si está arreglada, con sus tres salidas", async () => {
  const html = await htmlDeLaFicha();
  assert.match(html, /Avería del 04\/01\/2026/);
  assert.match(html, /Se rompió el eje del ventilador/);
  assert.match(html, /Sigue sin arreglar/);
  const acciones = botonesDe(html).map((boton) => boton.accion);
  assert.ok(acciones.includes("maquina-averia-corregir"));
  assert.ok(acciones.includes("maquina-averia-borrar"));
  assert.ok(acciones.includes("maquina-anular"));
});

// ---------------------------------------------------------------------------
// 4. Una inspección sin papel se apunta y se dice que no lo trae
// ---------------------------------------------------------------------------

test("una inspección sin papel se enseña y dice que no lo trae", async () => {
  const html = await htmlDeLaFicha();
  assert.match(html, /De esta inspección no has apuntado ningún papel\./);
  // Y la que sí lo trae **dice cuál es** y se puede abrir: en una inspección, el papel es lo que se enseña.
  assert.match(html, /Con su papel: Certificado de la ITEAF/);
  const acciones = botonesDe(html).filter((boton) => boton.accion === "papel-ver");
  assert.ok(acciones.length >= 2, "ni la obligación ni la inspección dejan abrir su papel");
  assert.deepEqual(acciones.map((boton) => boton.id), ["4", "4"]);
});

test("el formulario de una inspección se puede rellenar sin papel, y lo dice", async () => {
  const { pantallaDeUnaMaquina } = await cargarLaPantalla();
  const ficha = fichaConCosas();
  const formulario = {
    clase: "inspeccion",
    titulo: MAQUINARIA.form_inspeccion_titulo,
    pista: MAQUINARIA.form_inspeccion_pista,
    guardar: MAQUINARIA.apuntar_inspeccion,
    cancelar: "VOLVER SIN GUARDAR",
    guardando: MAQUINARIA.form_guardando,
    datos: { id: "" },
    bloques: [
      {
        tipo: "opciones",
        campo: "tipo",
        etiqueta: MAQUINARIA.campo_tipo_inspeccion,
        elegido: "iteaf",
        opciones: [
          { valor: "itv", texto: "ITV", elegido: false },
          { valor: "iteaf", texto: "ITEAF", elegido: true },
        ],
      },
      { tipo: "fecha", id: "inspeccion-fecha", etiqueta: MAQUINARIA.campo_fecha, pista: MAQUINARIA.campo_fecha_pista, valor: "2026-10-03" },
      {
        tipo: "opciones",
        campo: "resultado",
        etiqueta: MAQUINARIA.resultado,
        elegido: "no_consta",
        opciones: [{ valor: "no_consta", texto: "No lo pone el papel", elegido: true }],
      },
      { tipo: "fecha", id: "inspeccion-proxima", etiqueta: MAQUINARIA.campo_proxima_fecha, pista: MAQUINARIA.campo_proxima_fecha_pista, valor: "" },
      {
        tipo: "opciones",
        campo: "documento_id",
        etiqueta: MAQUINARIA.campo_documento,
        pista: MAQUINARIA.sin_papeles_guardados,
        elegido: "",
        opciones: [{ valor: "", texto: "Sin papel apuntado" }],
      },
      { tipo: "area", id: "inspeccion-notas", etiqueta: MAQUINARIA.campo_notas, valor: "", filas: 2 },
    ],
  };
  const html = globalThis.ReactDOMServer.renderToStaticMarkup(
    React.createElement(pantallaDeUnaMaquina({}).type, {
      textos: TEXTOS,
      maquina: ficha.maquina,
      obligaciones: ficha.obligaciones,
      inspecciones: [],
      averias: [],
      formulario,
    }),
  );
  assert.match(html, /Apuntar una inspección/);
  assert.match(html, /No tienes ningún papel guardado\./);
  assert.match(html, /Sin papel apuntado/);
  // Y los campos que `app.js` lee por su `id`, con su nombre exacto.
  assert.deepEqual(idsDe(html).filter((id) => id.startsWith("inspeccion-")), [
    "inspeccion-fecha",
    "inspeccion-proxima",
    "inspeccion-notas",
  ]);
});

// ---------------------------------------------------------------------------
// 5. Los botones y los campos
// ---------------------------------------------------------------------------

test("cada botón de la ficha lleva su acción y sus datos", async () => {
  const html = await htmlDeLaFicha();
  const acciones = botonesDe(html).map((boton) => boton.accion);
  for (const esperada of [
    "maquina-corregir",
    "maquina-declarar",
    "maquina-inspeccion-nueva",
    "maquina-averia-nueva",
    "maquinaria-ver",
  ]) {
    assert.ok(acciones.includes(esperada), `la ficha no tiene el botón ${esperada}`);
  }
  // Y el que apunta una inspección dice **de qué obligación**, que es lo que no se puede deducir después.
  const apuntar = botonesDe(html).filter((boton) => boton.accion === "maquina-inspeccion-nueva");
  assert.deepEqual(apuntar.map((boton) => boton.tipo).sort(), [
    "iteaf",
    "itv",
    "mantenimiento",
    "roma",
    "seguro",
  ]);
});

test("el formulario de una máquina lleva los campos con su id y las tres preguntas sin contestar", async () => {
  const formulario = {
    clase: "maquina",
    titulo: MAQUINARIA.form_nueva_titulo,
    pista: MAQUINARIA.form_nueva_pista,
    guardar: MAQUINARIA.guardar,
    cancelar: "VOLVER SIN GUARDAR",
    guardando: MAQUINARIA.form_guardando,
    bloques: [
      { tipo: "texto", id: "maquina-nombre", etiqueta: MAQUINARIA.nombre, pista: MAQUINARIA.nombre_pista, valor: "" },
      {
        tipo: "opciones",
        campo: "clase",
        etiqueta: MAQUINARIA.clase,
        pista: MAQUINARIA.clase_pista,
        elegido: "",
        opciones: [
          { valor: "tractor", texto: "Tractor", elegido: false },
          { valor: "apero", texto: "Apero", elegido: false },
        ],
      },
      { tipo: "texto", id: "maquina-clasificacion", etiqueta: MAQUINARIA.clasificacion, pista: MAQUINARIA.clasificacion_pista, valor: "" },
      { tipo: "numero", id: "maquina-horas", etiqueta: MAQUINARIA.horas, pista: MAQUINARIA.horas_pista, valor: "" },
    ],
  };
  const html = await htmlDeLaLista({ tabla: null, maquinas: [], formulario, tabla: null });
  assert.match(html, /Apuntar una máquina/);
  assert.deepEqual(
    idsDe(html).filter((id) => id.startsWith("maquina-")),
    ["maquina-nombre", "maquina-clasificacion", "maquina-horas"],
  );
  // **Las tres preguntas que no nacen contestadas**: ninguna opción sale marcada como elegida.
  assert.doesNotMatch(html, /data-elegido="1"/);
  assert.match(html, /data-accion="maquina-elegir" data-campo="clase" data-valor="tractor"/);
});

// ---------------------------------------------------------------------------
// 6. La lista
// ---------------------------------------------------------------------------

test("la lista enseña la tabla con sus columnas y las máquinas con lo que hay que mirar", async () => {
  const html = await htmlDeLaLista();
  assert.match(html, /Máquina/);
  assert.match(html, /Matrícula o serie/);
  assert.match(html, /Próxima revisión/);
  assert.match(html, /Disponibilidad/);
  assert.match(html, /El Landini/);
  assert.match(html, /1 máquina/);
  // El estado va con palabras, no solo con color.
  assert.match(html, /Vencida/);
  assert.match(html, /1 aviso/);
  // Y lo que falta por saber va en su renglón (la pista), no pegado a la fecha: así la celda no se ensancha.
  assert.match(html, /4 más sin fecha/);
  // La tabla va dentro del contenedor que se desplaza solo ella: con nueve columnas, a 1024 px no cabe, y sin
  // esto la página entera se salía de lo ancho (medido en el navegador).
  assert.match(html, /<div class="solo-escritorio tabla-scroll">/);
});

test("sin máquinas se dice qué hacer, y el botón de apuntar una está siempre", async () => {
  const html = await htmlDeLaLista({ tabla: null, maquinas: [], cuantas: "" });
  assert.match(html, /Todavía no has apuntado ninguna máquina/);
  assert.match(html, /data-accion="maquina-nueva"/);
});

test("si el buscador no encuentra nada se dice, y se puede volver a verlas todas", async () => {
  const html = await htmlDeLaLista({ tabla: null, maquinas: [], filtro: "pepito" });
  assert.match(html, /Ninguna de tus máquinas se llama así/);
  assert.match(html, /data-accion="maquinaria-ver-todas"/);
});

test("los equipos del cuaderno que no están en la lista se enseñan, con el botón de traerlos", async () => {
  // **Media puerta de calidad del ticket**: `EquipoAplicacion` no cubre toda la maquinaria, pero lo que ya
  // estaba apuntado no puede desaparecer de la vista.
  const html = await htmlDeLaLista({
    equipos: [
      { id: 4, nombre: "Pulverizador grande", detalle: "Atomizador · ROMA-9876 · 01/03/2029" },
    ],
  });
  assert.match(html, /Equipos de echar producto que todavía no están en esta lista/);
  assert.match(html, /Pulverizador grande/);
  assert.match(html, /data-accion="maquina-traer-equipo" data-id="4"/);
});

test("la lista lleva lo que el programa no calcula, para que no parezca un olvido", async () => {
  const html = await htmlDeLaLista({
    queFalta: [
      {
        que: "Cada cuánto toca pasar la ITV y la ITEAF, por clasificación técnica.",
        para_que: "Poder calcular la próxima fecha.",
        de_quien_depende: "Es el trabajo legal L07.",
      },
    ],
  });
  assert.match(html, /Lo que este programa todavía no calcula/);
  assert.match(html, /<strong>De quién depende<\/strong><span> Es el trabajo legal L07\.<\/span>/);
});

// ---------------------------------------------------------------------------
// 7. Ni una frase escrita a mano
// ---------------------------------------------------------------------------

test("la lista no lleva ni una frase escrita a mano", async () => {
  const equipos = [{ id: 4, nombre: "Pulverizador grande", detalle: "Atomizador · ROMA-9876" }];
  const queFalta = [{ que: "Lo que falta", para_que: "Para esto", de_quien_depende: "De esto" }];
  const html = await htmlDeLaLista({ equipos, queFalta });
  const delServidor = new Set([
    ...todosLosTextos(TEXTOS),
    ...todosLosTextos(tablaDeEjemplo()),
    ...todosLosTextos([maquinaDeLaLista()]),
    ...todosLosTextos(equipos),
    ...todosLosTextos(queFalta),
    MAQUINARIA.cuantas,
  ]);
  for (const frase of frasesVisibles(html)) {
    assert.ok(delServidor.has(frase), `frase escrita a mano: «${frase}»`);
  }
});

test("la ficha no lleva ni una frase escrita a mano", async () => {
  const html = await htmlDeLaFicha();
  const ficha = fichaConCosas();
  const delServidor = new Set([
    ...todosLosTextos(TEXTOS),
    ...todosLosTextos(ficha),
  ]);
  for (const frase of frasesVisibles(html)) {
    assert.ok(delServidor.has(frase), `frase escrita a mano: «${frase}»`);
  }
});


test("las máquinas que se pueden elegir: fuera la que no se puede contar, dentro la que no se sabe", async () => {
  /*
   * CRM-07 #7, 14/10/2026. El informe del dueño lo pide así: «**máquina indisponible no se ofrece como
   * disponible**». Y la casa tiene TRES estados, no dos (`app/maquinaria.py`):
   *
   *   «Si se puede contar con ella para trabajar. Tres estados otra vez, y `NO_SE` de partida: una máquina
   *    de la que nadie ha dicho nada **no está "disponible", está "sin decir"**.»
   *
   * Así que esta prueba fija **las dos mitades**, y la segunda es la que se rompería por hacer lo obvio:
   *
   *  1. La que está apuntada como que **no puedes contar con ella** (o su avería) **no se ofrece**.
   *  2. Y la que **nadie ha dicho nada de ella** (`no_se`) **sí se ofrece**: quitarla sería convertir «sin
   *     decir» en «no», que es lo que este programa no hace en ningún sitio.
   *
   * Se prueba la función **del módulo** (`maquinaria.js`) y no la pantalla: es una regla de qué máquinas
   * se pueden elegir, no de cómo se pinta. Y vive ahí, con `export`, **para poder probarse** —`app.js`
   * necesita un DOM y no tiene pruebas—.
   */
  const { lasMaquinasParaElegir } = await cargarLaPantalla();
  const tabla = {
    maquinas: [
      { id: 1, nombre: "El tractor", disponibilidad: "disponible" },
      { id: 2, nombre: "La sulfatadora", disponibilidad: "no_disponible" },
      { id: 3, nombre: "La empacadora", disponibilidad: "no_se" },
    ],
  };
  const salen = lasMaquinasParaElegir(tabla);

  assert.deepEqual(
    salen.map((una) => una.texto),
    ["El tractor", "La empacadora"],
    "la que no se puede contar no se ofrece, y la que no se sabe SÍ (no es lo mismo «sin decir» que «no»)"
  );
  // Y salen **como las quiere el desplegable**: con su valor y su texto, y en el mismo orden.
  assert.deepEqual(salen, [
    { valor: 1, texto: "El tractor" },
    { valor: 3, texto: "La empacadora" },
  ]);
  // Una finca sin máquinas no revienta: devuelve la lista vacía, que es lo que el desplegable espera.
  assert.deepEqual(lasMaquinasParaElegir({}), []);
});

test("sin permiso de modificar, la ficha de la maquina NO ofrece los botones de las lecturas", async () => {
  // **LA MITAD DE PANTALLA DEL PUNTO 2** (17/10/2026). El encargo dice «permisos en servidor **y
  // pantalla**»: el servidor ya lo comprueba -la puerta contesta 403-, y esto es que la pantalla
  // **no ofrezca** lo que va a dar 403.
  //
  // **Y hacia falta una prueba, no solo el cambio.** El envoltorio (`pantallaDeUnaMaquina`) usa
  // **reparto** -pasa lo que le den-, asi que no puede perder una prop; **pero el componente si**: si no
  // declarara `puede_modificar`, el valor por defecto `= true` la taparia y los botones saldrian igual,
  // **sin un solo error**.
  //
  // ***Y eso mismo paso, de verdad, en la ficha de contacto***: alli el envoltorio leia
  // `propiedades.puedo_modificar` -con «puedo» y no «puede»-, `app.js` manda `puede_modificar`, llegaba
  // `undefined`… **y `undefined` y `true` se comportan igual**. Ninguna prueba lo cazaba, porque la que
  // habia miraba el valor que llegaba y el valor por defecto lo tapaba.
  //
  // Asi que esta mira **las dos mitades**: que con `false` los botones no salgan, y que con `true` si.
  // *Sin la segunda, un componente que no pintara nunca nada tambien «pasaria» -y estariamos arreglando
  // un fallo con otro-.*
  // ***Las lecturas se pasan aqui y NO en el ayudante*** (17/10/2026): `fichaConCosas()` las trae, pero
  // meterlas en `htmlDeLaFicha` cambia **todos** los tests que usan ese ayudante, y uno de ellos afirma
  // justo lo contrario -que no hay **ninguna fecha**-. *El ayudante compartido no se toca para una
  // prueba: se le pasan a esta los datos que necesita.*
  const conLecturas = { lecturas: fichaConCosas().lecturas, contador: null };
  const sinPermiso = await htmlDeLaFicha({ ...conLecturas, puede_modificar: false });
  for (const accion of [
    "maquina-lectura-nueva",
    "maquina-lectura-corregir",
    "maquina-lectura-anular",
  ]) {
    assert.ok(
      !sinPermiso.includes(accion),
      `quien no puede modificar no puede recibir el boton de las lecturas (${accion}):\n${sinPermiso}`,
    );
  }

  const conPermiso = await htmlDeLaFicha({ ...conLecturas, puede_modificar: true });
  for (const accion of ["maquina-lectura-nueva", "maquina-lectura-corregir"]) {
    assert.ok(
      conPermiso.includes(accion),
      `con permiso los botones tienen que estar (${accion}), o la prueba de arriba no prueba nada:\n${conPermiso}`,
    );
  }
});

test("la ficha de la maquina ensena sus RESERVAS, y sin permiso no ofrece los botones", async () => {
  // **CRM-07 #9** (17/10/2026). *Lo que la cola pide con estas palabras: «***Reserva para planificar no es
  // consumo***».*
  //
  // ***Y esto era un hueco de verdad, no un adorno***: `app/reservas.py` y sus 21 pruebas -el solape, las
  // averias, los estados, **dos peticiones a la vez**- llevaban hechas desde hacia rondas, y `reserva` **no
  // aparecia ni una vez en todo `web/`**. *El agricultor no lo podia usar.* Es lo que el objetivo llama
  // «una funcion que solo existe en servidor».
  //
  // La prueba mira las cuatro cosas que importan:
  //   · que **la reserva se vea** -el cuando y su estado-;
  //   · que **con permiso** se ofrezcan los tres botones;
  //   · que **sin permiso** no se ofrezcan… ***pero la reserva se siga viendo*** -no ofrecer no es no
  //     poder mirar, y esa es la mitad que se olvida-;
  //   · que **una anulada** no se pueda corregir ni anular otra vez, y se vea con su motivo.
  const unaReserva = (cambios = {}) => ({
    id: 5,
    cuando_texto: "20/04/2026 08:00 → 20/04/2026 14:00",
    estado_texto: "Pedida",
    responsable_texto: "Sin decir quién la coge",
    tarea_texto: "Laboreo · cultivador",
    notas: null,
    anulada: false,
    motivo_anulacion: null,
    ...cambios,
  });

  const conPermiso = await htmlDeLaFicha({ reservas: [unaReserva()] });
  assert.ok(conPermiso.includes("20/04/2026 08:00"), `la reserva tiene que verse:\n${conPermiso}`);
  assert.ok(conPermiso.includes("Sin decir quién la coge"), "y decir que no se sabe quien la coge");
  assert.ok(
    conPermiso.includes("maquina-reserva-nueva"),
    `con permiso se ofrece reservar:\n${conPermiso}`,
  );
  assert.ok(
    conPermiso.includes("maquina-reserva-corregir") && conPermiso.includes('data-que="reserva"'),
    "y corregir y anular la reserva",
  );

  const sinPermiso = await htmlDeLaFicha({ reservas: [unaReserva()], puede_modificar: false });
  // ***El de anular se mira POR SU `data-que`, no por su nombre*** (17/10/2026). *Anular una reserva va por
  // `maquina-anular` -la puerta que ya existia, para que el motivo y su pregunta sean los mismos que en una
  // averia-, **y `maquina-anular` es tambien el boton de las averias**, que no esta detras del permiso.
  // Buscar solo el nombre daria un falso fallo: la prueba encontraria el de una averia y diria que el
  // permiso no funciona.*
  //
  // *Y `data-que="reserva"` solo lo pone el boton de una reserva, asi que no se puede confundir.*
  assert.ok(
    sinPermiso.includes("maquina-reserva-nueva") === false &&
      sinPermiso.includes("maquina-reserva-corregir") === false,
    `quien no puede modificar no puede recibir los botones de la reserva:\n${sinPermiso}`,
  );
  assert.ok(
    !sinPermiso.includes('data-que="reserva"'),
    `ni el de anular -que se reconoce por su \`data-que\`-:\n${sinPermiso}`,
  );
  for (const accion of []) {
    assert.ok(
      !sinPermiso.includes(accion),
      `quien no puede modificar no puede recibir el boton (${accion}):\n${sinPermiso}`,
    );
  }
  assert.ok(
    sinPermiso.includes("20/04/2026 08:00"),
    "***pero la reserva se sigue VIENDO***: no ofrecer un boton no es no poder mirar",
  );

  const anulada = await htmlDeLaFicha({
    reservas: [unaReserva({ anulada: true, motivo_anulacion: "Se cayó el trabajo" })],
  });
  assert.ok(anulada.includes("Se cayó el trabajo"), `una anulada dice por que:\n${anulada}`);
  assert.ok(
    !anulada.includes("maquina-reserva-corregir") && !anulada.includes('data-que="reserva"'),
    "***y una anulada no se corrige ni se anula otra vez***",
  );

  const vacia = await htmlDeLaFicha({ reservas: [] });
  assert.ok(
    vacia.includes("No has reservado esta máquina para nada"),
    `sin reservas se dice que no hay, en vez de dejar el hueco:\n${vacia}`,
  );

  // ***Y `null` NO es `[]`***, que es la distincion de la casa -la misma que `papeles` y `costes`-:
  //   · **`[]`** es «se pidieron y no hay ninguna» -> se dice, **y se ofrece reservar**;
  //   · **`null`** es «***todavia no se han pedido***» -> **ni se dice ni se ofrece**.
  //
  // ***Y esto no es un adorno: es un defecto que se cometio***. Cuando se añadio la seccion, `app.js`
  // todavia no traia las reservas, asi que la ficha **ofrecia un boton de reservar que no llevaba a
  // ninguna parte** -con su texto de «no has reservado nada», que ademas era mentira: no es que no haya
  // ninguna, es que no se habian pedido-. *La distincion `null`/`[]` es lo que hace que no se pueda
  // ofrecer de mas.*
  const sinPedir = await htmlDeLaFicha({ reservas: null });
  assert.ok(
    !sinPedir.includes("maquina-reserva-nueva"),
    `mientras no se hayan pedido las reservas NO se ofrece reservar:\n${sinPedir}`,
  );
  assert.ok(
    !sinPedir.includes("No has reservado esta máquina para nada"),
    "***y tampoco se dice que no hay ninguna: no es que no haya, es que no se ha preguntado***",
  );
});
