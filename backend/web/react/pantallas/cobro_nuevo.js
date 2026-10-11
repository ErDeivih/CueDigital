/*
 * cobro_nuevo.js — Apuntar un cobro, que puede ser una parte (T12).
 *
 * EL CASO A06, ENTERO, EN ESTA PANTALLA
 *
 * «Factura 121 EUR, pago 40 EUR → pendiente 81; un segundo importe conciliado no crea una segunda
 * factura». Las dos mitades están aquí y en el servidor:
 *
 *  · **Puede ser una parte.** El campo del importe admite cualquier cantidad y no está obligado a cuadrar
 *    con lo que se debe. Lo que sobra o lo que falta se dice con el número exacto en cuanto se guarda.
 *  · **No crea ninguna factura.** Aquí se elige **contra qué factura ya hecha** va el dinero, de una lista
 *    que enseña, de cada una, lo que le queda por cobrar. No hay ninguna opción de «hacer una factura»:
 *    apuntar dinero que entra solo apunta dinero que entra.
 *  · **Y puede no saberse de qué factura es.** La primera opción de la lista es «todavía no sé de qué
 *    factura es», y entonces el cobro se queda sin asignar, que es lo que el contrato pide («pagos sin
 *    factura quedan por conciliar»). Un pago sin asignar no se pierde: se le dice de qué factura es
 *    después, desde su ficha, y esa decisión se puede deshacer sin borrar el movimiento.
 *
 * Lo que no hace: ni una cuenta (el pendiente de cada factura llega escrito del servidor) y ni una frase
 * escrita a mano.
 */

import { Boton, frase, html } from "../componentes.js";
import { Campo } from "../piezas/campo_de_un_importe.js";

/**
 * La pantalla entera.
 *
 * Propiedades:
 *
 *  - `textos`: `{ cobro, acciones }` del servidor.
 *  - `borrador`: lo que se lleva escrito (la fecha de hoy ya puesta).
 *  - `facturas`: las nuestras, cada una con su título y **lo que le queda por cobrar**: elegir a ciegas
 *    entre cuatro números de factura no es elegir.
 *  - `contactos`: las fichas de los clientes, para enlazar el cobro con una.
 *  - `error`: lo que ha dicho el servidor, o nada.
 */
export function PantallaCobroNuevo({ textos = {}, borrador = {}, facturas = [], contactos = [], error = "" }) {
  const c = textos.cobro || {};
  const acciones = textos.acciones || {};
  const formas = Object.entries(c.formas || {}).map(([valor, texto]) => ({ valor, texto }));
  return html`
    <h1>${frase(c.nuevo_titulo)}</h1>
    <p className="pista">${frase(c.explica)}</p>
    ${error ? html`<p className="aviso-error" role="alert">${frase(error)}</p>` : null}
    <${Campo} id="cobro-fecha" etiqueta=${c.fecha} tipo="fecha" valor=${borrador.fecha} />
    <${Campo}
      id="cobro-importe"
      etiqueta=${c.importe}
      pista=${c.importe_pista}
      tipo="numero"
      valor=${borrador.importe}
    />
    <${Campo} id="cobro-cliente" etiqueta=${c.cliente} valor=${borrador.cliente} />
    ${
      // **Con qué ficha de cliente queda enlazado el cobro** (revisión del T12): el que ha pagado, que no
      // siempre es el mismo al que se le facturó (una cooperativa paga por un socio). La lista son sus
      // contactos, y sin elegir ninguno el cobro se queda como estaba.
      contactos.length > 1
        ? html`<${Campo}
            id="cobro-contacto"
            etiqueta=${c.cliente_ficha}
            pista=${c.cliente_ficha_pista}
            opciones=${contactos}
            valor=${borrador.contacto_id}
          />`
        : null
    }
    <div className="campo">
      <label htmlFor="cobro-factura">${frase(c.factura)}</label>
      <p className="pista-campo">${frase(c.sin_factura_pista)}</p>
      <select id="cobro-factura" defaultValue=${String(borrador.factura_emitida_id || "")}>
        <option value="">${frase(c.sin_factura)}</option>
        ${facturas.map(
          (factura) => html`<option value=${String(factura.id)} key=${String(factura.id)}>
            ${frase(factura.titulo_con_pendiente)}
          </option>`,
        )}
      </select>
    </div>
    ${
      // **Un ingreso puede saldar varias deudas** (CRM-01, 11/10/2026): 350 que entran de una vez y saldan
      // una factura de 100 y otra de 250. Eso no se puede decir con el desplegable de arriba, que es de una
      // sola; aquí se marcan **varias** y, si no se escribe nada, a cada una se le aplica **lo que le
      // queda por cobrar** —que es lo que se quiere casi siempre y evita teclear dos cifras para nada—.
      // El importe se puede escribir cuando se cobra **menos** de lo que se debe, que también pasa.
      facturas.length
        ? html`<div className="campo">
            <p className="pista-campo">${frase(c.reparto_pista)}</p>
            ${facturas.map(
              (factura) => html`<div className="reparto-fila" key=${`reparto-${factura.id}`}>
                <label htmlFor=${`cobro-reparto-${factura.id}`}>
                  <input
                    type="checkbox"
                    id=${`cobro-reparto-${factura.id}`}
                    data-factura=${String(factura.id)}
                    defaultChecked=${Boolean(
                      (borrador.reparto || []).some(
                        (fila) => Number(fila.factura_emitida_id) === Number(factura.id),
                      ),
                    )}
                  />
                  ${frase(factura.titulo_con_pendiente)}
                </label>
                <input
                  type="text"
                  inputMode="decimal"
                  id=${`cobro-reparto-importe-${factura.id}`}
                  placeholder=${frase(c.reparto_lo_que_le_queda)}
                  defaultValue=${String(
                    ((borrador.reparto || []).find(
                      (fila) => Number(fila.factura_emitida_id) === Number(factura.id),
                    ) || {}).importe || "",
                  )}
                />
              </div>`,
            )}
          </div>`
        : null
    }
    <${Campo} id="cobro-forma" etiqueta=${c.forma} opciones=${formas} valor=${borrador.forma} />
    <${Campo}
      id="cobro-referencia"
      etiqueta=${c.referencia}
      pista=${c.referencia_pista}
      valor=${borrador.referencia}
    />
    <${Campo} id="cobro-notas" etiqueta=${c.notas} valor=${borrador.notas} />
    ${
      // Si no hay ninguna factura, se dice por qué y qué hacer: el cobro se apunta igual y queda sin
      // asignar, y para que vaya contra una factura hay que hacerla antes.
      facturas.length === 0 ? html`<p className="pista-campo">${frase(c.no_hay_facturas)}</p>` : null
    }
    <div className="barra-acciones">
      <button type="button" className="boton" data-accion="cobro-guardar">${frase(acciones.guardar)}</button>
      <${Boton} etiqueta=${acciones.volver} accion="cobros-ver" clase="boton-claro" />
    </div>
  `;
}

/** El elemento de React de esta pantalla, ya con sus propiedades puestas. */
export function pantallaDeCobroNuevo(propiedades) {
  return html`<${PantallaCobroNuevo}
    textos=${propiedades.textos}
    borrador=${propiedades.borrador}
    facturas=${propiedades.facturas}
    contactos=${propiedades.contactos}
    error=${propiedades.error}
  />`;
}
