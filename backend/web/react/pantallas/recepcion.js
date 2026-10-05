/*
 * recepcion.js — La ficha de un albarán (T09), escrita en React.
 *
 * POR QUÉ ESTA PANTALLA
 *
 * Un albarán apuntado no puede ser una línea en una lista que no se puede abrir: lo que trae el papel
 * —cada producto, cuánto, de qué lote y hasta cuándo vale— es lo que después se mira cuando el
 * fabricante avisa de una partida o cuando llega una inspección. Y hay dos cosas que solo se pueden
 * hacer desde aquí:
 *
 *  1. **Anular el albarán**, con su motivo. Nada se borra: queda con lo que dijo el papel y sus
 *     entradas dejan de contar en el almacén. Es el camino para arreglar un albarán mal apuntado —y el
 *     que el propio programa propone cuando reconoce que ese albarán ya estaba apuntado—.
 *  2. **Decir de qué factura es**, cuando la factura llega después. Eso **no mete mercancía otra vez**:
 *     la mercancía entró el día que llegó el camión, y esta pantalla lo dice con esas palabras.
 *
 * LO QUE NO HACE
 *
 *  · **No calcula ni suma nada.** Las líneas y sus cuentas vienen del servidor, con los nombres ya
 *    resueltos (no se cruzan listas aquí).
 *  · **No borra.** Anular pide el motivo y lo manda; el motivo es lo único que explica dentro de dos
 *    años por qué ese papel no cuenta.
 *  · **No enseña un cero donde no hay dato**: si una línea no trae cantidad, se dice que no la trae.
 *  · Ni una frase escrita aquí: todo llega por propiedades.
 *
 * El `id` del campo del motivo (`albaran-motivo-anulacion`) es el que lee `app.js`: igual que en el
 * resto de la aplicación, lo que se escribe se lee por el `id` del campo.
 */

import { AvisoDeError, Boton, Botones, frase, html } from "../componentes.js";

/** Una línea de lo que venía: qué, cuánto, de qué lote y hasta cuándo vale. */
function LineaDelAlbaran({ linea, textos }) {
  const c = textos.cesta || {};
  return html`
    <li>
      <div className="apunte-cabecera">
        <strong>${frase(linea.que_es)}</strong>
        <span>${frase(linea.cantidad)}</span>
      </div>
      <div className="apunte-detalle">${frase(c.libro_lote)}: ${frase(linea.lote)}</div>
      <div className="apunte-detalle">${frase(c.libro_caducidad)}: ${frase(linea.caducidad)}</div>
      ${
        // El envase y dónde está guardado: son datos del lote, y en una inspección el envase es lo que
        // se tiene en la mano. Si no constan, la fila no se pinta: un hueco es mejor que un invento.
        linea.envase ? html`<div className="apunte-detalle">${frase(c.libro_envase)}: ${frase(linea.envase)}</div>` : null
      }
      ${
        linea.donde
          ? html`<div className="apunte-detalle">${frase(c.libro_donde_esta)}: ${frase(linea.donde)}</div>`
          : null
      }
      ${
        // Si el lote no trae número, se dice **y se explica por qué importa** (es lo que permite
        // seguirle la pista si el fabricante avisa).
        linea.sin_numero
          ? html`<p className="pista-campo">${frase(c.libro_sin_numero_de_lote_pista)}</p>`
          : null
      }
    </li>
  `;
}

/**
 * La ficha entera.
 *
 * Propiedades:
 *
 *  - `textos`: `{ cesta, acciones }` del servidor.
 *  - `recepcion`: la cabecera (título, fecha, proveedor, notas, si está anulada y con qué motivo,
 *    cuántas entradas metió) y sus líneas ya preparadas.
 *  - `factura`: si este albarán ya tiene factura o no, con la frase que lo dice.
 *  - `anulando`: si se está preguntando el motivo para anular (entonces sale el campo y los dos
 *    botones: anular pide una razón, siempre).
 *  - `error`: lo que ha dicho el servidor, o nada.
 */
