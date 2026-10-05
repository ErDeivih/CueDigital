/*
 * campo.js — Un campo del asistente: su pregunta, su casilla de escribir, su pista y su ayuda.
 *
 * POR QUÉ EXISTE ESTE FICHERO
 *
 * El asistente pregunta casi todo escribiendo algo: los días que hay que esperar, cuántas hectáreas,
 * cuánto producto por hectárea, qué laboratorio hizo el análisis… En `app.js` había **tres funciones**
 * que montaban ese mismo bloque (`pintaFecha`, `pintaNumero` y `pintaCamposMaestro`) y cada una se
 * acordaba de cosas distintas: una ponía la pista, otra la ayuda, otra el `inputmode` para que en el
 * móvil salga el teclado de números. Aquí está **una vez**.
 *
 * LAS TRES REGLAS QUE NO SE PUEDEN ROMPER
 *
 *  1. **El campo lleva su `id`, y es el de siempre.** No es decoración: `app.js` lee lo que el
 *     agricultor ha escrito **por ese `id`** (`recogeCampos`, `recogeCamposMaestro`, `estadoDelMapa`).
 *     Si un `id` cambia al pasar a React, el formulario se rellena y **se guarda vacío sin que salte
 *     ningún error**, que es el peor fallo posible aquí. Hay pruebas que miran la lista de `id` entera.
 *  2. **El valor inicial va en `defaultValue`, no en `value`.** El campo es **descontrolado** a
 *     propósito: React lo pinta y `app.js` lo lee. Guardar estado en las dos mitades sería la forma
 *     más segura de que un día digan cosas distintas.
 *  3. **Los textos llegan por propiedades.** La etiqueta, la pista y la ayuda vienen del servidor; aquí
 *     no se escribe ni una frase. Las frases compuestas (la fecha «10/04/2026 — viernes, 10 de abril»)
 *     las monta `app.js`, que es quien conoce la fecha.
 *
 * El componente es PURO: no llama a `fetch`, no lee `localStorage` y no toca el DOM.
 */

import { BotonSencillo, frase, html } from "../componentes.js";
import { AyudaDeUnCampo } from "./ayuda_de_un_campo.js";

/**
 * La casilla de escribir, según lo que se pregunte.
 *
 *  - `texto`: lo de siempre.
 *  - `numero`: con `inputmode="decimal"`, que es lo que hace que en el móvil salga el teclado de
 *    números **con coma**, que es como se escribe aquí («2,43» y no «2.43»).
 *  - `entero`: un número **sin decimales** (una hora, cuántos operarios). En el móvil sale el teclado de
 *    números a secas, sin la coma: en una hora, la coma no pinta nada.
 *  - `fecha`: el calendario del navegador. Sin `inputmode`: en un móvil, el teclado de números tapa el
 *    calendario.
 *  - `area`: para escribir un párrafo (las observaciones). Lleva `filas` para decir de qué alto sale.
 */
function Casilla({ id, tipo, valor, placeholder, autocompletar, filas }) {
  if (tipo === "area") {
    return html`<textarea
      id=${id}
      rows=${filas || null}
      placeholder=${placeholder || null}
      defaultValue=${valor}
    ></textarea>`;
  }
  if (tipo === "fecha") {
    return html`<input id=${id} type="date" defaultValue=${valor} />`;
  }
  return html`<input
    id=${id}
    type="text"
    inputMode=${tipo === "numero" ? "decimal" : tipo === "entero" ? "numeric" : null}
    autoComplete=${autocompletar || null}
    placeholder=${placeholder || null}
    defaultValue=${valor}
  />`;
}

