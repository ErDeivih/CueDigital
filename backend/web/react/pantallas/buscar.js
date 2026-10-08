/**
 * La búsqueda global: la pantalla.
 *
 * Es la pieza que le faltaba a la caja de la cabecera. **Lo que se enseña no se decide aquí**: eso está en
 * `nucleo.losGruposDeLaBusqueda`, que es donde se puede probar sin navegador (los grupos, sus nombres, el
 * aviso de «cortado» y las dos frases que no son un error). Esta pantalla **solo pinta** lo que aquello
 * devuelve, y las palabras las pide al servidor: aquí no hay ni una frase escrita a mano.
 *
 * Propiedades:
 *
 *  - `textos`: el bloque `buscar` de `/api/interfaz`.
 *  - `resultado`: lo que contestó `GET /api/buscar` (o `null` si todavía no se ha buscado).
 *  - `puedeBuscar`: si el agricultor tiene permiso para buscar (por defecto, sí).
 *
 * El cuadro y el botón los pinta **la pantalla**, y llevan los mismos `id` y `data-accion` que usa el resto
 * de la aplicación: el manejador de clics de siempre los lee sin que haya nada nuevo que aprender.
 */

import { frase, html } from "../componentes.js";
import { losGruposDeLaBusqueda } from "../../nucleo.js";

export function PantallaBuscar({ textos = {}, resultado = null, puedeBuscar = true }) {
  const t = textos.buscar || {};
  const suyo = losGruposDeLaBusqueda(resultado, t);

  return html`
    <h1>${frase(t.titulo)}</h1>
    <p className="pista">${frase(t.pista)}</p>

    <div className="campo">
      <label className="etiqueta-campo" for="buscar_global">${frase(t.caja)}</label>
      <input
        id="buscar_global"
        type="search"
        value=${suyo.texto}
        placeholder=${frase(t.caja)}
        disabled=${!puedeBuscar}
      />
      <div className="barra-acciones">
        <button type="button" className="boton boton-principal" data-accion="buscar" disabled=${!puedeBuscar}>
          ${frase(t.boton)}
        </button>
      </div>
    </div>

    ${
      // **Las dos frases que no son un error**: no se ha buscado nada todavía, o se ha buscado y no hay
      // nada. La primera no es un fracaso y la segunda tampoco: se dicen y ya está.
      suyo.mensaje ? html`<div className="aviso"><p className="pista-campo">${frase(suyo.mensaje)}</p></div>` : null
    }

    ${suyo.grupos.map(
      (grupo, indice) => html`
        <div className="tarjeta" key=${`${grupo.clave}-${indice}`}>
          <h2>${frase(grupo.titulo)}</h2>
          ${
            // Y si el grupo se ha cortado, se dice: un grupo de diez resultados que en realidad son
            // cuarenta, sin avisar, hace creer que solo hay diez.
            grupo.aviso_cortado ? html`<p className="pista-campo">${frase(grupo.aviso_cortado)}</p>` : null
          }
          <ul className="lista">
            ${grupo.lineas.map(
              (linea, suyoIndice) => html`
                <li key=${`${grupo.clave}-${suyoIndice}`}>
                  <strong>${frase(linea.etiqueta)}</strong>
                  ${
                    // El detalle es el importe, la matrícula o el teléfono, y puede no constar: entonces no
                    // se enseña nada (ni un guion ni un cero, que dirían que hay un dato).
                    linea.detalle ? html`<span className="pista-campo"> ${frase(linea.detalle)}</span>` : null
                  }
                </li>
              `,
            )}
          </ul>
        </div>
      `,
    )}
  `;
}

/** El elemento de React de esta pantalla, ya con sus propiedades puestas. */
export function pantallaDeLaBusqueda(propiedades) {
  return html`<${PantallaBuscar}
    pantalla=${propiedades.pantalla}
    textos=${propiedades.textos}
    resultado=${propiedades.resultado}
    puedeBuscar=${propiedades.puedeBuscar}
  />`;
}
