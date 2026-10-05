/*
 * dictado.js — «Dímelo con la voz», escrito en React.
 *
 * POR QUÉ ESTA PANTALLA
 *
 * Es la decimotercera que se pasa a React, y es la puerta de la aplicación para quien está en el
 * campo con las manos ocupadas: se pulsa el micrófono, se dice lo que se ha hecho y el programa lo
 * convierte en un apunte que hay que revisar antes de guardarlo.
 *
 * **Primera pantalla migrada con un campo de texto largo.** Conserva el patrón que ya usan «mis
 * datos» y «las medidas»: el campo **sigue teniendo su `id`** (`dictado-texto`) y quien lo lee es
 * `app.js`, porque el manejador de clics es uno solo y vive allí. Aquí se pinta con
 * `defaultValue`, que en React es lo que hace que el agricultor pueda escribir: si se pintara con
 * `value` sin estado, cada tecla borraría lo anterior.
 *
 * LO QUE SE CONSERVA A PROPÓSITO
 *
 *  1. El aviso de que el navegador no sabe escuchar sale **en el sitio del botón de hablar**, y el
 *     campo de escribir se queda igual: el dictado es un atajo, nunca un requisito. Donde no haya
 *     voz, el agricultor teclea y sigue.
 *  2. Los `data-accion` (`dictado-hablar`, `dictado-entender`, `ir-inicio`) son los mismos: los
 *     atiende el manejador delegado de `document`.
 *  3. Nada de `esc()` y ninguna frase escrita aquí: los textos llegan por propiedades, del servidor.
 *
 * El componente es PURO: no llama a `fetch`, no toca el micrófono y no lee `localStorage`. Quien
 * habla con el reconocimiento de voz del móvil es `hablar()` en `app.js`.
 */

import { AvisoDeError, Boton, frase, html } from "../componentes.js";

/**
 * La pantalla entera.
 *
 * Se exporta (y no se deja solo el envoltorio de abajo) porque las pruebas del componente la usan
 * directamente: es donde se comprueba, frase por frase, que ninguna está escrita a mano.
 *
 * Propiedades:
 *
 *  - `textos`: `{ dictado, acciones }`, tal y como los sirve `/api/interfaz`.
 *  - `escrito`: lo que ya hay escrito (lo que se ha dictado antes, o lo que se tecleó).
 *  - `puedeHablar`: si este navegador trae reconocimiento de voz. Si no, se dice y se sigue
 *    pudiendo escribir.
 *  - `error`: lo que ha dicho el servidor o el navegador cuando algo no ha salido.
 */
export function PantallaDictado({ textos = {}, escrito = "", puedeHablar = false, error = "" }) {
  const d = textos.dictado || {};
  const acciones = textos.acciones || {};

  return html`
    <h1>${frase(d.titulo)}</h1>
    <p className="pista">${frase(d.intro)}</p>
    <${AvisoDeError} texto=${error} />
    ${
      // **El botón de hablar va primero** (diseño de Stitch de esta pantalla, ronda 90): es la acción
      // principal —el atajo del campo— y lo que se viene a hacer aquí. El recuadro de lo escrito va
      // debajo, que es donde aparece lo que se acaba de decir, con su explicación de que se puede
      // corregir con el dedo. Antes el recuadro iba arriba y el botón debajo: se leía como un formulario
      // que había que rellenar, y hablar parecía el plan B.
      puedeHablar
        ? html`
            <button type="button" className="boton boton-principal" data-accion="dictado-hablar">
              <span className="icono" aria-hidden="true">🎤</span>
              <span className="texto">
                <span>${frase(d.boton)}</span>
                ${
                  d.pista_boton
                    ? html`<span className="pista-boton">${frase(d.pista_boton)}</span>`
                    : null
                }
              </span>
            </button>
          `
        : html`<div className="aviso">${frase(d.no_se_puede)}</div>`
    }
    <div className="campo">
      <label htmlFor="dictado-texto">${frase(d.escribe)}</label>
      <textarea id="dictado-texto" rows="3" defaultValue=${frase(escrito)}></textarea>
      ${d.escribe_pista ? html`<p className="pista-campo">${frase(d.escribe_pista)}</p>` : null}
      <p className="pista-campo">${frase(d.ejemplo)}</p>
    </div>
    <div className="barra-acciones">
      <${Boton} etiqueta=${d.entender} accion="dictado-entender" />
      <${Boton} etiqueta=${acciones.volver} accion="ir-inicio" clase="boton-claro" />
    </div>
  `;
}

/** El elemento de React de esta pantalla, ya con sus propiedades puestas. */
export function pantallaDeDictado(propiedades) {
  return html`<${PantallaDictado}
    textos=${propiedades.textos}
    escrito=${propiedades.escrito}
    puedeHablar=${propiedades.puedeHablar}
    error=${propiedades.error}
  />`;
}
