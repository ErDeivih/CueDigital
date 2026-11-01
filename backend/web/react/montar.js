/*
 * montar.js — El único sitio de la aplicación que habla con ReactDOM.
 *
 * POR QUÉ ESTÁ APARTE
 *
 * Porque es la frontera. Todo lo que hay dentro de los componentes de `react/` es puro —no
 * toca el DOM, no llama a `fetch`, no lee `localStorage`— y por eso se puede probar sin
 * navegador. Aquí vive la única línea que de verdad necesita un navegador:
 * `ReactDOM.createRoot(contenedor).render(elemento)`.
 *
 * Y POR QUÉ NO REVIENTA CUANDO NO HAY REACTDOM
 *
 * Las pruebas de JavaScript corren sin navegador (no hay `jsdom`, y no se va a meter: es una
 * dependencia que no hace falta). Si esto exigiera ReactDOM para funcionar, las 150 pruebas
 * que ya miran la interfaz no podrían ni arrancar `app.js`. Así que cuando no hay ReactDOM,
 * `montarEn` **apunta lo que se le ha pedido montar y sigue**: la pantalla no se pinta, pero
 * la aplicación arranca y las pruebas pueden comprobar que esa pantalla se le pide a React.
 *
 * Salida de emergencia: si no hay ReactDOM pero sí un navegador de verdad (es decir: el
 * fichero de React no se ha cargado, por ejemplo con la caché del móvil a medias después de
 * un despliegue), se escribe en el contenedor un aviso y un botón de recargar. **Nunca una
 * pantalla en blanco.** Los textos de ese aviso NO se escriben aquí: vienen de `textos.py`
 * (`react.sin_react` y `react.recargar`) por el tercer argumento.
 */

/**
 * Lo que se ha pedido montar, por orden. Lo miran las pruebas.
 *
 * Cada entrada es `{ contenedor, elemento, motor }`, y `motor` dice qué ha pasado de verdad:
 * `"react"` si ReactDOM lo ha montado, y `"apuntado"` si no había ReactDOM y solo se ha
 * apuntado (que es lo que pasa en las pruebas).
 *
 * **Los montajes de verdad no guardan el elemento** (ver `apuntarElMontaje`): las pruebas
 * necesitan el historial entero y corren sin ReactDOM, pero en una jornada de trabajo la
 * pantalla se pide a React cientos de veces y quedarse con cada árbol ya dibujado es una
 * fuga. De esos montajes se recuerdan los últimos `RECUERDO_DE_MONTAJES`, sin el elemento.
 */
export const montajes = [];

/**
 * Cuántos montajes hechos con React se recuerdan en `montajes` para poder mirarlos desde
 * fuera (la auditoría y el medidor de memoria). No es un número de pantallas: es cuánto
 * historial merece la pena conservar sin retener los árboles dibujados.
 */
export const RECUERDO_DE_MONTAJES = 20;

/**
 * Las raíces de React que están puestas, por contenedor.
 *
 * Una raíz por contenedor, no una por montaje. Se probó al revés (una raíz nueva cada vez)
 * cuando la interfaz vieja vaciaba el contenedor con `innerHTML = …`, y esa época se acabó:
 * hoy `montar()` es el único sitio que escribe en la pantalla, y una raíz que se tira sin
 * desmontar se queda con sus nodos, sus efectos y sus referencias hasta que el recolector
 * de basura la encuentra. En una sesión larga eso es una fuga, y el marco se monta en cada
 * cambio de módulo.
 *
 * Es un `Map` (una referencia fuerte) y no un `WeakMap` porque hay que poder recorrerlo para
 * desmontar las raíces cuyo contenedor ya se ha retirado del documento. El número de
 * contenedores es fijo y pequeño (`#pantalla` y `#marco`), y el barrido quita los que se
 * van; no crece con el uso.
 */
const raices = new Map();

/**
 * Cuántas raíces se han creado y desmontado desde que arrancó la página. Lo mira el medidor
 * de memoria y la auditoría: si al recorrer la aplicación `creadas - desmontadas` no se queda
 * en el número de contenedores que hay en el documento, hay una fuga.
 */
export const laCuentaDeLasRaices = { creadas: 0, desmontadas: 0 };

/** Las raíces que siguen puestas ahora mismo. */
export function raicesActivas() {
  return raices.size;
}

