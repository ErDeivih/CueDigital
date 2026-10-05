/*
 * panel_de_mando.js — El panel de mando del ordenador (fase 4, 30/09/2026).
 *
 * POR QUÉ EXISTE
 *
 * Es **la pantalla que se abre al entrar desde un pc**, y hasta hoy era la del móvil estirada: ocho botones
 * de ancho completo, uno debajo de otro, en un monitor. Lo que hace un programa de gestión al abrirse es
 * enseñar **el estado**: cuatro números del año, lo que falta por completar (con el botón que lo arregla) y
 * lo último que se ha apuntado. David lo pidió con estas palabras: *«una versión para pc que parezca una
 * aplicación de gestión tipo SAP»*.
 *
 * El diseño del que sale está en `docs/stitch/escritorio/panel.png`, pedido a Stitch con nuestro `DESIGN.md`
 * (por eso usa nuestros colores y nuestras formas sin que haya que repintar nada).
 *
 * LO QUE HAY QUE SABER DE ESTA PIEZA
 *
 *  1. **No calcula nada.** Los cuatro números, cuántas cosas faltan, las últimas filas y sus textos los
 *     prepara `app.js`, que es quien tiene los datos. Aquí solo se coloca.
 *  2. **Los textos vienen del servidor** (`textos.PANEL_DE_MANDO`, `TABLA`, `CUADERNO`…): ni una frase
 *     escrita aquí. Los iconos sí van en el `app.js` porque son datos de `textos.py` (los mismos de la
 *     pantalla de inicio).
 *  3. **La tabla de los últimos apuntes es una tabla de verdad** (`<table>`), con la misma forma que las
 *     demás del programa, pero **sin ordenar ni elegir fila**: son cinco filas para mirar y el enlace que
 *     lleva a la lista entera. Una tabla de cinco filas no necesita ser una tabla de gestión.
 *  4. **Una cosa del diseño NO está, y es a propósito**: la tarjeta del gasto en fitosanitarios en euros. Ese
 *     número no existe en el programa, y ponerlo de adorno sería inventarse un dato. En su sitio va la
 *     tarjeta de las tierras, que dice lo que hay que hacer.
 *
 * El componente es PURO: no llama a `fetch`, no lee `localStorage` y no toca el DOM.
 */

import { Boton, BotonSencillo, frase, html } from "../componentes.js";

/** Una de las cuatro tarjetas de números. */
function Numero({ numero }) {
  return html`
    <li className="mando-numero">
      <p className="mando-numero-etiqueta">${frase(numero.etiqueta)}</p>
      <p className="mando-numero-valor">${frase(numero.valor)}</p>
      ${
        // El detalle es una línea de contexto («de 187,42 ha de tus tierras»). Si no hay, no se deja el
        // hueco: un renglón vacío debajo del número parece un dato que no ha llegado.
        numero.detalle ? html`<p className="mando-numero-detalle">${frase(numero.detalle)}</p>` : null
      }
    </li>
  `;
}

/** Lo que falta por completar: cada cosa con el botón que la arregla. */
function LoQueFalta({ faltantes }) {
  return html`
    <section className="mando-bloque" aria-label=${frase(faltantes.titulo)}>
      <div className="mando-bloque-cabecera">
        <h3>${frase(faltantes.titulo)}</h3>
        ${
          faltantes.cuantas
            ? html`<span className="etiqueta-estado etiqueta-estado-mirar">${frase(faltantes.cuantas)}</span>`
            : null
        }
      </div>
      ${
        faltantes.pendientes && faltantes.pendientes.length
          ? html`
              <ul className="mando-pendientes">
                ${faltantes.pendientes.map(
                  (pendiente, indice) => html`
                    <li key=${indice}>
                      <p className="mando-pendiente-texto">${frase(pendiente.mensaje)}</p>
                      ${
                        // **El que no tiene pantalla propia se queda con su texto y sin botón**, que es la
                        // regla de la casa: un aviso sin salida no vale, pero un botón que no lleva a
                        // ninguna parte tampoco.
                        pendiente.accion
                          ? html`<${BotonSencillo}
                              etiqueta=${pendiente.etiqueta}
                              accion=${pendiente.accion}
                              datos=${pendiente.datos}
                              clase="boton-claro"
                            />`
                          : null
                      }
                    </li>
                  `,
                )}
              </ul>
            `
          : html`<p className="pista-campo">${frase(faltantes.vacio)}</p>`
      }
    </section>
  `;
}

