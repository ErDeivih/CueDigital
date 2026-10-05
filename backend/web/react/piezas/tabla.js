/*
 * tabla.js — La tabla de una lista, para el ordenador.
 *
 * POR QUÉ EXISTE (30/09/2026)
 *
 * David lo pidió así: *«no es una app usable de gestión… hacer una versión para pc que parezca una
 * aplicación de gestión»*. Y lo que hace que un programa de gestión sea un programa de gestión es
 * **poder ver muchos datos a la vez en una tabla**: ordenarlos, compararlos y tocar una fila. En el móvil
 * la misma lista va en tarjetas (una detrás de otra, con letra grande, para el dedo); en el ordenador va
 * en tabla, con las columnas que se pueden mirar de arriba abajo.
 *
 * **La misma lista, las dos formas, y las dos en el mismo HTML**: el CSS enseña una u otra según el ancho
 * (`.solo-escritorio` y `.solo-movil`). Así no hay dos aplicaciones que se separen y el manejador de clics
 * sigue siendo uno solo: los botones de una fila son los mismos que los de su tarjeta.
 *
 * LO QUE HAY QUE SABER DE ESTA PIEZA
 *
 *  1. **No calcula nada.** Ni los totales, ni el orden, ni qué está en ámbar: todo eso lo prepara `app.js`,
 *     que es quien tiene los datos. Aquí solo se coloca.
 *  2. **Los textos de las columnas y del resumen vienen del servidor** (`textos.py`): los nombres de las
 *     columnas son frases («Referencia SIGPAC», «Qué tiene este año») y no se escriben aquí.
 *  3. **La cabecera de la columna por la que se ordena es un botón** (`data-accion="ordenar-tabla"` con su
 *     `data-campo` y su `data-tabla`): pulsarla ordena por esa columna, y pulsarla otra vez le da la
 *     vuelta. La flecha de «por aquí va el orden» **la pone el CSS** (`.tabla-ordenada::after`), no una
 *     frase dentro del componente: el color y una flecha dibujada, nunca solo el color.
 *  4. **Cada fila lleva sus acciones a la derecha**, con la pieza de siempre
 *     (`acciones_de_una_ficha.js`): CORREGIR y BORRAR, más la acción propia de la fila (por ejemplo
 *     «DECIR QUÉ HAY SEMBRADO»). La fila entera **no** es un botón: en una tabla, tocar una fila para
 *     abrir algo es lo que menos se espera. **Y esa celda la pinta esta pieza, no `app.js`**: quien prepara
 *     una tabla escribe **una celda menos que columnas tiene** (la última columna, «Acciones», la pone aquí).
 *     Escribir además una celda vacía al final —que es lo que hacían las cinco tablas hasta el 30/09/2026—
 *     deja los botones en una columna **sin cabecera**: la tabla se ensancha sola y el encabezado no queda
 *     encima de sus botones. Hay una prueba que lo impide (`celdas = columnas − 1`).
 *  5. **Al pie, el total**: es lo que se viene a mirar en una tabla de tierras («¿cuántas hectáreas
 *     tengo?»).
 *
 * El componente es PURO: no llama a `fetch`, no lee `localStorage` y no toca el DOM.
 */

import { Botones, DibujoDeLaParcela, datosDelBoton, frase, html } from "../componentes.js";
import { AccionesDeUnaFicha } from "./acciones_de_una_ficha.js";

/** Una cabecera: si la columna se puede ordenar, es un botón; si no, es texto. */
function Cabecera({ columna, tabla }) {
  if (!columna.campo) {
    return html`<th scope="col" className=${columna.clase || ""}>${frase(columna.texto)}</th>`;
  }
  const clases = [
    columna.clase || "",
    columna.ordenada ? (columna.descendente ? "tabla-ordenada tabla-ordenada-abajo" : "tabla-ordenada") : "",
  ]
    .filter(Boolean)
    .join(" ");
  return html`
    <th scope="col" className=${clases} aria-sort=${columna.ordenada ? (columna.descendente ? "descending" : "ascending") : "none"}>
      <button
        type="button"
        className="tabla-orden"
        data-accion="ordenar-tabla"
        data-tabla=${tabla}
        data-campo=${columna.campo}
        title=${frase(columna.orden || "")}
      >
        ${frase(columna.texto)}
      </button>
    </th>
  `;
}

