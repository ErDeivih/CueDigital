/*
 * enganchar_la_factura.js — Decir de qué factura es un albarán que ya está apuntado (T09), en React.
 *
 * POR QUÉ ESTA PANTALLA, Y POR QUÉ **PROPONER NO ES ESCRIBIR**
 *
 * La mercancía entra el día que llega el camión, y eso lo dice el albarán; la factura llega después y
 * solo dice de quién era y cuánto costó. El caso está en el contrato (caso A15) y es el que más se
 * equivoca si se hace mal: **si la factura metiera mercancía, el almacén contaría cada litro dos
 * veces** —una por el papel que llegó y otra por la factura—.
 *
 * Aquí eso no puede pasar, y no por cuidado: la pantalla **no tiene ningún campo de cantidad**. Manda la
 * factura y las líneas que se casan; nada más.
 *
 * Y el otro peligro es el de siempre en este programa: que una máquina decida por el agricultor. El
 * servidor **propone** qué albaranes podrían ser los de esa factura, y esa propuesta **no se guarda**:
 * lo que se enseña es una sugerencia, el agricultor la mira y dice que sí. Enseñar la propuesta **no
 * escribe nada** —y eso está comprobado con una prueba que mira que la pantalla solo pide datos hasta
 * que se pulsa el botón de decir que sí—.
 *
 * LO QUE NO HACE
 *
 *  · **No calcula** qué factura es la buena: eso lo dice el servidor, y aquí se enseña con su porqué.
 *  · **No cambia ni un litro**: lo dice con esas palabras, porque es la duda que tiene el agricultor al
 *    ver dos papeles del mismo pedido.
 *  · **No esconde que no se ha podido comprobar**: sin cobertura lo dice y no da por bueno nada.
 *  · Ni una frase escrita aquí: todo llega por propiedades.
 */

import { AvisoDeError, Boton, Botones, frase, html } from "../componentes.js";

/** Una factura de la lista, con el botón que la elige (y que **no** engancha nada todavía). */
function FacturaParaElegir({ factura, textos }) {
  const c = textos.cesta || {};
  return html`
    <li>
      <div className="apunte-cabecera">
        <strong>${frase(factura.titulo)}</strong>
        <span>${frase(factura.cuando)}</span>
      </div>
      ${factura.proveedor ? html`<div className="apunte-detalle">${frase(factura.proveedor)}</div>` : null}
      ${factura.total ? html`<div className="apunte-detalle">${frase(factura.total)}</div>` : null}
      <div className="barra-acciones">
        <${Boton}
          etiqueta=${c.libro_factura_es_esta}
          accion="factura-proponer"
          datos=${{ id: factura.id }}
          clase="boton-claro"
        />
      </div>
    </li>
  `;
}

/**
 * La pantalla entera.
 *
 * Propiedades:
 *
 *  - `textos`: `{ cesta, acciones, facturas }` del servidor.
 *  - `albaran`: de qué albarán se está diciendo la factura (su título y su detalle), para no confundirlo
 *    con otro: en una finca puede haber tres albaranes del mismo proveedor.
 *  - `facturas`: sus facturas guardadas, para elegir.
 *  - `eleccion`: la factura elegida y **lo que el servidor propone** para ella: si este albarán está
 *    entre las propuestas, por qué se propone y qué líneas parecen el mismo producto. `null` es «todavía
 *    no se ha elegido ninguna».
 *  - `comprobando`: si se está preguntando al servidor (el botón que engancha se apaga y lo dice: sin
 *    eso, el mismo enganche se puede mandar dos veces).
 *  - `aviso`: lo que se dice cuando no se ha podido preguntar (sin cobertura) o cuando el servidor
 *    contesta que esa factura ya estaba enganchada a otro albarán.
 *  - `error`: lo que ha dicho el servidor, o nada.
 */
export function PantallaEngancharLaFactura({
  textos = {},
  albaran = {},
  facturas = [],
  eleccion = null,
  comprobando = false,
  aviso = "",
  error = "",
}) {
  const c = textos.cesta || {};
  return html`
    <h1>${frase(c.libro_factura_titulo)}</h1>
    <p className="pista">${frase(c.libro_factura_explica)}</p>
    <${AvisoDeError} texto=${error} />
    <div className="ayuda-campo">
      <p><strong>${frase(albaran.titulo)}</strong></p>
      <p>${frase(albaran.detalle)}</p>
    </div>
    ${aviso ? html`<div className="aviso">${frase(aviso)}</div>` : null}

    ${
      // La lista de facturas: elegir una **no apunta nada**, y se dice antes de tocar, no después.
      eleccion
        ? null
        : html`
            <h2>${frase(c.libro_factura_elige)}</h2>
            ${
              facturas.length
                ? html`
                    <p className="pista-campo">${frase(c.libro_factura_nada_apuntado)}</p>
                    <ul className="lista">
                      ${facturas.map(
                        (factura, indice) => html`
                          <${FacturaParaElegir} key=${indice} factura=${factura} textos=${textos} />
                        `,
                      )}
                    </ul>
                  `
                : html`
                    <div className="aviso">${frase(c.libro_factura_nada)}</div>
                    <${Boton} etiqueta=${facturas_texto(textos)} accion="facturas-abrir" clase="boton-claro" />
                  `
            }
          `
    }

    ${
      eleccion
        ? html`
            <h2>${frase(eleccion.titulo)}</h2>
            <div className=${eleccion.propuesta ? "aviso" : "aviso aviso-error"}>
              ${frase(eleccion.propuesta ? c.libro_factura_propuesta : c.libro_factura_no_propuesta)}
            </div>
            ${
              eleccion.como
                ? html`<p className="pista-campo">${frase(c.libro_factura_como)}: ${frase(eleccion.como)}</p>`
                : null
            }
            ${
              (eleccion.lineas || []).length
                ? html`
                    <h3>${frase(c.libro_factura_lineas)}</h3>
                    <ul className="lista">
                      ${eleccion.lineas.map(
                        (linea, indice) => html`<li key=${indice}>${frase(linea.texto)}</li>`,
                      )}
                    </ul>
                  `
                : null
            }
            <div className="barra-acciones">
              <button
                type="button"
                className="boton"
                data-accion="factura-enganchar-si"
                data-id=${eleccion.factura_id}
                disabled=${comprobando}
              >
                ${frase(
                  comprobando
                    ? c.libro_factura_comprobando
                    : eleccion.propuesta
                      ? c.libro_factura_si
                      : c.libro_factura_si_igual,
                )}
              </button>
              <${Boton}
                etiqueta=${c.libro_factura_otra}
                accion="factura-enganchar"
                datos=${{ id: albaran.id }}
                clase="boton-claro"
              />
            </div>
          `
        : null
    }

    <${Botones} botones=${albaran.acciones} />
  `;
}

/** El nombre de la pantalla de las facturas, que es a donde lleva el botón cuando no hay ninguna. */
function facturas_texto(textos) {
  return ((textos || {}).facturas || {}).titulo || "";
}

/** El elemento de React de esta pantalla, ya con sus propiedades puestas. */
export function pantallaDeEngancharLaFactura(propiedades) {
  return html`
    <${PantallaEngancharLaFactura}
      textos=${propiedades.textos}
      albaran=${propiedades.albaran}
      facturas=${propiedades.facturas}
      eleccion=${propiedades.eleccion}
      comprobando=${propiedades.comprobando}
      aviso=${propiedades.aviso}
      error=${propiedades.error}
    />
  `;
}
