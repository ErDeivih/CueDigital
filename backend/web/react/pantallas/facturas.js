/*
 * facturas.js — «Mis facturas» (la lista) y «Factura guardada», escritas en React.
 *
 * POR QUÉ ESTA PANTALLA
 *
 * Es la decimonovena que se pasa a React, y es la mitad de un apartado que importa: **la factura es
 * el papel que demuestra la compra**. El programa lee la factura (de una foto o del PDF que manda el
 * proveedor) y de ahí salen tres cosas: cuánto producto tienes comprado, el número de factura y la
 * empresa que te lo vendió —que es lo que el cuaderno tiene que poder decir.
 *
 * **Lo que NO hace este componente:** no suma, no formatea y no decide si un papel tiene fichero o
 * no. Cada factura le llega ya contada desde `app.js`: su proveedor (o el texto de «sin proveedor»),
 * su línea de detalle, el total ya escrito en euros y cuántas líneas trae.
 *
 * DOS PANTALLAS EN UN FICHERO, Y POR QUÉ
 *
 * Son la misma idea en dos momentos: la lista de las que hay y la confirmación de la que se acaba de
 * guardar. Viven en el mismo fichero porque comparten textos y botones, y separarlas obligaría a
 * cargar dos módulos para enseñar una pantalla que se ve de un tirón.
 *
 * LO QUE SE CONSERVA A PROPÓSITO
 *
 *  1. Los `data-accion` (`factura-nueva`, `facturas-abrir`, `cesta-ver`, `ir-inicio`) y las clases.
 *  2. **Un total desconocido se enseña como «—», no como cero.** Un cero sería un dato inventado: la
 *     factura se guardó sin que el agricultor dijera el total, y eso es distinto de que valga cero.
 *  3. El aviso del lector (lo que el programa sabe leer y lo que no) va en su bloque, tal cual lo
 *     manda el servidor.
 *  4. Nada de `esc()` y ninguna frase escrita aquí: los textos llegan por propiedades.
 *
 * El componente es PURO: no llama a `fetch` ni toca el DOM.
 */

import { AvisoDeError, Boton, frase, html } from "../componentes.js";
import { AccionesDeUnaFicha } from "../piezas/acciones_de_una_ficha.js";
import { Tabla } from "../piezas/tabla.js";

/**
 * Una factura de la lista: el proveedor arriba, el detalle debajo, sus dos números y **su papel**.
 *
 * Del diseño de Stitch de esta pantalla (ronda 90, `docs/stitch/rediseno/facturas.png`): cada factura dice
 * si tiene guardada la foto del papel —es lo que se pide en una inspección— y ofrece el botón que toca:
 * **verla** si la tiene, o **subirla** si no. Ese dato estaba en el servidor desde la ronda 40 y no lo
 * enseñaba nadie.
 *
 * Y desde la ronda 93 ofrece **BORRAR**, que es lo que le falta a una factura que se subió equivocada
 * —David lo pidió con estas palabras: «recuerda también dejar borrar las cosas que introduzca porque
 * puede que me equivoque»—. Corregirla no se ofrece todavía: en una factura, corregir es revisar sus
 * líneas, y ese camino (que existe en el servidor) aún no se abre con lo que ya está guardado. El
 * programa dice lo que puede hacer, no lo que le gustaría.
 */
function Ficha({ factura, textos }) {
  const f = textos.facturas || {};
  return html`
    <li>
      <strong>${frase(factura.proveedor)}</strong>
      <div className="apunte-detalle">${frase(factura.detalle)}</div>
      <dl>
        <div className="resumen-dato">
          <dt>${frase(f.campo_total)}</dt>
          <dd>${frase(factura.total)}</dd>
        </div>
        <div className="resumen-dato">
          <dt>${frase(f.lineas_titulo)}</dt>
          <dd>${frase(factura.lineas)}</dd>
        </div>
      </dl>
      ${
        factura.tiene_fichero
          ? html`
              <p className="pista-campo">${frase(f.papel_guardado)}</p>
              <${Boton}
                etiqueta=${f.ver_fichero}
                accion="factura-papel-ver"
                datos=${{ id: factura.id }}
                clase="boton-claro"
              />
            `
          : html`
              <p className="tarjeta-aviso">
                <span className="tarjeta-aviso-icono" aria-hidden="true">!</span>
                ${frase(f.sin_fichero)}
              </p>
              <input type="file" id=${`factura-papel-${factura.id}`} className="oculto" />
              <${Boton}
                etiqueta=${f.subir_el_papel}
                accion="factura-papel-subir"
                datos=${{ id: factura.id }}
                clase="boton-claro"
              />
            `
      }
      <${AccionesDeUnaFicha} acciones=${factura.acciones} />
    </li>
  `;
}

