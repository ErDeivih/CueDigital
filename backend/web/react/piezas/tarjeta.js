/*
 * tarjeta.js — La tarjeta: un trozo de pantalla con su nombre, sus datos y lo que hay que mirar.
 *
 * POR QUÉ EXISTE
 *
 * En el asistente, la pregunta más repetida es «¿en cuál?»: en qué tierra has echado el producto, de
 * cuál salió la muestra, cuál vas a abonar. Hasta el rediseño eso era **una fila de texto**: el nombre,
 * «4,90 ha · secano» y una flecha. Con cincuenta y una tierras, todas las filas se parecen, y elegir la
 * equivocada es lo más fácil del mundo —y ese fallo se apunta en el cuaderno y no se nota—.
 *
 * El rediseño con Stitch (`docs/stitch/rediseno/asistente.png`) propone lo que ya hace cualquier lista
 * de tierras que se entienda: **el dibujo de la forma de la tierra**, que es como el agricultor la
 * reconoce de verdad (la ve en el mapa y en el papel del SIGPAC), su superficie, su pueblo, y un
 * **círculo** que dice «esto se toca».
 *
 * Y SE LLAMABA `tarjeta_de_tierra.js` HASTA LA RONDA 79
 *
 * Porque la segunda vez que hizo falta (ronda 78, `docs/stitch/rediseno/mis_tierras.png`) fue en «Mis
 * parcelas, productos y máquinas» —la misma lista, pero sin poder hacer nada con ella—, y la tercera
 * (ronda 79, `docs/stitch/rediseno/mi_cuaderno.png`) fue en **«mi cuaderno»**, para los apuntes de
 * producto: allí la tarjeta cuenta una cosa que **no se toca**, y por eso esta pieza sabe pintarse de
 * las dos maneras. Con un nombre que decía «tierra», la siguiente tarjeta habría sido una copia; con
 * este nombre, es la misma.
 *
 * LAS DOS MANERAS, Y POR QUÉ LA DIFERENCIA IMPORTA
 *
 *   · **Con `accion`, la tarjeta es un `<button>`**. Es lo que hace que el toque funcione: el manejador
 *     de clics de la aplicación es **uno solo**, vive en `app.js` y lee `data-accion` y los demás
 *     `data-*`. Si aquí se escribiera un `div` con su `onClick`, el agricultor tocaría y no pasaría nada.
 *   · **Sin `accion`, la tarjeta es un `<div>`**: un trozo de pantalla que se lee, como el apunte de un
 *     tratamiento en «mi cuaderno». **Un botón que no hace nada es peor que un texto**: promete una
 *     salida y no la da. Por eso la caja se elige por la acción, y no por lo que le pase el que llama.
 *
 * LO QUE SE CONSERVA A PROPÓSITO
 *
 *  1. **La elegida se dice con una palabra**, no solo con el color: «ELEGIDA» en su etiqueta y el
 *     círculo con su visto bueno. Es la regla de la casa: el color nunca informa solo.
 *  2. **Los avisos van dentro de la tarjeta**, no en una lista aparte: si esa tierra tiene algo que
 *     mirar (está en zona de nitratos, tiene una masa de agua cerca), se ve **mientras se elige**, que
 *     es cuando importa. Y son datos que ya se saben: aquí no se supone nada.
 *  3. **Los datos van con su nombre delante cuando el dato es un código o un número suelto**: un
 *     «37-70-0-0-503-51-1» o un «4,90 ha» sin decir de qué son no se entienden. Eso es `filas`.
 *  4. **Ninguna frase escrita aquí**: los textos llegan por propiedades, del servidor. El «Aviso» de
 *     cada línea y la palabra «ELEGIDA» los prepara `app.js` desde `textos.py`.
 *
 * El componente es PURO: no llama a `fetch`, no lee `localStorage` y no toca el DOM.
 */

import { DibujoDeLaParcela, datosDelBoton, frase, html } from "../componentes.js";

