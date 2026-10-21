/*
 * cultivos.js — «Lo que hay sembrado», escrita en React.
 *
 * POR QUÉ ESTA PANTALLA
 *
 * Es la sexta que se pasa a React y la tercera de listas. Responde a una pregunta que la Junta pide
 * por escrito —qué hay sembrado este año en cada tierra y qué hubo antes— y que en su día **no se
 * podía contestar desde ninguna pantalla**: el dato estaba en la base y no lo leía nadie.
 *
 * **Lo que NO hace este componente:** no sabe nada de `estado` ni de la API. Recibe las tierras **ya
 * preparadas** —su nombre, su detalle, sus filas contadas y lo que sembró antes— y las pinta. Quien
 * las prepara es `app.js`, que es quien tiene los datos.
 *
 * Y conserva dos cosas que importan:
 *
 *  1. **El aviso de que repites el cultivo del año pasado.** No es para reñir: es porque sembrar lo
 *     mismo dos años seguidos gasta la tierra y la ley lo mira. Va con su texto del servidor.
 *  2. **Si no se sabe qué hay sembrado, se dice que falta decirlo** y se da el botón para decirlo.
 *     Un hueco en blanco dejaría al agricultor sin saber si el programa se ha equivocado.
 */

import { AvisoDeError, Boton, frase, html } from "../componentes.js";
import { Tabla } from "../piezas/tabla.js";

/**
 * Una tierra: lo que tiene sembrado ahora, lo de años anteriores y el botón para cambiarlo.
 *
 * Del diseño de Stitch de esta pantalla (ronda 90, `docs/stitch/rediseno/cultivos.png`):
 *
 *  1. **La etiqueta de estado** («Al día» / «Falta rellenar»), arriba a la derecha: con más de cincuenta
 *     tierras, lo que se viene a buscar aquí es **a cuáles les falta decirlo**, y eso no se saca leyendo
 *     la ficha de cada una.
 *  2. **La que no lo tiene dicho lo dice en su franja de aviso y su botón es el grande** (el de color de
 *     acción): es lo único que le falta a esa tierra, así que es lo que tiene que destacar. Las que están
 *     al día llevan el botón claro de «CAMBIARLO».
 *  3. **El aviso de que repites el cultivo va en su franja**, dentro de la tarjeta, como los avisos de una
 *     tierra: es «algo que hay que mirar», y en esta aplicación eso va con su señal.
 */
function Tierra({ parcela, textos }) {
  const c = textos.cultivos || {};
  return html`
    <li>
      <div className="apunte-cabecera">
        <strong>${frase(parcela.alias)}</strong>
        ${
          parcela.estado && parcela.estado.texto
            ? html`<span className=${`etiqueta-estado etiqueta-estado-${parcela.estado.tipo || "bien"}`}
                >${frase(parcela.estado.texto)}</span
              >`
            : null
        }
      </div>
      <div className="apunte-detalle">${frase(parcela.detalle)}</div>
      ${
        parcela.tiene_cultivo
          ? html`
              <dl>
                ${parcela.filas.map(
                  (fila, indice) => html`
                    <div className="resumen-dato" key=${indice}>
                      <dt>${frase(fila.etiqueta)}</dt>
                      <dd>${frase(fila.valor)}</dd>
                    </div>
                  `,
                )}
              </dl>
            `
          : html`
              <p className="tarjeta-aviso">
                <span className="tarjeta-aviso-icono" aria-hidden="true">!</span>
                ${frase(c.falta_decirlo)}
              </p>
            `
      }
      ${
        parcela.anteriores
          ? html`<p className="pista-campo">${frase(c.otros_anos)}: ${frase(parcela.anteriores)}</p>`
          : null
      }
      ${
        parcela.repite
          ? html`
              <p className="tarjeta-aviso">
                <span className="tarjeta-aviso-icono" aria-hidden="true">!</span>
                ${frase(c.repite)}
              </p>
            `
          : null
      }
      <${Boton}
        etiqueta=${parcela.tiene_cultivo ? c.cambiar : c.decir}
        accion="cultivo-decir"
        datos=${{ id: parcela.parcela_id }}
        clase=${parcela.tiene_cultivo ? "boton-claro" : "boton-principal"}
      />
    </li>
  `;
}

