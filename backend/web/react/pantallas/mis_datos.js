/*
 * mis_datos.js — «Mis datos»: la portada del cuaderno, escrita en React.
 *
 * POR QUÉ ESTA PANTALLA Y POR QUÉ IMPORTA MÁS QUE LAS ANTERIORES
 *
 * Es la octava que se pasa a React, pero es **la primera con campos que se rellenan**, y eso la
 * convierte en el modelo de las que faltan: la mitad de las pantallas que quedan (el asistente de
 * apuntar, las altas, las facturas) son formularios, y hasta ahora no había ninguna hecha en React.
 *
 * LA DECISIÓN QUE HAY QUE ENTENDER, PORQUE VALE PARA TODAS LAS DEMÁS
 *
 * Los campos **siguen teniendo su `id`** (`finca-nombre`, `finca-nif`…) y **los sigue leyendo
 * `app.js`** al guardar, igual que antes. No es un descuido ni una migración a medias:
 *
 *  - En esta aplicación, **un solo manejador de clics** (en `document`) atiende todos los botones, y
 *    vive en `app.js`. Cuando alguien pulsa «GUARDAR», quien guarda es `app.js`, y lee los campos por
 *    su `id`.
 *  - Poner el estado dentro del componente obligaría a que el componente le contara a `app.js` cada
 *    tecla, o a montar un estado compartido entre las dos mitades. Eso es **otro trabajo, y más
 *    grande**, y no es lo que arregla esta pantalla.
 *  - Y hay una razón que se ve al momento: **decenas de pruebas escriben en esos campos por su `id`**
 *    (y con razón: es como lo hace una persona). Si los `id` cambian, esas pruebas dejan de
 *    comprobar nada.
 *
 * Así que aquí se usa lo que en React se llama un **formulario no controlado**: los campos los pinta
 * React con su valor de partida, y quien los lee al guardar es el mismo de siempre. Lo que cambia es
 * **quién los dibuja**, que es el objetivo de esta migración.
 *
 * QUÉ SE CONSERVA A PROPÓSITO
 *
 *  1. Los mismos `id` y los mismos nombres de campo.
 *  2. Los mismos textos del servidor (`textos.py`): el título, la explicación, el nombre de cada
 *     campo y su pista.
 *  3. El aviso de «guardado» y el de error, con sus clases de siempre (`aviso`, `aviso-error`).
 *  4. El botón de volver, que lleva a «mi cuaderno» con `data-accion="inicio" data-ir="mi_cuaderno"`.
 *  5. **El botón que lleva a «quién entra en mi finca»** (ronda 89), debajo de los campos: esta es la
 *     pantalla de la finca —el titular, sus datos y su nombre—, así que es aquí donde se busca quién más
 *     entra en ella. La otra mitad de eso (en qué finca estás trabajando) vive en la misma pantalla, y por
 *     eso las dos van con los mismos textos.
 */

import { AvisoDeError, Boton, frase, html } from "../componentes.js";

/**
 * Un campo: su nombre, su valor de partida y su pista.
 *
 * **Ojo con los comentarios dentro de una plantilla `htm`**: si llevan una comilla invertida (la que
 * se usa para escribir las plantillas), cierran la plantilla y el fichero deja de compilar. Pasó al
 * escribir esto: un comentario que explicaba «`defaultValue` y no `value`» rompió la pantalla entera.
 * Los comentarios van aquí fuera, en el código.
 *
 * Se usa `defaultValue` y no `value` a propósito: así el agricultor puede escribir sin que React le
 * devuelva el valor viejo en cada tecla. Lo que escriba lo lee `app.js` cuando pulsa GUARDAR.
 */
