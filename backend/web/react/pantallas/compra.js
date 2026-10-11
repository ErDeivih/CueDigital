/*
 * compra.js — La ficha de una compra (S11): facturado, recibido, pagado y pendiente (09/10/2026).
 *
 * POR QUÉ ESTA PANTALLA
 *
 * Las cuatro cifras de una compra estaban en tres pantallas distintas y **nadie las juntaba**: la
 * factura en «Mis facturas», lo que entró en el almacén y el dinero en «Gastos». Así que la pregunta
 * que de verdad se hace el agricultor —«¿cuánto me falta por pagar de esto?» y «¿me ha llegado ya todo?»
 * — había que contestarla recorriendo las tres a mano y sumando de cabeza.
 *
 * Aquí están las cuatro juntas, y **cada una dice de dónde sale**, porque son cosas distintas que se
 * confunden con facilidad:
 *
 *  · **Facturado** es lo que dice el papel del proveedor. No mete mercancía.
 *  · **Recibido** es lo que ha entrado en el almacén, y lo mete **el albarán**, no la factura. Por eso
 *    esta pantalla puede decir «facturado 663, recibido 300» sin que nada esté mal.
 *  · **Pagado** es el dinero que ha salido **para esta compra** (lo aplicado a sus gastos, no el importe
 *    de un pago que además pagaba otras cosas).
 *  · **Pendiente** es lo que queda.
 *
 * LO QUE NO HACE
 *
 *  · **No calcula ni suma nada.** Las cuatro cifras y sus frases llegan hechas del servidor, que las
 *    cuenta con `Decimal` (en el navegador todo número es de coma flotante y el dinero no se suma ahí).
 *  · **No enseña un cero donde no hay dato.** Si de una línea no se puede saber lo que ha entrado —no
 *    está enganchada con el albarán— se dice eso, no un 0 que parecería «no ha entrado nada».
 *  · **No navega por su cuenta.** Lleva a otro registro con un botón (`data-accion` + `data-id`), que es
 *    como se navega en toda la aplicación: la pantalla no escribe direcciones.
 */

import { AvisoDeError, Botones, frase, html } from "../componentes.js";

/** Una de las cuatro cifras, grande y con su explicación debajo. */
function UnaCifra({ etiqueta, valor, pista }) {
  return html`
    <div className="ficha-resumen">
      <div className="ficha-resumen-etiqueta">${frase(etiqueta)}</div>
      <div className="ficha-resumen-valor">${frase(valor)}</div>
      <div className="pista-campo">${frase(pista)}</div>
    </div>
  `;
}

/** Un albarán de la compra, con su fecha, lo que trajo y su botón para abrirlo. */
function UnAlbaran({ albaran, textos }) {
  return html`
    <li>
      <div className="apunte-cabecera">
        <strong>${frase(albaran.titulo)}</strong>
        <span>${frase(albaran.cuando)}</span>
      </div>
      <div className="apunte-detalle">${frase(albaran.trajo)}</div>
      ${
        // Un albarán anulado se dice en su fila: sigue a la vista —existió— pero no cuenta, y eso hay
        // que verlo aquí o parecería que la mercancía entró.
        albaran.anulado
          ? html`<div className="aviso aviso-error">${frase(albaran.anulado)}</div>`
          : null
      }
      <${Botones}
        botones=${[
          {
            etiqueta: textos.ver_el_albaran,
            accion: "albaran-abrir",
            datos: { id: albaran.id },
            clase: "boton-claro",
            sencillo: true,
          },
        ]}
        barra=${false}
      />
    </li>
  `;
}

/** Una línea de la factura, con lo que ha entrado de ella y lo que falta. */
function UnaLinea({ linea }) {
  return html`
    <li>
      <div className="apunte-cabecera">
        <strong>${frase(linea.descripcion)}</strong>
        <span>${frase(linea.facturado)}</span>
      </div>
      <div className="apunte-detalle">${frase(linea.recibido)}</div>
      ${
        // Lo que falta solo se puede decir cuando se sabe: si no hay enganche con el albarán, la frase
        // ya lo explica y no se añade una resta que no se ha podido hacer.
        linea.falta ? html`<div className="apunte-detalle">${frase(linea.falta)}</div>` : null
      }
    </li>
  `;
}

