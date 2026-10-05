/*
 * campo_de_un_importe.js — Las piezas de un formulario de dinero (T12).
 *
 * POR QUÉ ES UNA PIEZA Y NO CÓDIGO DE CADA PANTALLA
 *
 * El T12 trae cuatro pantallas que se rellenan —poner el importe de una entrega, apuntarle una devolución
 * o un ajuste, juntar entregas en una factura y apuntar un cobro—, y las cuatro necesitan lo mismo: un
 * campo de escribir con su rótulo del servidor, una lista de botones para elegir una cosa (los tipos de
 * ajuste, el origen, la forma de cobro) y el aviso de que la factura nuestra no es un documento oficial.
 * Copiar eso cuatro veces es la forma más segura de que dentro de un mes tres pantallas lo hagan bien y
 * una se quede sin el `id` del campo, que es el fallo que este proyecto ya ha pagado dos veces: **un campo
 * que se pinta y no se puede leer se guarda vacío sin que salte ningún error**.
 *
 * LO QUE NO HACE, como todas las piezas de aquí: no calcula nada, no llama a `fetch` y no tiene ni una
 * frase escrita a mano. Los rótulos llegan por propiedades, del servidor.
 *
 * Y una decisión que hay que entender: **el importe es un campo de texto, no de número** (`inputMode`
 * decimal para que el móvil saque el teclado de números con coma). Un `type="number"` convertiría lo que
 * el agricultor escribe en un número de coma flotante del navegador, que es justo lo que el ticket del
 * dinero no puede permitir: el importe viaja como **texto decimal** y se lee con `Decimal` en el servidor.
 */

import { Botones, frase, html } from "./../componentes.js";

/** Un campo de escribir con su etiqueta y su pista, con el `id` que lee `app.js`. */
export function Campo({ id, etiqueta, pista, tipo = "texto", valor = "", opciones = [] }) {
  return html`
    <div className="campo">
      <label htmlFor=${id}>${frase(etiqueta)}</label>
      ${pista ? html`<p className="pista-campo">${frase(pista)}</p>` : null}
      ${
        tipo === "fecha"
          ? html`<input id=${id} type="date" defaultValue=${frase(valor)} />`
          : opciones.length
            ? html`<select id=${id} defaultValue=${frase(valor)}>
                ${opciones.map(
                  (opcion) => html`<option value=${String(opcion.valor)} key=${String(opcion.valor)}>
                    ${frase(opcion.texto)}
                  </option>`,
                )}
              </select>`
            : html`<input
                id=${id}
                type="text"
                inputMode=${tipo === "numero" ? "decimal" : undefined}
                defaultValue=${frase(valor)}
              />`
      }
    </div>
  `;
}

/** Una lista de botones para elegir una cosa: los ajustes y los orígenes se eligen, no se escriben. */
export function Elegir({ rotulo, pista, opciones = [], accion, campo, elegido = "" }) {
  return html`
    <div className="campo">
      <p className="etiqueta-campo">${frase(rotulo)}</p>
      ${pista ? html`<p className="pista-campo">${frase(pista)}</p>` : null}
      <${Botones}
        botones=${opciones.map((opcion) => ({
          etiqueta: opcion.texto,
          accion,
          datos: { campo, valor: opcion.valor },
          clase: elegido === opcion.valor ? "boton" : "boton-claro",
          sencillo: true,
        }))}
        barra=${false}
      />
    </div>
  `;
}

/**
 * El aviso de que la factura nuestra **no es un documento con validez oficial**.
 *
 * Va en su propia pieza y con nombre propio para que no se pueda quitar de una pantalla sin que se note:
 * el contrato dice por escrito (§4, S12) que la emisión fiscal completa «requiere especificación
 * normativa propia antes de activarse como tal», y una pantalla que llamara «factura» a esto sin decirlo
 * le estaría diciendo al agricultor que puede presentarlo donde no puede. Hay una prueba que exige que
 * salga en las tres pantallas de la factura.
 */
export function AvisoNoOficial({ textos = {} }) {
  const f = textos.factura_emitida || {};
  return html`<p className="pista-campo">${frase(f.aviso_no_oficial)}</p>`;
}
