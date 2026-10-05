/*
 * cuaderno_de_la_junta.js — «Traer tus tierras del cuaderno de la Junta», escrita en React.
 *
 * POR QUÉ ESTA PANTALLA
 *
 * Es la vigesimocuarta que se pasa a React, y es la que ahorra más trabajo de todas: el agricultor
 * descarga su cuaderno del Cuecyl y **este programa le apunta sus tierras de una vez** —con su
 * polígono, su parcela, su recinto, su cultivo y sus hectáreas— en lugar de teclearlas una a una. Con
 * 54 líneas y 51 tierras, eso es la diferencia entre empezar y no empezar.
 *
 * Y hay una regla que se conserva tal cual: **leer el fichero no apunta nada.** Primero enseña lo que
 * trae (para que el agricultor lo mire), y solo cuando él pulsa el botón se apunta. Traer 51 tierras
 * sin preguntar sería meterle en el cuaderno cosas que no ha visto.
 *
 * TRES ESTADOS, UNA PANTALLA
 *
 *  1. **El formulario**: elegir el fichero del Cuecyl y leerlo.
 *  2. **El resumen**: lo que trae el fichero, con sus cuentas y la lista de tierras, y el botón de
 *     confirmar.
 *  3. **El resultado**: lo que se ha apuntado, lo que ya estaba y lo que no vino, con el aviso de que
 *     se puede leer otra vez sin miedo (lo que ya está no se duplica).
 *
 * LO QUE SE CONSERVA A PROPÓSITO
 *
 *  1. **El `id` del campo del fichero** (`cuaderno-fichero`): es como `app.js` coge el Excel. Si
 *     cambia, el agricultor elige su cuaderno, pulsa traer y no pasa nada.
 *  2. **Los números que están a cero no se enseñan** (menos «tierras nuevas», que sale siempre: si es
 *     cero, eso también hay que decirlo). Un «0» en un resumen invita a pensar que se ha mirado algo
 *     que no se ha mirado.
 *  3. **El botón de leer dice «Eligiendo el fichero…» mientras lee**, y no se puede volver a pulsar.
 *  4. Los `data-accion` y las clases de siempre. Nada de `esc()` y ninguna frase escrita aquí.
 *
 * El componente es PURO: no llama a `fetch`, no lee ficheros y no toca el DOM.
 */

import { AvisoDeError, Boton, frase, html } from "../componentes.js";

/**
 * La barra de las tres fases de esta pantalla, con la que toca marcada.
 *
 * Del diseño de Stitch de esta pantalla (ronda 90, `docs/stitch/rediseno/cuaderno_de_la_junta.png`):
 * son **tres pantallas en una** (elegir el fichero, mirar el resumen y ver el resultado) y sin una señal
 * de dónde estás, la impresión es que la pantalla no se acaba nunca. Se reutiliza la barra por tramos del
 * asistente (`.pasos`), que ya lleva su `role="progressbar"` para quien use un lector de pantalla: los
 * tramos hechos, en verde, y el que toca, marcado.
 */
function BarraDeFases({ fase }) {
  return html`
    <div className="pasos" role="progressbar" aria-valuenow=${fase} aria-valuemax=${3}>
      ${[1, 2, 3].map(
        (numero) => html`<div key=${numero} className=${numero <= fase ? "paso paso-hecho" : "paso"}></div>`,
      )}
    </div>
  `;
}

/** Una tabla de dos columnas (lo que el agricultor lee de un vistazo). */
function Tabla({ filas }) {
  if (!filas.length) return null;
  return html`
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
  `;
}

/** Los avisos de la lectura del cuaderno, con su título. */
function Avisos({ textos, avisos }) {
  const c = textos.cuaderno_cyl || {};
  if (!avisos.length) return null;
  return html`
    <h2>${frase(c.avisos_titulo)}</h2>
    ${avisos.map((aviso, indice) => html`<p className="aviso" key=${indice}>${frase(aviso)}</p>`)}
  `;
}