/** Un gasto de esta compra, con lo pagado y lo que le queda, y su botón. */
function UnGasto({ gasto, textos }) {
  return html`
    <li>
      <div className="apunte-cabecera">
        <strong>${frase(gasto.concepto)}</strong>
        <span>${frase(gasto.importe)}</span>
      </div>
      <div className="apunte-detalle">${frase(gasto.pagado)}</div>
      <div className="apunte-detalle">${frase(gasto.pendiente)}</div>
      <${Botones}
        botones=${[
          {
            etiqueta: textos.ver_el_gasto,
            accion: "gasto-abrir",
            datos: { id: gasto.id },
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
 * La ficha entera.
 *
 * Propiedades: `textos` (los del servidor), `compra` (la cabecera, las cuatro cifras y sus listas, todo
 * ya en frases), `cargando` y `error`. **Ni una frase escrita aquí**: todo llega por propiedades, que es
 * lo que permite cambiarlas sin tocar el dibujo.
 */
export function PantallaCompra({ textos = {}, compra = {}, cargando = false, error = "" }) {
  const cifras = compra.cifras || [];
  const albaranes = compra.albaranes || [];
  const lineas = compra.lineas || [];
  const gastos = compra.gastos || [];
  const pagos = compra.pagos || [];
  return html`
    <h1>${frase(compra.titulo)}</h1>
    <p className="pista">${frase(compra.cuando)}</p>
    <${AvisoDeError} texto=${error} />
    ${cargando ? html`<p className="pista">${frase(compra.buscando)}</p>` : null}
    ${
      // La factura anulada se dice arriba: cambia el sentido de todo lo de abajo.
      compra.anulada
        ? html`<div className="aviso aviso-error">${frase(compra.anulada)}</div>`
        : null
    }
    ${(compra.avisos || []).map(
      (aviso, indice) => html`<div className="aviso" key=${indice}>${frase(aviso)}</div>`,
    )}

    <div className="ficha-resumen-cifras">
      ${cifras.map(
        (cifra, indice) =>
          html`<${UnaCifra}
            key=${indice}
            etiqueta=${cifra.etiqueta}
            valor=${cifra.valor}
            pista=${cifra.pista}
          />`,
      )}
    </div>

    <h2>${frase((textos || {}).los_albaranes)}</h2>
    ${
      albaranes.length
        ? html`<ul className="lista">
            ${albaranes.map(
              (albaran, indice) =>
                html`<${UnAlbaran} key=${indice} albaran=${albaran} textos=${textos} />`,
            )}
          </ul>`
        : html`<p className="pista-campo">${frase((textos || {}).sin_albaran)}</p>`
    }

    <h2>${frase(compra.las_lineas)}</h2>
    ${
      lineas.length
        ? html`<ul className="lista">
            ${lineas.map((linea, indice) => html`<${UnaLinea} key=${indice} linea=${linea} />`)}
          </ul>`
        : html`<p className="pista-campo">${frase((textos || {}).sin_lineas)}</p>`
    }

    <h2>${frase((textos || {}).el_dinero)}</h2>
    ${
      gastos.length
        ? html`<ul className="lista">
            ${gastos.map(
              (gasto, indice) => html`<${UnGasto} key=${indice} gasto=${gasto} textos=${textos} />`,
            )}
          </ul>`
        : html`<p className="pista-campo">${frase((textos || {}).sin_gasto)}</p>`
    }
    ${
      // Los pagos solo salen si los hay: una lista vacía con su título sería ruido.
      pagos.length
        ? html`
            <h3>${frase((textos || {}).los_pagos)}</h3>
            <ul className="lista">
              ${pagos.map(
                (pago, indice) => html`
                  <li key=${indice}>
                    <div className="apunte-cabecera">
                      <strong>${frase(pago.cuando)}</strong>
                      <span>${frase(pago.importe)}</span>
                    </div>
                    <div className="apunte-detalle">${frase(pago.aplicado)}</div>
                  </li>
                `,
              )}
            </ul>
          `
        : null
    }

    <${Botones} botones=${compra.acciones} />
  `;
}

/** El elemento de React de esta pantalla, ya con sus propiedades puestas. */
export function pantallaDeLaCompra(propiedades) {
  return html`
    <${PantallaCompra}
      textos=${propiedades.textos}
      compra=${propiedades.compra}
      cargando=${propiedades.cargando}
      error=${propiedades.error}
    />
  `;
}
