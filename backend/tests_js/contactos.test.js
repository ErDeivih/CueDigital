/**
 * Pruebas de las pantallas de las personas y las empresas (T11, 03/10/2026), **sin navegador**.
 *
 * POR QUÉ ESTÁN AQUÍ Y NO EN `interfaz.test.js`
 *
 * Las cuatro pantallas están escritas en React (`web/react/pantallas/contactos.js` y
 * `revision_de_contactos.js`), y en el DOM de mentira de `interfaz.test.js` React no se puede montar.
 * Así que se prueban **contra el componente**: se le dan las propiedades y se mira el HTML que produce
 * con `renderToStaticMarkup`, como se hace con las demás pantallas migradas. No hay `jsdom` ni ninguna
 * dependencia nueva.
 *
 * QUÉ SE COMPRUEBA, Y POR QUÉ ESAS COSAS
 *
 *  1. **Que lo que no se puede asegurar no lleve botón de apuntar.** Es la prueba más importante de
 *     todas: en la revisión de los nombres, una ficha «que se parece» a otra **se enseña y no se puede
 *     apuntar**. Un botón ahí sería la forma de fusionar a un proveedor con su hermano de un toque, y
 *     eso no se puede deshacer. El servidor también se niega (contesta 409), pero el «no» tiene que
 *     estar en los dos sitios.
 *  2. **Que el nombre escrito del agricultor no se pueda tocar desde aquí.** No hay ni un campo que lo
 *     cambie: lo único que se puede hacer con él es enlazarlo o quitarle el enlace.
 *  3. **Que los papeles se solapen**: se marcan de uno en uno y se pueden marcar varios, porque la
 *     misma cooperativa vende y compra.
 *  4. **Que ninguna frase esté escrita dentro del componente**: todas vienen de la copia de los textos
 *     del servidor que hay aquí abajo, y una prueba de Python (`tests/test_contactos.py`) comprueba,
 *     clave por clave, que esa copia no se queda vieja.
 */

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import vm from "node:vm";

// El apuntador de montajes: es de donde lo lee la aplicación, así que es lo que dice qué pantalla se
// ha pedido a React. Se importa (no se copia) porque es de la aplicación, no del arnés.
import { montajes } from "../web/react/montar.js";

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
// Los textos: los mismos que sirve el servidor
// ---------------------------------------------------------------------------

/**
 * La copia de los textos de los contactos, **tal y como los sirve `/api/interfaz`**.
 *
 * Si se inventaran aquí, estas pruebas comprobarían una pantalla que el agricultor no tiene. La prueba
 * de Python (`tests/test_contactos.py::TestLaCopiaDeLosTextosNoSeQuedaVieja`) lee este fichero y
 * comprueba, clave por clave, que dice lo mismo que el servidor.
 */
const TEXTOS = {
  contactos: {
    titulo: "Las personas y las empresas",
    explica:
      "Aquí apuntas una vez a quien te vende, a quien te compra, a quien te asesora o a quien te lleva la mercancía. Después, en cada factura y en cada venta, solo tienes que decir cuál de ellos es: su nombre ya no hay que volver a escribirlo.",
    vacia:
      "Todavía no tienes ninguna ficha apuntada. Puedes empezar por los nombres que ya has escrito en tus facturas y en tus ventas: el programa te los enseña y tú dices cuáles son la misma persona.",
    cuantas: "Tienes {cuantas} fichas apuntadas.",
    cuantas_una: "Tienes 1 ficha apuntada.",
    cuantos_escritos: "Su nombre está escrito en {cuantas} papeles.",
    // Las notas con autor (CRM-03, criterio (f), 11/10/2026). **Copiadas del servidor**, no
    // transcritas a mano: el guardián exige que sean las mismas palabras.
    // Los rótulos del saldo (Entrega 1). Copiados del servidor, no transcritos a mano.
    saldo_titulo: "Lo que hay con este contacto",
    saldo_explica: "Lo que nos debe y lo que le debemos, cada cosa por su lado. No se restan: que a la misma persona se le venda y se le compre es lo normal, y juntarlo escondería las dos.",
    saldo_nos_debe: "Nos debe",
    saldo_le_debemos: "Le debemos",
    saldo_nada: "Nada",
    saldo_importe: "Importe",
    saldo_cobrado: "Cobrado",
    saldo_pagado: "Pagado",
    saldo_pendiente: "Queda",
    saldo_sin_importe: "No se sabe cuánto",
    saldo_sin_documentos: "No hay ningún documento apuntado a este contacto.",
    saldo_sin_asignar: "Dinero sin asignar",
    saldo_sin_asignar_pista: "Está apuntado y no se sabe de qué es, así que no rebaja ninguna deuda. No es un anticipo.",
    saldo_para_revisar: "Para revisar",
    saldo_para_revisar_pista: "Se ha cobrado o pagado más de lo que valía el documento. Puede ser un tecleo, un pago de otra cosa o una devolución pendiente.",
    saldo_cobertura: "Hasta dónde llega",
    saldo_cobertura_pista: "Solo cuenta lo que está apuntado a este contacto. Las facturas de compra no llevan contacto, así que no se adjudican por el nombre.",
    saldo_en_euros: "En euros",
    saldo_no_se_adjudica_por_nombre: "No se adjudica nada por el nombre.",
    saldo_abrir: "Ver los documentos",
    notas_titulo: "Lo que se sabe de esta ficha",
    notas_pista: "Por ejemplo: el del pienso, o que pasa los martes.",
    sin_notas: "Todavía no hay ninguna nota.",
    nota_nueva: "Apuntar una nota",
    nota_nueva_pista: "Lo que quieras acordarte de esta ficha.",
    apuntar_la_nota: "APUNTAR LA NOTA",
    nota_la_escribio: "La escribió",
    nota_lo_escribio_el_programa: "Lo apuntó el programa",
    nota_autor_sin_nombre: "alguien cuyo nombre ya no está",
    cuantos_escritos_uno: "Su nombre está escrito en 1 papel.",
    // El estado y sus botones (CRM-03, criterio (e), 11/10/2026). El guardián los exige copiados aquí: las
    // pruebas de las pantallas solo ven lo que hay en este fichero.
    de_baja: "DE BAJA",
    de_baja_pista: "Ya no se trabaja con esta ficha. Sigue aquí porque sus papeles la necesitan.",
    dejarlo_de_usar: "DEJAR DE USARLO",
    dejarlo_de_usar_pista: "Deja de ofrecerse sin borrar nada: sus facturas y sus ventas siguen apuntándole.",
    volver_a_usarlo: "VOLVER A USARLO",
    // Los rótulos de la tabla del ordenador (11/10/2026). El guardián de textos
    // (`tests/test_que_no_falte_ningun_texto.py`) los exige copiados aquí: las pruebas de las pantallas solo ven
    // lo que hay en este fichero, y así se comprueba que la pantalla **no escribe ninguna frase dentro** del
    // componente. Los pidió él, con la lista exacta, en cuanto los añadí al servidor.
    tabla_nombre: "Nombre",
    tabla_que_es: "Qué es",
    tabla_nif: "NIF",
    tabla_telefono: "Teléfono",
    tabla_localidad: "Localidad",
    tabla_acciones: "Acciones",
    tabla_abrir: "ABRIR LA FICHA",
    tabla_sin_dato: "—",
    tabla_que_es_sin_papel: "Sin papel apuntado",
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
    ficha_titulo: "Una ficha nueva",
    ficha_titulo_corregir: "Corregir esta ficha",
    ficha_explica:
      "Escribe lo que sepas. Lo que no sepas, déjalo en blanco: se queda vacío y no pasa nada.",
    nombre: "Cómo se llama",
    nombre_pista: "El nombre tal y como lo escribes tú. Es el que verás en la lista.",
    es_persona_o_empresa: "¿Es una persona o una empresa?",
    es_empresa_si: "Es una empresa",
    es_empresa_no: "Es una persona",
    es_empresa_no_se: "No lo sé",
    nif: "Su NIF o su CIF",
    nif_pista:
      "El número que viene en sus facturas. Si dos nombres distintos lo comparten, el programa sabe que son la misma empresa.",
    telefono: "Su teléfono",
    correo: "Su correo",
    direccion: "Su dirección",
    localidad: "Su pueblo",
    notas: "Lo que quieras apuntar de él",
    notas_pista: "Por ejemplo: el del pienso, o que pasa los martes.",
    los_papeles: "¿Qué hace contigo?",
    los_papeles_pista:
      "Puedes marcar más de uno: la misma cooperativa te vende la semilla y te compra el trigo.",
    papeles_que_dicen_sus_papeles: "Según lo que tienes apuntado, también sería:",
    papeles_que_tendria: "Haría contigo:",
    guardar: "GUARDAR LA FICHA",
    guardando: "Guardando…",
    guardada: "Ficha guardada.",
    volver_a_los_contactos: "VOLVER A LAS FICHAS",
    borrar: "BORRAR ESTA FICHA",
    borrar_pista:
      "Se borra la ficha, pero no se borra ningún nombre de tus facturas ni de tus ventas: siguen diciendo lo mismo.",
    borrar_confirmar: "¿Seguro que quieres borrar esta ficha?",
    borrar_si: "SÍ, BORRARLA",
    borrar_no: "MEJOR NO",
    borrada: "Ficha borrada. Los nombres de tus facturas y de tus ventas siguen donde estaban.",
    donde_aparece: "Dónde está escrito su nombre",
    donde_aparece_explica:
      "Estos son los papeles en los que aparece. El nombre que escribiste tú no se ha tocado: si quieres, puedes quitar el enlace y el papel se queda como estaba.",
    sin_enlaces:
      "Su nombre todavía no está enlazado con ningún papel. Puedes buscarlo entre los nombres que ya tienes escritos y decir que es él.",
    enlazar: "ENLAZAR UN NOMBRE QUE YA TENGO ESCRITO",
    quitar_enlace: "QUITAR EL ENLACE",
    enlace_quitado: "Enlace quitado. El nombre sigue escrito en el papel, tal y como lo escribiste.",
    el_texto_ha_cambiado:
      "Ojo: en ese papel ahora pone lo siguiente: {ahora}. Cuando lo enlazaste ponía: {entonces}. Si ya no es él, quita el enlace.",
    esta_anulada: "anulada",
    de_la_migracion: "Apuntada desde los nombres que ya tenías escritos",
    de_la_migracion_pista:
      "Esta ficha la propuso el programa a partir de tus papeles. Si la corriges, se queda como tuya y ya no se deshace con las demás.",
    escritos_titulo: "Los nombres que ya tienes escritos",
    escritos_explica:
      "Estos nombres están escritos en tus papeles y todavía no los has enlazado con ninguna ficha. Toca el que sea esta persona y quedará enlazado. No se cambia ni una letra de tu papel.",
    escritos_vacio:
      "No hay ningún nombre escrito sin enlazar. Todo lo que tienes apuntado ya tiene su ficha.",
    escritos_cuantos: "Hay {cuantos} nombres escritos esperando a que les digas de quién son.",
    escritos_cuantos_uno: "Hay 1 nombre escrito esperando a que le digas de quién es.",
    escritos_buscar: "Buscar entre los nombres escritos",
    escritos_buscar_pista: "Escribe unas letras del nombre que buscas.",
    escritos_buscar_boton: "BUSCAR",
    escritos_ver_todos: "VERLOS TODOS",
    enlazar_este: "ESTE ES",
    enlazado: "Enlazado. Ese nombre ya es de esta ficha.",
    revision_titulo: "Los nombres que ya tienes escritos",
    revision_explica:
      "He mirado los nombres que están escritos a mano en tus facturas, tus albaranes, tus ventas y tus análisis, y te propongo una ficha por cada uno. No he apuntado nada todavía: mira la lista y apunta solo las que quieras.",
    revision_nada:
      "No hay ningún nombre escrito sin dueño. Todo lo que tienes apuntado ya tiene su ficha.",
    revision_cuantas: "Se te proponen {cuantas} fichas, con {nombres} nombres escritos.",
    revision_cuantas_una: "Se te propone 1 ficha, con 1 nombre escrito.",
    revision_se_parecen_estos:
      "«{uno}» y «{otro}» se parecen, pero no son iguales. El programa no los junta: míralos y decide tú.",
    revision_nifs_dos: "Los NIF de esos papeles son {nifs}.",
    revision_apuntadas:
      "Apuntadas {cuantas} fichas, con {nombres} nombres enlazados. Ni una letra de tus papeles se ha tocado.",
    revision_apuntadas_uno:
      "Apuntada 1 ficha, con 1 nombre enlazado. Ni una letra de tus papeles se ha tocado.",
    revision_que_se_hace: "Qué hace el programa con esto",
    revision_que_se_hace_explica:
      "Lo que apuntes no cambia ni una letra de tus papeles: los nombres siguen escritos donde estaban. Lo único que hace es apuntar de quién son, para que no tengas que volver a escribirlos.",
    revision_seguras: "Se pueden apuntar",
    revision_seguras_pista:
      "Estos nombres están escritos igual en todas partes, así que son la misma persona o la misma empresa.",
    revision_mirar: "Estos los tienes que mirar tú",
    revision_mirar_pista:
      "El programa no los junta solo, y no es un fallo: son nombres que se parecen, y juntar a dos que no son el mismo no se puede deshacer.",
    revision_apuntar: "APUNTAR ESTA FICHA",
    revision_apuntar_todas: "APUNTARLAS TODAS",
    revision_deshacer: "DESHACER ESTO",
    revision_deshacer_pista:
      "Quita las fichas que apuntó el programa. Las que hayas corregido tú se quedan.",
    revision_deshecho:
      "Deshecho: {fichas} fichas quitadas y {enlaces} enlaces deshechos. Tus papeles siguen igual.",
    revision_cuantos_ya: "Ya tenías {cuantos} nombres enlazados, y esos no salen aquí.",
    revision_motivo_el_mismo_nombre: "Está escrito igual en todas partes",
    revision_motivo_mismo_nif: "Tienen el mismo NIF, así que son la misma empresa",
    revision_motivo_se_parecen:
      "Se parecen, pero no son iguales. El programa no los junta: míralos y decide tú.",
    revision_motivo_el_mismo_nombre_dos_nif:
      "El nombre es el mismo, pero el NIF no. Pueden ser dos personas distintas, así que el programa no las junta.",
    revision_motivo_mismo_nif_nombres_distintos:
      "El NIF es el mismo, pero los nombres no se parecen en nada. Uno de los dos papeles está mal escrito, así que el programa no los junta: míralos y decide tú.",
    revision_nif_compartido: "Los dos papeles llevan el mismo NIF: {nifs}.",
    revision_nombres_escritos: "Así está escrito en tus papeles:",
    revision_volver: "VOLVER A LAS FICHAS",
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
    tabla_facturas: "Una factura",
    tabla_albaranes: "Un albarán",
    tabla_ventas: "Una venta",
    tabla_analisis: "Un análisis",
    tabla_productos: "Un producto de los que compras",
    tabla_aplicadores: "Quien echa el producto",
    tabla_asesores: "Un asesor",
  },
};

