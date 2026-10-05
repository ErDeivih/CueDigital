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
 */
export const montajes = [];

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
 * **Cada vez que se llama se crea una raíz nueva.** Se probó a guardar la raíz y reutilizarla
 * (que es lo normal en una aplicación entera de React) y aquí no vale: la interfaz vieja sigue
 * pintando las pantallas que no se han migrado con `pintar()`, que hace `innerHTML = …` sobre
 * este mismo contenedor. Con la raíz guardada, React seguiría creyendo que su pantalla está
 * puesta, no la volvería a dibujar y el agricultor vería la pantalla anterior. Con una raíz
 * nueva se vacía el contenedor y se dibuja entero, que es lo que se espera. El precio es que
 * las raíces viejas se quedan por ahí hasta que las recoja el recolector de basura; está
 * apuntado en `docs/REACT.md` como lo que queda por resolver.
 */
export function montarEn(contenedor, elemento, avisoDeEmergencia = {}) {
  const ReactDOM = globalThis.ReactDOM;
  const puedeMontar = Boolean(ReactDOM) && typeof ReactDOM.createRoot === "function";

  if (puedeMontar && elemento) {
    montajes.push({ contenedor, elemento, motor: "react" });
    contenedor.innerHTML = "";
    ReactDOM.createRoot(contenedor).render(elemento);
    return true;
  }

  // Sin ReactDOM (las pruebas) o sin pantalla que montar (los ficheros de React no han
  // llegado): se apunta y se sigue. La aplicación tiene que arrancar igual.
  montajes.push({ contenedor, elemento: elemento || null, motor: "apuntado" });
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
  montajesDelMarco.push({ contenedor, elemento });
  if (!puedeMontar) return false;
  contenedor.innerHTML = "";
  ReactDOM.createRoot(contenedor).render(elemento);
  return true;
}
