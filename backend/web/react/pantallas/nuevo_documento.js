/*
 * nuevo_documento.js — «Guardar un papel», escrito en React.
 *
 * POR QUÉ ESTA PANTALLA
 *
 * Es la decimoquinta que se pasa a React y **cierra el apartado de los papeles**: la lista ya era de
 * React y lo que quedaba era el formulario con el que se guarda uno.
 *
 * **Es la pantalla con más campos migrada hasta ahora: seis.** Y por eso es la que mejor enseña el
 * patrón que vale para todas las que quedan: los campos son **descontrolados** (React los pinta con
 * su `id` y no los gobierna), y quien lee lo que el agricultor ha escrito es `app.js`
 * (`guardarDocumento()`), porque el manejador de clics es uno solo y vive allí. Si un `id` cambia,
 * el agricultor rellena el formulario y se guarda un papel **sin título, sin carpeta y sin fecha**,
 * sin que salte ningún error. Por eso los `id` se conservan tal cual y hay una prueba que los mira
 * uno a uno, más otra que rellena el formulario en un navegador de verdad y comprueba que el papel
 * se guarda con lo que se escribió.
 *
 * LO QUE SE CONSERVA A PROPÓSITO
 *
 *  1. Los `id` de los seis campos: `papel-titulo`, `papel-tipo`, `papel-carpeta` (con su
 *     `datalist` de carpetas sugeridas), `papel-fecha`, `papel-quien` y `papel-notas`.
 *  2. Que «otros» venga elegido en la lista de qué es: es el caso de casi todos los papeles que no
 *     son ni contrato ni factura, y era el valor por defecto de la pantalla vieja.
 *  3. Los `data-accion` (`papel-guardar`, `papel-ver-todos`) y las mismas clases.
 *  4. Nada de `esc()` y ninguna frase escrita aquí: los textos llegan del servidor.
 *
 * El componente es PURO: no llama a `fetch`, no lee `localStorage` y no toca el DOM.
 */

import { AvisoDeError, Boton, BotonSencillo, frase, html } from "../componentes.js";

/**
 * Un campo del formulario: su etiqueta, su pista y lo que se escribe dentro.
 *
 * Va aquí porque los seis campos son iguales salvo en eso, y copiar seis veces el mismo bloque es
 * como se acaba teniendo un campo con la pista en otro sitio.
 */
function Campo({ id, etiqueta, pista, children }) {
  return html`
    <div className="campo">
      <label htmlFor=${id}>${frase(etiqueta)}</label>
      ${pista ? html`<p className="pista-campo">${frase(pista)}</p>` : null}
      ${children}
    </div>
  `;
}

/**
 * La pantalla entera.
 *
 * Propiedades:
 *
 *  - `textos`: `{ documentos, acciones }`, tal y como los sirve `/api/interfaz`.
 *  - `tipos`: las clases de papel (`[{valor, etiqueta}]`), del catálogo del servidor. No se escriben
 *    aquí: en el servidor es donde se sabe qué clases hay.
 *  - `carpetas`: las carpetas que ya tiene el agricultor, para sugerirlas en el campo de texto.
 *  - `error`: lo que ha dicho el servidor cuando no se ha podido guardar.
 */