/** Una fila: sus celdas y, al final, sus botones. */
function Fila({ fila }) {
  return html`
    <tr className=${fila.elegida ? "tabla-fila-elegida" : ""}>
      ${fila.celdas.map(
        (celda, indice) => html`
          <td key=${indice} className=${celda.clase || ""}>
            ${
              // Una celda puede llevar su etiqueta de estado (el ámbar de «le falta decirlo»): se dice con
              // palabras además del color, como todo en esta aplicación.
              celda.estado
                ? html`<span className=${`etiqueta-estado etiqueta-estado-${celda.estado.tipo}`}
                    >${frase(celda.estado.texto)}</span
                  >`
                : null
            }
            ${
              // **Y una celda puede ser un botón** (30/09/2026): el nombre de una tierra se toca para verla
              // en el panel de al lado. Es como se hace en cualquier programa de gestión —se toca el nombre,
              // no la fila entera— y así funciona también con el teclado: un `<tr>` no se puede enfocar, un
              // botón sí. La fila entera **no** es un botón: en una tabla, eso es lo que menos se espera.
              celda.accion
                ? html`<button
                    type="button"
                    className="tabla-enlace"
                    data-accion=${celda.accion}
                    ...${datosDelBoton(celda.datos)}
                  >
                    ${frase(celda.texto)}
                  </button>`
                : celda.texto
                  ? html`<span className="tabla-dato">${frase(celda.texto)}</span>`
                  : null
            }
            ${celda.pista ? html`<span className="tabla-pista">${frase(celda.pista)}</span>` : null}
          </td>
        `,
      )}
      <td className="tabla-acciones">
        <${AccionesDeUnaFicha} acciones=${fila.acciones} />
      </td>
    </tr>
  `;
}

/**
 * El panel de al lado de la tabla: lo que se ve al tocar el nombre de una fila, **sin salir de la página**.
 *
 * POR QUÉ (30/09/2026, fase 3). Es la mitad de lo que hace que una tabla sirva: se mira la lista, se toca
 * una fila y se ve su ficha al lado, con sus datos y sus botones, sin cambiar de pantalla ni volver. Es lo
 * que hace cualquier programa de gestión, y es lo que pidió David.
 *
 * **La ficha la prepara `app.js`** (su título, sus filas con el nombre delante y sus botones): aquí solo se
 * coloca, como en la tabla. Cuando no hay nada elegido, el panel lo dice en vez de quedarse en blanco.
 */
function Panel({ panel }) {
  if (!panel) return null;
  return html`
    <aside className="panel-detalle" aria-label=${frase(panel.etiqueta || "")}>
      <h2>${frase(panel.titulo)}</h2>
      ${
        panel.elegida
          ? html`
              ${panel.detalle ? html`<p className="pista-campo">${frase(panel.detalle)}</p>` : null}
              ${
                // **La forma de la tierra, dibujada** (30/09/2026). El diseño de escritorio de esta pantalla
                // (`docs/stitch/escritorio/estructura.png`) la pide y el dato ya estaba: es como el agricultor
                // reconoce una tierra —la ve así en el SIGPAC—, y en el móvil la tarjeta la lleva desde la
                // ronda 78. El panel era el único sitio donde la ficha salía sin su dibujo.
                panel.dibujo
                  ? html`<p className="panel-dibujo">
                      <${DibujoDeLaParcela} dibujo=${panel.dibujo} etiqueta=${panel.titulo} />
                    </p>`
                  : null
              }
              ${panel.filas && panel.filas.length
                ? html`<dl>
                    ${panel.filas.map(
                      (fila, indice) => html`<div className="resumen-dato" key=${indice}>
                        <dt>${frase(fila.etiqueta)}</dt>
                        <dd>${frase(fila.valor)}</dd>
                      </div>`,
                    )}
                  </dl>`
                : null}
              ${(panel.avisos || []).map(
                (aviso, indice) => html`<p className="tarjeta-aviso" key=${indice}>
                  <span className="tarjeta-aviso-icono" aria-hidden="true">!</span>
                  ${frase(aviso)}
                </p>`,
              )}
              ${
                // Y sus últimos apuntes, si los tiene: es lo que se pregunta al mirar una tierra en el
                // despacho («¿qué le he hecho este año?») y ya venía en el diseño.
                panel.ultimos && panel.ultimos.filas && panel.ultimos.filas.length
                  ? html`
                      <h3 className="panel-subtitulo">${frase(panel.ultimos.titulo)}</h3>
                      <ul className="panel-ultimos">
                        ${panel.ultimos.filas.map(
                          (linea, indice) => html`<li key=${indice}>${frase(linea)}</li>`,
                        )}
                      </ul>
                    `
                  : null
              }
              <${Botones} botones=${panel.acciones} barra=${false} />
            `
          : html`<p className="pista-campo">${frase(panel.vacio)}</p>`
      }
    </aside>
  `;
}

