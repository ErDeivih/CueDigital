/*
 * medidas.js — «Las medidas preventivas», escrita en React.
 *
 * POR QUÉ ESTA PANTALLA
 *
 * Es la novena que se pasa a React y la **segunda con campos**: las diez medidas preventivas que la
 * ley pide haber probado antes de echar producto (cambiar de cultivo, mirar el campo antes de
 * decidir, limpiar la máquina…). El agricultor las marca una vez y valen para todo el año.
 *
 * LA MISMA DECISIÓN QUE EN «MIS DATOS», Y POR EL MISMO MOTIVO
 *
 * Los diez botones llevan su `data-codigo` y los campos de notas su `id` (`nota-<código>`), y **los
 * sigue leyendo `app.js`**: el manejador de clics es uno solo y vive allí. Hay un detalle que
 * importa y que está escrito en el código de `app.js` desde hace rondas: al marcar o desmarcar una
 * medida la pantalla **se vuelve a pintar**, así que las notas que el agricultor ya había escrito se
 * recogen del DOM **antes** de repintar. Con React eso se sigue cumpliendo igual, porque los campos
 * son nodos de verdad del navegador.
 *
 * QUÉ SE CONSERVA A PROPÓSITO
 *
 *  1. El icono de cada medida va **marcado o sin marcar** (✅ / ⬜) además del color del botón: el
 *     proyecto tiene la regla de no informar con el color en solitario, y aquí se cumple.
 *  2. La nota solo se pide **de la medida que está marcada**: pedir diez notas siempre sería pedir
 *     diez cosas para nada.
 *  3. Los textos del servidor, incluido el aviso de que el catálogo es una muestra y no una lista
 *     cerrada.
 */

import { Boton, frase, html } from "../componentes.js";

/** Una medida: su pregunta, si está marcada y, si lo está, su nota. */
function Medida({ medida, textos }) {
  const m = textos.medidas || {};
  return html`
    ${
      // La etiqueta de «hecho en mi finca» (diseño de Stitch de esta pantalla, ronda 90): lo marcado se
      // ve por el visto del cuadro y por el color, pero **se dice con palabras**, que es la regla del
      // proyecto para no informar solo con el color.
      medida.marcada
        ? html`<span className="etiqueta-estado etiqueta-estado-bien">${frase(m.hecho_en_mi_finca)}</span>`
        : null
    }
    <${Boton}
      etiqueta=${medida.pregunta}
      icono=${medida.marcada ? "✅" : "⬜"}
      accion="medidas-marcar"
      datos=${{ codigo: medida.codigo }}
      clase=${medida.marcada ? "boton-elegido" : "boton-claro"}
      flecha=${false}
    />
    ${
      medida.marcada
        ? html`
            <div className="campo">
              <label htmlFor=${`nota-${medida.codigo}`}>${frase(m.observaciones)}</label>
              <input
                id=${`nota-${medida.codigo}`}
                type="text"
                defaultValue=${medida.nota || ""}
                placeholder=${frase(m.tus_palabras)}
              />
            </div>
          `
        : null
    }
  `;
}

/**
 * La pantalla entera.
 *
 * Propiedades:
 *
 *  - `textos`: `{ medidas, acciones }`, tal y como los sirve `/api/interfaz`.
 *  - `medidas`: las diez medidas de la finca, en su orden, con lo que ya está marcado y sus notas.
 *  - `hay_declaracion`: si la finca **ya tiene** declarado qué hace (lo dice el servidor). Con eso se
 *    ofrece quitarlo, y sin eso no: en una finca sin declarar no hay nada que quitar (ronda 93).
 */
export function PantallaMedidas({ textos = {}, medidas = [], hay_declaracion = false }) {
  const m = textos.medidas || {};
  const acciones = textos.acciones || {};

  return html`
    <h1>${frase(m.titulo)}</h1>
    <p className="pista">${frase(m.explica)}</p>
    <h2>${frase(m.marcar_titulo)}</h2>
    <p className="pista-campo">${frase(m.marcar_pista)}</p>
    ${
      // Las diez medidas, **numeradas** (diseño de Stitch de esta pantalla, ronda 90): son diez y, sin
      // números, no se sabe cuántas quedan por mirar. El número lo pone el CSS con un contador, así que
      // la pregunta sigue siendo la del servidor, palabra por palabra.
      html`
        <ol className="medidas-numeradas">
          ${medidas.map((medida) => html`<li key=${medida.codigo}>
            <${Medida} medida=${medida} textos=${textos} />
          </li>`)}
        </ol>
      `
    }
    <p className="pista-campo">${frase(m.catalogo_aviso)}</p>
    <div className="barra-acciones">
      <${Boton} etiqueta=${m.guardar} accion="medidas-guardar" />
      <${Boton} etiqueta=${m.no_hago_ninguna} accion="medidas-ninguna" clase="boton-claro" />
      <${Boton} etiqueta=${acciones.volver} accion="inicio" datos=${{ ir: "mi_cuaderno" }} clase="boton-claro" />
    </div>
    ${
      // **Quitar la declaración entera** (ronda 93): no es lo mismo que «no hago ninguna», y por eso no
      // está en la barra de guardar. Va debajo, aparte, con su explicación: lo que hace es dejar la finca
      // **sin contestar**, como recién dada de alta, y el programa vuelve a preguntar.
      hay_declaracion
        ? html`
            <${Boton} etiqueta=${m.quitar} accion="medidas-quitar" clase="boton-peligro" />
            <p className="pista-campo">${frase(m.quitar_pista)}</p>
          `
        : null
    }
  `;
}

/** El elemento de React de esta pantalla, ya con sus propiedades puestas. */
export function pantallaDeMedidas(propiedades) {
  return html`
    <${PantallaMedidas}
      textos=${propiedades.textos}
      medidas=${propiedades.medidas}
      hay_declaracion=${propiedades.hay_declaracion}
    />
  `;
}