export function PantallaNuevoDocumento({
  textos = {},
  tipos = [],
  carpetas = [],
  error = "",
  papel = null,
  corrigiendo = false,
}) {
  const d = textos.documentos || {};
  const acciones = textos.acciones || {};
  // Lo que ya estaba, cuando se está **corrigiendo** un papel (ronda 93). Es `null` al guardar uno nuevo,
  // y entonces todos los campos van vacíos como iban. Los campos siguen siendo **descontrolados** (los lee
  // `app.js` por su `id`): lo único que cambia es lo que traen puesto de salida.
  const suyo = papel || {};

  return html`
    <h1>${frase(corrigiendo ? textos.corregir_el_papel : d.nuevo)}</h1>
    <p className="pista">${frase(corrigiendo ? textos.pista_corregir : d.para_que)}</p>
    <${AvisoDeError} texto=${error} />
    ${
      // Los campos **numerados** (diseño de Stitch de esta pantalla, ronda 90): son seis renglones y, sin
      // números, no se sabe cuánto queda. El número lo pone el CSS con un contador.
      html`
        <ol className="campos-numerados">
          <li>
            <${Campo} id="papel-titulo" etiqueta=${d.titulo_del_papel} pista=${d.titulo_pista}>
              ${
                // El único campo que hace falta de verdad, dicho con su etiqueta: sin nombre no se guarda el
                // papel (la pantalla lo dice y no lo guarda).
                d.hace_falta
                  ? html`<span className="etiqueta-estado etiqueta-estado-obligatorio"
                      >${frase(d.hace_falta)}</span
                    >`
                  : null
              }
              <input
                id="papel-titulo"
                type="text"
                autoComplete="off"
                defaultValue=${suyo.titulo || ""}
              />
            <//>
          </li>
          <li>
            <${Campo} id="papel-tipo" etiqueta=${d.que_es}>
              <select id="papel-tipo">
                ${tipos.map(
                  (tipo) => html`
                    <option
                      value=${tipo.valor}
                      selected=${tipo.valor === (suyo.tipo || "otros")}
                      key=${tipo.valor}
                    >
                      ${frase(tipo.etiqueta)}
                    </option>
                  `,
                )}
              </select>
            <//>
          </li>
          <li>
            <${Campo} id="papel-carpeta" etiqueta=${d.carpeta} pista=${d.carpeta_pista}>
              ${
                // **Las carpetas que ya tiene, para tocarlas** (diseño de Stitch): en el móvil, y con guantes,
                // escribir el nombre de la carpeta es lo que más cuesta. Se toca una y se rellena el campo —
                // lo rellena `app.js`, que es quien lee los campos por su `id`—, y si ninguna vale se
                // escribe una nueva como antes.
                carpetas.length
                  ? html`
                      <p className="pista-campo">${frase(d.toca_una)}</p>
                      <div className="barra-acciones">
                        ${carpetas.map(
                          (nombre) => html`<${BotonSencillo}
                            key=${nombre}
                            etiqueta=${nombre}
                            accion="papel-carpeta"
                            datos=${{ nombre }}
                          />`,
                        )}
                      </div>
                    `
                  : null
              }
              <input
                id="papel-carpeta"
                type="text"
                list="papel-carpetas"
                autoComplete="off"
                defaultValue=${suyo.carpeta || ""}
              />
              <datalist id="papel-carpetas">
                ${carpetas.map((nombre) => html`<option value=${nombre} key=${nombre}></option>`)}
              </datalist>
            <//>
          </li>
          <li>
            <${Campo} id="papel-fecha" etiqueta=${d.fecha_del_papel} pista=${d.fecha_pista}>
              <input id="papel-fecha" type="date" defaultValue=${suyo.fecha || ""} />
            <//>
          </li>
          <li>
            <${Campo} id="papel-quien" etiqueta=${d.quien} pista=${d.quien_pista}>
              <input
                id="papel-quien"
                type="text"
                autoComplete="off"
                defaultValue=${suyo.quien || ""}
              />
            <//>
          </li>
          <li>
            <${Campo} id="papel-notas" etiqueta=${d.notas}>
              <textarea id="papel-notas" rows="2" defaultValue=${suyo.notas || ""}></textarea>
            <//>
          </li>
        </ol>
      `
    }
    ${
      // **El papel, en la misma pantalla** (diseño de Stitch): antes había que guardarlo, ir a la lista y
      // subirlo desde allí. El campo se lee por su `id` (`papel-fichero`) y `app.js` lo manda después de
      // crear el papel, por el camino que ya existe (`POST /api/documentos/{id}/fichero`). Al corregir
      // sirve igual: se elige otro fichero y sustituye al que había.
      html`
        <div className="campo">
          <label htmlFor="papel-fichero">${frase(d.el_fichero)}</label>
          <p className="pista-campo">${frase(d.fichero_pista)}</p>
          <input id="papel-fichero" type="file" accept=".pdf,image/*" />
        </div>
      `
    }
    <div className="barra-acciones">
      <${Boton}
        etiqueta=${corrigiendo ? textos.guardar_cambios : acciones.guardar}
        accion="papel-guardar"
      />
      <${Boton} etiqueta=${acciones.volver} accion="papel-ver-todos" clase="boton-claro" />
    </div>
  `;
}

/** El elemento de React de esta pantalla, ya con sus propiedades puestas. */
export function pantallaDeNuevoDocumento(propiedades) {
  return html`<${PantallaNuevoDocumento}
    textos=${propiedades.textos}
    tipos=${propiedades.tipos}
    carpetas=${propiedades.carpetas}
    error=${propiedades.error}
    papel=${propiedades.papel}
    corrigiendo=${propiedades.corrigiendo}
  />`;
}