/**
 * La tabla entera.
 *
 * Propiedades:
 *
 *  - `tabla`: `{ clave, columnas, filas, resumen, etiqueta, panel }`, ya preparada por `app.js`.
 *    · `columnas`: `[{texto, campo?, ordenada?, descendente?, clase?, orden?}]`. Con `campo`, la columna
 *      se puede ordenar (y el botón lleva ese `data-campo`); `orden` es el texto del `title` («Ordenar por:
 *      Nombre»), que viene del servidor como todo lo que se lee.
 *    · `filas`: `[{celdas: [{texto, pista?, estado?, clase?, accion?, datos?}], acciones, elegida?}]`. Una
 *      celda con `accion` es un botón: es como se elige una fila para verla en el panel de al lado.
 *    · `resumen`: el total del pie, ya compuesto (o vacío).
 *    · `etiqueta`: el nombre de la tabla, para quien no ve la pantalla.
 *    · `panel`: el panel de al lado (o `null`, y entonces la tabla ocupa todo el ancho).
 */
export function Tabla({ tabla = {} }) {
  const columnas = tabla.columnas || [];
  const filas = tabla.filas || [];
  if (!filas.length) return null;
  const soloLaTabla = html`
    <table className="tabla" aria-label=${frase(tabla.etiqueta || "")}>
      <thead>
        <tr>
          ${columnas.map((columna, indice) => html`<${Cabecera} key=${indice} columna=${columna} tabla=${tabla.clave} />`)}
        </tr>
      </thead>
      <tbody>
        ${filas.map((fila, indice) => html`<${Fila} key=${indice} fila=${fila} />`)}
      </tbody>
      ${
        tabla.resumen
          ? html`<tfoot>
              <tr>
                <td colSpan=${columnas.length}>${frase(tabla.resumen)}</td>
              </tr>
            </tfoot>`
          : null
      }
    </table>
  `;
  // **Con panel va dentro de su rejilla; sin panel, la tabla sola.** No se envuelve «por si acaso»: un
  // `div` de más sin clase es basura en el HTML y desconcierta al que lo lea buscando la tabla.
  //
  // Y con panel, la tabla va dentro de `.tabla-scroll`: al lado de la ficha se queda menos ancho y una
  // tabla de ocho columnas **no puede encogerse hasta apretarse** (los botones de la última columna se
  // metían debajo del panel). Con el contenedor, la tabla conserva su ancho mínimo y, si no cabe, se
  // desplaza en horizontal, que es lo que hace cualquier programa de gestión.
  if (!tabla.panel) return soloLaTabla;
  return html`<div className="tabla-y-panel">
    <div className="tabla-scroll">${soloLaTabla}</div>
    <${Panel} panel=${tabla.panel} />
  </div>`;
}

/** El elemento de React de esta pieza, ya con sus propiedades puestas. */
export function tablaDeUnaLista(propiedades) {
  return html`<${Tabla} tabla=${propiedades.tabla} />`;
}