export function PantallaRecepcion({
  textos = {},
  recepcion = {},
  factura = {},
  anulando = false,
  error = "",
}) {
  const c = textos.cesta || {};
  const lineas = recepcion.lineas || [];
  return html`
    <h1>${frase(recepcion.titulo)}</h1>
    <p className="pista">${frase(recepcion.cuando)}</p>
    <${AvisoDeError} texto=${error} />
    ${
      // Un albarán anulado se dice arriba y con palabras, además de en su etiqueta: es lo primero que
      // hay que saber de él, porque sus entradas no cuentan.
      recepcion.anulado
        ? html`<div className="aviso aviso-error">${frase(recepcion.anulado)}</div>`
        : null
    }
    <dl>
      ${(recepcion.filas || []).map(
        (fila, indice) => html`
          <div className="resumen-dato" key=${indice}>
            <dt>${frase(fila.etiqueta)}</dt>
            <dd>${frase(fila.valor)}</dd>
          </div>
        `,
      )}
    </dl>
    ${
      recepcion.notas
        ? html`<div className="ayuda-campo"><p>${frase(recepcion.notas)}</p></div>`
        : null
    }

    <h2>${frase(c.libro_lineas)}</h2>
    ${
      recepcion.entradas
        ? html`<p className="cuantas">${frase(recepcion.entradas)}</p>`
        : html`<p className="pista-campo">${frase(recepcion.sin_entradas)}</p>`
    }
    <ul className="lista">
      ${lineas.map(
        (linea, indice) => html`<${LineaDelAlbaran} key=${indice} linea=${linea} textos=${textos} />`,
      )}
    </ul>

    <h2>${frase(c.libro_factura_de)}</h2>
    ${
      factura.hay
        ? html`<div className="aviso">${frase(c.libro_factura_enganchada)}</div>`
        : html`
            <p>${frase(c.libro_factura_sin)}</p>
            <p className="pista-campo">${frase(c.libro_factura_explica)}</p>
          `
    }
    ${
      // El botón solo sale cuando **no** tiene factura: volver a engancharla no es nada que el
      // agricultor pueda querer, y un botón que lleva a «ya estaba» es un botón de más.
      factura.hay
        ? null
        : html`<${Boton}
            etiqueta=${c.libro_engancharla}
            accion="factura-enganchar"
            datos=${{ id: recepcion.id }}
            clase="boton-claro"
          />`
    }

    ${
      // Anular: primero el motivo (el motivo es lo único que lo explica), y solo después se manda.
      anulando
        ? html`
            <div className="campo">
              <label htmlFor="albaran-motivo-anulacion">${frase(c.libro_anular_pregunta)}</label>
              <p className="pista-campo">${frase(c.libro_anular_pista)}</p>
              <input id="albaran-motivo-anulacion" type="text" />
            </div>
            <div className="barra-acciones">
              <button
                type="button"
                className="boton boton-peligro"
                data-accion="albaran-anular-si"
                data-id=${recepcion.id}
              >
                ${frase(c.libro_anular_si)}
              </button>
              <${Boton} etiqueta=${c.libro_anular_no} accion="albaran-abrir" datos=${{ id: recepcion.id }} clase="boton-claro" />
            </div>
          `
        : recepcion.anulado
          ? null
          : html`<div className="barra-acciones">
              <${Boton}
                etiqueta=${c.libro_anular}
                accion="albaran-anular"
                datos=${{ id: recepcion.id }}
                clase="boton-peligro"
              />
            </div>`
    }

    <${Botones} botones=${recepcion.acciones} />
  `;
}

/** El elemento de React de esta pantalla, ya con sus propiedades puestas. */
export function pantallaDeRecepcion(propiedades) {
  return html`
    <${PantallaRecepcion}
      textos=${propiedades.textos}
      recepcion=${propiedades.recepcion}
      factura=${propiedades.factura}
      anulando=${propiedades.anulando}
      error=${propiedades.error}
    />
  `;
}