/**
 * Los mensajes del servidor que la aplicación enseña tal cual, los mismos que sirve `/api/interfaz`.
 *
 * El primero lo enseña `app.js` cuando el agricultor pulsa GUARDAR sin escribir el nombre; el segundo
 * es el que dice que una confirmación reenviada **no ha apuntado dos veces** (defecto 3 de la revisión:
 * antes contestaba «la lista ha cambiado», que era mentira).
 */
const MENSAJES = {
  C7_un_contacto_necesita_nombre:
    "Falta el nombre. Sin nombre no se sabe de quién es la ficha: escríbelo y guárdala.",
  C11_ya_estaba_apuntada:
    "Esa ficha ya estaba apuntada de antes, así que no se ha apuntado dos veces. Mírala en tu lista: está con el nombre {nombre}.",
};

/** Los papeles, en su orden, como los sirve `/api/interfaz`. */
const PAPELES = Object.entries(TEXTOS.contactos.papeles).map(([valor, texto]) => ({
  valor,
  texto,
}));

function textosDePrueba() {
  return structuredClone(TEXTOS);
}

// ---------------------------------------------------------------------------
// Un lector del HTML: para mirar lo que se ve como lo miraría una persona
// ---------------------------------------------------------------------------

/** Los `id` de los campos, en el orden en que salen. */
function idsDe(html) {
  return [...html.matchAll(/(?<![\w-])id="([^"]+)"/g)].map((encontrado) => encontrado[1]);
}

/** Todos los textos de una estructura anidada, sean diccionarios o listas. */
function todosLosTextos(valor) {
  if (typeof valor === "string") return [valor];
  if (Array.isArray(valor)) return valor.flatMap(todosLosTextos);
  if (valor && typeof valor === "object") return Object.values(valor).flatMap(todosLosTextos);
  return [];
}

/** Lo que de verdad se lee en el HTML: el texto que hay entre las etiquetas. */
function frasesVisibles(html) {
  return html
    .replace(/<span class="tarjeta-aviso-icono"[^>]*>[^<]*<\/span>/g, "")
    .replace(/<span class="flecha"[^>]*>[^<]*<\/span>/g, "")
    .replace(/<[^>]*>/g, "\u0000")
    .split("\u0000")
    .map((trozo) => trozo.trim())
    .filter(Boolean);
}

/** Los `data-accion` que salen pintados. */
function accionesDe(html) {
  return [...html.matchAll(/data-accion="([a-z0-9_-]+)"/g)].map((encontrado) => encontrado[1]);
}

/** Los botones de los papeles, con si están marcados o no. */
function papelesDe(html) {
  return [...html.matchAll(/data-accion="contacto-papel"[^>]*?data-papel="([^"]+)"[^>]*?data-elegido="([01])"/g)].map(
    (encontrado) => ({ papel: encontrado[1], elegido: encontrado[2] === "1" }),
  );
}

async function cargar(nombre) {
  return import(`../web/react/pantallas/${nombre}.js?prueba=${Math.random()}`);
}

async function htmlDe(nombre, componente, propiedades) {
  const modulo = await cargar(nombre);
  return globalThis.ReactDOMServer.renderToStaticMarkup(
    React.createElement(modulo[componente], propiedades),
  );
}

const htmlDeLosContactos = (cambios = {}) =>
  htmlDe("contactos", "PantallaDeLosContactos", {
    textos: textosDePrueba(),
    tarjetas: [],
    resumen: "",
    buscado: "",
    aviso: "",
    error: "",
    cargando: false,
    ...cambios,
  });

const htmlDeUnContacto = (cambios = {}) =>
  htmlDe("contactos", "PantallaDeUnContacto", {
    textos: textosDePrueba(),
    borrador: {},
    papeles: PAPELES,
    vivos: [],
    corrigiendo: false,
    borrando: false,
    guardando: false,
    error: "",
    ...cambios,
  });

const htmlDeLosNombresEscritos = (cambios = {}) =>
  htmlDe("contactos", "PantallaDeLosNombresEscritos", {
    textos: textosDePrueba(),
    escritos: [],
    resumen: "",
    buscado: "",
    hayContacto: true,
    aviso: "",
    error: "",
    cargando: false,
    ...cambios,
  });

const htmlDeLaRevision = (cambios = {}) =>
  htmlDe("revision_de_contactos", "PantallaDeLaRevisionDeLosNombres", {
    textos: textosDePrueba(),
    seguras: [],
    paraMirar: [],
    resumenTexto: "",
    hayYaEnlazados: false,
    yaEnlazadosTexto: "",
    sePuedeDeshacer: false,
    apuntado: "",
    deshecho: "",
    aviso: "",
    error: "",
    cargando: false,
    ...cambios,
  });

/** Una propuesta ya preparada por `app.js`, como la recibe la pantalla. */
function unaPropuesta(cambios = {}) {
  return {
    clave: "a1b2c3",
    nombre: "Cooperativa Agrícola de Peñaranda",
    segura: true,
    motivo: "el_mismo_nombre",
    motivo_texto: TEXTOS.contactos.revision_motivo_el_mismo_nombre,
    nifs_texto: "",
    papeles_texto: "",
    escritos: [
      {
        claveTarjeta: "facturas-proveedor-1",
        texto: "Cooperativa Agrícola de Peñaranda",
        rotulo: "Una factura · 2026/00123 · 12/03/2026",
        filas: [],
        avisos: [],
      },
    ],
    ...cambios,
  };
}

/** Un nombre escrito ya preparado por `app.js`. */
function unEscrito(cambios = {}) {
  return {
    claveTarjeta: "facturas-proveedor-1",
    tabla: "facturas",
    campo: "proveedor",
    registro_id: 1,
    texto: "Cooperativa Agrícola de Peñaranda",
    rotulo: "Una factura · 2026/00123 · 12/03/2026",
    lineas: [],
    filas: [],
    avisos: [],
    ...cambios,
  };
}

// ---------------------------------------------------------------------------
// La lista
// ---------------------------------------------------------------------------

test("la lista sale con su título, su explicación y sus tres botones", async () => {
  const html = await htmlDeLosContactos();
  assert.match(html, /Las personas y las empresas/);
  assert.match(html, /su nombre ya no hay que volver a escribirlo/);
  assert.ok(accionesDe(html).includes("contacto-nuevo"), "falta el botón de añadir una ficha");
  assert.ok(
    accionesDe(html).includes("contactos-revisar-abrir"),
    "falta el camino a los nombres que ya están escritos",
  );
  assert.ok(accionesDe(html).includes("ir-inicio"), "falta la vuelta al inicio");
});

test("sin ninguna ficha se dice, y con su botón para salir de ahí", async () => {
  const html = await htmlDeLosContactos();
  assert.match(html, /Todavía no tienes ninguna ficha apuntada/);
  assert.ok(
    accionesDe(html).includes("contacto-nuevo"),
    "un aviso sin el botón que lo arregla deja al agricultor sin salida",
  );
});

test("cada ficha sale como una tarjeta, con sus papeles y dónde está su nombre", async () => {
  const html = await htmlDeLosContactos({
    tarjetas: [
      {
        id: 3,
        etiqueta: "Cooperativa Agrícola de Peñaranda",
        rotulo: "Quien te vende el producto · Quien te compra la cosecha",
        lineas: ["Cooperativa Agrícola de Peñaranda"],
        filas: [{ etiqueta: "Su NIF o su CIF", valor: "B34123456" }],
        avisos: [],
      },
    ],
    resumen: "Tienes 1 ficha apuntada.",
  });
  assert.match(html, /Cooperativa Agrícola de Peñaranda/);
  assert.match(html, /Quien te vende el producto · Quien te compra la cosecha/);
  assert.match(html, /B34123456/);
  assert.ok(accionesDe(html).includes("contacto-abrir"), "la tarjeta no abre la ficha");
  assert.ok(html.includes('data-id="3"'), "la tarjeta no dice de qué ficha es");
});

test("una ficha sin ningún nombre enlazado no dice «0 papeles»", async () => {
  // **Un cero ahí sería mentira**: lo que pasa es que su nombre todavía no está enlazado con nada, y
  // eso se dice con palabras en la ficha, no con un número.
  const html = await htmlDeLosContactos({
    tarjetas: [
      { id: 3, etiqueta: "La coop", rotulo: "", lineas: [], filas: [], avisos: [] },
    ],
  });
  assert.ok(!/0 papeles/.test(html), "la tarjeta cuenta un cero que no es un dato");
});

test("el buscador lleva su campo y sus dos botones", async () => {
  const html = await htmlDeLosContactos({ buscado: "coop" });
  assert.deepEqual(idsDe(html), ["contacto-buscar"]);
  assert.match(html, /value="coop"/, "el buscador pierde lo que el agricultor había escrito");
  assert.match(html, /BUSCAR/, "el botón de buscar no dice qué hace");
  assert.ok(accionesDe(html).includes("contactos-buscar"));
  assert.ok(accionesDe(html).includes("contactos-buscar-limpiar"));
});

// ---------------------------------------------------------------------------
// La ficha de un contacto
// ---------------------------------------------------------------------------

test("la ficha pide sus datos, cada uno con su id", async () => {
  const html = await htmlDeUnContacto();
  assert.deepEqual(idsDe(html), [
    "contacto-nombre",
    "contacto-nif",
    "contacto-telefono",
    "contacto-correo",
    "contacto-direccion",
    "contacto-localidad",
    "contacto-notas",
    "contacto-es-empresa",
  ]);
});

test("lo que no se sabe se queda en blanco, y se dice que se puede dejar así", async () => {
  const html = await htmlDeUnContacto({ borrador: { nombre: "La coop" } });
  assert.match(html, /value="La coop"/);
  assert.match(html, /Lo que no sepas, déjalo en blanco/);
});

test("«¿es una persona o una empresa?» tiene tres respuestas, no dos", async () => {
  // **«No lo sé» es una respuesta de verdad**: hay nombres que no dicen qué hay detrás, y convertirlos
  // en «es una persona» sería afirmar algo que nadie ha mirado.
  const html = await htmlDeUnContacto();
  assert.match(html, /No lo sé/);
  assert.match(html, /Es una empresa/);
  assert.match(html, /Es una persona/);
});

test("los papeles se marcan de uno en uno, y se pueden solapar", async () => {
  const html = await htmlDeUnContacto({ borrador: { papeles: ["proveedor", "comprador"] } });
  const papeles = papelesDe(html);
  assert.equal(papeles.length, PAPELES.length, "no salen todos los papeles del catálogo");
  const marcados = papeles.filter((uno) => uno.elegido).map((uno) => uno.papel);
  assert.deepEqual(marcados, ["proveedor", "comprador"], "los papeles que se solapan no se marcan");
  for (const papel of papeles) {
    assert.ok(
      html.includes(`data-papel="${papel.papel}"`),
      `el papel ${papel.papel} no dice cuál es`,
    );
  }
});

test("dónde está escrito su nombre: el texto del papel, de dónde es y el botón de quitarlo", async () => {
  const html = await htmlDeUnContacto({
    corrigiendo: true,
    borrador: { id: 3, nombre: "La coop" },
    vivos: [
      {
        id: 11,
        origen: "a_mano",
        escrito: { texto: "COOP. AGRICOLA DE PEÑARANDA" },
        rotulo: "Una factura · 2026/00123 · 12/03/2026",
        aviso: "",
      },
    ],
  });
  assert.match(html, /COOP\. AGRICOLA DE PEÑARANDA/, "no se lee el nombre que hay escrito");
  assert.match(html, /Una factura · 2026\/00123/, "no se dice de dónde es ese nombre");
  assert.ok(accionesDe(html).includes("contacto-desenlazar"), "no se puede quitar el enlace");
  assert.ok(html.includes('data-id="11"'), "el botón no dice qué enlace quita");
});

