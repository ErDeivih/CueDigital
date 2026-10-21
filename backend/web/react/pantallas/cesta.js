/*
 * cesta.js — «Lo que tengo en el almacén», escrita en React.
 *
 * POR QUÉ ESTA PANTALLA
 *
 * Es la quinta que se pasa a React. Cuenta **el libro de movimientos de cada producto**: lo que se
 * compró (y de dónde), lo que se ha gastado y lo que queda. Es la pantalla que responde a «¿me queda
 * producto para el próximo tratamiento?», y cuando no se puede restar lo dice en vez de inventarse un
 * número.
 *
 * **Lo que NO hace este componente:** no calcula nada. Los números —lo comprado, lo gastado, lo que
 * queda— los calcula el servidor, y aquí llegan **ya contados**, con sus etiquetas. Lo único que hace
 * `app.js` es preparar esas filas y pasarle los textos del servidor.
 *
 * Y una cosa que se conserva tal cual: **cuando un dato no se sabe, se enseña un guion (—), no un
 * cero.** Un cero sería un dato inventado, y en un cuaderno eso es lo peor que puede pasar.
 */

import { AvisoDeError, Boton, frase, html } from "../componentes.js";
import { AccionesDeUnaFicha } from "../piezas/acciones_de_una_ficha.js";
import { Tabla } from "../piezas/tabla.js";

/**
 * Un producto: su nombre, su etiqueta de estado y sus cuentas, fila a fila.
 *
 * Tres cosas del diseño de Stitch de esta pantalla (ronda 90, `docs/stitch/rediseno/cesta.png`):
 *
 *  1. **La etiqueta de estado** arriba a la derecha («Las cuentas cuadran», «Sin saber cuánto
 *     compraste», «No se puede comparar», «Míralo»): con la lista llena, lo primero que se busca es
 *     **cuál hay que mirar**, y eso no se puede sacar de tres números sueltos.
 *  2. **La fila de «Te queda» va en su recuadro y con el número grande**: es lo que se viene a ver.
 *  3. **El motivo va en su franja de aviso** (la misma que llevan los avisos de una tierra), no como un
 *     párrafo suelto: es «algo que hay que mirar», y en esta aplicación las cosas que hay que mirar van
 *     en su franja, con su señal.
 *
 * Y una cosa que se añadió el 30/09/2026: **sus dos botones**, CORREGIR y BORRAR (la pieza de siempre,
 * `acciones_de_una_ficha.js`). Los prepara `app.js` (`botonesDeCorregirYBorrar`) y son los mismos que lleva
 * el renglón de ese producto en «mis parcelas, productos y máquinas»: el almacén también se equivoca —una
 * cantidad mal escrita, un producto que ya no se usa—, y hasta hoy había que salir de esta pantalla para
 * arreglarlo (David lo pidió así: «recuerda también dejar borrar las cosas que introduzca»).
 */
function Producto({ producto, textos }) {
  const c = textos.cesta || {};
  const conEstado = producto.estado && producto.estado.texto;
  return html`
    <li>
      <div className="apunte-cabecera">
        <strong>${frase(producto.nombre_comercial)}</strong>
        ${conEstado
          ? html`<span className=${`etiqueta-estado etiqueta-estado-${producto.estado.tipo || "bien"}`}
              >${frase(producto.estado.texto)}</span
            >`
          : null}
      </div>
      ${
        producto.materia_activa
          ? html`<div className="apunte-detalle">${frase(producto.materia_activa)}</div>`
          : null
      }
      <dl>
        ${producto.filas.map((fila, indice) =>
          fila.destacada
            ? html`
                <div className="resumen-dato resumen-destacado" key=${indice}>
                  <dt>${frase(fila.etiqueta)}</dt>
                  <dd><span className="dato-grande">${frase(fila.valor)}</span></dd>
                </div>
              `
            : html`
                <div className="resumen-dato" key=${indice}>
                  <dt>${frase(fila.etiqueta)}</dt>
                  <dd>${frase(fila.valor)}</dd>
                </div>
              `,
        )}
      </dl>
      ${
        // El motivo de por qué no se puede restar (por ejemplo, porque lo comprado va en litros y lo
        // echado en kilos). Se enseña para que el agricultor sepa por qué no hay número, en vez de
        // ver un hueco y pensar que el programa se ha equivocado.
        producto.motivo
          ? html`
              <p className="tarjeta-aviso">
                <span className="tarjeta-aviso-icono" aria-hidden="true">!</span>
                ${frase(producto.motivo)}
              </p>
            `
          : null
      }
      <${AccionesDeUnaFicha} acciones=${producto.acciones} />
    </li>
  `;
}