function Campo({ campo, valor, tipo, textos }) {
  const d = textos.mis_datos || {};
  // **El campo de tres respuestas** (A13, 05/10/2026): la producción ecológica de la finca no es un sí o un
  // no, son **tres cosas** —«sí», «no» y «no lo sé»— y el intermedio importa: mientras no conste, el
  // programa avisa de que no ha podido comprobar si un producto vale para ecológico, en vez de dar por
  // bueno que la finca no es ecológica (que es lo que hacía, porque el campo nacía en «no»).
  //
  // Es un `select` y no dos botones porque esta pantalla es un formulario de campos numerados y el
  // agricultor la rellena de arriba abajo: un desplegable no rompe el orden y se lee con el teclado.
  // El valor vacío es «no lo sé», y es el que sale elegido cuando nadie ha contestado.
  if (tipo === "si_no_no_se") {
    return html`
      <div className="campo">
        <label htmlFor=${`finca-${campo}`}>${frase(d[campo])}</label>
        <select id=${`finca-${campo}`} defaultValue=${valor || ""}>
          <option value="">No lo sé</option>
          <option value="si">Sí</option>
          <option value="no">No</option>
        </select>
        <p className="pista-campo">${frase(d[`${campo}_pista`])}</p>
      </div>
    `;
  }
  return html`
    <div className="campo">
      <label htmlFor=${`finca-${campo}`}>${frase(d[campo])}</label>
      <input id=${`finca-${campo}`} type="text" defaultValue=${valor || ""} />
      <p className="pista-campo">${frase(d[`${campo}_pista`])}</p>
    </div>
  `;
}

/**
 * La pantalla entera.
 *
 * Propiedades:
 *
 *  - `textos`: `{ mis_datos, acciones }`, tal y como los sirve `/api/interfaz`.
 *  - `campos`: la lista de campos, en su orden, con su valor actual.
 *  - `guardado`: si acaba de guardarse, para enseñar el aviso.
 *  - `error`: lo que ha dicho el servidor cuando no se ha podido guardar.
 */
export function PantallaMisDatos({ textos = {}, campos = [], guardado = false, error = "" }) {
  const d = textos.mis_datos || {};
  const fincas = textos.fincas || {};
  const campanas = textos.campanas || {};
  const acciones = textos.acciones || {};

  return html`
    <h1>${frase(d.titulo)}</h1>
    <p className="pista">${frase(d.explica)}</p>
    <${AvisoDeError} texto=${error} />
    ${guardado ? html`<p className="aviso">${frase(d.guardado)}</p>` : null}
    ${
      // Los campos van **numerados** (diseño de Stitch de esta pantalla, ronda 90): es un formulario de
      // once renglones y, sin números, no se sabe cuánto queda. Los pone el CSS con un contador —no hay
      // ningún número escrito en el componente—, así que el rótulo del campo sigue siendo el del servidor.
      html`
        <ol className="campos-numerados">
          ${campos.map(
            (campo) => html`<li key=${campo.campo}>
              <${Campo}
                campo=${campo.campo}
                valor=${campo.valor}
                tipo=${campo.tipo}
                textos=${textos}
              />
            </li>`,
          )}
        </ol>
      `
    }
    <div className="barra-acciones">
      <${Boton} etiqueta=${d.guardar} accion="mis-datos-guardar" />
      ${
        // El camino a «quién entra en mi finca», con su explicación debajo (diseño de Stitch): es una
        // pantalla que no se busca si no se sabe que está.
        html`<${Boton}
          etiqueta=${fincas.titulo}
          pista=${fincas.pista_boton}
          accion="quien-entra-abrir"
          clase="boton-claro"
        />`
      }
      ${
        // Y el de **los años del cuaderno** (ronda 93), por el mismo motivo y en el mismo sitio: el año
        // es de la finca y del cuaderno, que es lo que se toca en esta pantalla. Sin esta puerta, el
        // agricultor no tenía forma de arreglar un año mal puesto ni de empezar el año siguiente.
        html`<${Boton}
          etiqueta=${campanas.abrir}
          pista=${campanas.explica}
          accion="campanas-abrir"
          clase="boton-claro"
        />`
      }
      <${Boton} etiqueta=${acciones.volver} accion="inicio" datos=${{ ir: "mi_cuaderno" }} clase="boton-claro" />
    </div>
  `;
}

/** El elemento de React de esta pantalla, ya con sus propiedades puestas. */
export function pantallaDeMisDatos(propiedades) {
  return html`
    <${PantallaMisDatos}
      textos=${propiedades.textos}
      campos=${propiedades.campos}
      guardado=${propiedades.guardado}
      error=${propiedades.error}
    />
  `;
}
