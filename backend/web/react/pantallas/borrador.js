/*
 * borrador.js — La revisión de lo dictado: «he entendido esto», escrita en React.
 *
 * POR QUÉ ESTA PANTALLA
 *
 * Es la decimocuarta que se pasa a React y **cierra el camino del dictado**: el agricultor dice lo
 * que ha hecho, el servidor lo entiende y aquí lo revisa él antes de que se guarde nada. Esta
 * pantalla es lo que en el cuaderno se llama «generative UI»: la respuesta no es un texto de chat
 * que hay que creerse, es el formulario a medio rellenar.
 *
 * **Lo que NO hace este componente:** no decide qué se ha entendido. Eso viene del servidor
 * (`POST /api/borradores/desde-texto`), y llega con **sus propias frases** —el título, la
 * introducción, lo que falta y el aviso de que no se ha entendido nada—, que el servidor saca de
 * `textos.py` (`app/routers/borradores_api.py`). Aquí no se escribe ni una.
 *
 * LO QUE SE CONSERVA A PROPÓSITO
 *
 *  1. Lo que se ha entendido y **dónde se ha colocado** sale como una ficha (`<dl>` de etiqueta y
 *     valor). Lo que se ha oído pero **no se sabe dónde va** sale aparte, en su bloque, y no se
 *     tira: eso era una decisión de la pantalla vieja y es la razón de que el agricultor pueda
 *     corregirlo en vez de perderlo.
 *  2. Los `data-accion` (`borrador-apuntar`, `borrador-corregir`) son los mismos: los atiende el
 *     manejador delegado de `document`.
 *  3. Nada de `esc()` y ninguna frase escrita aquí.
 *
 * El componente es PURO: no llama a `fetch` ni toca el DOM.
 */

import { Boton, frase, html } from "../componentes.js";

/**
 * La pantalla entera.
 *
 * Propiedades:
 *
 *  - `textos`: `{ maestros, dictado }`, tal y como los sirve `/api/interfaz`. Son las tres frases
 *    que no vienen con el borrador (el título de «no sé dónde ponerlo» y las palabras de los dos
 *    botones).
 *  - `borrador`: lo que ha devuelto el servidor: `titulo`, `intro`, `entendido` (cada cosa con su
 *    pregunta, su valor y —si se ha sabido— su campo), `falta`, `falta_intro` y `nada_entendido`.
 *  - `dicho`: **lo que contó el agricultor, tal cual**, para poder compararlo con lo que se ha entendido.
 *    Viene de `app.js` (lo tiene en memoria desde que lo mandó) y no del servidor.
 *
 * Dos cosas del diseño de Stitch de esta pantalla (ronda 90, `docs/stitch/rediseno/borrador.png`):
 *
 *  1. **Lo que has dicho, arriba y entero.** Lo único que veía el agricultor eran los datos ya colocados:
 *     si el programa oyó mal una palabra, no tenía con qué compararlo, y es él el único que puede darse
 *     cuenta.
 *  2. **Lo que falta para poder apuntarlo va en su caja de aviso**, no como un título suelto con una lista
 *     debajo: es lo que impide terminar, y tiene que verse como tal.
 */
export function PantallaBorrador({ textos = {}, borrador = {}, dicho = "" }) {
  const maestros = textos.maestros || {};
  const dictado = textos.dictado || {};
  const entendido = Array.isArray(borrador.entendido) ? borrador.entendido : [];
  const colocados = entendido.filter((entrada) => entrada.campo);
  const sinColocar = entendido.filter((entrada) => !entrada.campo);
  const falta = Array.isArray(borrador.falta) ? borrador.falta : [];

  return html`
    <h1>${frase(borrador.titulo)}</h1>
    <p className="pista">${frase(borrador.intro)}</p>
    ${
      dicho
        ? html`<p className="apunte-detalle"><strong>${frase(dictado.has_dicho)}</strong> ${frase(dicho)}</p>`
        : null
    }
    ${
      // Sin nada entendido se dice, en vez de enseñar una ficha vacía: es el caso de quien dicta
      // algo que el programa no sabe colocar, y tiene que saber que no se ha perdido nada.
      borrador.nada_entendido
        ? html`<div className="aviso">${frase(borrador.nada_entendido)}</div>`
        : null
    }
    ${
      colocados.length
        ? html`<dl>
            ${colocados.map(
              (entrada, indice) => html`
                <div className="resumen-dato" key=${indice}>
                  <dt>${frase(entrada.pregunta)}</dt>
                  <dd>${frase(entrada.valor)}</dd>
                </div>
              `,
            )}
          </dl>`
        : null
    }
    ${
      // Lo oído que no se sabe dónde va. No se esconde: se enseña tal cual, para que el agricultor
      // lo pueda decir de otra forma o apuntarlo a mano.
      sinColocar.length
        ? html`<div className="ayuda-campo">
            <h3>${frase(maestros.sin_sitio_titulo)}</h3>
            ${sinColocar.map(
              (entrada, indice) =>
                html`<p key=${indice}>${frase(entrada.pregunta)} <strong>${frase(entrada.valor)}</strong></p>`,
            )}
          </div>`
        : null
    }
    ${
      falta.length
        ? html`<div className="aviso">
            <strong>${frase(borrador.falta_intro)}</strong>
            <ul className="lista">
              ${falta.map((item, indice) => html`<li key=${indice}>${frase(item.pregunta)}</li>`)}
            </ul>
          </div>`
        : null
    }
    <div className="barra-acciones">
      <${Boton} etiqueta=${dictado.apuntarlo} accion="borrador-apuntar" />
      <${Boton} etiqueta=${dictado.corregir} accion="borrador-corregir" clase="boton-claro" />
    </div>
  `;
}

/** El elemento de React de esta pantalla, ya con sus propiedades puestas. */
export function pantallaDeBorrador(propiedades) {
  return html`<${PantallaBorrador}
    textos=${propiedades.textos}
    borrador=${propiedades.borrador}
    dicho=${propiedades.dicho}
  />`;
}