/**
 * La tarjeta entera.
 *
 * Propiedades:
 *
 *  - `etiqueta`: el nombre de lo que se cuenta (la tierra, el producto que se echó).
 *  - `rotulo`: una línea pequeña **encima** del nombre («Tierra n.º 1», «Apunte 2»). En un muro de
 *    cincuenta y una tierras sirve para saber por dónde vas y para decir «mira la número doce» por
 *    teléfono. Va opcional: donde la tarjeta se lee de una en una, no hace falta.
 *  - `lineas`: los datos que se leen debajo, ya escritos (`["4,90 hectáreas", "Medina del Campo"]`). La
 *    primera va más grande y en negrita, que es la que se busca.
 *  - `filas`: datos **con su nombre delante** (`[{etiqueta: "Referencia oficial SIGPAC", valor: "…"}]`).
 *  - `dibujo`: la forma de la tierra, lista para un `<path>` de SVG. Si no la hay, no se enseña el
 *    cuadro: un cuadro vacío parece un fallo del programa.
 *  - `avisos`: lo que hay que mirar, ya escrito. Cada uno sale en su franja.
 *  - `pendiente`: lo que le falta y tiene arreglo desde aquí («le falta decir qué tiene sembrado este
 *    año»). Va en la misma franja de aviso que los demás, porque para el agricultor es lo mismo: algo
 *    que mirar. Se enseña **dentro de la tarjeta**, que es donde está mirando.
 *  - `accionTexto`: qué pasa si se toca. Va al pie, con su flecha. Se pone cuando la tarjeta **abre**
 *    algo (mirar o cambiar lo que hay sembrado) y no cuando solo elige.
 *  - `marca`: el círculo de la derecha, que dice «aquí se elige». Se quita cuando la tarjeta no elige
 *    nada: un círculo sin marcar en una lista que no se elige es una promesa que no se cumple.
 *  - `elegida`: si es la que el agricultor acaba de tocar.
 *  - `accion` y `datos`: lo de siempre, que es lo que hace que el toque funcione. **Sin `accion`, la
 *    tarjeta se pinta como un `<div>` de lectura** (ver el comentario de arriba).
 */
export function Tarjeta({
  etiqueta,
  rotulo,
  lineas = [],
  filas = [],
  dibujo,
  avisos = [],
  pendiente,
  accionTexto,
  marca = true,
  elegida = false,
  accion,
  datos,
  textos = {},
}) {
  // La caja se decide por la acción: con acción es un botón (se toca), sin ella es un trozo que se lee.
  const Caja = accion ? "button" : "div";
  const clase = elegida ? "tarjeta tarjeta-elegida" : "tarjeta";
  return html`
    <${Caja}
      type=${accion ? "button" : null}
      className=${clase}
      data-accion=${accion}
      ...${datosDelBoton(datos)}
    >
      ${
        dibujo
          ? html`<span className="tarjeta-dibujo"><${DibujoDeLaParcela} dibujo=${dibujo} etiqueta=${etiqueta} /></span>`
          : null
      }
      <span className="tarjeta-datos">
        ${rotulo ? html`<span className="tarjeta-rotulo">${frase(rotulo)}</span>` : null}
        <span className="tarjeta-cabecera">
          <span className="tarjeta-nombre">${frase(etiqueta)}</span>
          ${elegida ? html`<span className="tarjeta-etiqueta">${frase(textos.elegida)}</span>` : null}
        </span>
        ${(lineas || []).map(
          (linea, indice) =>
            html`<span className=${indice === 0 ? "tarjeta-linea" : "tarjeta-linea-suave"} key=${indice}
              >${frase(linea)}</span
            >`,
        )}
        ${(filas || []).map(
          (fila, indice) => html`
            <span className="tarjeta-fila" key=${"f" + indice}>
              <span className="tarjeta-fila-etiqueta">${frase(fila.etiqueta)}</span>
              <span className="tarjeta-fila-valor">${frase(fila.valor)}</span>
            </span>
          `,
        )}
        ${(avisos || []).map(
          (aviso, indice) => html`
            <span className="tarjeta-aviso" key=${"a" + indice}>
              <span className="tarjeta-aviso-icono" aria-hidden="true">!</span>${frase(aviso)}
            </span>
          `,
        )}
        ${
          pendiente
            ? html`
                <span className="tarjeta-aviso" key="pendiente">
                  <span className="tarjeta-aviso-icono" aria-hidden="true">!</span>${frase(pendiente)}
                </span>
              `
            : null
        }
        ${
          accionTexto
            ? html`
                <span className="tarjeta-accion">
                  ${frase(accionTexto)}<span className="flecha" aria-hidden="true">→</span>
                </span>
              `
            : null
        }
      </span>
      ${
        marca
          ? html`
              <span
                className=${elegida ? "tarjeta-marca tarjeta-marca-si" : "tarjeta-marca"}
                aria-hidden="true"
              >
                ${elegida ? "✓" : ""}
              </span>
            `
          : null
      }
    </${Caja}>
  `;
}
