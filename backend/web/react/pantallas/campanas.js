/*
 * campanas.js — «Los años de mi cuaderno» (la campaña), escrita en React.
 *
 * POR QUÉ ESTA PANTALLA
 *
 * Hasta la ronda 93, **la campaña la creaba el programa** al darse de alta la cuenta y no había ninguna
 * pantalla que la enseñara: `GET/POST/PUT/DELETE /api/campanas` estaban en el servidor desde la ronda 93
 * y no los pedía nadie. De la campaña cuelga **el año entero del cuaderno** (cada apunte guarda su
 * `campana_id`), así que no poder tocarla tenía dos consecuencias de verdad:
 *
 *  1. Un año mal escrito —2027 donde iba 2026— dejaba **todos los apuntes de ese año** colgando de un año
 *     que no es el suyo, y no había forma de arreglarlo.
 *  2. Cuando llegaba el año siguiente, **no había forma de empezar el cuaderno de ese año**: el programa
 *     seguía apuntando en el año viejo.
 *
 * LO QUE SE CONSERVA A PROPÓSITO
 *
 *  1. Los `data-accion` (`campanas-abrir` se queda donde estaba, `campana-nueva`, `cosa-corregir`,
 *     `cosa-borrar`, `inicio`) y las clases.
 *  2. **Ningún número se calcula aquí.** Cuántas cosas tiene dentro un año lo dice el servidor
 *     (`cuantas_cosas`), y la frase la arma `app.js` con `conCuenta` (singular y plural). Un cero
 *     inventado al lado de un año es exactamente lo que este programa no hace. Cuando el servidor **no lo
 *     ha contado** (`null`, que es lo que devuelve `/api/campanas/actual`), no se dice nada.
 *  3. **El botón de borrar se enseña apagado cuando ese año no se puede quitar**, y al lado se explica por
 *     qué (diseño de Stitch de esta pantalla, ronda 93): ofrecer un botón que va a fallar y no decir nada
 *     hasta que se pulse es la forma de que el agricultor crea que el programa está roto.
 *  4. Nada de `esc()` y ninguna frase escrita aquí: los textos llegan por propiedades.
 *
 * El componente es PURO: no llama a `fetch` ni toca el DOM. Los años le llegan ya contados: el año ya
 * escrito («2026»), sus dos fechas ya formateadas, si es el que se está llevando, si está cerrado, cuánto
 * tiene dentro y **si se puede quitar**.
 */

import { AvisoDeError, Boton, frase, html } from "../componentes.js";
import { AccionesDeUnaFicha } from "../piezas/acciones_de_una_ficha.js";
import { Tabla } from "../piezas/tabla.js";

/** Un año del cuaderno, con lo que hay que saber de él de un vistazo. */
function Ficha({ campana, textos }) {
  const c = textos.campanas || {};
  const fila = (etiqueta, valor) =>
    valor
      ? html`<p className="tarjeta-fila">
          <span className="tarjeta-fila-etiqueta">${frase(etiqueta)}</span>
          <span className="tarjeta-fila-valor">${frase(valor)}</span>
        </p>`
      : null;
  return html`
    <li>
      <p className="tarjeta-rotulo">${frase(c.rotulo)}</p>
      <div className="campana-cabecera">
        <strong className="campana-anio">${frase(campana.anio)}</strong>
        ${
          // El estado del año, en una etiqueta: cuál se está llevando (es lo que se viene a mirar) y si
          // ya lo ha dado por terminado. Se dice **con palabras** además del color.
          campana.es_la_que_llevo
            ? html`<span className="etiqueta-estado etiqueta-estado-mirar">${frase(c.el_que_llevo)}</span>`
            : campana.cerrada
              ? html`<span className="etiqueta-estado">${frase(c.cerrado)}</span>`
              : html`<span className="etiqueta-estado">${frase(c.abierto)}</span>`
        }
      </div>
      ${fila(c.empieza, campana.desde)} ${fila(c.termina, campana.hasta)}
      ${
        // Cuánto hay dentro. Es lo que explica **por qué** un año no se puede quitar, así que va antes que
        // los botones y no después. Si el servidor no lo ha contado, no se dice nada (ni un cero).
        campana.dentro ? html`<p className="pista-campo">${frase(campana.dentro)}</p>` : null
      }
      ${
        campana.dentro && !campana.se_puede_quitar
          ? html`
              <p className="tarjeta-aviso">
                <span className="tarjeta-aviso-icono" aria-hidden="true">!</span>
                ${frase(c.no_se_puede_quitar)}
              </p>
            `
          : null
      }
      <${AccionesDeUnaFicha} acciones=${campana.acciones} />
    </li>
  `;
}

/**
 * La pantalla entera.
 *
 * Propiedades:
 *
 *  - `textos`: `{ campanas, acciones, corregir }`, tal y como los sirve `/api/interfaz`.
 *  - `campanas`: los años, ya preparados por `app.js` (el año escrito, sus fechas formateadas, si es el
 *    que se está llevando, si está cerrado, cuánto tiene dentro y sus dos botones).
 *  - `tabla`: la misma lista como tabla, para el ordenador (o `null`, y entonces solo salen las fichas).
 *  - `error`: lo que ha dicho el servidor (o vacío).
 */
export function PantallaCampanas({
  textos = {},
  campanas = [],
  tabla = null,
  error = "",
  // ***Y si la carga fallo*** (21/10/2026, D03).
  noSePudoCargar = false,
  noSePudoCargarTexto = "",
}) {
  const c = textos.campanas || {};
  const acciones = textos.acciones || {};

  return html`
    <h1>${frase(c.titulo)}</h1>
    <p className="pista">${frase(c.explica)}</p>
    <${AvisoDeError} texto=${error} />
    ${
      // **La tabla, solo en el ordenador** (30/09/2026): los años de un vistazo, uno debajo de otro, con lo
      // que tiene cada uno dentro. En el móvil, la ficha de siempre.
      tabla && campanas.length
        ? html`<div className="solo-escritorio"><${Tabla} tabla=${tabla} /></div>`
        : null
    }
    ${
      campanas.length === 0
        ? noSePudoCargar
          ? html`<div className="aviso aviso-error">${frase(noSePudoCargarTexto)}</div>`
          : html`<div className="aviso">${frase(c.sin_campanas)}</div>`
        : html`<ul className="lista solo-movil">
            ${campanas.map(
              (campana, indice) =>
                html`<${Ficha} key=${indice} campana=${campana} textos=${textos} />`,
            )}
          </ul>`
    }
    <${Boton}
      etiqueta=${c.anadir}
      pista=${c.anadir_pista}
      accion="campana-nueva"
      clase="boton-claro"
    />
    <div className="barra-acciones">
      <${Boton} etiqueta=${acciones.volver} accion="inicio" datos=${{ ir: "mi_cuaderno" }} clase="boton-claro" />
    </div>
  `;
}

/** El elemento de React de esta pantalla, ya con sus propiedades puestas. */
export function pantallaDeCampanas(propiedades) {
  return html`<${PantallaCampanas}
    textos=${propiedades.textos}
    campanas=${propiedades.campanas}
    noSePudoCargar=${propiedades.noSePudoCargar}
    noSePudoCargarTexto=${propiedades.noSePudoCargarTexto}
    tabla=${propiedades.tabla}
    error=${propiedades.error}
  />`;
}