test("el aviso de que el papel ha cambiado desde el enlace se enseña", async () => {
  // El enlace no se rompe cuando el agricultor corrige el nombre del papel, **pero tampoco se calla**:
  // puede que ya no sea el mismo señor.
  const html = await htmlDeUnContacto({
    corrigiendo: true,
    vivos: [
      {
        id: 11,
        origen: "migracion",
        escrito: { texto: "Transportes López" },
        rotulo: "Una factura · 2026/00123",
        aviso: "Ojo: en ese papel ahora pone lo siguiente: Transportes López.",
      },
    ],
  });
  assert.match(html, /Ojo: en ese papel ahora pone lo siguiente/);
});

test("sin ningún enlace se dice, y se ofrece buscarlo entre los nombres escritos", async () => {
  const html = await htmlDeUnContacto({ corrigiendo: true });
  assert.match(html, /Su nombre todavía no está enlazado con ningún papel/);
  assert.ok(
    accionesDe(html).includes("contacto-enlazar-abrir"),
    "el aviso no lleva el botón que lo arregla",
  );
});

test("al dar de alta no se ofrece enlazar ni borrar: no hay nada que enlazar todavía", async () => {
  const html = await htmlDeUnContacto();
  assert.ok(!accionesDe(html).includes("contacto-enlazar-abrir"));
  assert.ok(!accionesDe(html).includes("contacto-borrar"));
  assert.match(html, /Una ficha nueva/);
});

test("al corregir cambia el título y salen BORRAR y ENLAZAR", async () => {
  const html = await htmlDeUnContacto({ corrigiendo: true, borrador: { id: 3 } });
  assert.match(html, /Corregir esta ficha/);
  assert.ok(accionesDe(html).includes("contacto-borrar"));
  assert.ok(accionesDe(html).includes("contacto-enlazar-abrir"));
});

test("borrar no se hace de un toque: se pregunta antes, y se puede decir que no", async () => {
  const html = await htmlDeUnContacto({ corrigiendo: true, borrando: true, borrador: { id: 3 } });
  assert.match(html, /¿Seguro que quieres borrar esta ficha\?/);
  assert.match(html, /no se borra ningún nombre de tus facturas/);
  assert.ok(accionesDe(html).includes("contacto-borrar-si"));
  assert.ok(accionesDe(html).includes("contacto-borrar-no"));
  assert.ok(html.includes('data-id="3"'), "el botón de borrar no dice qué ficha borra");
});

test("una ficha que apuntó el programa desde los papeles se dice que lo es", async () => {
  const html = await htmlDeUnContacto({ corrigiendo: true, borrador: { id: 3, origen: "migracion" } });
  assert.match(html, /Apuntada desde los nombres que ya tenías escritos/);
});

test("los papeles que dicen sus propios papeles se enseñan aparte", async () => {
  const html = await htmlDeUnContacto({
    corrigiendo: true,
    borrador: {
      id: 3,
      papeles_segun_lo_escrito_texto:
        "Según lo que tienes apuntado, también sería: Quien te vende el producto",
    },
  });
  assert.match(html, /Según lo que tienes apuntado, también sería: Quien te vende el producto/);
});

test("el botón de guardar se apaga mientras guarda, y lo dice", async () => {
  const html = await htmlDeUnContacto({ guardando: true });
  assert.match(html, /Guardando…/);
  assert.match(html, /data-accion="contacto-guardar"[^>]*disabled/);
});

// ---------------------------------------------------------------------------
// Los nombres escritos que todavía no son de nadie
// ---------------------------------------------------------------------------

test("la lista de nombres escritos sale con su título y su buscador", async () => {
  const html = await htmlDeLosNombresEscritos({ escritos: [unEscrito()] });
  assert.match(html, /Los nombres que ya tienes escritos/);
  assert.match(html, /No se cambia ni una letra de tu papel/);
  assert.deepEqual(idsDe(html), ["escrito-buscar"]);
  assert.ok(accionesDe(html).includes("contacto-escritos-buscar"));
  assert.ok(accionesDe(html).includes("contacto-escritos-buscar-limpiar"));
});

test("cada nombre escrito se puede enlazar, y el botón dice de cuál es", async () => {
  const html = await htmlDeLosNombresEscritos({ escritos: [unEscrito()], resumen: "Hay 1 nombre escrito." });
  assert.match(html, /Cooperativa Agrícola de Peñaranda/);
  assert.match(html, /Una factura · 2026\/00123 · 12\/03\/2026/);
  assert.ok(accionesDe(html).includes("contacto-enlazar"));
  assert.ok(html.includes('data-tabla="facturas"'), "el botón no dice de qué tabla es el nombre");
  assert.ok(html.includes('data-campo="proveedor"'));
  assert.ok(html.includes('data-registro="1"'));
});

test("sin ningún nombre esperando se dice, y sin ninguna ficha se ofrece el botón que lo arregla", async () => {
  const html = await htmlDeLosNombresEscritos({ hayContacto: false });
  assert.match(html, /No hay ningún nombre escrito sin enlazar/);
  assert.match(html, /Todavía no tienes ninguna ficha apuntada/);
  assert.ok(
    accionesDe(html).includes("contacto-nuevo"),
    "un aviso sin el botón que lo arregla deja al agricultor sin salida",
  );
  // Y **sin ficha no se ofrece enlazar**, porque no hay con qué: un botón que no puede hacer nada
  // promete una salida y no la da.
  const htmlConEscritos = await htmlDeLosNombresEscritos({
    hayContacto: false,
    escritos: [unEscrito()],
  });
  assert.ok(
    !accionesDe(htmlConEscritos).includes("contacto-enlazar"),
    "se ofrece enlazar sin ninguna ficha con la que enlazar",
  );
});

test("una factura anulada se dice que lo está", async () => {
  const html = await htmlDeLosNombresEscritos({
    escritos: [unEscrito({ avisos: ["anulada"] })],
  });
  assert.match(html, /anulada/);
});

// ---------------------------------------------------------------------------
// La revisión de los nombres: propone y NO fusiona
// ---------------------------------------------------------------------------

test("la revisión enseña lo que se puede apuntar y lo que hay que mirar, en dos bloques", async () => {
  const html = await htmlDeLaRevision({
    seguras: [unaPropuesta()],
    paraMirar: [
      unaPropuesta({
        clave: "zz",
        nombre: "Agricola Penaranda",
        segura: false,
        motivo: "se_parecen",
        motivo_texto: "«Agricola Penaranda» y «Agrícola Peñaranda» se parecen, pero no son iguales.",
      }),
    ],
    resumenTexto: "Se te proponen 1 ficha, con 1 nombre escrito.",
  });
  assert.match(html, /Se pueden apuntar/);
  assert.match(html, /Estos los tienes que mirar tú/);
  assert.match(html, /Se te proponen 1 ficha, con 1 nombre escrito/);
});

test("**lo que se puede apuntar lleva su botón, y lo que se parece NO**", async () => {
  // **La prueba más importante de este fichero.** Un botón de apuntar en una propuesta que «se parece»
  // sería la forma de fusionar a un proveedor con su hermano de un toque, y eso no se puede deshacer.
  const html = await htmlDeLaRevision({
    seguras: [unaPropuesta({ clave: "segura1" })],
    paraMirar: [
      unaPropuesta({ clave: "dudosa1", segura: false, motivo: "se_parecen" }),
      unaPropuesta({ clave: "dudosa2", segura: false, motivo: "el_mismo_nombre_dos_nif" }),
    ],
  });
  const claves = [...html.matchAll(/data-accion="contacto-migracion-apuntar"[^>]*data-clave="([^"]+)"/g)].map(
    (encontrado) => encontrado[1],
  );
  assert.deepEqual(claves, ["segura1"], "se puede apuntar una propuesta que no está asegurada");
  // Y la de «apuntarlas todas» solo sale cuando hay alguna que se puede apuntar.
  assert.ok(accionesDe(html).includes("contacto-migracion-todas"));
  const sinSeguras = await htmlDeLaRevision({
    paraMirar: [unaPropuesta({ segura: false, motivo: "se_parecen" })],
  });
  assert.ok(
    !accionesDe(sinSeguras).includes("contacto-migracion-apuntar"),
    "hay un botón de apuntar en una revisión sin nada asegurado",
  );
  assert.ok(
    !accionesDe(sinSeguras).includes("contacto-migracion-todas"),
    "se ofrece apuntarlas todas cuando no hay ninguna que se pueda apuntar",
  );
});

test("los cuatro motivos se leen, cada uno con lo que le hace falta", async () => {
  const html = await htmlDeLaRevision({
    seguras: [
      unaPropuesta({ clave: "a", motivo_texto: "Está escrito igual en todas partes" }),
      unaPropuesta({ clave: "b", motivo_texto: "Tienen el mismo NIF, así que son la misma empresa" }),
    ],
    paraMirar: [
      unaPropuesta({
        clave: "c",
        segura: false,
        motivo_texto: "«Cooperativa X» y «Cooperativa X S.L.» se parecen, pero no son iguales.",
      }),
      unaPropuesta({
        clave: "d",
        segura: false,
        motivo_texto: "El nombre es el mismo, pero el NIF no.",
        nifs_texto: "Los NIF de esos papeles son 12345678Z, 87654321X.",
      }),
    ],
  });
  assert.match(html, /Está escrito igual en todas partes/);
  assert.match(html, /Tienen el mismo NIF/);
  assert.match(html, /«Cooperativa X» y «Cooperativa X S\.L\.» se parecen/);
  assert.match(html, /Los NIF de esos papeles son 12345678Z, 87654321X/);
});

test("se dice que no se ha apuntado nada todavía, y que no se toca ni una letra", async () => {
  const html = await htmlDeLaRevision({ seguras: [unaPropuesta()] });
  assert.match(html, /No he apuntado nada todavía/);
  assert.match(html, /no cambia ni una letra de tus papeles/);
});

test("el aviso de que no se junta solo dice también qué sí se puede hacer", async () => {
  const html = await htmlDeLaRevision({
    paraMirar: [unaPropuesta({ segura: false, motivo: "se_parecen" })],
  });
  assert.match(html, /El programa no los junta solo, y no es un fallo/);
  assert.ok(
    accionesDe(html).includes("contacto-nuevo"),
    "el aviso de que no se juntan deja al agricultor sin saber qué hacer",
  );
});

test("sin nada que proponer se dice, y sin nada que deshacer no se ofrece deshacer", async () => {
  const html = await htmlDeLaRevision();
  assert.match(html, /No hay ningún nombre escrito sin dueño/);
  assert.ok(!accionesDe(html).includes("contacto-migracion-deshacer"));
  const conAlgo = await htmlDeLaRevision({ seguras: [unaPropuesta()], sePuedeDeshacer: true });
  assert.ok(accionesDe(conAlgo).includes("contacto-migracion-deshacer"));
  assert.match(conAlgo, /Las que hayas corregido tú se quedan/);
});

test("lo que ya estaba enlazado se cuenta, y lo apuntado y lo deshecho se dicen", async () => {
  const html = await htmlDeLaRevision({
    hayYaEnlazados: true,
    yaEnlazadosTexto: "Ya tenías 3 nombres enlazados, y esos no salen aquí.",
    apuntado: "Apuntadas 2 fichas, con 5 nombres enlazados. Ni una letra de tus papeles se ha tocado.",
  });
  assert.match(html, /Ya tenías 3 nombres enlazados/);
  assert.match(html, /Apuntadas 2 fichas, con 5 nombres enlazados/);
  const deshecho = await htmlDeLaRevision({
    deshecho: "Deshecho: 2 fichas quitadas y 5 enlaces deshechos. Tus papeles siguen igual.",
  });
  assert.match(deshecho, /Deshecho: 2 fichas quitadas y 5 enlaces deshechos/);
});

test("los nombres escritos de una propuesta se enseñan con lo que dicen los papeles", async () => {
  const html = await htmlDeLaRevision({
    seguras: [
      unaPropuesta({
        escritos: [
          {
            claveTarjeta: "f1",
            texto: "COOPERATIVA AGRÍCOLA DE PEÑARANDA",
            rotulo: "Una factura · 2026/00124 · 13/03/2026",
            filas: [],
            avisos: [],
          },
        ],
      }),
    ],
  });
  assert.match(html, /Así está escrito en tus papeles:/);
  assert.match(html, /COOPERATIVA AGRÍCOLA DE PEÑARANDA/);
  assert.match(html, /Una factura · 2026\/00124/);
});

// ---------------------------------------------------------------------------
// Ni una frase escrita a mano
// ---------------------------------------------------------------------------