/**
 * La pantalla entera.
 *
 * Propiedades:
 *
 *  - `textos`: `{ cesta, facturas, acciones }`, tal y como los sirve `/api/interfaz`.
 *  - `productos`: cada uno con su nombre, su materia activa, sus filas ya contadas y su motivo.
 *  - `tabla`: la misma lista para el ordenador, ya preparada por `app.js`: sus columnas ordenables, sus
 *    celdas y **el panel de al lado** con la ficha del producto elegido (30/09/2026). En el móvil no se pinta
 *    (el CSS esconde `.solo-escritorio`): allí manda la tarjeta, con el número grande de «te queda».
 *  - `resumen`: cuántos productos hay, ya en singular o en plural y dicho por el servidor (ronda 84). Va en
 *    su línea destacada, como el número de las tierras y el de los apuntes del cuaderno.
 *  - `error`: lo que ha dicho el servidor cuando algo ha fallado, o nada. Igual que en «los papeles»
 *    (la otra pantalla que enseña un error): se pasa aparte de los textos, porque **no es un texto
 *    de la pantalla: es lo que ha pasado**.
 */
export function PantallaCesta({
  textos = {},
  productos = [],
  tabla = null,
  resumen = "",
  error = "",
  // ***Y si la carga fallo*** (21/10/2026, D03): *«la cesta esta vacia» es una afirmacion sobre lo que el
  // agricultor tiene comprado; no se puede hacer sin haber podido preguntar.*
  noSePudoCargar = false,
  noSePudoCargarTexto = "",
}) {
  const c = textos.cesta || {};
  const acciones = textos.acciones || {};

  return html`
    <h1>${frase(c.titulo)}</h1>
    <p className="pista">${frase(c.explica)}</p>
    <${AvisoDeError} texto=${error} />
    ${
      // **Cuántos productos hay, con su palabra** (ronda 84). El servidor ya lo contaba y lo mandaba
      // —«Tienes 1 producto apuntado.», «Tienes 3 productos apuntados.»—, pero no lo enseñaba nadie: la
      // pantalla no lo leía. Es la misma línea de cuenta que llevan «mis cosas» y «mi cuaderno».
      productos.length && resumen ? html`<p className="cuantas">${frase(resumen)}</p>` : null
    }
    ${
      // **La tabla, solo en el ordenador**: el libro de entradas y salidas, producto por producto, con lo
      // comprado, lo echado y lo que queda uno debajo de otro (diseño de escritorio de Stitch).
      tabla && productos.length
        ? html`<div className="solo-escritorio"><${Tabla} tabla=${tabla} /></div>`
        : null
    }
    ${
      productos.length === 0
        ? noSePudoCargar
          ? html`<div className="aviso aviso-error">${frase(noSePudoCargarTexto)}</div>`
          : html`<div className="aviso">${frase(c.vacia)}</div>`
        : html`
            <ul className="lista solo-movil">
              ${productos.map(
                (producto, indice) =>
                  html`<${Producto} key=${indice} producto=${producto} textos=${textos} />`,
              )}
            </ul>
          `
    }
    <div className="ayuda-campo">
      <p><strong>${frase(c.para_que_sirve)}</strong></p>
      <p>${frase(c.como_apuntarlo)}</p>
    </div>
    <div className="barra-acciones">
      ${
        // **La puerta del libro del almacén** (T09, 03/10/2026). Esta pantalla contesta a «¿me queda
        // producto?» con lo comprado menos lo echado; lo que no puede contestar es lo que pide una
        // inspección: de qué lote salió cada cosa y qué entró de verdad el día que llegó el camión. Eso
        // vive en el libro, y desde aquí se llega a él. Las dos pantallas se dicen la una a la otra: allí
        // está el botón de volver a esta.
        html`<${Boton} etiqueta=${c.libro_ver_el_libro} accion="libro-ver" clase="boton-claro" />`
      }
      <${Boton} etiqueta=${textos.facturas ? textos.facturas.titulo : ""} accion="facturas-abrir" clase="boton-claro" />
      <${Boton} etiqueta=${c.ir_a_productos} accion="mis-cosas" clase="boton-claro" />
      <${Boton} etiqueta=${acciones.volver} accion="ir-inicio" clase="boton-claro" />
    </div>
  `;
}

/** El elemento de React de esta pantalla, ya con sus propiedades puestas. */
export function pantallaDeCesta(propiedades) {
  return html`
    <${PantallaCesta}
      textos=${propiedades.textos}
      productos=${propiedades.productos}
    noSePudoCargar=${propiedades.noSePudoCargar}
    noSePudoCargarTexto=${propiedades.noSePudoCargarTexto}
      tabla=${propiedades.tabla}
      resumen=${propiedades.resumen}
      error=${propiedades.error}
    />
  `;
}