/**
 * El campo entero: la etiqueta, la casilla, la pista, la ayuda y, si los hay, sus atajos.
 *
 * Propiedades:
 *
 *  - `id`: el `id` de la casilla. **Tiene que ser el de siempre** (ver la regla 1 de arriba).
 *  - `etiqueta`: lo que se pregunta. Se acepta vacío (hay campos que solo llevan la pista).
 *  - `tipo`: `"texto"` (por defecto), `"numero"`, `"entero"`, `"fecha"` o `"area"`.
 *  - `valor`: lo que ya hay escrito (viene del borrador o del maestro que se está rellenando).
 *  - `sufijo`: la pista de debajo, por ejemplo la unidad («hectáreas»).
 *  - `unidad`: la unidad que va **dentro de la etiqueta**, en su propio trocito de texto
 *    (`.pista-boton`). Es distinto del sufijo: hay preguntas («¿Cuánta materia orgánica?») donde la
 *    unidad forma parte de la pregunta y tiene que leerse con ella.
 *  - `placeholder`: el ejemplo que sale dentro de la casilla vacía («07:30»), de dónde saca la idea el
 *    agricultor. Se acepta vacío.
 *  - `autocompletar`: lo que el navegador puede ofrecer («off» en las horas, para que no salga el
 *    historial de lo que hayas escrito antes).
 *  - `filas`: el alto del área de escribir (`tipo: "area"`).
 *  - `ayuda`: `{ datos, rotulos }` o nada (ver `ayuda_de_un_campo.js`).
 *  - `ayudaAntes`: si la ayuda va **encima** de la casilla en vez de debajo. Es como estaba en el primer
 *    campo de «cómo se echó» el producto: esa explicación es la introducción de la pantalla, y se lee
 *    antes de empezar a rellenarla.
 *  - `botones`: los atajos de debajo, con la misma forma que los demás botones
 *    (`etiqueta`, `accion`, `datos`).
 */
export function Campo({
  id,
  etiqueta,
  tipo = "texto",
  valor = "",
  sufijo = "",
  unidad = "",
  placeholder = "",
  autocompletar = "",
  filas = null,
  ayuda = null,
  ayudaAntes = false,
  botones = [],
}) {
  const bloqueDeAyuda = html`
    <${AyudaDeUnCampo} datos=${ayuda ? ayuda.datos : null} rotulos=${ayuda ? ayuda.rotulos : null} />
  `;
  return html`
    <div className="campo">
      ${ayudaAntes ? bloqueDeAyuda : null}
      ${
        // **Sin etiqueta no se pinta el `<label>`**, y no es un descuido: hay pasos en los que la
        // pregunta ya es el título de la pantalla (las observaciones de un apunte, los detalles de una
        // labor) y una etiqueta vacía solo estorba —un lector de pantalla lee un campo sin nombre—. Es
        // como estaba en la interfaz de siempre.
        etiqueta
          ? html`<label htmlFor=${id}>
              ${frase(etiqueta)}${unidad ? html` <span className="pista-boton">${frase(unidad)}</span>` : null}
            </label>`
          : null
      }
      <${Casilla}
        id=${id}
        tipo=${tipo}
        valor=${valor}
        placeholder=${placeholder}
        autocompletar=${autocompletar}
        filas=${filas}
      />
      ${sufijo ? html`<p className="pista-campo">${frase(sufijo)}</p>` : null}
      ${ayudaAntes ? null : bloqueDeAyuda}
    </div>
    ${botones.map(
      (boton, indice) => html`
        <${BotonSencillo}
          key=${indice}
          etiqueta=${boton.etiqueta}
          accion=${boton.accion}
          datos=${boton.datos}
        />
      `,
    )}
  `;
}

/** El elemento de React de este campo, ya con sus propiedades puestas. */
export function campo(propiedades) {
  return html`
    <${Campo}
      id=${propiedades.id}
      etiqueta=${propiedades.etiqueta}
      tipo=${propiedades.tipo}
      valor=${propiedades.valor}
      sufijo=${propiedades.sufijo}
      unidad=${propiedades.unidad}
      placeholder=${propiedades.placeholder}
      autocompletar=${propiedades.autocompletar}
      filas=${propiedades.filas}
      ayuda=${propiedades.ayuda}
      ayudaAntes=${propiedades.ayudaAntes}
      botones=${propiedades.botones}
    />
  `;
}
