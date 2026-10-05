/*
 * campos_del_maestro.js — Un grupo de datos que se piden juntos: la ficha de un producto, la de una
 * máquina, la de un asesor, los números de un plan…
 *
 * POR QUÉ ES UNA PIEZA Y NO SE USA `campo.js` A SECAS
 *
 * Casi todos los pasos del asistente que no son una lista son **varios datos seguidos**: el nombre, el
 * número de registro y la dosis de un producto; la marca, el modelo y el número de ROMA de una máquina.
 * Cada uno de esos datos se pinta como un campo… **menos los que se contestan eligiendo**, que en vez de
 * una casilla llevan sus botones dentro del mismo bloque (un sí o un no, la unidad de dosis, el tipo de
 * carné). Esa mezcla es lo que se resuelve aquí: un grupo de bloques, cada uno de escribir o de elegir.
 *
 * En `app.js` esto lo hacía `pintaCamposMaestro()` con una cadena de HTML, y lo llamaban **veinte pasos**
 * distintos. Ahora la lista de bloques se prepara en `app.js` (que es quien conoce el vocabulario y el
 * borrador) y aquí solo se pinta.
 *
 * LO QUE NO SE PUEDE ROMPER
 *
 *  1. **Cada campo de escribir lleva su `id`**, que es lo único que tiene `app.js` para leer lo escrito
 *     (`recogeCamposMaestro`). Si cambia, el formulario se rellena y **se guarda vacío sin ningún
 *     error**.
 *  2. **Los botones de elegir llevan `data-campo` y `data-valor`**, que es lo que lee el manejador de
 *     clics de `app.js` (`accion: "elegir"`). Y el elegido va marcado (`boton-elegido`), que es como el
 *     agricultor sabe qué contestó.
 *  3. **La etiqueta de un bloque de elegir no lleva `for`**: no apunta a ninguna casilla, porque la
 *     casilla son los botones.
 *  4. **El valor va en `defaultValue`**: el campo es descontrolado.
 *
 * El componente es PURO: no llama a `fetch`, no lee `localStorage` y no toca el DOM.
 */

import { Boton, frase, html } from "../componentes.js";
import { AyudaDeUnCampo } from "./ayuda_de_un_campo.js";
import { Campo } from "./campo.js";

/**
 * Un dato que se contesta eligiendo: su pregunta, sus botones, su pista y su ayuda.
 *
 * El `campo` viene del bloque (no de cada botón) porque los botones son las respuestas **de ese dato**:
 * así no hay forma de que dos botones del mismo bloque manden a campos distintos.
 */
function CampoDeOpciones({ campo, etiqueta, pista, ayuda = null, opciones = [] }) {
  return html`
    <div className="campo">
      <label>${frase(etiqueta)}</label>
      ${opciones.map(
        (opcion, indice) => html`
          <${Boton}
            key=${indice}
            etiqueta=${opcion.etiqueta}
            accion="elegir"
            datos=${{ campo, valor: opcion.valor }}
            clase=${opcion.elegido ? "boton-elegido" : "boton-claro"}
          />
        `,
      )}
      ${pista ? html`<p className="pista-campo">${frase(pista)}</p>` : null}
      <${AyudaDeUnCampo} datos=${ayuda ? ayuda.datos : null} rotulos=${ayuda ? ayuda.rotulos : null} />
    </div>
  `;
}

/**
 * Un grupo de datos del maestro.
 *
 * Propiedades:
 *
 *  - `bloques`: los datos, ya preparados y en su orden. Cada uno es:
 *      · de escribir: `{ tipo: "texto" | "numero" | "fecha", id, etiqueta, valor, pista, ayuda }`
 *      · de elegir:   `{ tipo: "opciones", campo, etiqueta, pista, ayuda, opciones: [{etiqueta, valor, elegido}] }`
 *
 * **Un bloque con un `tipo` que no se conoce se pinta como texto**, que es lo que hacía la interfaz de
 * siempre. Está decidido a propósito: significa que `app.js` no ha sabido prepararlo, y entre un campo de
 * más (que el agricultor puede rellenar y se guarda en su sitio) y un campo que desaparece sin decir
 * nada, el de más. Un campo que no se pinta es un dato que se pierde **sin que nadie se entere**, y eso
 * aquí es lo peor que puede pasar.
 */
export function CamposDelMaestro({ bloques = [] }) {
  return html`
    ${bloques.map((bloque, indice) =>
      bloque.tipo === "opciones"
        ? html`
            <${CampoDeOpciones}
              key=${indice}
              campo=${bloque.campo}
              etiqueta=${bloque.etiqueta}
              pista=${bloque.pista}
              ayuda=${bloque.ayuda}
              opciones=${bloque.opciones}
            />
          `
        : html`
            ${
              // Un bloque de escribir puede llevar **su título**: hay pantallas del asistente que son
              // varias secciones seguidas («cómo se echó»: la hora, el estado del cultivo, cómo estaba el
              // día…), y cada sección tiene su encabezado. En las fichas del maestro no se usa (allí el
              // título es la pregunta del paso).
              bloque.titulo ? html`<h2>${frase(bloque.titulo)}</h2>` : null
            }
            <${Campo}
              key=${indice}
              id=${bloque.id}
              etiqueta=${bloque.etiqueta}
              tipo=${bloque.tipo}
              valor=${bloque.valor}
              sufijo=${bloque.pista}
              unidad=${bloque.unidad}
              placeholder=${bloque.placeholder}
              autocompletar=${bloque.autocompletar}
              filas=${bloque.filas}
              ayuda=${bloque.ayuda}
              ayudaAntes=${bloque.ayudaAntes}
            />
          `,
    )}
  `;
}

/** El elemento de React de un grupo de campos, ya con sus propiedades puestas. */
export function camposDelMaestro(propiedades) {
  return html`<${CamposDelMaestro} bloques=${propiedades.bloques} />`;
}
