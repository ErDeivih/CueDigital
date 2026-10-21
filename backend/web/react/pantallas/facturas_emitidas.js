/*
 * facturas_emitidas.js — La lista de las facturas **nuestras** de lo vendido (T12).
 *
 * QUÉ ES ESTA PANTALLA, Y QUÉ NO ES (esto importa más que el resto del comentario)
 *
 * **No emite ningún documento con validez oficial.** El contrato lo dice con estas palabras (§4, S12):
 * «La emisión fiscal completa requiere especificación normativa propia antes de activarse como tal».
 * Aquí no hay número de serie oficial, ni impuestos, ni nada que se pueda presentar donde haga falta. Lo
 * que hay es **la cuenta del agricultor**: qué entregó, a quién, por cuánto y qué le deben. Por eso el
 * aviso de que no es un documento oficial se pinta siempre (la pieza `AvisoNoOficial`) y no se puede
 * quitar sin que salte una prueba.
 *
 * LO QUE MUESTRA CADA FICHA, Y POR QUÉ SON TRES NÚMEROS Y NO UNO
 *
 * El total de la factura, lo que ya se ha cobrado y lo que falta. Los tres son distintos y los tres hacen
 * falta: con el total solo, el agricultor no sabe si le deben algo; con el pendiente solo, no sabe de qué
 * le hablan. Y ninguno se calcula aquí: llegan ya escritos del servidor, porque en JavaScript el dinero
 * se perdería por el camino (todo número es de coma flotante) y una cifra de la pantalla no puede ser
 * distinta de la del servidor.
 */

import { Boton, Botones, frase, html } from "../componentes.js";
import { AvisoNoOficial } from "../piezas/campo_de_un_importe.js";

/** La ficha de una factura en la lista, con sus tres números. */
function FichaDeFactura({ factura, textos }) {
  const f = textos.factura_emitida || {};
  return html`
    <li>
      ${
        // La fecha con su rótulo del servidor («Fecha: 20/07/2026») y el estado con su palabra: el color,
        // si lo lleva, es un adorno que va **además** de la palabra y nunca en su lugar.
        factura.fecha ? html`<p className="pista-campo">${frase(factura.fecha_linea)}</p>` : null
      }
      <strong>${frase(factura.titulo)}</strong>
      ${factura.etiqueta_estado ? html`<p className="pista-campo">${frase(factura.etiqueta_estado)}</p>` : null}
      <dl>
        <div className="resumen-dato">
          <dt>${frase(f.total)}</dt>
          <dd>${frase(factura.texto_total)}</dd>
        </div>
        <div className="resumen-dato">
          <dt>${frase(f.cobrado)}</dt>
          <dd>${frase(factura.texto_cobrado)}</dd>
        </div>
        <div className="resumen-dato">
          <dt>${frase(f.pendiente)}</dt>
          <dd>${frase(factura.texto_pendiente)}</dd>
        </div>
        <div className="resumen-dato">
          <dt>${frase(f.entregas)}</dt>
          <dd>${frase(String(factura.entregas))}</dd>
        </div>
      </dl>
      <${Botones}
        botones=${[
          {
            etiqueta: f.ver_ficha,
            accion: "factura-emitida-abrir",
            datos: { id: factura.id },
            sencillo: true,
          },
        ]}
        barra=${false}
      />
    </li>
  `;
}

/**
 * La lista entera.
 *
 * Propiedades:
 *
 *  - `textos`: `{ factura_emitida, venta, acciones }`, tal y como los sirve `/api/interfaz`.
 *  - `facturas`: las facturas del año, con su total, su cobrado y su pendiente **ya calculados**.
 *  - `resumen`: cuántas hay con algo por cobrar, en singular o plural (lo elige `app.js`, que es quien
 *    tiene el número).
 *  - `error`: lo que ha dicho el servidor, o nada.
 */
export function PantallaFacturasEmitidas({
  textos = {},
  facturas = [],
  resumen = "",
  error = "",
  // ***Y si la carga fallo*** (21/10/2026, D03): *«no hay facturas emitidas» es una afirmacion sobre lo que el
  // agricultor ha facturado; no se puede hacer sin haber podido preguntar.*
  noSePudoCargar = false,
}) {
  const f = textos.factura_emitida || {};
  const acciones = textos.acciones || {};
  return html`
    <h1>${frase(f.titulo)}</h1>
    <p className="pista">${frase(f.explica)}</p>
    <${AvisoNoOficial} textos=${textos} />
    ${error ? html`<p className="aviso-error" role="alert">${frase(error)}</p>` : null}
    ${resumen ? html`<p className="cuantas">${frase(resumen)}</p>` : null}
    ${
      facturas.length === 0
        ? noSePudoCargar
          ? html`<div className="aviso aviso-error">${frase(f.sin_nada_fallo)}</div>`
          : html`<div className="aviso">${frase(f.sin_nada)}</div>`
        : html`<ul className="lista">
            ${facturas.map(
              (factura, indice) => html`<${FichaDeFactura} key=${indice} factura=${factura} textos=${textos} />`,
            )}
          </ul>`
    }
    <div className="barra-acciones">
      <${Boton} etiqueta=${f.nueva} accion="factura-emitida-nueva" />
      <${Boton} etiqueta=${acciones.volver} accion="ventas-ver" clase="boton-claro" />
    </div>
  `;
}

/** El elemento de React de esta pantalla, ya con sus propiedades puestas. */
export function pantallaDeFacturasEmitidas(propiedades) {
  return html`<${PantallaFacturasEmitidas}
    textos=${propiedades.textos}
    facturas=${propiedades.facturas}
      noSePudoCargar=${propiedades.noSePudoCargar}
    resumen=${propiedades.resumen}
    error=${propiedades.error}
  />`;
}