/** Los últimos apuntes, en una tabla corta, y el enlace a la lista entera. */
function LosUltimos({ ultimos }) {
  return html`
    <section className="mando-bloque" aria-label=${frase(ultimos.titulo)}>
      <div className="mando-bloque-cabecera">
        <h3>${frase(ultimos.titulo)}</h3>
      </div>
      ${
        ultimos.filas && ultimos.filas.length
          ? html`
              <table className="tabla mando-ultimos">
                <thead>
                  <tr>
                    ${ultimos.columnas.map(
                      (columna, indice) => html`<th key=${indice} scope="col">${frase(columna)}</th>`,
                    )}
                  </tr>
                </thead>
                <tbody>
                  ${ultimos.filas.map(
                    (fila, indice) => html`
                      <tr key=${indice}>
                        ${fila.map(
                          (celda, posicion) => html`<td key=${posicion}>${frase(celda)}</td>`,
                        )}
                      </tr>
                    `,
                  )}
                </tbody>
              </table>
            `
          : html`<p className="pista-campo">${frase(ultimos.vacio)}</p>`
      }
      ${
        ultimos.ver_todos
          ? html`<${BotonSencillo}
              etiqueta=${ultimos.ver_todos.etiqueta}
              accion=${ultimos.ver_todos.accion}
              datos=${ultimos.ver_todos.datos}
              clase="boton-claro"
            />`
          : null
      }
    </section>
  `;
}

/**
 * El panel de mando entero.
 *
 * Propiedades:
 *
 *  - `textos`: `{ panel_de_mando }`, tal y como los sirve `/api/interfaz`.
 *  - `numeros`: las cuatro tarjetas (`{ etiqueta, valor, detalle }`), ya contadas por `app.js`.
 *  - `faltantes`: `{ titulo, cuantas, pendientes: [{ mensaje, accion, etiqueta }], vacio }`.
 *  - `ultimos`: `{ titulo, columnas: [texto], filas: [[celda]], vacio, ver_todos: { etiqueta, accion } }`.
 *  - `apuntar`: los botones de «apuntar algo de hoy», con los mismos textos e iconos que los del móvil.
 *  - `cierre`: `{ titulo, explica, botones: [botón] }`, lo que se saca del programa.
 */
export function PanelDeMando({
  textos = {},
  numeros = [],
  faltantes = {},
  ultimos = {},
  apuntar = [],
  cierre = {},
}) {
  const p = textos.panel_de_mando || {};

  return html`
    <div className="mando">
      <h2>${frase(p.titulo)}</h2>
      <p className="pista">${frase(p.explica)}</p>
      <ul className="mando-numeros">
        ${numeros.map((numero, indice) => html`<${Numero} key=${indice} numero=${numero} />`)}
      </ul>
      <div className="mando-columnas">
        <${LoQueFalta} faltantes=${faltantes} />
        <${LosUltimos} ultimos=${ultimos} />
      </div>
      ${
        // Apuntar algo de hoy, sin tener que ir al cuaderno a buscarlo: son los mismos botones que el móvil
        // enseña grandes, aquí en una fila.
        apuntar.length
          ? html`
              <section className="mando-bloque mando-apuntar" aria-label=${frase(p.apuntar_titulo)}>
                <h3>${frase(p.apuntar_titulo)}</h3>
                <div className="barra-acciones">
                  ${apuntar.map(
                    (boton, indice) => html`
                      <${Boton}
                        key=${indice}
                        etiqueta=${boton.etiqueta}
                        pista=${boton.pista}
                        icono=${boton.icono}
                        accion=${boton.accion}
                        datos=${boton.datos}
                        clase=${boton.clase || ""}
                      />
                    `,
                  )}
                </div>
              </section>
            `
          : null
      }
      ${
        cierre.botones && cierre.botones.length
          ? html`
              <section className="mando-bloque mando-cierre" aria-label=${frase(cierre.titulo)}>
                <h3>${frase(cierre.titulo)}</h3>
                <p className="pista-campo">${frase(cierre.explica)}</p>
                <div className="barra-acciones">
                  ${cierre.botones.map(
                    (boton, indice) => html`
                      <${BotonSencillo}
                        key=${indice}
                        etiqueta=${boton.etiqueta}
                        accion=${boton.accion}
                        datos=${boton.datos}
                        clase=${boton.clase}
                      />
                    `,
                  )}
                </div>
              </section>
            `
          : null
      }
    </div>
  `;
}

/** El elemento de React de esta pieza, ya con sus propiedades puestas. */
export function panelDeMando(propiedades) {
  return html`
    <${PanelDeMando}
      textos=${propiedades.textos}
      numeros=${propiedades.numeros}
      faltantes=${propiedades.faltantes}
      ultimos=${propiedades.ultimos}
      apuntar=${propiedades.apuntar}
      cierre=${propiedades.cierre}
    />
  `;
}