test("las cuatro pantallas usan los textos del servidor y no frases propias", async () => {
  const delServidor = new Set(todosLosTextos(TEXTOS));
  for (const texto of [...delServidor]) {
    // Los huecos que `app.js` rellena con datos no cambian la frase: se aceptan las frases que salen de
    // meterle dentro lo que hay escrito.
    delServidor.add(texto.replace(/\{[a-z_]+\}/g, "3"));
    delServidor.add(texto.replace(/\{[a-z_]+\}/g, "Cooperativa X"));
    delServidor.add(texto.replace(/\{[a-z_]+\}/g, "B34123456"));
  }
  // Lo que la pantalla recibe ya montado (lo prepara `app.js` con textos del servidor) y lo que son
  // datos, no frases.
  const permitidas = new Set([
    "Cooperativa Agrícola de Peñaranda",
    "B34123456",
    "923 000 000",
    "La coop",
    "Una factura · 2026/00123 · 12/03/2026",
    "Quien te vende el producto · Quien te compra la cosecha",
    "Según lo que tienes apuntado, también sería: Quien te vende el producto",
    "Ojo: en ese papel ahora pone lo siguiente: Transportes López.",
    "«Agricola Penaranda» y «Agrícola Peñaranda» se parecen, pero no son iguales.",
    "«Cooperativa X» y «Cooperativa X S.L.» se parecen, pero no son iguales.",
    "Los NIF de esos papeles son 12345678Z, 87654321X.",
    "Está escrito igual en todas partes",
    "Tienen el mismo NIF, así que son la misma empresa",
    "El nombre es el mismo, pero el NIF no.",
    "Se te proponen 1 ficha, con 1 nombre escrito.",
    "Hay 1 nombre escrito.",
    "Apuntadas 2 fichas, con 5 nombres enlazados. Ni una letra de tus papeles se ha tocado.",
    "Deshecho: 2 fichas quitadas y 5 enlaces deshechos. Tus papeles siguen igual.",
    "Ya tenías 3 nombres enlazados, y esos no salen aquí.",
    "COOP. AGRICOLA DE PEÑARANDA",
    "COOPERATIVA AGRÍCOLA DE PEÑARANDA",
    "Transportes López",
    "anulada",
    "·",
  ]);
  const pantallas = [
    await htmlDeLosContactos({
      tarjetas: [
        {
          id: 3,
          etiqueta: "Cooperativa Agrícola de Peñaranda",
          rotulo: "Quien te vende el producto · Quien te compra la cosecha",
          lineas: ["Cooperativa Agrícola de Peñaranda"],
          filas: [{ etiqueta: "Su NIF o su CIF", valor: "B34123456" }],
          avisos: [],
        },
      ],
      resumen: "Tienes 1 ficha apuntada.",
      buscado: "coop",
    }),
    await htmlDeUnContacto({
      corrigiendo: true,
      borrador: {
        id: 3,
        nombre: "La coop",
        papeles: ["proveedor"],
        papeles_segun_lo_escrito_texto:
          "Según lo que tienes apuntado, también sería: Quien te vende el producto",
      },
      vivos: [
        {
          id: 11,
          origen: "migracion",
          escrito: { texto: "COOP. AGRICOLA DE PEÑARANDA" },
          rotulo: "Una factura · 2026/00123 · 12/03/2026",
          aviso: "Ojo: en ese papel ahora pone lo siguiente: Transportes López.",
        },
      ],
    }),
    await htmlDeLosNombresEscritos({
      escritos: [unEscrito(), unEscrito({ avisos: ["anulada"] })],
      resumen: "Hay 1 nombre escrito.",
      buscado: "coop",
    }),
    await htmlDeLaRevision({
      seguras: [unaPropuesta()],
      paraMirar: [
        unaPropuesta({
          clave: "zz",
          segura: false,
          motivo: "se_parecen",
          motivo_texto: "«Agricola Penaranda» y «Agrícola Peñaranda» se parecen, pero no son iguales.",
        }),
        unaPropuesta({
          clave: "yy",
          segura: false,
          motivo: "el_mismo_nombre_dos_nif",
          motivo_texto: "El nombre es el mismo, pero el NIF no.",
          nifs_texto: "Los NIF de esos papeles son 12345678Z, 87654321X.",
        }),
      ],
      resumenTexto: "Se te proponen 1 ficha, con 1 nombre escrito.",
      hayYaEnlazados: true,
      yaEnlazadosTexto: "Ya tenías 3 nombres enlazados, y esos no salen aquí.",
      sePuedeDeshacer: true,
      apuntado: "Apuntadas 2 fichas, con 5 nombres enlazados. Ni una letra de tus papeles se ha tocado.",
    }),
  ];
  for (const html of pantallas) {
    for (const frase of frasesVisibles(html)) {
      assert.ok(
        delServidor.has(frase) || permitidas.has(frase),
        `frase escrita a mano en una pantalla de contactos: «${frase}»`,
      );
    }
  }
});

test("los textos de la copia son los que pide la aplicación", async () => {
  // Si alguien renombra una clave en `app.js` y no aquí (o al revés), la pantalla sale con un hueco y
  // ninguna prueba se entera. Esta es la comprobación mínima; la de verdad, clave por clave contra el
  // servidor, está en `tests/test_contactos.py`.
  const claves = [
    "titulo",
    "explica",
    "vacia",
    "cuantas",
    "cuantas_una",
    "anadir",
    "traer_los_nombres",
    "volver_al_inicio",
    "ficha_titulo",
    "ficha_titulo_corregir",
    "donde_aparece",
    "sin_enlaces",
    "enlazar",
    "quitar_enlace",
    "escritos_titulo",
    "escritos_vacio",
    "revision_titulo",
    "revision_seguras",
    "revision_mirar",
    "revision_apuntar",
    "revision_apuntar_todas",
    "revision_deshacer",
    "papeles",
  ];
  for (const clave of claves) {
    assert.ok(TEXTOS.contactos[clave], `a la copia le falta la clave ${clave}`);
  }
  assert.equal(Object.keys(TEXTOS.contactos.papeles).length, PAPELES.length);
});

// ===========================================================================
// Los botones, pulsados de verdad (defecto 2 de la revisión independiente)
//
// **POR QUÉ ESTA SECCIÓN EXISTE, CON EL FALLO QUE LA TRAJO.** Hasta aquí, las 32 pruebas de este
// fichero **pintaban** las pantallas con `renderToStaticMarkup` y leían los `data-accion` del HTML. Eso
// comprueba que la pantalla se dibuja; **no comprueba que el botón haga nada**. Y en este programa
// todos los clics los atiende **un manejador delegado** de `app.js` que lee `data-accion`: un botón
// cuya acción no llegue al manejador **se pinta, se pulsa y no pasa nada**, sin ningún error. Es
// exactamente lo que en el T10 escondió el botón «SEMBRAR ESTA SEMILLA», que no pintaba ninguna
// pantalla, y solo se encontró porque una prueba lo pulsaba.
//
// Aquí se hace lo mismo que allí: se arranca **la aplicación de verdad** (`web/app.js`) con un DOM y un
// servidor de mentira, y se pulsa contra el manejador. Lo que se mira no es lo que se pinta: es **lo que
// sale por la puerta** (la petición que llega al servidor con sus datos) y en qué pantalla acaba.
//
// El arnés es **una copia reducida** del de `tests_js/interfaz.test.js` —un DOM con los nodos que
// `app.js` busca, `localStorage` con el vale puesto y un `fetch` que apunta lo que se manda—, copiada y
// no importada a propósito: importar aquel fichero **registraría sus 300 pruebas dos veces** dentro de
// esta ejecución. Lo que se comparte de verdad —el apuntador de montajes— sí se importa.
// ===========================================================================

/** Los nodos que `app.js` busca al arrancar, y nada más. */
function crearNodo(id = "") {
  const clases = new Set();
  return {
    id,
    innerHTML: "",
    textContent: "",
    className: "",
    dataset: {},
    value: "",
    classList: {
      add: (c) => clases.add(c),
      remove: (c) => clases.delete(c),
      contains: (c) => clases.has(c),
      toggle: () => {},
    },
    appendChild() {},
    remove() {},
    click() {},
  };
}