/**
 * La pantalla entera.
 *
 * Propiedades:
 *
 *  - `textos`: `{ facturas, acciones }`, tal y como los sirve `/api/interfaz`.
 *  - `facturas`: las facturas del año, ya preparadas (o vacío, que es el caso del que no ha subido
 *    ninguna todavía).
 *  - `resumen`: cuántas hay, ya en singular o en plural y dicho por el servidor (`con_cuenta`).
 *  - `lector`: la nota del lector de facturas (lo que sabe leer y lo que no), o vacío.
 *  - `error`: lo que ha dicho el servidor.
 *  - `guardada`: la frase que se enseña cuando se acaba de guardar una factura (o vacío). Cuando
 *    viene, la pantalla es la de «Factura guardada», no la lista.
 */
export function PantallaFacturas({
  textos = {},
  facturas = [],
  resumen = "",
  lector = "",
  tabla = null,
  error = "",
  guardada = "",
}) {
  const f = textos.facturas || {};
  const acciones = textos.acciones || {};

  if (guardada) {
    return html`
      <h1>${frase(f.guardada)}</h1>
      <p>${frase(f.guardada_pista)}</p>
      <div className="barra-acciones">
        <${Boton} etiqueta=${f.ver_almacen} accion="cesta-ver" />
        <${Boton} etiqueta=${f.titulo} accion="facturas-abrir" clase="boton-claro" />
      </div>
      <${Boton} etiqueta=${acciones.volver} accion="ir-inicio" clase="boton-claro" />
    `;
  }

  return html`
    <h1>${frase(f.titulo)}</h1>
    <p className="pista">${frase(f.explica)}</p>
    <${AvisoDeError} texto=${error} />
    ${
      facturas.length && resumen
        ? html`<p className="cuantas">${frase(resumen)}</p>`
        : null
    }
    ${
      // **La tabla, solo en el ordenador** (30/09/2026): las facturas del año juntas, con sus números y si
      // tienen el papel guardado. En el móvil, la ficha de cada una con su papel al lado.
      tabla && facturas.length
        ? html`<div className="solo-escritorio">
            ${tabla.indicadores && tabla.indicadores.length ? html`
              <ul className="mando-numeros" aria-label=${frase(f.resumen_cifras)}>
                ${tabla.indicadores.map((indicador, indice) => html`
                  <li className="mando-numero" key=${indice}>
                    <p className="mando-numero-etiqueta">${frase(indicador.etiqueta)}</p>
                    <p className="mando-numero-valor">${frase(indicador.valor)}</p>
                  </li>
                `)}
              </ul>
            ` : null}
            <${Tabla} tabla=${tabla} />
          </div>`
        : null
    }
    ${
      facturas.length === 0
        ? html`<div className="aviso">${frase(f.sin_facturas)}</div>
            <p className="pista-campo">${frase(f.sin_facturas_pista)}</p>`
        : html`<ul className="lista solo-movil">
            ${facturas.map(
              (factura, indice) => html`<${Ficha} key=${indice} factura=${factura} textos=${textos} />`,
            )}
          </ul>`
    }
    ${
      // Lo que el lector sabe leer y lo que no. Va aquí, con la lista, porque es donde el agricultor
      // se pregunta por qué una factura se leyó mal.
      lector ? html`<h2>${frase(f.avisos_titulo)}</h2><p className="aviso">${frase(lector)}</p>` : null
    }
    <div className="barra-acciones">
      <${Boton} etiqueta=${f.anadir} accion="factura-nueva" />
      <${Boton} etiqueta=${acciones.volver} accion="ir-inicio" clase="boton-claro" />
    </div>
  `;
}

/** El elemento de React de esta pantalla, ya con sus propiedades puestas. */
export function pantallaDeFacturas(propiedades) {
  return html`<${PantallaFacturas}
    textos=${propiedades.textos}
    facturas=${propiedades.facturas}
    resumen=${propiedades.resumen}
    lector=${propiedades.lector}
    tabla=${propiedades.tabla}
    error=${propiedades.error}
    guardada=${propiedades.guardada}
  />`;
}
