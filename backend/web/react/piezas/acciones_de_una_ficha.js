/*
 * acciones_de_una_ficha.js — Los botones que lleva una ficha de una lista: CORREGIR y BORRAR.
 *
 * POR QUÉ EXISTE
 *
 * Desde la ronda 91, cada apunte del cuaderno se puede corregir y borrar, y desde entonces **lo mismo
 * se ha ido pidiendo para todo lo demás**: las tierras y los grupos (92), los maestros, los análisis,
 * las ventas y los planes (93). Cada vez, el mismo trozo: una barra de acciones debajo de la ficha con
 * sus dos botones, y la ficha **sin** ser un botón (la tarjeta de una tierra abre lo que hay sembrado;
 * la de un apunte se lee; ninguna de las dos puede convertirse en un botón que no hace nada).
 *
 * Estaba escrito a mano en cuatro pantallas y copiándose a las que venían. Aquí está una vez, y las
 * pantallas le pasan **los botones ya preparados** (`app.js`, `botonesDeCorregirYBorrar`).
 *
 * LO QUE HAY QUE SABER DE ESTA PIEZA
 *
 *  1. **Sin acciones no se pinta la barra**, y con acciones se pinta aunque la ficha no lleve nada
 *     más: una barra vacía es un hueco con un borde, y promete botones que no están.
 *  2. **Los `data-*` de cada botón los prepara `app.js`** (`data-accion`, `data-tipo`, `data-id`): el
 *     manejador de clics de la aplicación es **uno solo** y lee de ahí. Si un botón saliera sin su
 *     tipo o sin su identificador, pulsarlo no haría nada o haría algo sobre otra ficha.
 *  3. La `pista` es opcional y va debajo, en pequeño. La usa la lista del cuaderno cuando quiere
 *     explicar la diferencia entre los dos botones sin gastar una línea en cada ficha (hoy no la usa
 *     ninguna: el que lo explica es la pantalla que pregunta antes de borrar).
 *  4. **Un botón puede venir apagado** (`deshabilitado`), y lo decide `app.js`, que es quien sabe si ese
 *     botón puede hacer algo (ronda 93: el BORRAR de un año del cuaderno que tiene cosas dentro). La
 *     pieza no lo decide: **pinta lo que le pasen**, y la pantalla que lo apaga pone al lado la frase que
 *     lo explica.
 *
 * El componente es PURO: no llama a `fetch`, no lee `localStorage` y no toca el DOM.
 */

import { BotonSencillo, frase, html } from "../componentes.js";

export function AccionesDeUnaFicha({ acciones = [], pista = "" }) {
  const botones = (acciones || []).filter(Boolean);
  if (!botones.length && !pista) return null;
  return html`
    ${
      botones.length
        ? html`
            <div className="barra-acciones">
              ${botones.map(
                (accion, indice) => html`
                  <${BotonSencillo}
                    key=${indice}
                    etiqueta=${accion.etiqueta}
                    accion=${accion.accion}
                    datos=${accion.datos}
                    clase=${accion.clase}
                    deshabilitado=${Boolean(accion.deshabilitado)}
                  />
                `,
              )}
            </div>
          `
        : null
    }
    ${pista ? html`<p className="pista-campo">${frase(pista)}</p>` : null}
  `;
}

/** El elemento de React de esta pieza, ya con sus propiedades puestas. */
export function accionesDeUnaFicha(propiedades) {
  return html`<${AccionesDeUnaFicha} acciones=${propiedades.acciones} pista=${propiedades.pista} />`;
}
