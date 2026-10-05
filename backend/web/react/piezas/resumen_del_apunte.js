/*
 * resumen_del_apunte.js — El resumen del asistente: lo que se va a apuntar, antes de apuntarlo.
 *
 * POR QUÉ ESTA PANTALLA, Y POR QUÉ ES LA PRIMERA DEL ASISTENTE
 *
 * El asistente de apuntar (echar producto, abonar, hacer un trabajo) es lo que más se usa de todo el
 * programa, y su **resumen** es el paso que más se ve: es donde el agricultor repasa antes de dar el
 * visto bueno. Es también el paso que **menos campos lee** (los demás leen lo que se ha escrito en
 * cada pantalla), y por eso es por donde se empieza a migrar el asistente.
 *
 * **Es la primera pieza que NO es una pantalla entera** (por eso vive en `react/piezas/` y no en
 * `react/pantallas/`: la lista de pantallas migradas es la lista de pantallas, y esto es un trozo). El asistente se pinta con `pintar()`
 * (interfaz vieja) y cada paso se dibuja en un hueco: el `<div id="formulario">`. Lo que se ha hecho
 * aquí es dejar que un paso diga `montar` en vez de `pintar`, y que sea **React quien llene ese
 * hueco**. Así el asistente se puede migrar **paso a paso sin tocar su motor** (`pintarAsistente`,
 * `irA`, `normalizaIndice` se quedan donde estaban).
 *
 * LO QUE SE CONSERVA A PROPÓSITO
 *
 *  1. **Un resumen con cinco «—» no ayuda a repasar**: solo salen las filas que tienen dato. Quien
 *     decide qué filas hay es `app.js`, que es quien conoce los datos; aquí no se filtra nada.
 *  2. El **aviso del plazo de espera** va en su bloque aparte, como estaba: es lo que evita que el
 *     agricultor coja la cosecha antes de tiempo.
 *  3. Nada de `esc()` y ninguna frase escrita aquí: los textos llegan por propiedades.
 *
 * El componente es PURO: no llama a `fetch`, no calcula fechas y no toca el DOM.
 */

import { frase, html } from "../componentes.js";

/**
 * El resumen entero.
 *
 * Propiedades:
 *
 *  - `filas`: las filas ya preparadas (`[[etiqueta, valor], …]`), **solo las que tienen dato**.
 *  - `titulo`: un rótulo **encima** de las filas, o nada. Lo usa la pantalla que pregunta si de verdad se
 *    quiere borrar algo: allí lo que se lee es lo que va a desaparecer, y una caja de datos sin título es
 *    una caja de datos (diseño de Stitch de la ronda 92). El resumen del asistente va sin título: la
 *    pregunta de arriba ya dice qué es.
 *  - `pista`: una línea de explicación **antes** de las filas, o nada. La necesita el resumen del plan
 *    de abono, que tiene que decir que los kilos son **por hectárea**: sin eso, los tres números del
 *    plan se pueden leer al revés.
 *  - `espera`: el aviso del plazo de espera (`{ texto, dias }`) o nada. `dias` puede ser vacío
 *    cuando no se puede contar (por ejemplo, si la fecha no es de este año).
 */
export function ResumenDelApunte({ filas = [], titulo = "", pista = "", espera = null }) {
  return html`
    ${titulo ? html`<h2>${frase(titulo)}</h2>` : null}
    ${pista ? html`<p className="pista-campo">${frase(pista)}</p>` : null}
    <dl>
      ${filas.map(
        ([etiqueta, valor], indice) => html`
          <div className="resumen-dato" key=${indice}>
            <dt>${frase(etiqueta)}</dt>
            <dd>${frase(valor)}</dd>
          </div>
        `,
      )}
    </dl>
    ${
      espera
        ? html`<div className="ayuda-campo">
            <p><span className="etiqueta-dato">${frase(espera.texto)}</span></p>
            ${espera.dias ? html`<p>${frase(espera.dias)}</p>` : null}
          </div>`
        : null
    }
  `;
}

/** El elemento de React de este resumen, ya con sus propiedades puestas. */
export function resumenDelApunte(propiedades) {
  return html`
    <${ResumenDelApunte}
      filas=${propiedades.filas}
      titulo=${propiedades.titulo}
      pista=${propiedades.pista}
      espera=${propiedades.espera}
    />
  `;
}