/**
 * Lo que se ha pedido montar **fuera de la pantalla**: hoy, el armazón (el menú y la barra de arriba).
 *
 * POR QUÉ ESTÁ APARTE DE `montajes` (30/09/2026). Las pruebas de cableado cuentan **cuántas pantallas** se
 * le piden a React al pulsar un botón (`se han pedido N montajes: solo esta`), y eso es lo que caza que una
 * pantalla se pinte dos veces o que se quede la anterior. El armazón se monta cuando cambia el módulo, no
 * cuando cambia la pantalla, así que si se apuntara en la misma lista estas pruebas empezarían a contar
 * cosas que no son pantallas y dejarían de servir. Va en su propia lista, y también se puede comprobar.
 *
 * Cada entrada es `{ contenedor, elemento }`.
 */
export const montajesDelMarco = [];

/**
 * ¿Hay un DOM de verdad?
 *
 * No vale con mirar que exista `document`: las pruebas montan un DOM de mentira con las
 * cuatro cosas que necesita la interfaz vieja. Un elemento de verdad tiene `nodeType` y sabe
 * insertar hijos; el de mentira, no. Se prueba con un `div` de usar y tirar.
 */
function hayDomDeVerdad() {
  try {
    if (typeof document === "undefined" || !document) return false;
    if (typeof document.createElement !== "function") return false;
    const prueba = document.createElement("div");
    return typeof prueba.nodeType === "number" && typeof prueba.insertBefore === "function";
  } catch (error) {
    // Un DOM a medias no es un DOM: mejor no escribir nada que romper el arranque.
    return false;
  }
}

/**
 * Enseña el aviso de emergencia: qué pasa y el botón para volver a abrir la aplicación.
 *
 * Se construye con las clases de siempre (`.aviso`, `.boton`, `.boton-principal`) y sin
 * `innerHTML`: son textos del servidor, y montarlos con texto crudo es justo lo que React
 * viene a quitarnos de encima.
 */
export function avisoSinReact(contenedor, aviso = {}) {
  if (!hayDomDeVerdad() || !contenedor) return;

  const texto = aviso.sin_react || "";
  const recargar = aviso.recargar || "";

  const caja = document.createElement("div");
  caja.className = "aviso";
  caja.setAttribute("role", "alert");
  const fuerte = document.createElement("strong");
  fuerte.textContent = texto;
  caja.appendChild(fuerte);

  const boton = document.createElement("button");
  boton.type = "button";
  boton.className = "boton boton-principal";
  // Mismo mecanismo que el resto de la aplicación: quien pulsó, qué botón. Aunque este no
  // pasa por el manejador delegado (que no conoce esta acción), se le pone para que se vea
  // de un vistazo qué botón es en las herramientas del navegador.
  boton.setAttribute("data-accion", "recargar");
  boton.textContent = recargar;
  boton.addEventListener("click", () => {
    globalThis.location.reload();
  });

  contenedor.innerHTML = "";
  contenedor.appendChild(caja);
  contenedor.appendChild(boton);
}

/**
 * Monta un elemento de React en un contenedor. Devuelve `true` si lo ha montado de verdad.
 *
 * **Una raíz por contenedor, y se reutiliza.** El contenedor se vacía solo la primera vez,
 * cuando se crea la raíz: a partir de ahí sus hijos son de React, y borrarlos a mano dejaría
 * a la raíz apuntando a unos nodos que ya no están (React intentaría actualizarlos y no
 * encontraría dónde). Si el elemento anterior era otro, `render` lo sustituye entero, que es
 * justo lo que se espera al cambiar de pantalla.
 */
export function montarEn(contenedor, elemento, avisoDeEmergencia = {}) {
  const ReactDOM = globalThis.ReactDOM;
  const puedeMontar = Boolean(ReactDOM) && typeof ReactDOM.createRoot === "function";

  if (puedeMontar && elemento && contenedor) {
    barrerLasRaicesRetiradas();
    montarEnSuRaiz(contenedor, elemento, ReactDOM);
    apuntarElMontaje({ contenedor, elemento: null, motor: "react", ligero: true });
    return true;
  }

  // Sin ReactDOM (las pruebas) o sin pantalla que montar (los ficheros de React no han
  // llegado): se apunta y se sigue. La aplicación tiene que arrancar igual.
  montajes.push({ contenedor, elemento: elemento || null, motor: "apuntado" });
  // Si este contenedor tenía una raíz viva, se retira antes de escribir el aviso a mano:
  // si no, React seguiría creyendo que la pantalla está puesta sobre unos nodos que el
  // aviso acaba de borrar.
  desmontarDe(contenedor);
  avisoSinReact(contenedor, avisoDeEmergencia);
  return false;
}

