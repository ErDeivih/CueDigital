/*
 * asistente.js — El asistente de apuntar: la pantalla que envuelve cada pregunta.
 *
 * QUÉ ES ESTO Y POR QUÉ ERA LO ÚLTIMO QUE QUEDABA
 *
 * El asistente es la parte que más se usa de la aplicación: echar producto, abonar, sembrar, regar,
 * coger la cosecha… Se contesta **una pregunta por pantalla**, y cada pregunta es un *paso* que trae su
 * formulario (una lista de tierras, unos campos que se escriben, un resumen para repasar).
 *
 * Hasta hoy, el que envolvía esos formularios —las barras de progreso, la pregunta, la pista, el aviso de
 * error, el hueco donde va el formulario y los botones de VOLVER / DEJARLO / SEGUIR— se pintaba a mano en
 * `app.js` con `pintar()`, que era **el último `innerHTML` de la aplicación**. Los 65 pasos ya estaban en
 * React, pero el motor no, y por eso el asistente no se apuntaba en `PANTALLAS_EN_REACT`.
 *
 * LO QUE HACE ESTE COMPONENTE, Y LO QUE NO
 *
 * - **Sí**: pinta lo que rodea a la pregunta (las barras, el título, la pista, el error y los botones) y
 *   **el formulario del paso**, que le llega ya construido en la propiedad `formulario`.
 * - **No**: no decide qué paso toca, ni lee el borrador, ni sabe qué se ha contestado. Eso sigue en
 *   `app.js` (`irA`, `normalizaIndice`, el `recoger()` de cada paso), que es lo que **no** se ha tocado en
 *   toda la migración: el motor sigue haciendo lo mismo, solo que ahora pinta React.
 * - **No** compone frases: el título, la pista, los mensajes de error y las etiquetas de los botones
 *   llegan escritos desde `textos.py`, por `app.js`.
 *
 * LO QUE SE CONSERVA A PROPÓSITO (todo esto estaba así y se queda así)
 *
 *  1. **Las barras de progreso** (`role="progressbar"` con `aria-valuenow` y `aria-valuemax`): son lo
 *     que le dice al agricultor —y a un lector de pantalla— por dónde va de largo que es el apunte.
 *  2. **El hueco del formulario con su `id`** (`#formulario`): es donde va el formulario del paso. Se
 *     queda con el mismo `id` a propósito, porque lo buscan las pruebas de los pasos y la comprobación en
 *     un navegador de verdad, y porque deja claro en el DOM dónde acaba la pregunta y empieza lo que hay
 *     que contestar.
 *  3. **Los tres botones, con sus acciones y su forma**: `asistente-atras` (VOLVER, botón claro),
 *     `asistente-saltar` (DEJARLO, solo en los pasos opcionales) y `asistente-seguir` (SEGUIR, o
 *     APUNTARLO en el resumen, que es el botón principal). Los tres van **sencillos**, sin icono y sin
 *     flecha, como estaban: el de seguir no lleva a otra pantalla, hace avanzar esta.
 *  4. **El orden**: barras, pregunta, pista, error, formulario, botones. La pista va **debajo** de la
 *     pregunta y **encima** del formulario, que es donde se lee.
 *
 * El componente es PURO: no llama a `fetch`, no lee `localStorage` y no toca el DOM.
 */

import { AvisoDeError, Botones, frase, html } from "../componentes.js";

/**
 * Las barras de arriba: una por paso, y las hechas (hasta la actual) en verde.
 *
 * Se pintan todas las veces (no se guardan en estado) porque el asistente se vuelve a montar entero cada
 * vez que el agricultor contesta: es lo que hace que no haya dos cosas diciendo cosas distintas.
 */
function BarraDePasos({ indice, total }) {
  return html`
    <div className="pasos" role="progressbar" aria-valuenow=${indice + 1} aria-valuemax=${total}>
      ${Array.from({ length: total }, (_, numero) => html`
        <div key=${numero} className=${numero <= indice ? "paso paso-hecho" : "paso"}></div>
      `)}
    </div>
  `;
}

