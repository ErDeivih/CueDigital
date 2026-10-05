/*
 * ayuda_de_un_campo.js — La explicación que va debajo de un campo: qué es, para qué sirve, un ejemplo y
 * qué pasa si se deja en blanco.
 *
 * POR QUÉ ES UNA PIEZA
 *
 * Este bloque estaba escrito **cinco veces** dentro de `app.js`, dentro de `ayudaDeCampo()`, y lo
 * pedían casi todos los pasos del asistente que preguntan algo escrito (la fecha, las hectáreas, la
 * dosis, los datos del maestro, los números del boletín). Es el bloque que hace que este programa se
 * pueda usar **sin saber de informática ni de normativa**: en vez de preguntar «plazo de seguridad»
 * pregunta «¿cuántos días hay que esperar para poder coger la cosecha?» y, debajo, explica por qué se
 * pregunta eso.
 *
 * Y hay un motivo de fondo para que sea una pieza y no una cadena de HTML: **los cuatro rótulos van
 * dentro**. Estaban escritos a mano en `app.js` —donde no pasan por la prueba que vigila que no haya
 * jerga— y se vieron justo al empezar a migrar. Ahora llegan del servidor (`textos.py`), los pase
 * quien los pase.
 *
 * El componente es PURO: no llama a `fetch` y no toca el DOM.
 */

import { frase, html } from "../componentes.js";

/**
 * El bloque de ayuda de un campo.
 *
 * Propiedades:
 *
 *  - `datos`: lo que el servidor sabe de ese campo (`titulo`, `que_es`, `por_que`, `ejemplo`,
 *    `si_falta`). **Si no viene, no se dibuja nada**: un hueco con cuatro rótulos y nada dentro es
 *    peor que no tener ayuda.
 *  - `rotulos`: los cuatro rótulos, también del servidor (`que_es`, `por_que`, `ejemplo`, `si_falta`).
 */
export function AyudaDeUnCampo({ datos, rotulos }) {
  if (!datos) return null;
  const r = rotulos || {};
  return html`
    <div className="ayuda-campo">
      <h3>${frase(datos.titulo)}</h3>
      <p><span className="etiqueta-dato">${frase(r.que_es)}</span> ${frase(datos.que_es)}</p>
      <p><span className="etiqueta-dato">${frase(r.por_que)}</span> ${frase(datos.por_que)}</p>
      <p><span className="etiqueta-dato">${frase(r.ejemplo)}</span> ${frase(datos.ejemplo)}</p>
      <p><span className="etiqueta-dato">${frase(r.si_falta)}</span> ${frase(datos.si_falta)}</p>
    </div>
  `;
}

/** El elemento de React de esta ayuda, ya con sus propiedades puestas. */
export function ayudaDeUnCampo(propiedades) {
  return html`<${AyudaDeUnCampo} datos=${propiedades.datos} rotulos=${propiedades.rotulos} />`;
}
