/*
 * facturar_entregas.js — Juntar entregas en una factura nuestra (T12).
 *
 * LA PANTALLA QUE IMPIDE CONTAR EL DINERO DOS VECES
 *
 * El contrato lo pide con estas palabras (§4, S12): «Una entrega puede facturarse después o agruparse;
 * **no duplicar ingresos al agrupar**». Aquí está la mitad visible de esa regla: las entregas que **ya
 * están** en una factura salen dichas una por una, con la frase del servidor («Esa entrega ya está dentro
 * de la factura F-2026-1…»), y no se pueden marcar. La otra mitad está en la base de datos —una entrega
 * viva solo puede estar en una factura viva—, así que aunque esta pantalla se equivocara, la base no
 * dejaría contar el dinero dos veces.
 *
 * Y LAS QUE NO SE PUEDEN FACTURAR TODAVÍA SE DICEN TAMBIÉN
 *
 * Una entrega **sin importe** no se puede facturar: es el caso A08 del contrato (cantidad conocida e
 * importe pendiente). En vez de esconderla, la pantalla dice qué hacer: ponerle el importe primero. Es la
 * regla de este programa entera —«si le dices al agricultor que le falta algo, le das el botón que lo
 * arregla»—, y aquí el botón está en la pantalla de lo que se ha vendido.
 *
 * Lo que no hace: ni una cuenta (el importe de la factura lo suma el servidor con `Decimal`) y ni una
 * frase escrita a mano (los rótulos y las frases son del servidor).
 */

import { Boton, frase, html } from "../componentes.js";
import { AvisoNoOficial, Campo } from "../piezas/campo_de_un_importe.js";

/**
 * La pantalla entera.
 *
 * Propiedades:
 *
 *  - `textos`: `{ factura_emitida, venta, acciones }` del servidor.
 *  - `entregas`: las del año, cada una con `titulo`, si ya está facturada y en qué factura, y si se ha
 *    marcado (`elegida`).
 *  - `borrador`: los cuatro campos de la factura (número, fecha, vencimiento, cliente, notas).
 *  - `contactos`: las fichas de los clientes, para enlazar la factura con una.
 *  - `error`: lo que ha dicho el servidor, o nada.
 */
export function PantallaFacturarEntregas({ textos = {}, entregas = [], borrador = {}, contactos = [], error = "" }) {
  const f = textos.factura_emitida || {};
  const acciones = textos.acciones || {};
  const elegibles = entregas.filter((entrega) => !entrega.facturada && entrega.importe);
  const sinImporte = entregas.filter((entrega) => !entrega.importe);
  return html`
    <h1>${frase(f.nueva_titulo)}</h1>
    <p className="pista">${frase(f.nueva_explica)}</p>
    <${AvisoNoOficial} textos=${textos} />
    ${error ? html`<p className="aviso-error" role="alert">${frase(error)}</p>` : null}

    ${
      sinImporte.length
        ? html`<p className="tarjeta-aviso">
            <span className="tarjeta-aviso-icono" aria-hidden="true">!</span>${frase(f.sin_importe_aun)}
          </p>`
        : null
    }

    ${
      // Las que sí se pueden marcar. Cada una lleva su casilla con el `id` y el `data-id` que lee `app.js`:
      // lo que está marcado vive en el estado de la aplicación y no en el componente, que es lo que hace
      // que un repintado no pierda lo marcado.
      elegibles.length === 0
        ? html`<div className="aviso">${frase(f.elegir_una)}</div>`
        : html`<ul className="lista">
            ${elegibles.map(
              (entrega) => html`
                <li key=${entrega.id}>
                  <label className="campo-casilla">
                    <input
                      type="checkbox"
                      id=${`facturar-${entrega.id}`}
                      data-accion="facturar-marcar"
                      data-id=${entrega.id}
                      checked=${Boolean(entrega.elegida)}
                    />
                    <span>${frase(entrega.titulo)}</span>
                  </label>
                  <p className="pista-campo">${frase(entrega.texto_importe)}</p>
                </li>
              `,
            )}
          </ul>`
    }

    ${
      // Y las que ya están dentro de otra factura, con la frase del servidor: es lo que hace imposible
      // meter la misma entrega dos veces y, con ello, contar el dinero dos veces.
      entregas.some((entrega) => entrega.aviso_facturada)
        ? html`<div>
            ${entregas
              .filter((entrega) => entrega.aviso_facturada)
              .map(
                (entrega, indice) => html`<p className="pista-campo" key=${indice}>
                  ${frase(entrega.aviso_facturada)}
                </p>`,
              )}
          </div>`
        : null
    }

    <${Campo}
      id="factura-emitida-numero"
      etiqueta=${f.numero}
      pista=${f.numero_pista}
      valor=${borrador.numero}
    />
    <${Campo} id="factura-emitida-fecha" etiqueta=${f.fecha} tipo="fecha" valor=${borrador.fecha} />
    <${Campo}
      id="factura-emitida-vencimiento"
      etiqueta=${f.vencimiento}
      tipo="fecha"
      valor=${borrador.vencimiento}
    />
    <${Campo} id="factura-emitida-cliente" etiqueta=${f.cliente} valor=${borrador.cliente} />
    ${
      // **Con qué ficha de cliente queda enlazada la factura** (revisión del T12): es lo que permite
      // preguntar «¿cuánto me debe la cooperativa?» sin comparar nombres a ojo. La lista son sus
      // contactos, tal cual, y sin elegir ninguno la factura se queda como estaba.
      contactos.length > 1
        ? html`<${Campo}
            id="factura-emitida-contacto"
            etiqueta=${f.cliente_ficha}
            pista=${f.cliente_ficha_pista}
            opciones=${contactos}
            valor=${borrador.contacto_id}
          />`
        : null
    }
    <${Campo} id="factura-emitida-notas" etiqueta=${f.notas} valor=${borrador.notas} />

    <div className="barra-acciones">
      <button type="button" className="boton" data-accion="factura-emitida-guardar">
        ${frase(acciones.guardar)}
      </button>
      <${Boton} etiqueta=${acciones.volver} accion="facturas-emitidas-ver" clase="boton-claro" />
    </div>
  `;
}

/** El elemento de React de esta pantalla, ya con sus propiedades puestas. */
export function pantallaDeFacturarEntregas(propiedades) {
  return html`<${PantallaFacturarEntregas}
    textos=${propiedades.textos}
    entregas=${propiedades.entregas}
    borrador=${propiedades.borrador}
    contactos=${propiedades.contactos}
    error=${propiedades.error}
  />`;
}
