/*
 * grupos.js — «Los grupos de parcelas», escrita en React.
 *
 * POR QUÉ ESTA PANTALLA
 *
 * Es la undécima que se pasa a React y la última de las que son de mirar y pulsar. Un grupo es lo que
 * la app oficial llama **UHC**: parcelas que se llevan igual (mismo cultivo, mismo sistema) y que se
 * apuntan de una vez. Cuando hay cincuenta tierras, eso es la diferencia entre apuntar un tratamiento
 * una vez o cincuenta.
 *
 * **Lo que NO hace este componente:** no junta nada. Cada grupo le llega **ya contado**: su nombre, de
 * cuántas parcelas es, cuántas hectáreas suma, qué cultivo tiene y **las parcelas, ya escritas**. Quien
 * prepara eso es `app.js`.
 *
 * Y hay un aviso que importa de verdad, que se conserva tal cual: **si faltan cultivos por decir, los
 * grupos automáticos no se pueden calcular bien** (el grupo se hace por cultivo). En vez de dejar un
 * botón que no haría lo que promete, se dice y se da el botón que lo arregla: es la regla del proyecto
 * de no dejar al agricultor sin salida.
 */

import { AvisoDeError, Boton, frase, html } from "../componentes.js";
import { AccionesDeUnaFicha } from "../piezas/acciones_de_una_ficha.js";

/** Un grupo: su nombre, sus cuentas y las tierras que lo forman. */
function Grupo({ grupo, textos }) {
  const g = textos.grupos || {};
  return html`
    <li>
      ${
        // De quién es el grupo, en su etiqueta (diseño de Stitch de esta pantalla, ronda 90): lo juntó el
        // programa o lo juntó él, y eso importa para saber si puede cambiarlo.
        html`<span className="etiqueta-estado etiqueta-estado-voluntario"
          >${frase(grupo.automatico ? g.automatico : g.juntado_por_ti)}</span
        >`
      }
      <strong>${frase(grupo.nombre)}</strong>
      <div className="apunte-detalle">${frase(grupo.detalle)}</div>
      ${
        // Las tierras del grupo, una por una y con sus hectáreas: antes era una línea con los nombres
        // separados por puntos, y con seis tierras no se sabía cuál era cuál ni cuánto tenía cada una.
        grupo.tierras && grupo.tierras.length
          ? html`
              <p className="pista-campo">${frase(g.tierras_del_grupo)}</p>
              <ol className="tierras-del-grupo">
                ${grupo.tierras.map(
                  (tierra, indice) => html`<li key=${indice}>
                    <span>${frase(tierra.nombre)}</span>
                    <span>${frase(tierra.hectareas)}</span>
                  </li>`,
                )}
              </ol>
            `
          : html`<p className="pista-campo">${frase(grupo.parcelas)}</p>`
      }
      ${
        // **CORREGIR y BORRAR el grupo** (ronda 92). Un grupo lo junta el programa, así que lo único que
        // se cambia es el nombre: «Cebada (3 parcelas)» es como lo llama el programa; el agricultor lo
        // llamará «el de mi hermano». Y se puede borrar, porque un grupo es una forma de apuntar de una
        // vez, no un dato del cuaderno.
        html`<${AccionesDeUnaFicha} acciones=${grupo.acciones} />`
      }
    </li>
  `;
}

/**
 * La pantalla entera.
 *
 * Propiedades:
 *
 *  - `textos`: `{ grupos, cultivos, maestros, acciones }`, tal y como los sirve `/api/interfaz`.
 *  - `grupos`: los grupos, ya preparados por `app.js`.
 *  - `faltanCultivos`: cuántas tierras no dicen todavía qué tienen sembrado este año.
 *  - `error`: lo que ha dicho el servidor cuando algo ha fallado, o nada.
 */
export function PantallaGrupos({
  textos = {},
  grupos = [],
  faltanCultivos = 0,
  error = "",
  // ***Y si la carga fallo*** (21/10/2026, D03).
  noSePudoCargar = false,
  noSePudoCargarTexto = "",
}) {
  const g = textos.grupos || {};
  const cultivos = textos.cultivos || {};
  const maestros = textos.maestros || {};
  const acciones = textos.acciones || {};

  return html`
    <h1>${frase(g.titulo)}</h1>
    <p className="pista">${frase(g.explica)}</p>
    <${AvisoDeError} texto=${error} />
    ${
      faltanCultivos
        ? html`
            <div className="aviso">${frase(g.faltan_cultivos)}</div>
            <${Boton} etiqueta=${cultivos.titulo} accion="cultivo-ver-todos" clase="boton-claro" />
          `
        : null
    }
    ${
      grupos.length === 0
        ? noSePudoCargar
          ? html`<div className="aviso aviso-error">${frase(noSePudoCargarTexto)}</div>`
          : html`<div className="aviso">${frase(g.sin_grupos)}</div>`
        : null
    }
    ${
      grupos.length
        ? html`
            <ul className="lista">
              ${grupos.map((grupo, indice) => html`<${Grupo} key=${indice} grupo=${grupo} textos=${textos} />`)}
            </ul>
          `
        : null
    }
    <div className="ayuda-campo">
      <p><strong>${frase(g.para_que)}</strong></p>
    </div>
    <div className="barra-acciones">
      <${Boton} etiqueta=${g.calcular} accion="grupo-calcular" clase="boton-principal" />
      <${Boton} etiqueta=${maestros.titulo} accion="mis-cosas" clase="boton-claro" />
      <${Boton} etiqueta=${acciones.volver} accion="ir-inicio" clase="boton-claro" />
    </div>
  `;
}

/** El elemento de React de esta pantalla, ya con sus propiedades puestas. */
export function pantallaDeGrupos(propiedades) {
  return html`
    <${PantallaGrupos}
      textos=${propiedades.textos}
      grupos=${propiedades.grupos}
    noSePudoCargar=${propiedades.noSePudoCargar}
    noSePudoCargarTexto=${propiedades.noSePudoCargarTexto}
      faltanCultivos=${propiedades.faltanCultivos}
      error=${propiedades.error}
    />
  `;
}