/**
 * Monta el armazón (el menú y la barra de arriba) fuera del contenedor de las pantallas.
 *
 * **No escribe el aviso de emergencia**: si React no ha llegado, el aviso ya sale dentro de la pantalla, y
 * dos avisos iguales en la misma página sobran. Y si no hay contenedor (una página de prueba que no lo
 * tenga), no hace nada.
 */
export function montarFueraDeLaPantalla(contenedor, elemento) {
  if (!contenedor || !elemento) return false;
  const ReactDOM = globalThis.ReactDOM;
  const puedeMontar = Boolean(ReactDOM) && typeof ReactDOM.createRoot === "function";
  if (!puedeMontar) {
    // Sin ReactDOM (las pruebas) el armazón se apunta con su elemento: hay pruebas de
    // cableado que miran las propiedades que se le pasan.
    montajesDelMarco.push({ contenedor, elemento });
    return false;
  }
  barrerLasRaicesRetiradas();
  montarEnSuRaiz(contenedor, elemento, ReactDOM);
  apuntarElMontaje({ contenedor, elemento: null, motor: "react", ligero: true }, montajesDelMarco);
  return true;
}

/**
 * Monta (o vuelve a dibujar) en la raíz que ya tiene ese contenedor, creándola la primera vez.
 *
 * El vaciado del contenedor ocurre **solo al crear la raíz**. No lleva `innerHTML` de
 * pantallas: es la preparación del contenedor vacío para el primer `render`, que es otra cosa
 * (y la prueba de la migración lo distingue).
 */
function montarEnSuRaiz(contenedor, elemento, ReactDOM) {
  let raiz = raices.get(contenedor);
  if (!raiz) {
    contenedor.innerHTML = "";
    raiz = ReactDOM.createRoot(contenedor);
    raices.set(contenedor, raiz);
    laCuentaDeLasRaices.creadas += 1;
  }
  const renderizar = () => raiz.render(elemento);
  // Quien monta restaura después posición y foco. createRoot.render programa
  // el trabajo: sin confirmar aquí, esos consumidores ven el contenedor vacío.
  if (typeof ReactDOM.flushSync === "function") ReactDOM.flushSync(renderizar);
  else renderizar();
}

/**
 * Retira la raíz de React de un contenedor, si la tiene. Devuelve `true` si había algo que retirar.
 *
 * Se usa antes de escribir en el contenedor por otra vía (el aviso de emergencia) y al vaciar
 * el armazón. Desmontar quita los nodos, los efectos y las referencias; además se olvida la
 * entrada para que el siguiente montaje cree una raíz nueva y limpia.
 */
export function desmontarDe(contenedor) {
  if (!contenedor || !raices.has(contenedor)) return false;
  const raiz = raices.get(contenedor);
  raices.delete(contenedor);
  try {
    const ReactDOM = globalThis.ReactDOM;
    const desmontar = () => raiz.unmount();
    if (ReactDOM && typeof ReactDOM.flushSync === "function") ReactDOM.flushSync(desmontar);
    else desmontar();
  } finally {
    laCuentaDeLasRaices.desmontadas += 1;
  }
  return true;
}

/**
 * Desmonta las raíces cuyo contenedor ya no está en el documento (por ejemplo, el armazón de
 * una página que se ha sustituido entera). Un contenedor de pruebas de mentira no tiene
 * `isConnected`; solo se retira cuando dice **explícitamente** `false`.
 */
function barrerLasRaicesRetiradas() {
  for (const contenedor of raices.keys()) {
    if (contenedor && contenedor.isConnected === false) desmontarDe(contenedor);
  }
}

/**
 * Apunta un montaje para poder mirarlo desde fuera. Los de React van **sin el elemento** y
 * solo se recuerdan los últimos: el árbol ya dibujado lo retiene la raíz, y quedarse además
 * con una copia en una lista que no para de crecer era parte de la fuga.
 */
function apuntarElMontaje(entrada, lista = montajes) {
  lista.push(entrada);
  let ligeros = 0;
  for (const montaje of lista) if (montaje.ligero) ligeros += 1;
  let sobran = ligeros - RECUERDO_DE_MONTAJES;
  for (let i = 0; sobran > 0 && i < lista.length; ) {
    if (lista[i].ligero) {
      lista.splice(i, 1);
      sobran -= 1;
    } else {
      i += 1;
    }
  }
}