/**
 * La pantalla entera.
 *
 * Propiedades:
 *
 *  - `textos`: `{ cuaderno_cyl, acciones }`, tal y como los sirve `/api/interfaz`.
 *  - `resultado`: lo que se ha apuntado, ya contado (`{ cuentas, sin_apuntar, titular, avisos }`), o
 *    nada. Cuando viene, la pantalla es la del resultado.
 *  - `resumen`: lo que trae el fichero (`{ filas, lineas, avisos }`), o nada. Cuando viene (y no hay
 *    resultado), la pantalla es la del resumen.
 *  - `leyendo`: si está leyendo el fichero ahora mismo.
 *  - `error`: lo que ha dicho el servidor.
 */
export function PantallaCuadernoDeLaJunta({
  textos = {},
  resultado = null,
  resumen = null,
  leyendo = false,
  error = "",
}) {
  const c = textos.cuaderno_cyl || {};
  const acciones = textos.acciones || {};

  return html`
    <h1>${frase(c.titulo)}</h1>
    <p className="pista">${frase(c.explica)}</p>
    <${BarraDeFases} fase=${resultado ? 3 : resumen ? 2 : 1} />
    ${
      resultado
        ? html`
            <h2>${frase(c.hecho_titulo)}</h2>
            ${resultado.cuentas.map(
              (cuenta, indice) => html`<p key=${indice}>${frase(cuenta)}</p>`,
            )}
            ${
              resultado.sin_apuntar
                ? html`<p className="aviso aviso-error">${frase(resultado.sin_apuntar)}</p>`
                : null
            }
            <p className="pista-campo">${frase(resultado.titular)}</p>
            <${Avisos} textos=${textos} avisos=${resultado.avisos} />
            <p className="pista-campo">${frase(c.otra_vez)}</p>
            <div className="barra-acciones">
              <${Boton} etiqueta=${c.ver_tierras} accion="mis-cosas" />
              <${Boton} etiqueta=${acciones.volver} accion="cuaderno-volver" clase="boton-claro" />
            </div>
          `
        : resumen
          ? html`
              <h2>${frase(c.resumen_titulo)}</h2>
              <${Tabla} filas=${resumen.filas} />
              <${Avisos} textos=${textos} avisos=${resumen.avisos} />
              <p className="pista-campo">${frase(c.lineas_titulo)}</p>
              <${Tabla} filas=${resumen.lineas} />
              <div className="barra-acciones">
                <${Boton} etiqueta=${c.confirmar} accion="cuaderno-traer" />
                <${Boton} etiqueta=${c.volver} accion="cuaderno-volver" clase="boton-claro" />
              </div>
            `
          : html`
              <p className="pista-campo">${frase(c.como_se_hace)}</p>
              <${AvisoDeError} texto=${error} />
              <div className="campo">
                <label htmlFor="cuaderno-fichero">${frase(c.que_fichero)}</label>
                <input id="cuaderno-fichero" type="file" accept=".xlsx,.xlsm" />
              </div>
              ${
                // El aviso de que leer no apunta nada (ronda 90, del diseño): es la duda que tiene con el
                // dedo encima del botón —«¿esto no me va a pisar lo que ya tengo?»— y va justo antes.
                c.no_apunta_nada
                  ? html`
                      <p className="tarjeta-aviso">
                        <span className="tarjeta-aviso-icono" aria-hidden="true">!</span>
                        ${frase(c.no_apunta_nada)}
                      </p>
                    `
                  : null
              }
              <div className="barra-acciones">
                <button type="button" className="boton" data-accion="cuaderno-leer" disabled=${leyendo}>
                  ${frase(leyendo ? c.eligiendo : c.traer)}
                </button>
                <${Boton} etiqueta=${acciones.volver} accion="cuaderno-volver" clase="boton-claro" />
              </div>
            `
    }
  `;
}

/** El elemento de React de esta pantalla, ya con sus propiedades puestas. */
export function pantallaDeCuadernoDeLaJunta(propiedades) {
  return html`<${PantallaCuadernoDeLaJunta}
    textos=${propiedades.textos}
    resultado=${propiedades.resultado}
    resumen=${propiedades.resumen}
    leyendo=${propiedades.leyendo}
    error=${propiedades.error}
  />`;
}