function montarEntorno() {
  const nodos = new Map();
  for (const id of ["pantalla", "aviso-pendientes", "cabecera-texto", "pie", "marco"]) {
    nodos.set(id, crearNodo(id));
  }
  const almacen = new Map();
  almacen.set("cuedigital.token", "token-de-prueba");
  const manejadores = {};
  const entorno = {
    nodos,
    manejadores,
    document: {
      getElementById: (id) => nodos.get(id) || null,
      createElement: () => crearNodo(),
      addEventListener: (tipo, manejador) => {
        manejadores[tipo] = manejador;
      },
      body: crearNodo("body"),
    },
    window: {
      addEventListener: (tipo, manejador) => {
        manejadores[tipo] = manejador;
      },
      scrollTo() {},
      confirm: () => true,
      location: { hash: "" },
      history: {
        pushState(_e, _t, url) {
          entorno.window.location.hash = url;
        },
        replaceState(_e, _t, url) {
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
  return entorno;
}

/** Una respuesta que dice que no, como la del servidor de verdad (`{detail: …}` y su estado). */
function falla(detalle, estado = 400) {
  return { FALLA: { detail: detalle }, ESTADO: estado };
}

/**
 * El servidor de mentira: apunta lo que se le pide y contesta lo que dice la tabla.
 *
 * `retener` es la lista de rutas cuyas respuestas se quedan **en el aire** hasta que la prueba las
 * suelta con `suelta()`: es la única forma de probar de verdad el doble toque (el segundo toque con la
 * primera petición todavía sin contestar), que es cuando el botón se deshabilita.
 */
function montarServidor(respuestas = {}, { retener = [] } = {}) {
  const llamadasConMetodo = [];
  const enviados = [];
  const pendientes = [];
  const fetchFalso = (ruta, opciones = {}) => {
    const metodo = (opciones.method || "GET").toUpperCase();
    llamadasConMetodo.push(`${metodo} ${ruta}`);
    let enviado = null;
    if (typeof opciones.body === "string" && opciones.body) {
      try {
        enviado = JSON.parse(opciones.body);
      } catch (error) {
        enviado = opciones.body;
      }
    }
    enviados.push({ metodo, ruta, cuerpo: enviado });
    const conMetodo = respuestas[`${metodo} ${ruta}`];
    const crudo =
      conMetodo !== undefined ? conMetodo : respuestas[ruta] !== undefined ? respuestas[ruta] : [];
    const contestar = () => {
      if (crudo && typeof crudo === "object" && "FALLA" in crudo) {
        return {
          ok: false,
          status: crudo.ESTADO || 400,
          headers: { get: () => "application/json" },
          json: async () => crudo.FALLA,
          text: async () => JSON.stringify(crudo.FALLA),
          blob: async () => ({ size: 0 }),
        };
      }
      return {
        ok: crudo !== undefined,
        status: crudo !== undefined ? 200 : 404,
        headers: { get: () => "application/json" },
        json: async () => crudo,
        text: async () => JSON.stringify(crudo),
        blob: async () => ({ size: 0 }),
      };
    };
    if (!retener.includes(`${metodo} ${ruta}`)) return Promise.resolve(contestar());
    return new Promise((resolver) => pendientes.push(() => resolver(contestar())));
  };
  const suelta = () => {
    const enElAire = pendientes.splice(0, pendientes.length);
    for (const resolver of enElAire) resolver();
  };
  return { fetchFalso, llamadasConMetodo, enviados, suelta };
}

/** Arranca la aplicación de verdad (`web/app.js`) con el DOM y el servidor de mentira. */
async function arrancarCon(respuestas = {}, { retener = [] } = {}) {
  const entorno = montarEntorno();
  const servidor = montarServidor(respuestas, { retener });
  const definir = (nombre, valor) =>
    Object.defineProperty(globalThis, nombre, { value: valor, configurable: true, writable: true });
  definir("document", entorno.document);
  definir("window", entorno.window);
  definir("navigator", entorno.navigator);
  definir("URL", entorno.URL);
  definir("fetch", servidor.fetchFalso);
  definir("localStorage", entorno.window.localStorage);
  await import(`../web/app.js?contactos=${Math.random()}`);
  await new Promise((resolver) => setTimeout(resolver, 80));
  return { entorno, servidor };
}

/**
 * Pulsa un botón **por el mismo camino que un dedo**: el manejador delegado que lee `data-accion`.
 *
 * `elemento.dataset` es lo que el manejador lee (`data-id`, `data-papel`, `data-tabla`, `data-clave`…),
 * y `closest` devuelve el propio elemento porque en la aplicación el clic se busca desde el objetivo
 * hacia arriba.
 */
async function pulsar(entorno, accion, datos = {}) {
  const elemento = { dataset: { accion, ...datos } };
  elemento.closest = () => elemento;
  await entorno.manejadores.click({ target: { closest: () => elemento } });
  await new Promise((resolver) => setTimeout(resolver, 40));
}

/** Escribe en una casilla del formulario, como lo haría el agricultor con el teclado. */
function escribir(entorno, id, valor) {
  const nodo = entorno.nodos.get(id) || { id, value: "" };
  nodo.value = valor;
  entorno.nodos.set(id, nodo);
}

/** La última pantalla que se le ha pedido a React. */
function ultimoMontaje() {
  return montajes[montajes.length - 1].elemento;
}

/** Cuántas veces se ha llamado a una ruta con un método (`"POST /api/…"`). */
function cuantasVeces(servidor, metodoYRuta) {
  return servidor.llamadasConMetodo.filter((una) => una === metodoYRuta).length;
}

/** Lo que se ha mandado a una ruta (la última vez). */
function loMandado(servidor, ruta, metodo = "POST") {
  const deEsa = servidor.enviados.filter((uno) => uno.metodo === metodo && uno.ruta === ruta);
  return deEsa[deEsa.length - 1];
}

/** Un contacto como lo devuelve la API. */
function unContacto(cambios = {}) {
  return {
    id: 4,
    nombre: "Cooperativa Agrícola de Peñaranda",
    es_empresa: true,
    nif: "B34123456",
    telefono: null,
    correo: null,
    direccion: null,
    localidad: null,
    notas: null,
    origen: "a_mano",
    papeles: ["proveedor"],
    papeles_segun_lo_escrito: [],
    enlaces: 0,
    nombres_escritos: [],
    ...cambios,
  };
}

/** Un nombre escrito, como lo devuelve `GET /api/contactos/escritos`. */
function unEscritoDeLaApi(cambios = {}) {
  return {
    tabla: "facturas",
    campo: "proveedor",
    registro_id: 1,
    texto: "Cooperativa Agrícola de Peñaranda",
    nif: "B34123456",
    papel: "proveedor",
    clave: "facturas",
    referencia: ["2026/00123"],
    fecha: "2026-03-12",
    anulada: false,
    enlace_id: null,
    contacto_id: null,
    texto_cambiado: false,
    texto_de_entonces: null,
    ...cambios,
  };
}

/** La ficha de un contacto con sus vínculos. */
function unaFicha(cambios = {}) {
  return {
    ...unContacto(),
    vivos: [],
    ...cambios,
  };
}

/** Las respuestas que `app.js` necesita para arrancar, más lo que use cada prueba. */
function lasRespuestasDeArranque(cambios = {}) {
  return {
    "/api/interfaz": {
      contactos: TEXTOS.contactos,
      papeles_de_un_contacto: PAPELES,
      mensajes: MENSAJES,
      acciones: {},
      aviso: {},
      etiquetas: {},
      rotulos: {},
      menu: {},
      marco: {},
      unidades: [],
    },
    "/api/campanas/actual": { id: 1, anio: 2026 },
    "/api/parcelas": [],
    "/api/contactos": [],
    "/api/contactos/escritos?sin_enlazar=true": [],
    ...cambios,
  };
}

// ---------------------------------------------------------------------------
// La lista y el alta
// ---------------------------------------------------------------------------

test("AÑADIR UNA FICHA abre el formulario y GUARDAR manda lo que se ha escrito", async () => {
  const { entorno, servidor } = await arrancarCon(
    lasRespuestasDeArranque({ "POST /api/contactos": unContacto() }),
  );
  await pulsar(entorno, "contactos-ver");
  assert.equal(ultimoMontaje().type.name, "PantallaDeLosContactos");

  await pulsar(entorno, "contacto-nuevo");
  assert.equal(ultimoMontaje().type.name, "PantallaDeUnContacto", "no se abre la ficha nueva");

  escribir(entorno, "contacto-nombre", "Cooperativa Agrícola de Peñaranda");
  escribir(entorno, "contacto-nif", "B34123456");
  escribir(entorno, "contacto-es-empresa", "si");
  escribir(entorno, "contacto-telefono", "923 000 000");
  await pulsar(entorno, "contacto-guardar");

  assert.equal(cuantasVeces(servidor, "POST /api/contactos"), 1, "el botón no manda la ficha");
  const cuerpo = loMandado(servidor, "/api/contactos").cuerpo;
  assert.equal(cuerpo.nombre, "Cooperativa Agrícola de Peñaranda");
  assert.equal(cuerpo.nif, "B34123456");
  assert.equal(cuerpo.es_empresa, true, "«es una empresa» no llega como verdadero");
  assert.equal(cuerpo.telefono, "923 000 000");
});

test("lo que no se contesta se queda en «no lo sé», no en «no»", async () => {
  const { entorno, servidor } = await arrancarCon(
    lasRespuestasDeArranque({ "POST /api/contactos": unContacto() }),
  );
  await pulsar(entorno, "contactos-ver");
  await pulsar(entorno, "contacto-nuevo");
  escribir(entorno, "contacto-nombre", "Hermanos Pérez");
  // La casilla se deja como viene: «no lo sé».
  await pulsar(entorno, "contacto-guardar");

  const cuerpo = loMandado(servidor, "/api/contactos").cuerpo;
  assert.equal(cuerpo.es_empresa, null, "«no lo sé» se está mandando como «es una persona»");
  assert.equal(cuerpo.nif, "", "un hueco se manda como texto vacío y el servidor lo guarda como nada");
});

test("sin nombre no se molesta al servidor y se dice qué falta", async () => {
  const { entorno, servidor } = await arrancarCon(lasRespuestasDeArranque());
  await pulsar(entorno, "contactos-ver");
  await pulsar(entorno, "contacto-nuevo");
  await pulsar(entorno, "contacto-guardar");

  assert.equal(cuantasVeces(servidor, "POST /api/contactos"), 0, "se ha mandado una ficha sin nombre");
  assert.equal(
    ultimoMontaje().props.error,
    MENSAJES.C7_un_contacto_necesita_nombre,
    "no se dice qué falta",
  );
});

test("abrir una ficha la pide al servidor y GUARDAR manda un PUT con el teléfono nuevo", async () => {
  // **Corregir y dar de alta son el mismo formulario**, y lo que cambia es el método: un `POST` a la
  // dirección de una ficha no es una corrección, es otra ficha.
  const { entorno, servidor } = await arrancarCon(
    lasRespuestasDeArranque({
      "/api/contactos/4": unaFicha(),
      "PUT /api/contactos/4": unaFicha({ telefono: "923 000 000" }),
    }),
  );
  await pulsar(entorno, "contactos-ver");
  await pulsar(entorno, "contacto-abrir", { id: 4 });

  assert.equal(cuantasVeces(servidor, "GET /api/contactos/4"), 1, "no se pide la ficha");
  assert.equal(ultimoMontaje().type.name, "PantallaDeUnContacto");
  assert.equal(ultimoMontaje().props.corrigiendo, true, "no se está corrigiendo");

  // El nombre hay que escribirlo también al corregir: el formulario es el mismo, y en este DOM de
  // mentira no hay ningún navegador que rellene el valor inicial de la casilla.
  escribir(entorno, "contacto-nombre", "Cooperativa Agrícola de Peñaranda");
  escribir(entorno, "contacto-telefono", "923 000 000");
  await pulsar(entorno, "contacto-guardar");

  assert.equal(cuantasVeces(servidor, "PUT /api/contactos/4"), 1, "la corrección no se manda");
  assert.equal(cuantasVeces(servidor, "POST /api/contactos"), 0, "una corrección se ha mandado como alta");
  assert.equal(loMandado(servidor, "/api/contactos/4", "PUT").cuerpo.telefono, "923 000 000");
});

test("marcar un papel lo manda al servidor con el papel y si se pone o se quita", async () => {
  const { entorno, servidor } = await arrancarCon(
    lasRespuestasDeArranque({
      "/api/contactos/4": unaFicha(),
      "POST /api/contactos/4/papeles": unaFicha({ papeles: ["proveedor", "comprador"] }),
    }),
  );
  await pulsar(entorno, "contactos-ver");
  await pulsar(entorno, "contacto-abrir", { id: 4 });
  await pulsar(entorno, "contacto-papel", { papel: "comprador", puesto: "1" });

  assert.equal(cuantasVeces(servidor, "POST /api/contactos/4/papeles"), 1, "el papel no se manda");
  const cuerpo = loMandado(servidor, "/api/contactos/4/papeles").cuerpo;
  assert.deepEqual(cuerpo, { papel: "comprador", puesto: true });

  // Y desmarcarlo manda lo contrario.
  await pulsar(entorno, "contacto-papel", { papel: "comprador", puesto: "0" });
  assert.deepEqual(loMandado(servidor, "/api/contactos/4/papeles").cuerpo, {
    papel: "comprador",
    puesto: false,
  });
});

// ---------------------------------------------------------------------------
// Los enlaces
// ---------------------------------------------------------------------------

test("ENLAZAR UN NOMBRE abre la lista de nombres escritos y ENLAZAR manda dónde está el texto", async () => {
  const { entorno, servidor } = await arrancarCon(
    lasRespuestasDeArranque({
      "/api/contactos/4": unaFicha(),
      "/api/contactos/escritos?sin_enlazar=true": [unEscritoDeLaApi()],
      "POST /api/contactos/4/enlaces": unaFicha({
        enlaces: 1,
        nombres_escritos: ["Cooperativa Agrícola de Peñaranda"],
      }),
    }),
  );
  await pulsar(entorno, "contactos-ver");
  await pulsar(entorno, "contacto-abrir", { id: 4 });
  await pulsar(entorno, "contacto-enlazar-abrir");

  assert.equal(
    cuantasVeces(servidor, "GET /api/contactos/escritos?sin_enlazar=true"),
    1,
    "no se piden los nombres escritos que están sin dueño",
  );
  assert.equal(ultimoMontaje().type.name, "PantallaDeLosNombresEscritos");

  await pulsar(entorno, "contacto-enlazar", {
    tabla: "facturas",
    campo: "proveedor",
    registro: 1,
  });
  assert.equal(cuantasVeces(servidor, "POST /api/contactos/4/enlaces"), 1, "el enlace no se manda");
  assert.deepEqual(loMandado(servidor, "/api/contactos/4/enlaces").cuerpo, {
    tabla: "facturas",
    campo: "proveedor",
    registro_id: 1,
  });
  // **Y no se manda el texto**: el servidor lee lo que dice el papel, no lo que diga el navegador.
  assert.equal(
    Object.prototype.hasOwnProperty.call(loMandado(servidor, "/api/contactos/4/enlaces").cuerpo, "texto"),
    false,
    "el navegador está mandando el nombre que se va a guardar",
  );
});

test("QUITAR EL ENLACE manda el borrado con el identificador del vínculo", async () => {
  const { entorno, servidor } = await arrancarCon(
    lasRespuestasDeArranque({
      "/api/contactos/4": unaFicha({
        enlaces: 1,
        vivos: [{ id: 11, origen: "a_mano", escrito: unEscritoDeLaApi({ enlace_id: 11, contacto_id: 4 }) }],
      }),
      "DELETE /api/contactos/4/enlaces/11": unaFicha(),
    }),
  );
  await pulsar(entorno, "contactos-ver");
  await pulsar(entorno, "contacto-abrir", { id: 4 });
  assert.equal(ultimoMontaje().props.vivos.length, 1, "la ficha no enseña su vínculo");

  await pulsar(entorno, "contacto-desenlazar", { id: 11 });
  assert.equal(
    cuantasVeces(servidor, "DELETE /api/contactos/4/enlaces/11"),
    1,
    "el botón de quitar el enlace no manda nada",
  );
  assert.equal(loMandado(servidor, "/api/contactos/4/enlaces/11", "DELETE").cuerpo, null);
});

// ---------------------------------------------------------------------------
// Borrar: la confirmación primero, la llamada después
// ---------------------------------------------------------------------------

test("BORRAR no llama al servidor hasta que se confirma", async () => {
  const { entorno, servidor } = await arrancarCon(
    lasRespuestasDeArranque({
      "/api/contactos/4": unaFicha(),
      "DELETE /api/contactos/4": { hecho: true, textos_tocados: 0 },
    }),
  );
  await pulsar(entorno, "contactos-ver");
  await pulsar(entorno, "contacto-abrir", { id: 4 });

  await pulsar(entorno, "contacto-borrar");
  assert.equal(cuantasVeces(servidor, "DELETE /api/contactos/4"), 0, "se ha borrado sin preguntar");
  assert.equal(ultimoMontaje().props.borrando, true, "no se pide confirmación");

  await pulsar(entorno, "contacto-borrar-si", { id: 4 });
  assert.equal(cuantasVeces(servidor, "DELETE /api/contactos/4"), 1, "la confirmación no borra nada");
  assert.equal(ultimoMontaje().type.name, "PantallaDeLosContactos", "después de borrar no se vuelve a la lista");
});

test("decir «MEJOR NO» deja la ficha como estaba y no llama al servidor", async () => {
  const { entorno, servidor } = await arrancarCon(
    lasRespuestasDeArranque({ "/api/contactos/4": unaFicha() }),
  );
  await pulsar(entorno, "contactos-ver");
  await pulsar(entorno, "contacto-abrir", { id: 4 });
  await pulsar(entorno, "contacto-borrar");
  await pulsar(entorno, "contacto-borrar-no");

  assert.equal(cuantasVeces(servidor, "DELETE /api/contactos/4"), 0);
  assert.equal(ultimoMontaje().props.borrando, false, "la confirmación se queda puesta");
});

// ---------------------------------------------------------------------------
// La revisión: apuntar, apuntarlas todas y deshacer
// ---------------------------------------------------------------------------

/** La propuesta que contesta el servidor: una segura y una que hay que mirar. */
function laRevisionDeVerdad() {
  return {
    resumen: { fichas: 1, nombres: 1, se_parecen: 1, homonimos: 0, nif_con_nombres_distintos: 0 },
    propuestas: [
      {
        clave: "segura1",
        nombre: "Cooperativa Agrícola de Peñaranda",
        segura: true,
        motivo: "el_mismo_nombre",
        papeles: ["proveedor"],
        nombres: ["Cooperativa Agrícola de Peñaranda"],
        nifs: [],
        pareja: [],
        escritos: [unEscritoDeLaApi()],
      },
      {
        clave: "dudosa1",
        nombre: "Cooperativa Agricola de Penaranda",
        segura: false,
        motivo: "se_parecen",
        papeles: ["proveedor"],
        nombres: ["Agricola Penaranda", "Agrícola Peñaranda"],
        nifs: [],
        pareja: ["Agricola Penaranda", "Agrícola Peñaranda"],
        escritos: [unEscritoDeLaApi({ registro_id: 2, texto: "Agricola Penaranda" })],
      },
    ],
    ya_enlazados: 0,
    total_escritos: 2,
    se_puede_deshacer: true,
  };
}

test("APUNTAR ESTA FICHA manda la clave de esa propuesta", async () => {
  const { entorno, servidor } = await arrancarCon(
    lasRespuestasDeArranque({
      "/api/contactos/migracion": laRevisionDeVerdad(),
      "POST /api/contactos/migracion/aplicar": {
        fichas: 1,
        enlaces: 1,
        textos_tocados: 0,
        nombres: ["Cooperativa Agrícola de Peñaranda"],
        avisos: [],
        contactos: [4],
      },
    }),
  );
  await pulsar(entorno, "contactos-ver");
  await pulsar(entorno, "contactos-revisar-abrir");
  assert.equal(ultimoMontaje().type.name, "PantallaDeLaRevisionDeLosNombres");

  await pulsar(entorno, "contacto-migracion-apuntar", { clave: "segura1" });
  assert.equal(cuantasVeces(servidor, "POST /api/contactos/migracion/aplicar"), 1, "el botón no apunta nada");
  assert.deepEqual(loMandado(servidor, "/api/contactos/migracion/aplicar").cuerpo, {
    claves: ["segura1"],
  });
});

test("APUNTARLAS TODAS manda las seguras y **ninguna de las que hay que mirar**", async () => {
  // Es la comprobación que de verdad importa de estos dos botones: que la lista que se manda no lleve
  // ni una propuesta que el programa no puede asegurar.
  const { entorno, servidor } = await arrancarCon(
    lasRespuestasDeArranque({
      "/api/contactos/migracion": laRevisionDeVerdad(),
      "POST /api/contactos/migracion/aplicar": {
        fichas: 1,
        enlaces: 1,
        textos_tocados: 0,
        nombres: ["Cooperativa Agrícola de Peñaranda"],
        avisos: [],
        contactos: [4],
      },
    }),
  );
  await pulsar(entorno, "contactos-ver");
  await pulsar(entorno, "contactos-revisar-abrir");
  await pulsar(entorno, "contacto-migracion-todas");

  const cuerpo = loMandado(servidor, "/api/contactos/migracion/aplicar").cuerpo;
  assert.deepEqual(cuerpo.claves, ["segura1"]);
  assert.ok(!cuerpo.claves.includes("dudosa1"), "se está mandando una propuesta que no está asegurada");
});

test("DESHACER ESTO manda el deshacer y enseña lo que se ha quedado", async () => {
  const { entorno, servidor } = await arrancarCon(
    lasRespuestasDeArranque({
      "/api/contactos/migracion": laRevisionDeVerdad(),
      "POST /api/contactos/migracion/deshacer": {
        fichas: 1,
        enlaces: 2,
        se_quedan: ["Cooperativa X no se ha quitado: la has corregido o le has enlazado algo tú, así que es tuya."],
        textos_tocados: 0,
      },
    }),
  );
  await pulsar(entorno, "contactos-ver");
  await pulsar(entorno, "contactos-revisar-abrir");
  await pulsar(entorno, "contacto-migracion-deshacer");

  assert.equal(cuantasVeces(servidor, "POST /api/contactos/migracion/deshacer"), 1, "no se deshace nada");
  // Y lo que **no** se ha quitado se dice, con su motivo: callarlo haría creer que se ha deshecho todo.
  assert.match(ultimoMontaje().props.aviso, /no se ha quitado/);
  assert.match(ultimoMontaje().props.deshecho, /1 fichas quitadas/);
});

test("desde la lista se llega a la revisión, y el buscador filtra por lo escrito", async () => {
  const { entorno, servidor } = await arrancarCon(
    lasRespuestasDeArranque({
      "/api/contactos/migracion": laRevisionDeVerdad(),
      "/api/contactos?q=coop": [unContacto()],
    }),
  );
  await pulsar(entorno, "contactos-ver");
  await pulsar(entorno, "contactos-revisar-abrir");
  assert.equal(cuantasVeces(servidor, "GET /api/contactos/migracion"), 1, "no se pide la propuesta");
  assert.equal(ultimoMontaje().type.name, "PantallaDeLaRevisionDeLosNombres");

  await pulsar(entorno, "contactos-ver");
  escribir(entorno, "contacto-buscar", "coop");
  await pulsar(entorno, "contactos-buscar");
  assert.equal(cuantasVeces(servidor, "GET /api/contactos?q=coop"), 1, "el buscador no filtra por el nombre");
  assert.equal(ultimoMontaje().props.buscado, "coop", "el buscador pierde lo que se ha escrito");
});

// ---------------------------------------------------------------------------
// El doble toque: el botón se apaga mientras la petición está en el aire
// ---------------------------------------------------------------------------

test("mientras se apunta, los botones de apuntar están apagados (defecto 3)", async () => {
  // El camino de verdad: el agricultor pulsa con guantes y el móvil tarda. Sin el botón apagado, la
  // misma confirmación sale dos veces. El servidor ahora la contesta sin duplicar y devolviendo su
  // resultado, pero el botón no debe invitar a mandarla dos veces.
  const { entorno, servidor } = await arrancarCon(
    lasRespuestasDeArranque({
      "/api/contactos/migracion": laRevisionDeVerdad(),
      "POST /api/contactos/migracion/aplicar": {
        fichas: 1,
        enlaces: 1,
        textos_tocados: 0,
        nombres: ["Cooperativa Agrícola de Peñaranda"],
        avisos: [],
        contactos: [4],
      },
    }),
    { retener: ["POST /api/contactos/migracion/aplicar"] },
  );
  await pulsar(entorno, "contactos-ver");
  await pulsar(entorno, "contactos-revisar-abrir");
  assert.equal(ultimoMontaje().props.enviando, false);

  const enElAire = pulsar(entorno, "contacto-migracion-apuntar", { clave: "segura1" });
  await new Promise((resolver) => setTimeout(resolver, 20));
  assert.equal(
    ultimoMontaje().props.enviando,
    true,
    "la pantalla no dice que la petición está en el aire: el botón se puede volver a pulsar",
  );

  servidor.suelta();
  await enElAire;
  assert.equal(ultimoMontaje().props.enviando, false, "el botón se queda apagado para siempre");
});

test("el botón de apuntar sale apagado en el HTML mientras se envía", async () => {
  // La mitad que se ve: el `disabled` de verdad, comprobado sobre el HTML del componente.
  const html = await htmlDeLaRevision({
    seguras: [unaPropuestaPipeline()],
    enviando: true,
  });
  assert.match(html, /data-accion="contacto-migracion-apuntar"[^>]*disabled/, "el botón sigue pulsable");
  assert.match(html, /data-accion="contacto-migracion-todas"[^>]*disabled/, "el de apuntarlas todas también");
  const sinEnviar = await htmlDeLaRevision({ seguras: [unaPropuestaPipeline()] });
  assert.ok(
    !/data-accion="contacto-migracion-apuntar"[^>]*disabled/.test(sinEnviar),
    "el botón sale apagado sin haber nada en el aire",
  );
});

/** Una propuesta ya preparada, para la prueba del botón apagado. */
function unaPropuestaPipeline() {
  return unaPropuesta({ clave: "segura1" });
}

test("la lista de contactos, en el ordenador, va en tabla con sus columnas", async () => {
  // **La tabla del ordenador de la lista de contactos** (11/10/2026). Medido en el navegador, esa pantalla
  // pintaba **20 tarjetas de 92 px** y ninguna columna, donde un programa de gestión enseña filas de 45. Esto
  // lo deja escrito: si alguien la quita, se entera.
  //
  // Y se comprueba lo que costó tres intentos: que la tabla **se monta con las tarjetas que la pantalla ya
  // recibe**, no con una propiedad que se le pase desde fuera —la que se montaba en `app.js` no llegaba,
  // porque esta pantalla se repinta con los datos de la caché del campo—.
  const html = await htmlDeLosContactos({
    tarjetas: [
      {
        id: 1,
        etiqueta: "Cooperativa Agrícola de Peñaranda",
        rotulo: "Proveedor, Cliente",
        lineas: [],
        avisos: [],
        filas: [
          { etiqueta: TEXTOS.nif, valor: "B09123456" },
          { etiqueta: TEXTOS.telefono, valor: "947 123 456" },
        ],
      },
    ],
  });
  // **Se pregunta por la ETIQUETA `<table>`**, no por la clase (11/10/2026): la primera version preguntaba
  // por `class="tabla"` y **esa cadena aparece en esa pantalla por otro sitio**, asi que la prueba pasaba
  // aunque la tabla no estuviera. Se supo rompiendo la tabla a proposito y viendo que la prueba **no** se
  // ponia roja; la de cobros si se puso. Una prueba que no puede fallar no es una prueba.
  assert.ok(
    // **Se pregunta por SU contenedor** (`solo-escritorio tabla-scroll`), que es lo unico que solo
  // tiene la tabla nueva (11/10/2026): las tarjetas **tambien** llevan dentro una `<table class="tabla">`
  // para sus filas de datos, asi que preguntar por eso daba verde aunque la tabla no estuviera. Se supo
  // rompiendo la tabla a proposito y viendo que la prueba **no** se ponia roja.
    html.includes('data-tabla="contactos"'),
    `la lista de contactos no va en tabla:\n${html}`,
  );
  assert.ok(html.includes("solo-escritorio"), "la tabla tiene que ir en la parte de escritorio");
  assert.ok(html.includes("Cooperativa Agrícola de Peñaranda"), "la fila lleva el nombre");
  assert.ok(html.includes("B09123456"), "y el NIF, que viene de las filas de la tarjeta");
  assert.ok(html.includes("947 123 456"), "y el teléfono");
  assert.ok(
    html.includes("contacto-abrir"),
    "y el nombre es un botón que abre la ficha: en una tabla no se toca la fila entera",
  );
});

// ===========================================================================
// El diario de la ficha: las notas, con su autor y su fecha (CRM-03, criterio (f))
//
// **POR QUÉ ESTA SECCIÓN EXISTE.** La ficha tiene, desde el 13/10/2026, un diario: debajo de sus datos se
// leen las notas que se le han ido apuntando —de la más nueva a la más vieja, con quién la escribió y
// cuándo— y hay un campo con su botón para apuntar otra. Hasta hoy, ninguna de las 48 pruebas de este
// fichero miraba nada de eso: se podía cambiar el nombre de la acción, la ruta o el estado del autor y no
// se enteraba nadie. Lo pidió la revisión del dueño: **escribir, guardar, recargar, comprobar autor y
// fecha, y conservar el texto si falla el envío**.
//
// Lo que se comprueba, y por qué esas cosas:
//
//   1. **Lo que se ve**: dos notas con sus textos, el nombre de quien las escribió y su fecha. Y los
//      **tres estados del autor** —una persona con nombre, una persona **cuyo nombre ya no está** y el
//      programa— tienen que verse distintos: decirle «lo apuntó el programa» a una nota que escribió una
//      persona cuyo nombre ya no se puede poner es afirmar algo que no se sabe (por eso son tres estados y
//      no dos, desde la revisión del 13/10/2026).
//   2. **Que el botón mande la acción de verdad**: el texto escrito y su `clave_de_reenvio` llegan a
//      `POST /api/contactos/{id}/notas`, y después la ficha se recarga para que la nota salga con su autor
//      y su fecha. El **autor no viaja**: lo pone el servidor de su vale, porque aceptarlo del navegador
//      sería poder firmar cosas que no ha escrito uno.
//   3. **Que reintentar reutilice la clave**: es lo que protege del doble toque y del móvil sin cobertura
//      (dos pulsaciones de la misma nota son **una** acción, no dos notas).
//   4. **Que lo escrito no se pierda si el envío falla.**
// ===========================================================================

/** Una nota como la devuelve el servidor, dentro de `notas_con_autor` de la ficha. */
function unaNota(cambios = {}) {
  return {
    id: 21,
    texto: "Pasa los martes por la mañana.",
    autor: "Marta",
    autor_estado: "persona",
    creado_en: "2026-10-13T09:12:00",
    clave_de_reenvio: null,
    ...cambios,
  };
}

/**
 * El campo de escribir la nota, tal y como sale en el HTML, para poder mirarle el `value`.
 *
 * Se mira así —y no con un `includes` suelto— porque el `value` que hay que leer es el de **ese** campo:
 * buscarlo en toda la página daría verde aunque el texto estuviera en otro sitio.
 */
function elCampoDeLaNota(html) {
  const campo = html.match(/<input[^>]*id="contacto-nota-texto"[^>]*>/);
  assert.ok(campo, `la ficha no tiene campo para escribir la nota:\n${html}`);
  return campo[0];
}

test("la ficha enseña sus notas con el autor y la fecha, y los tres autores se ven distintos", async () => {
  // **Sin esto, el diario no sirve para acordarse de nada**: una nota sin quién la escribió ni cuándo es un
  // texto suelto. Y los tres estados del autor tienen que distinguirse, porque el caso raro —una persona
  // cuyo nombre ya no está— es justo el que antes se contaba mal.
  const html = await htmlDeUnContacto({
    corrigiendo: true,
    borrador: {
      id: 3,
      notas_con_autor: [
        unaNota(),
        unaNota({
          id: 22,
          texto: "El del pienso le subió el precio en marzo.",
          creado_en: "2026-10-02T08:00:00",
        }),
      ],
    },
  });
  assert.match(html, /Pasa los martes por la mañana\./, "no se lee el texto de la nota");
  assert.match(html, /El del pienso le subió el precio en marzo\./, "falta una de las dos notas");
  assert.match(html, /La escribió: Marta/, "no se lee quién la escribió");
  assert.match(html, /2026-10-13/, "no se lee cuándo se escribió la nota");
  // El campo para apuntar otra, con su botón: es la puerta que las otras tres pruebas pulsan. Y sale **vacío**:
  // el texto de una nota que ya está apuntada no se cuela en la casilla de la siguiente.
  assert.ok(accionesDe(html).includes("contacto-nota"), "no hay botón para apuntar una nota");
  assert.ok(
    !elCampoDeLaNota(html).includes('value="Pasa los martes'),
    "el campo de escribir la nota trae el texto de una nota ya apuntada",
  );

  // Los tres estados del autor, cada uno con lo que se sabe. **El `sin_nombre` se mira también solo**, porque
  // lo que hay que comprobar de él es lo que **no** dice: que no se le eche la culpa al programa.
  const losTres = await htmlDeUnContacto({
    corrigiendo: true,
    borrador: {
      id: 3,
      notas_con_autor: [
        unaNota({ id: 31, texto: "Me lo dijo Marta.", autor: "Marta", autor_estado: "persona" }),
        unaNota({
          id: 32,
          texto: "Se lo oí a alguien que ya no está en la casa.",
          autor: null,
          autor_estado: "sin_nombre",
        }),
        unaNota({
          id: 33,
          texto: "Lo apuntó el programa al traer los papeles.",
          autor: null,
          autor_estado: "el_programa",
        }),
      ],
    },
  });
  assert.match(losTres, /La escribió: Marta/, "no se lee el nombre de quien la escribió");
  assert.match(
    losTres,
    /La escribió: alguien cuyo nombre ya no está/,
    "no se dice que la escribió una persona cuyo nombre ya no está",
  );
  assert.match(losTres, /Lo apuntó el programa/, "no se dice que esa la apuntó el programa");

  const soloSinNombre = await htmlDeUnContacto({
    corrigiendo: true,
    borrador: {
      id: 3,
      notas_con_autor: [
        unaNota({
          id: 32,
          texto: "Se lo oí a alguien que ya no está en la casa.",
          autor: null,
          autor_estado: "sin_nombre",
        }),
      ],
    },
  });
  assert.ok(
    soloSinNombre.includes(TEXTOS.contactos.nota_autor_sin_nombre),
    "una nota de una persona sin nombre no dice que el nombre ya no está",
  );
  assert.ok(
    !soloSinNombre.includes(TEXTOS.contactos.nota_lo_escribio_el_programa),
    "una nota de una persona cuyo nombre ya no está se está diciendo que la apuntó el programa",
  );

  // Y una ficha sin ninguna nota lo dice, en vez de dejar un hueco que parezca un fallo.
  const sinNotas = await htmlDeUnContacto({ corrigiendo: true, borrador: { id: 3 } });
  assert.match(sinNotas, /Todavía no hay ninguna nota\./, "una ficha sin notas no lo dice");
});

test("APUNTAR LA NOTA manda el texto y su clave de reenvío, y recarga la ficha con la nota", async () => {
  // Lo que hace que la nota llegue al diario: se escribe, se pulsa y **se manda**. Y después la ficha se
  // vuelve a leer, que es lo que hace que la nota salga con su autor y su fecha (si no se recargara, la
  // pantalla seguiría enseñando el diario de antes).
  const respuestas = lasRespuestasDeArranque({
    "/api/contactos/4": unaFicha({ notas_con_autor: [] }),
    "POST /api/contactos/4/notas": unaFicha({ notas_con_autor: [unaNota()] }),
  });
  const { entorno, servidor } = await arrancarCon(respuestas);
  await pulsar(entorno, "contactos-ver");
  await pulsar(entorno, "contacto-abrir", { id: 4 });
  assert.equal(
    ultimoMontaje().props.borrador.notas_con_autor.length,
    0,
    "la ficha tiene notas antes de apuntar ninguna",
  );
  // **El servidor apunta la nota al recibirla**, así que la ficha que se lee después ya la trae: se cambia
  // aquí para que el servidor de mentira se comporte como el de verdad (el de la tabla se lee en cada
  // llamada, no se copia al arrancar). Lo que se comprueba es que la pantalla **vuelve a leer** la ficha.
  respuestas["/api/contactos/4"] = unaFicha({ notas_con_autor: [unaNota()] });
  escribir(entorno, "contacto-nota-texto", "Pasa los martes por la mañana.");
  await pulsar(entorno, "contacto-nota", { id: "4" });

  assert.equal(cuantasVeces(servidor, "POST /api/contactos/4/notas"), 1, "el botón no manda la nota");
  const cuerpo = loMandado(servidor, "/api/contactos/4/notas").cuerpo;
  assert.equal(cuerpo.texto, "Pasa los martes por la mañana.", "el texto escrito no viaja");
  assert.ok(
    typeof cuerpo.clave_de_reenvio === "string" && cuerpo.clave_de_reenvio.length > 0,
    "la nota viaja sin clave de reenvío: un reintento apuntaría la nota dos veces",
  );
  assert.equal(
    Object.prototype.hasOwnProperty.call(cuerpo, "autor"),
    false,
    "el navegador está firmando la nota: el autor lo pone el servidor",
  );

  // Y la nota vuelve a la pantalla, con lo que la hace útil: quién y cuándo.
  assert.equal(
    cuantasVeces(servidor, "GET /api/contactos/4"),
    2,
    "después de apuntar la nota no se recarga la ficha: la nota no saldría",
  );
  const notas = ultimoMontaje().props.borrador.notas_con_autor;
  assert.equal(notas.length, 1, "la nota recién apuntada no sale en la ficha");
  assert.equal(notas[0].texto, "Pasa los martes por la mañana.");
  assert.equal(notas[0].autor, "Marta", "la nota vuelve sin su autor");
});

test("reintentar la misma nota reutiliza la clave de reenvío, también cuando la primera ha fallado", async () => {
  // **La clave es de la ACCIÓN, no del clic** (13/10/2026, revisión), y esto es lo que protege del doble
  // toque y del móvil sin cobertura: dos pulsaciones de la misma nota son **una** acción, así que las dos
  // llamadas llevan la misma clave y el servidor reconoce la segunda y no apunta otra nota. Se prueba de las
  // dos formas que pasan de verdad: con la primera todavía en el aire (el doble toque) y con la primera
  // contestando que no (el reintento después de un fallo).
  const primero = await arrancarCon(
    lasRespuestasDeArranque({
      "/api/contactos/4": unaFicha({ notas_con_autor: [] }),
      "POST /api/contactos/4/notas": unaFicha({ notas_con_autor: [unaNota()] }),
    }),
    // La respuesta se queda en el aire: es la única forma de que el segundo toque llegue antes que la
    // primera contestación, que es cuando el doble clic pasa de verdad.
    { retener: ["POST /api/contactos/4/notas"] },
  );
  await pulsar(primero.entorno, "contactos-ver");
  await pulsar(primero.entorno, "contacto-abrir", { id: 4 });
  escribir(primero.entorno, "contacto-nota-texto", "Pasa los martes por la mañana.");
  const elDeSiempre = pulsar(primero.entorno, "contacto-nota", { id: "4" });
  const elDeLosGuantes = pulsar(primero.entorno, "contacto-nota", { id: "4" });
  await new Promise((resolver) => setTimeout(resolver, 20));
  primero.servidor.suelta();
  await Promise.all([elDeSiempre, elDeLosGuantes]);

  const lasDelDobleToque = primero.servidor.enviados
    .filter((uno) => uno.metodo === "POST" && uno.ruta === "/api/contactos/4/notas")
    .map((uno) => uno.cuerpo.clave_de_reenvio);
  assert.equal(lasDelDobleToque.length, 2, "los dos toques tienen que llegar al servidor");
  assert.ok(lasDelDobleToque[0], "el primer envío no lleva clave de reenvío");
  assert.equal(
    lasDelDobleToque[1],
    lasDelDobleToque[0],
    "el segundo toque trae una clave nueva: apuntaría la nota dos veces",
  );

  // Y ahora el reintento de verdad: la primera contesta que no (sin cobertura, el servidor de mal humor…).
  const segundo = await arrancarCon(
    lasRespuestasDeArranque({
      "/api/contactos/4": unaFicha({ notas_con_autor: [] }),
      "POST /api/contactos/4/notas": falla("No se ha podido guardar la nota."),
    }),
  );
  await pulsar(segundo.entorno, "contactos-ver");
  await pulsar(segundo.entorno, "contacto-abrir", { id: 4 });
  escribir(segundo.entorno, "contacto-nota-texto", "Pasa los martes por la mañana.");
  await pulsar(segundo.entorno, "contacto-nota", { id: "4" });
  await pulsar(segundo.entorno, "contacto-nota", { id: "4" });

  const lasDelReintento = segundo.servidor.enviados
    .filter((uno) => uno.metodo === "POST" && uno.ruta === "/api/contactos/4/notas")
    .map((uno) => uno.cuerpo.clave_de_reenvio);
  assert.equal(lasDelReintento.length, 2, "el reintento no vuelve a intentarlo");
  assert.ok(lasDelReintento[1], "el reintento no lleva clave de reenvío");
  assert.equal(
    lasDelReintento[1],
    lasDelReintento[0],
    "el reintento trae una clave nueva: apuntaría la nota dos veces",
  );
});

test("lo escrito sigue estando si el envío de la nota falla", async () => {
  // **Lo que la revisión pidió comprobar**: si el envío falla —un móvil sin cobertura, el servidor de mal
  // humor— el agricultor **no puede perder lo escrito**, porque lo escribió con guantes y volver a teclearlo
  // es exactamente lo que este programa no puede pedirle. Se mira por los dos lados que se pueden mirar hoy:
  //
  //   · **Por el camino de verdad**: se escribe, se hace fallar el POST, se pulsa, y el texto sigue ahí —el
  //     reintento lo vuelve a mandar entero, que es lo que solo puede pasar si no se ha borrado—.
  //   · **En la pantalla**: una ficha repintada con lo que se quedó a medias (`nota_a_medias`, que es donde
  //     `app.js` lo deja) lo lleva al campo, en vez de salir vacía.
  //
  // **HUECO CONOCIDO, Y SE DICE EN VEZ DE TAPARLO** (13/10/2026). `apuntarLaNota` (`web/app.js`) guarda el
  // texto en `suyo.nota_a_medias`, pero `pantallaFichaDeContacto` **no lo mete en el `borrador` que le pasa a
  // la pantalla**: el estado se guarda y no se usa, así que de punta a punta ese texto no llega al campo (solo
  // se salva lo que el agricultor ya tenía escrito en la casilla del navegador). Por eso la comprobación de la
  // pantalla se hace aquí sobre el componente, que sí lo pinta, y **no** sobre los `props` del último montaje.
  // El día que se cablee, esta prueba tiene que cerrar el círculo con
  // `assert.equal(ultimoMontaje().props.borrador.nota_a_medias, texto)`.
  const texto = "Pasa los martes por la mañana.";
  const { entorno, servidor } = await arrancarCon(
    lasRespuestasDeArranque({
      "/api/contactos/4": unaFicha({ notas_con_autor: [] }),
      "POST /api/contactos/4/notas": falla("No se ha podido guardar la nota."),
    }),
  );
  await pulsar(entorno, "contactos-ver");
  await pulsar(entorno, "contacto-abrir", { id: 4 });
  escribir(entorno, "contacto-nota-texto", texto);
  await pulsar(entorno, "contacto-nota", { id: "4" });

  assert.equal(
    cuantasVeces(servidor, "POST /api/contactos/4/notas"),
    1,
    "no se ha intentado guardar la nota",
  );
  assert.equal(
    ultimoMontaje().props.error,
    "No se ha podido guardar la nota.",
    "no se dice que la nota no se ha podido guardar",
  );

  await pulsar(entorno, "contacto-nota", { id: "4" });
  assert.equal(
    cuantasVeces(servidor, "POST /api/contactos/4/notas"),
    2,
    "el texto se ha perdido: el reintento no manda nada",
  );
  assert.equal(loMandado(servidor, "/api/contactos/4/notas").cuerpo.texto, texto);

  // La mitad que se ve: el campo lleva lo que se quedó a medias… y **no** lo lleva cuando nadie lo ha escrito.
  // Las dos direcciones, porque una prueba que solo mira el `includes` da verde aunque el campo pinte de más.
  const html = await htmlDeUnContacto({ corrigiendo: true, borrador: { id: 4, nota_a_medias: texto } });
  assert.ok(
    elCampoDeLaNota(html).includes(`value="${texto}"`),
    `la ficha repintada deja el campo vacío y se pierde lo escrito:\n${html}`,
  );
  const sinNada = await htmlDeUnContacto({ corrigiendo: true, borrador: { id: 4 } });
  assert.ok(
    !elCampoDeLaNota(sinNada).includes(`value="${texto}"`),
    "el campo de la nota sale con un texto que no ha escrito nadie",
  );

  // **Y el círculo cerrado de punta a punta** (13/10/2026): lo que el agricultor escribió tiene que **llegar
  // hasta la pantalla**, no quedarse en el estado. Esta aserción estaba escrita aquí esperando a que se cableara
  // `nota_a_medias` en el `borrador` de la ficha, y **daba `undefined`** —lo encontró el subagente de pruebas
  // ejecutándola—. Ahora ya se cableó, así que se exige: si vuelve a faltar, esta prueba se pone roja.
  assert.equal(
    ultimoMontaje().props.borrador.nota_a_medias,
    texto,
    "lo escrito no llega a la pantalla: se queda en el estado y el agricultor lo pierde",
  );
});

// ===========================================================================
// El conflicto de reenvío: la misma clave con OTRO texto (revisión del dueño, 13/10/2026)
//
// **POR QUÉ ESTA SECCIÓN EXISTE.** La clave de reenvío protege del doble toque, pero **no es la acción
// entera**: una acción es *esta nota, en este contacto, con este texto*. Si la clave se reutilizara sin
// mirar el texto, el agricultor escribiría «Preguntar por el abono», la respuesta se perdería (sin
// cobertura), le añadiría «y por el gasóleo» y volvería a pulsar… y el servidor contestaría «ya está»
// **sin haber guardado nunca la nota**: su texto nuevo desaparecería en silencio. Por eso la puerta
// contesta **409** cuando la clave ya se usó con otro texto o en otro contacto, y por eso el front, ante
// ese 409, **conserva el borrador y renueva la clave**, para que lo escrito se pueda apuntar como nota
// nueva. Las dos mitades del acuerdo se vigilan aquí: la del servidor, en Python
// (`tests/test_las_notas_de_un_contacto.py`).
// ===========================================================================

/** Los envíos que han ido a la puerta de las notas de una ficha, en orden. */
function losEnviosDeLaNota(servidor, id = 4) {
  return servidor.enviados.filter(
    (uno) => uno.metodo === "POST" && uno.ruta === `/api/contactos/${id}/notas`,
  );
}

test("un 409 conserva lo escrito, lo explica y renueva la clave de la acción", async () => {
  // **El momento que la revisión pidió cerrar.** La clave ya se usó, pero **con otro texto**: el servidor
  // contesta **409** en vez de dar por guardado algo que no se guardó. Lo que se mira aquí es lo que tiene
  // que hacer la pantalla con ese «no»: (a) **no perder lo escrito** —lo que el agricultor tecleó con
  // guantes no se puede quedar por el camino— y (b) **renovar la clave**, porque si el reintento llevara la
  // clave vieja el servidor volvería a contestar 409 y el texto se quedaría atrapado: no se apuntaría nunca.
  const texto = "Preguntar por el abono";
  const explicacion = "Esta acción ya se había guardado, pero con otro texto.";
  const { entorno, servidor } = await arrancarCon(
    lasRespuestasDeArranque({
      "/api/contactos/4": unaFicha({ notas_con_autor: [] }),
      "POST /api/contactos/4/notas": falla(explicacion, 409),
    }),
  );
  await pulsar(entorno, "contactos-ver");
  await pulsar(entorno, "contacto-abrir", { id: 4 });
  escribir(entorno, "contacto-nota-texto", texto);
  await pulsar(entorno, "contacto-nota", { id: "4" });

  // (a) **Lo escrito sigue ahí**, y no se calla lo que ha pasado: el agricultor lee por qué.
  assert.equal(
    ultimoMontaje().props.borrador.nota_a_medias,
    texto,
    "el 409 se lleva por delante lo escrito: el agricultor tendría que teclearlo otra vez, con guantes",
  );
  const html = globalThis.ReactDOMServer.renderToStaticMarkup(ultimoMontaje());
  assert.ok(
    elCampoDeLaNota(html).includes(`value="${texto}"`),
    `la ficha repintada deja el campo de la nota vacío después del 409:\n${html}`,
  );
  assert.equal(
    ultimoMontaje().props.error,
    explicacion,
    "no se lee lo que ha contestado el servidor: el agricultor no sabe que no se ha guardado nada",
  );

  // (b) **Y la acción se renueva**: la segunda pulsación ya no es el reenvío de la primera (que el servidor
  // rechazó), así que tiene que viajar con una clave **distinta**. Es lo que permite que su texto no se
  // pierda: con la clave vieja, cada reintento chocaría otra vez contra el 409.
  await pulsar(entorno, "contacto-nota", { id: "4" });
  const envios = losEnviosDeLaNota(servidor);
  assert.equal(envios.length, 2, "el reintento después del 409 no ha llegado al servidor");
  const primera = envios[0].cuerpo.clave_de_reenvio;
  const segunda = envios[1].cuerpo.clave_de_reenvio;
  assert.ok(primera && segunda, "alguna de las dos llamadas viaja sin clave de reenvío");
  assert.notEqual(
    segunda,
    primera,
    "el reintento reutiliza la clave del 409: el servidor volvería a contestar 409 y el texto no se apuntaría nunca",
  );
  assert.equal(
    envios[1].cuerpo.texto,
    texto,
    "el reintento manda otra cosa que lo que hay en el campo de la nota",
  );
});

test("la respuesta perdida y la edición después: el reintento lleva la misma clave y lo editado", async () => {
  // **La otra cara del mismo acuerdo**, y por eso va pegada a la de arriba: allí el servidor dice «no lo he
  // guardado» (409) y la clave se renueva; aquí **no lo dice** —la respuesta se pierde, el móvil se quedó
  // sin cobertura con la petición ya mandada— y por eso la clave **se conserva**: la nota puede estar
  // guardada en el servidor, y la misma acción no se apunta dos veces. El agricultor **edita** entonces lo
  // que había escrito y vuelve a pulsar, así que se comprueban los dos momentos: **respuesta perdida →
  // edición → reintento**, con la misma clave y con **lo editado** en el cuerpo, que es el texto que tiene
  // delante.
  const primero = "Preguntar por el abono";
  const editado = "Preguntar por el abono y por el gasóleo";
  const { entorno, servidor } = await arrancarCon(
    lasRespuestasDeArranque({
      "/api/contactos/4": unaFicha({ notas_con_autor: [] }),
      "POST /api/contactos/4/notas": falla("No se ha podido guardar la nota."),
    }),
  );
  await pulsar(entorno, "contactos-ver");
  await pulsar(entorno, "contacto-abrir", { id: 4 });

  escribir(entorno, "contacto-nota-texto", primero);
  await pulsar(entorno, "contacto-nota", { id: "4" });
  assert.equal(
    ultimoMontaje().props.borrador.nota_a_medias,
    primero,
    "la respuesta perdida se lleva el borrador: no quedaría nada que editar",
  );

  // El agricultor le añade lo del gasóleo, con lo de antes delante, y vuelve a pulsar.
  escribir(entorno, "contacto-nota-texto", editado);
  await pulsar(entorno, "contacto-nota", { id: "4" });

  const envios = losEnviosDeLaNota(servidor);
  assert.equal(envios.length, 2, "el reintento después de editar no ha llegado al servidor");
  assert.equal(envios[0].cuerpo.texto, primero, "la primera llamada no llevaba lo que se había escrito");
  assert.equal(envios[1].cuerpo.texto, editado, "se manda lo de antes en vez de lo editado");
  assert.equal(
    envios[1].cuerpo.clave_de_reenvio,
    envios[0].cuerpo.clave_de_reenvio,
    "la respuesta perdida pudo haber guardado la nota: el reintento tiene que llevar la MISMA clave o la apuntaría dos veces",
  );
});

// ---------------------------------------------------------------------------
// El saldo del contacto (Entrega 1, 13/10/2026)
// ---------------------------------------------------------------------------

function unSaldo(cambios = {}) {
  return {
    contacto_id: 4,
    moneda: "EUR",
    nos_debe: {
      total: "810.00",
      total_texto: "810,00 €",
      documentos: [
        {
          clase: "factura_emitida",
          id: 1,
          referencia: "F-2026-1",
          fecha: "2026-07-10",
          importe: "1210",
          importe_texto: "1.210,00 €",
          cobrado: "400",
          cobrado_texto: "400,00 €",
          pendiente: "810",
          pendiente_texto: "810,00 €",
          exceso: null,
        },
      ],
      sin_importe: 0,
    },
    le_debemos: {
      total: "450.00",
      total_texto: "450,00 €",
      documentos: [
        {
          clase: "gasto",
          id: 9,
          referencia: "Abono",
          fecha: "2026-06-01",
          importe: "600",
          importe_texto: "600,00 €",
          pagado: "150",
          pagado_texto: "150,00 €",
          pendiente: "450",
          pendiente_texto: "450,00 €",
          exceso: null,
        },
      ],
      sin_importe: 0,
    },
    sin_asignar: { cobros: [], pagos: [], nota: "sin_asignar_no_es_un_anticipo" },
    para_revisar: [],
    cobertura: {
      se_adjudica_por: "contacto_id",
      no_se_adjudica_por_nombre: true,
      hay_facturas_de_compra_sin_contacto: false,
      nota: "las_facturas_de_compra_sin_gasto_con_contacto_no_entran_en_ningun_saldo",
    },
    ...cambios,
  };
}

test("el saldo va en la ficha con los dos sentidos SEPARADOS y sus documentos", async () => {
  // Lo que exige el encargo: **810 y 450 separadas** (no 360) y **cada cifra abre lo que la explica**.
  const html = await htmlDeUnContacto({ corrigiendo: true, borrador: { id: 4 }, saldo: unSaldo() });
  assert.ok(html.includes("810,00 €"), `no se ve lo que nos debe:\n${html}`);
  assert.ok(html.includes("450,00 €"), `no se ve lo que le debemos:\n${html}`);
  assert.ok(!html.includes("360,00 €"), "las dos deudas no se restan: eso escondería las dos");
  // Los documentos, con su fecha, su importe y lo que queda.
  assert.ok(html.includes("F-2026-1"), "la cifra tiene que abrir su factura");
  assert.ok(html.includes("Abono"), "y la suya su gasto");
  assert.ok(html.includes("1.210,00 €") && html.includes("400,00 €"), "con su importe y lo cobrado");
  // Y el enlace lleva **solo adonde hay pantalla**: el gasto tiene la suya.
  assert.ok(html.includes("#/cuentas/9"), `el gasto tiene que llevar a su ficha:\n${html}`);
});

test("un importe que no se sabe se dice con palabras, nunca con un cero", async () => {
  // La regla de la casa: un importe que no consta se enseña con la palabra que lo dice. Un `0,00 €` afirmaría que
  // el papel pone cero, que es justo lo contrario de «no se sabe».
  const html = await htmlDeUnContacto({
    corrigiendo: true,
    borrador: { id: 4 },
    saldo: unSaldo({
      le_debemos: {
        total: "0",
        total_texto: "0,00 €",
        documentos: [
          {
            clase: "gasto",
            id: 11,
            referencia: "Reparación sin factura",
            fecha: "2026-06-01",
            importe: null,
            importe_texto: "No se sabe cuánto",
            pagado: "0",
            pagado_texto: "0,00 €",
            pendiente: null,
            pendiente_texto: "No se sabe cuánto",
            exceso: null,
          },
        ],
        sin_importe: 1,
      },
    }),
  });
  assert.ok(html.includes("No se sabe cuánto"), `tiene que decirlo con palabras:\n${html}`);
  assert.ok(html.includes("Reparación sin factura"), "y el documento tiene que aparecer para revisarlo");
});

test("sin saldo, la ficha se sigue viendo y el bloque del saldo no aparece", async () => {
  // **Y esto importa**: el saldo es un agregado de dinero, y un agregado que falla **no puede** impedir ver los
  // datos del contacto. Con `saldo: null` la ficha se pinta entera y el bloque no está.
  const html = await htmlDeUnContacto({ corrigiendo: true, borrador: { id: 4 }, saldo: null });
  assert.ok(html.includes("contacto-nombre"), `la ficha tiene que seguir pintándose:\n${html}`);
  assert.ok(!html.includes(TEXTOS.saldo_titulo), "y el bloque del saldo, sin datos, no se enseña");
});
