/*
 * factura_emitida.js — La ficha de una factura nuestra: lo que va dentro, lo que te han pagado y lo que queda (T12).
 *
 * LO QUE ESTA PANTALLA TIENE QUE DECIR, Y POR QUÉ ES DIFÍCIL
 *
 *  1. **El total, lo cobrado y lo pendiente**, los tres ya calculados por el servidor. Es la respuesta a
 *     la única pregunta que se hace aquí: «¿cuánto me deben de esto?».
 *  2. **La diferencia observada, si la hay.** Si una entrega se corrigió después de facturarla, la línea
 *     conserva el importe del día en que se emitió y aquí sale la diferencia con las dos cifras. Es lo que
 *     el contrato pide («registrar diferencias observadas sin forzar a que una factura original cuadre con
 *     un redondeo distinto») y lo contrario de reescribir el documento, que sí sería mentir.
 *  3. **Los pagos que la saldan**, cada uno con lo que de él va contra esta factura. Un pago se apunta
 *     contra una factura y con **una** cantidad, así que el mismo dinero no puede estar contado dos veces.
 *  4. **Y el aviso de que esto no es un documento oficial** (la pieza `AvisoNoOficial`), que no se puede
 *     quitar de aquí sin que salte una prueba.
 *
 * Lo que no hace: ni una cuenta (todo llega en texto, ya calculado, porque el dinero no se suma en el
 * navegador) y ni una frase escrita a mano (los textos son del servidor).
 */

import { Boton, Botones, frase, html } from "../componentes.js";
import { AvisoNoOficial } from "../piezas/campo_de_un_importe.js";

/** Una línea de la factura: la entrega, con la fotografía del día que se emitió. */
function Linea({ linea, textos }) {
  const f = textos.factura_emitida || {};
  const v = textos.venta || {};
  return html`
    <li>
      <strong>${frase(linea.descripcion || f.linea_sin_entrega)}</strong>
      <dl>
        <div className="resumen-dato">
          <dt>${frase(v.tabla_fecha)}</dt>
          <dd>${frase(linea.fecha || "")}</dd>
        </div>
        <div className="resumen-dato">
          <dt>${frase(v.tabla_cantidad)}</dt>
          <dd>${frase(linea.cantidad ? `${linea.cantidad} ${linea.unidad || ""}`.trim() : "")}</dd>
        </div>
        <div className="resumen-dato">
          <dt>${frase(v.tabla_importe)}</dt>
          <dd>${frase(linea.texto_importe)}</dd>
        </div>
      </dl>
      ${
        // La diferencia observada, dicha con las dos cifras y su explicación del servidor.
        linea.diferencia
          ? html`<p className="tarjeta-aviso">
              <span className="tarjeta-aviso-icono" aria-hidden="true">!</span>
              ${frase(f.diferencia)}
            </p>`
          : null
      }
      ${
        // Y si la entrega ya no está (se borró), se dice en vez de enseñar una línea sin nada detrás.
        linea.entrega_existe === false ? html`<p className="pista-campo">${frase(f.linea_sin_entrega)}</p>` : null
      }
    </li>
  `;
}

/** Un cobro dentro de la factura, con lo que de él va contra ella. */
function Pago({ cobro, textos, factura }) {
  const c = textos.cobro || {};
  return html`
    <li>
      <strong>${frase(cobro.texto_imputado || cobro.texto_importe)}</strong>
      <dl>
        <div className="resumen-dato">
          <dt>${frase(c.fecha)}</dt>
          <dd>${frase(cobro.fecha || "")}</dd>
        </div>
        <div className="resumen-dato">
          <dt>${frase(c.forma)}</dt>
          <dd>${frase(cobro.etiqueta_forma)}</dd>
        </div>
        <div className="resumen-dato">
          <dt>${frase(c.referencia)}</dt>
          <dd>${frase(cobro.referencia || "")}</dd>
        </div>
      </dl>
      <${Botones}
        botones=${[
          {
            etiqueta: c.anular,
            accion: "cobro-anular",
            datos: { id: cobro.id, factura: factura.id },
            clase: "boton-claro",
            sencillo: true,
          },
        ]}
        barra=${false}
      />
    </li>
  `;
}

/**
 * La pantalla entera.
 *
 * Propiedades:
 *
 *  - `textos`: `{ factura_emitida, venta, cobro, acciones }` del servidor.
 *  - `factura`: la factura con sus líneas, sus cobros y sus tres números ya calculados.
 *  - `error`: lo que ha dicho el servidor, o nada.
 */
export function PantallaFacturaEmitida({ textos = {}, factura = {}, error = "" }) {
  const f = textos.factura_emitida || {};
  const c = textos.cobro || {};
  const acciones = textos.acciones || {};
  const lineas = factura.lineas || [];
  const cobros = factura.cobros || [];
  return html`
    <h1>${frase(factura.titulo)}</h1>
    <${AvisoNoOficial} textos=${textos} />
    ${error ? html`<p className="aviso-error" role="alert">${frase(error)}</p>` : null}

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
    </dl>
    <p className="pista-campo">${frase(factura.etiqueta_estado)}</p>
    ${
      // **Si está quitada, se dice lo que se está viendo** (revisión del T12): el total y las líneas que
      // salen debajo son los del día que se hizo, y no cuentan en lo que te deben. Y por eso una factura
      // quitada **no** se anuncia como «cobrada entera», que es lo que salía antes por su cero.
      factura.anulada
        ? html`<p className="tarjeta-aviso">
            <span className="tarjeta-aviso-icono" aria-hidden="true">!</span>${frase(f.anulada_lo_que_decia)}
          </p>`
        : // Si está cobrada entera se dice con palabras, y no se deja al agricultor deducirlo de un cero.
          factura.pendiente === "0.00"
          ? html`<p className="cuantas">${frase(f.cobrada_entera)}</p>`
          : null
    }

    <h2>${frase(f.lineas)}</h2>
    <ul className="lista">
      ${lineas.map((linea, indice) => html`<${Linea} key=${indice} linea=${linea} textos=${textos} />`)}
    </ul>

    <h2>${frase(f.pagos)}</h2>
    ${
      cobros.length === 0
        ? html`<p className="pista-campo">${frase(f.sin_pagos)}</p>`
        : html`<ul className="lista">
            ${cobros.map(
              (cobro, indice) => html`<${Pago} key=${indice} cobro=${cobro} textos=${textos} factura=${factura} />`,
            )}
          </ul>`
    }

    <div className="barra-acciones">
      <${Boton} etiqueta=${f.apuntar_cobro} accion="cobro-nuevo" datos=${{ factura: factura.id }} />
      <${Boton}
        etiqueta=${f.anular}
        accion="factura-emitida-anular"
        datos=${{ id: factura.id }}
        clase="boton-claro"
      />
      <${Boton} etiqueta=${acciones.volver} accion="facturas-emitidas-ver" clase="boton-claro" />
    </div>
  `;
}

/** El elemento de React de esta pantalla, ya con sus propiedades puestas. */
export function pantallaDeUnaFacturaEmitida(propiedades) {
  return html`<${PantallaFacturaEmitida}
    textos=${propiedades.textos}
    factura=${propiedades.factura}
    error=${propiedades.error}
  />`;
}
