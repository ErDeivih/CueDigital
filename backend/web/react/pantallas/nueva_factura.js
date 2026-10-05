/*
 * nueva_factura.js — «Añadir una factura», escrita en React.
 *
 * POR QUÉ ESTA PANTALLA
 *
 * Es la vigésima que se pasa a React y es la puerta del apartado de facturas: aquí el agricultor
 * elige la foto o el fichero que le ha mandado el proveedor y pide que se lea. Lo que se lee **no se
 * guarda nada** hasta que él lo confirma, y esa confirmación es otra pantalla.
 *
 * LO QUE SE CONSERVA A PROPÓSITO
 *
 *  1. **El `id` del campo del fichero** (`factura-fichero`): es como `app.js` coge la foto para
 *     leerla. Si cambia, el agricultor elige la factura, pulsa leer y no pasa nada.
 *  2. **Las tres salidas**, y en este orden: leerla, escribirla a mano (para quien tiene la factura
 *     en papel y prefiere teclearla) y volver a la lista. Ninguna sobra: la lectura puede fallar.
 *  3. **El botón de leer dice «Leyendo la factura…» mientras está leyendo**, y se deshabilita: sin
 *     eso, se puede pulsar dos veces y se manda la misma factura dos veces.
 *  4. Nada de `esc()` y ninguna frase escrita aquí: los textos llegan por propiedades.
 *
 * El componente es PURO: no llama a `fetch`, no lee ficheros y no toca el DOM.
 */

import { AvisoDeError, Boton, frase, html } from "../componentes.js";

/**
 * La pantalla entera.
 *
 * Propiedades:
 *
 *  - `textos`: `{ facturas, acciones }`, tal y como los sirve `/api/interfaz`.
 *  - `leyendo`: si el servidor está leyendo la factura ahora mismo.
 *  - `error`: lo que ha dicho el servidor o lo que falta para poder leerla.
 */
export function PantallaNuevaFactura({ textos = {}, leyendo = false, error = "" }) {
  const f = textos.facturas || {};

  return html`
    <h1>${frase(f.anadir)}</h1>
    <p className="pista">${frase(f.explica)}</p>
    <${AvisoDeError} texto=${error} />
    ${
      // **El fichero es la caja grande de la pantalla** (diseño de Stitch de esta pantalla, ronda 90): lo que
      // se viene a hacer aquí es darle el papel al programa, y un campo de fichero pelado no se ve como algo
      // que se toca. El campo sigue siendo el mismo —con su `id`, que es como `app.js` lo lee— pero va dentro
      // de una caja que se toca entera.
      html`
        <label className="caja-fichero" htmlFor="factura-fichero">
          <span className="caja-fichero-titulo">${frase(f.que_fichero)}</span>
          <span className="caja-fichero-pista">${frase(f.como_se_hace)}</span>
        </label>
        <input id="factura-fichero" className="oculto" type="file" accept=".pdf,image/*" />
      `
    }
    ${
      // **El trato claro** (diseño de Stitch): nada se guarda hasta que él lo mire. Es la duda que tiene con el
      // papel en la mano —«¿esto me lo va a apuntar sin preguntarme?»— y la respuesta es que no.
      f.trato_claro
        ? html`<p className="pista-campo"><strong>${frase(f.trato_claro)}</strong></p>`
        : null
    }
    <div className="barra-acciones">
      <button type="button" className="boton" data-accion="factura-leer" disabled=${leyendo}>
        ${frase(leyendo ? f.leyendo : f.leer)}
      </button>
      <${Boton} etiqueta=${f.a_mano} accion="factura-mano" clase="boton-claro" />
      <${Boton} etiqueta=${f.volver} accion="facturas-abrir" clase="boton-claro" />
    </div>
  `;
}

/** El elemento de React de esta pantalla, ya con sus propiedades puestas. */
export function pantallaDeNuevaFactura(propiedades) {
  return html`<${PantallaNuevaFactura}
    textos=${propiedades.textos}
    leyendo=${propiedades.leyendo}
    error=${propiedades.error}
  />`;
}