/**
 * La pantalla entera.
 *
 * Propiedades:
 *
 *  - `textos`: `{ cultivos, maestros, acciones }`, tal y como los sirve `/api/interfaz`.
 *  - `parcelas`: las tierras, ya preparadas por `app.js` (y ya filtradas, si está puesto el filtro de las que
 *    faltan).
 *  - `tabla`: la misma lista como tabla, para el ordenador (30/09/2026). Es la lista más larga del programa
 *    después de las tierras —una fila por tierra— y en el ordenador se veían **tres tarjetas enormes** por
 *    pantalla. En el móvil no se pinta (el CSS esconde `.solo-escritorio`): allí manda la tarjeta.
 *  - `aviso`: `{ texto, boton }` para la franja de arriba. El texto dice cuántas tierras no tienen dicho qué
 *    tienen, y el botón **enseña solo esas** (lo pide el diseño de escritorio de esta pantalla) o devuelve la
 *    lista entera. Sin botón, la franja es solo un aviso.
 *  - `error`: lo que ha dicho el servidor cuando algo ha fallado, o nada.
 */
export function PantallaCultivos({
  textos = {},
  parcelas = [],
  tabla = null,
  aviso = {},
  error = "",
  // ***Y si la carga fallo*** (21/10/2026, D03): *«no hay tierras» es una afirmacion sobre la finca.*
  noSePudoCargar = false,
  noSePudoCargarTexto = "",
}) {
  const c = textos.cultivos || {};
  const maestros = textos.maestros || {};
  const acciones = textos.acciones || {};

  return html`
    <h1>${frase(c.titulo)}</h1>
    <p className="pista">${frase(c.explica)}</p>
    <${AvisoDeError} texto=${error} />
    ${
      parcelas.length === 0 && !aviso.texto
        ? noSePudoCargar
          ? html`<div className="aviso aviso-error">${frase(noSePudoCargarTexto)}</div>`
          : html`<div className="aviso">${frase(c.sin_parcelas)}</div>`
        : null
    }
    ${
      // La franja de lo que falta, **con su botón al lado**: el aviso dice cuántas son y el botón enseña esas
      // y solo esas (o vuelve a verlas todas). Es la misma forma que la franja de un aviso con salida que
      // lleva la aplicación desde el principio: un aviso sin salida no vale.
      aviso.texto
        ? html`
            <div className="aviso aviso-con-boton">
              <span>${frase(aviso.texto)}</span>
              ${
                aviso.boton
                  ? html`<${Boton}
                      etiqueta=${aviso.boton.etiqueta}
                      accion=${aviso.boton.accion}
                      clase=${aviso.boton.clase || "boton-claro"}
                    />`
                  : null
              }
            </div>
          `
        : null
    }
    ${
      // **La tabla, solo en el ordenador**: las 64 tierras de arriba abajo, con lo que hay sembrado este año,
      // lo de los años anteriores y a cuáles les falta decirlo.
      tabla && parcelas.length
        ? html`<div className="solo-escritorio"><${Tabla} tabla=${tabla} /></div>`
        : null
    }
    ${
      parcelas.length
        ? html`
            <ul className="lista solo-movil">
              ${parcelas.map(
                (parcela, indice) =>
                  html`<${Tierra} key=${indice} parcela=${parcela} textos=${textos} />`,
              )}
            </ul>
          `
        : null
    }
    <div className="ayuda-campo">
      <p><strong>${frase(c.para_que)}</strong></p>
    </div>
    <div className="barra-acciones">
      <${Boton} etiqueta=${maestros.titulo} accion="mis-cosas" clase="boton-claro" />
      <${Boton} etiqueta=${acciones.volver} accion="ir-inicio" clase="boton-claro" />
    </div>
  `;
}

/** El elemento de React de esta pantalla, ya con sus propiedades puestas. */
export function pantallaDeCultivos(propiedades) {
  return html`
    <${PantallaCultivos}
      textos=${propiedades.textos}
      parcelas=${propiedades.parcelas}
    noSePudoCargar=${propiedades.noSePudoCargar}
    noSePudoCargarTexto=${propiedades.noSePudoCargarTexto}
      tabla=${propiedades.tabla}
      aviso=${propiedades.aviso}
      error=${propiedades.error}
    />
  `;
}