/**
 * La pantalla entera del asistente.
 *
 * Propiedades:
 *
 *  - `titulo` y `pista`: la pregunta del paso y su explicación, ya resueltas por `app.js` (pueden ser
 *    texto fijo o depender de lo contestado antes, y eso lo sabe `app.js`, no el componente).
 *  - `indice` y `total`: por dónde va y cuántos pasos hay (para los tramos de la barra).
 *  - `formulario`: **el formulario del paso, ya construido** (la lista de tierras, los campos, el
 *    resumen). Va dentro de `#formulario`, que es su sitio de siempre.
 *  - `error`: lo que ha dicho el servidor cuando el paso no ha podido seguir (por ejemplo, «dinos en qué
 *    parcela»). Si está vacío, no se pinta nada: un hueco con un borde rojo asusta sin motivo.
 *  - `botones`: los de abajo, ya preparados por `app.js` (etiqueta, acción y si es el principal). Van en
 *    una barra **pegada abajo** (`.asistente-acciones`): de pie en el campo y con una mano, el botón de
 *    seguir tiene que estar donde llega el pulgar y no al final de una lista de cincuenta tierras.
 *  - `paso`: el «Paso 2 de 5» ya escrito. La barra sola no dice cuántos quedan si no se cuentan los
 *    tramos, y eso con el sol de frente no se hace. **Va vacío cuando el asistente tiene un solo paso**
 *    (el del SIGPAC): no hay nada que contar.
 *  - `modo`: la etiqueta que dice **qué se está haciendo**, cuando no es apuntar algo nuevo. Hoy solo la
 *    usa corregir un apunte o una tierra («CORRIGIENDO LO APUNTADO», diseño de Stitch de la ronda 92): el
 *    título de arriba ya lo dice, pero en el paso 6 de 9 ya no se lee, y la barra de progreso —que es lo
 *    que se mira para saber por dónde vas— tiene que llevar al lado si esto es nuevo o es un arreglo. Va
 *    vacío en todo lo demás, y entonces no se pinta nada.
 *
 * **No recibe un diccionario de textos**, y no es un olvido: es la única pantalla de la aplicación que no
 * escribe ni un rótulo propio —la pregunta, la pista, el error, el «Paso 2 de 5» y las etiquetas de los
 * botones se los pasa `app.js` ya resueltos, cada uno del sitio de `textos.py` que le toca— y meter un
 * diccionario vacío solo para cumplir el patrón sería ruido.
 */
export function PantallaAsistente({
  titulo,
  pista,
  indice = 0,
  total = 1,
  formulario = null,
  error = "",
  botones = [],
  paso = "",
  modo = "",
}) {
  return html`
    ${
      // La barra **solo cuando hay más de un paso** (ronda 88): en un asistente de un solo paso —el del
      // SIGPAC— una barra llena y un «Paso 1 de 1» no dicen nada y empujan hacia abajo lo que sí importa.
      total > 1 ? html`<${BarraDePasos} indice=${indice} total=${total} />` : null
    }
    ${
      paso || modo
        ? html`
            <p className="paso-cuantos">
              ${frase(paso)}
              ${modo
                ? html`<span className="etiqueta-estado etiqueta-estado-mirar">${frase(modo)}</span>`
                : null}
            </p>
          `
        : null
    }
    <p className="pregunta">${frase(titulo)}</p>
    ${pista ? html`<p className="pista">${frase(pista)}</p>` : null}
    <${AvisoDeError} texto=${error} />
    <div id="formulario">${formulario}</div>
    <div className="asistente-acciones">
      <${Botones} botones=${botones} barra=${false} />
    </div>
  `;
}

/** El elemento de React de esta pantalla, ya con sus propiedades puestas. */
export function pantallaDelAsistente(propiedades) {
  return html`
    <${PantallaAsistente}
      titulo=${propiedades.titulo}
      pista=${propiedades.pista}
      indice=${propiedades.indice}
      total=${propiedades.total}
      formulario=${propiedades.formulario}
      error=${propiedades.error}
      botones=${propiedades.botones}
      paso=${propiedades.paso}
      modo=${propiedades.modo}
    />
  `;
}
