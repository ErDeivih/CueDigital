/*
 * venta_importe.js — Poner el importe de una entrega (T12). La puerta del caso A08.
 *
 * QUÉ SE ARREGLA AQUÍ
 *
 * Una entrega se apunta en el campo **sin precio** —a lo mejor el papel del comprador llega tres días
 * después— y hasta este momento esa entrega tiene los kilos conocidos y el importe **pendiente**. Es el
 * caso A08 del contrato: «Venta con 8.000 kg y sin precio → Cantidad conocida, importe pendiente; no
 * ingreso cero». Esta pantalla es donde ese hueco se cierra, y por eso existe: un hueco que no se puede
 * rellenar desde ningún sitio es un dato que el programa guarda y el agricultor no puede meter.
 *
 * LAS DOS FORMAS DE DECIRLO, Y CUÁL MANDA
 *
 *  · **El importe del papel.** Si el agricultor vio lo que le van a pagar y pone 1.205,40 €, ese manda: el
 *    programa no corrige lo que dice el papel de enfrente.
 *  · **El precio por kilo.** Si lo que sabe es a cómo se lo pagan, se multiplica por la cantidad y el
 *    servidor redondea **una sola vez al final** (redondear antes el precio al céntimo serían decenas de
 *    euros de diferencia en 42.000 kg).
 *  · **Y el vencimiento**, que no es un adorno: es lo único que permite decir «esto está vencido», que es
 *    la mitad de para qué sirve mirar lo que te deben.
 *
 * Lo que no hace: ni una cuenta (el importe y el vencimiento llegan y se mandan tal cual, y el cálculo lo
 * hace el servidor con `Decimal`) y ni una frase escrita a mano.
 */

import { Boton, frase, html } from "../componentes.js";
import { Campo } from "../piezas/campo_de_un_importe.js";

/**
 * La pantalla entera.
 *
 * Propiedades:
 *
 *  - `textos`: `{ venta, acciones }` del servidor.
 *  - `entrega`: `{ id, titulo, texto_cantidad }`, ya preparado por `app.js`.
 *  - `borrador`: lo que ya hay (`importe`, `precio_unitario`, `vencimiento`), para no teclear a ciegas.
 *  - `contactos`: las fichas de los clientes, para poder enlazar la entrega con una (ver abajo).
 *  - `error`: lo que ha dicho el servidor, o nada.
 */
export function PantallaImporte({ textos = {}, entrega = {}, borrador = {}, cosechas = [], contactos = [], error = "" }) {
  const v = textos.venta || {};
  const acciones = textos.acciones || {};
  return html`
    <h1>${frase(v.importe_titulo)}</h1>
    <p className="pista">${frase(v.importe_explica)}</p>
    ${error ? html`<p className="aviso-error" role="alert">${frase(error)}</p>` : null}
    <dl>
      <div className="resumen-dato">
        <dt>${frase(v.tabla_producto)}</dt>
        <dd>${frase(entrega.producto || "")}</dd>
      </div>
      <div className="resumen-dato">
        <dt>${frase(v.tabla_cantidad)}</dt>
        <dd>${frase(entrega.texto_cantidad || "")}</dd>
      </div>
    </dl>
    <${Campo}
      id="venta-importe"
      etiqueta=${v.importe}
      pista=${v.importe_pista}
      tipo="numero"
      valor=${borrador.importe}
    />
    <${Campo}
      id="venta-precio"
      etiqueta=${v.precio_unitario}
      pista=${v.precio_unitario_pista}
      tipo="numero"
      valor=${borrador.precio_unitario}
    />
    <${Campo}
      id="venta-vencimiento"
      etiqueta=${v.vencimiento}
      pista=${v.vencimiento_pista}
      tipo="fecha"
      valor=${borrador.vencimiento}
    />
    ${
      // **De qué cosecha salió**: es el «lote cosechado» que el contrato manda separar de la entrega (S12), y
      // aquí está su puerta. La lista son **las cosechas apuntadas** (las labores de tipo cosecha), que es lo
      // que el agricultor ya tiene en el cuaderno: no se elige la más parecida ni se inventa ninguna.
      cosechas.length > 1
        ? html`<${Campo}
            id="venta-cosecha"
            etiqueta=${v.de_que_cosecha}
            pista=${v.de_que_cosecha_pista}
            opciones=${cosechas}
            valor=${borrador.cosecha_id}
          />`
        : null
    }
    ${
      // **Y con qué ficha de cliente se enlaza** (revisión del T12). La columna `contacto_id` existía, el
      // servidor la validaba y **ninguna pantalla la preguntaba**: el agricultor no podía contestar
      // «¿cuánto me debe la cooperativa?» sin comparar nombres a ojo. La lista son **sus contactos**, con
      // su nombre tal cual: no se elige el que se parezca al comprador escrito.
      contactos.length > 1
        ? html`<${Campo}
            id="venta-contacto"
            etiqueta=${v.cliente_ficha}
            pista=${v.cliente_ficha_pista}
            opciones=${contactos}
            valor=${borrador.contacto_id}
          />`
        : null
    }
    <div className="barra-acciones">
      <button type="button" className="boton" data-accion="venta-importe-guardar">
        ${frase(acciones.guardar)}
      </button>
      <${Boton} etiqueta=${acciones.volver} accion="ventas-ver" clase="boton-claro" />
    </div>
  `;
}

/** El elemento de React de esta pantalla, ya con sus propiedades puestas. */
export function pantallaDeImporte(propiedades) {
  return html`<${PantallaImporte}
    textos=${propiedades.textos}
    entrega=${propiedades.entrega}
    borrador=${propiedades.borrador}
    cosechas=${propiedades.cosechas}
    contactos=${propiedades.contactos}
    error=${propiedades.error}
  />`;
}
