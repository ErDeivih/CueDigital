/*
 * mapa.js — El mapa del SIGPAC, escrito en React.
 *
 * POR QUÉ ESTA PANTALLA
 *
 * Es la vigesimosegunda que se pasa a React y es **el camino más corto para dar de alta una tierra**:
 * el agricultor abre el mapa donde está (o donde tiene sus parcelas), toca el trozo que es suyo, y el
 * SIGPAC le dice la referencia, la superficie, el uso, el pueblo y si cae en zona de nitratos. Sin
 * esto hay que copiar siete números por cada trozo.
 *
 * **Es la primera pantalla migrada que se toca con el dedo**, y eso no cambia nada: el toque lo sigue
 * atendiendo el manejador delegado de `document` (`data-accion="mapa-tocar"`), que lee **dónde** se ha
 * tocado de las coordenadas del propio evento. Por eso aquí no hay ni un manejador de React: si el
 * toque se enganchara al componente, se perdería la posición.
 *
 * LO QUE SE CONSERVA A PROPÓSITO
 *
 *  1. Los `data-accion` (`mapa-tocar`, `mapa-acercar`, `mapa-alejar`, `mapa-estoy-aqui`,
 *     `mapa-preguntar`, `mapa-apuntar`, `mapa-no-es-esa`, `mapa-volver`, `elegir`) y las clases del
 *     mapa (`.mapa-vista`, `.mapa-foto`, `.mapa-linderos`, `.mapa-svg`, `.mapa-tocar`, `.mapa-cruz`).
 *  2. **El campo del nombre (`alias_mapa`) conserva su `id`**: lo lee `recogeElMapa()` antes de
 *     repintar, y si cambia, el nombre que el agricultor escribe se pierde.
 *  3. **El dibujo del trozo va en el `svg`, con sus puntos ya convertidos a píxeles**: el componente
 *     no sabe de coordenadas.
 *  4. Cuando no se sabe por dónde empezar (sin parcelas y sin ubicación) **no se pinta un mapa**:
 *     se dice. Una caja de coordenadas inventada enseñaría el mapa de otro sitio.
 *  5. Nada de `esc()` y ninguna frase escrita aquí: los textos llegan por propiedades.
 *
 * El componente es PURO: no llama a `fetch`, no pide la ubicación y no toca el DOM.
 */

import { AvisoDeError, Boton, frase, html } from "../componentes.js";

/** El mapa con la foto, los linderos, el trozo marcado y la cruz del centro. */
function Vista({ textos, imagenes, poligono, cargando }) {
  const m = textos.mapa || {};
  return html`
    <div className="mapa-vista">
      <img className="mapa-foto" src=${imagenes.foto} alt=${frase(m.la_foto)} />
      <img className="mapa-linderos" src=${imagenes.linderos} alt=${frase(m.los_linderos)} />
      <svg className="mapa-svg" viewBox=${imagenes.vista} aria-hidden="true">
        ${poligono ? html`<polygon points=${poligono} />` : null}
      </svg>
      <button
        type="button"
        className="mapa-tocar"
        data-accion="mapa-tocar"
        aria-label=${frase(m.poner_en_el_centro)}
      ></button>
      <span className="mapa-cruz" aria-hidden="true"></span>
      ${cargando ? html`<p className="mapa-cargando">${frase(m.cargando)}</p>` : null}
    </div>
  `;
}

/** Lo que el SIGPAC ha contestado del trozo que se está mirando, y el botón de apuntarlo. */
function Elegido({ textos, elegido }) {
  const m = textos.mapa || {};
  return html`
    <div className="mapa-elegido">
      ${
        // **La confirmación de que el SIGPAC ha contestado, con su recordatorio** (diseño de Stitch de esta
        // pantalla, ronda 90): dice que se ha comprobado y que **compruebe él los datos contra su papel**, que
        // es lo único que garantiza que se apunta la tierra que es. El aviso se queda hasta que se apunte o se
        // diga que no es esa.
        m.comprobado
          ? html`
              <p className="pista-campo"><strong>${frase(m.comprobado)}</strong></p>
            `
          : null
      }
      <h2>${frase(m.encontrado_titulo)}</h2>
      <p className="pregunta">${frase(m.pregunta)}</p>
      <dl>
        ${elegido.filas.map(
          ([etiqueta, valor], indice) => html`
            <div className="resumen-dato" key=${indice}>
              <dt>${frase(etiqueta)}</dt>
              <dd>${frase(valor)}</dd>
            </div>
          `,
        )}
      </dl>
      <div className="campo">
        <label>${frase(elegido.sistema_etiqueta)}</label>
        ${elegido.sistemas.map(
          (sistema) => html`
            <${Boton}
              key=${sistema.valor}
              etiqueta=${sistema.texto}
              accion="elegir"
              datos=${{ campo: "sistema", valor: sistema.valor }}
              clase=${sistema.elegido ? "boton-elegido" : "boton-claro"}
            />
          `,
        )}
      </div>
      <div className="campo">
        <label htmlFor="alias_mapa">${frase(elegido.alias_etiqueta)}</label>
        <input id="alias_mapa" type="text" defaultValue=${frase(elegido.alias)} />
      </div>
      <div className="barra-acciones">
        <${Boton} etiqueta=${m.apuntarla} accion="mapa-apuntar" />
        <${Boton} etiqueta=${m.no_es_mia} accion="mapa-no-es-esa" clase="boton-claro" />
      </div>
    </div>
  `;
}

/**
 * La pantalla entera.
 *
 * Propiedades:
 *
 *  - `textos`: `{ mapa, sigpac, acciones }`, tal y como los sirve `/api/interfaz`.
 *  - `centrado`: si se sabe por dónde empezar. Si no, no se pinta el mapa y se ofrece «estoy aquí».
 *  - `imagenes`: las dos direcciones de las imágenes (la foto y los linderos), con la caja que se está
 *    mirando, y el `viewBox` del dibujo (el tamaño de la imagen: los puntos del trozo vienen en esos
 *    píxeles, así que el componente no tiene que convertir nada).
 *  - `poligono`: los puntos del trozo ya convertidos a píxeles, o vacío.
 *  - `centro`: las coordenadas del centro, ya escritas.
 *  - `elegido`: lo que ha contestado el SIGPAC de ese punto, ya preparado, o nada.
 *  - `cargando` y `error`: si está buscando y lo que ha dicho el servidor.
 */
export function PantallaMapa({
  textos = {},
  centrado = false,
  imagenes = {},
  poligono = "",
  centro = "",
  elegido = null,
  cargando = false,
  error = "",
}) {
  const m = textos.mapa || {};
  const acciones = textos.acciones || {};

  return html`
    <h1>${frase(m.titulo)}</h1>
    <p className="pista">${frase(m.pista_mover)}</p>
    <${AvisoDeError} texto=${error} />
    ${
      centrado
        ? html`
            <${Vista} textos=${textos} imagenes=${imagenes} poligono=${poligono} cargando=${cargando} />
            <div className="barra-acciones">
              <${Boton} etiqueta=${m.acercar} accion="mapa-acercar" clase="boton-claro" />
              <${Boton} etiqueta=${m.alejar} accion="mapa-alejar" clase="boton-claro" />
              <${Boton} etiqueta=${m.estoy_aqui} accion="mapa-estoy-aqui" clase="boton-claro" />
            </div>
            <${Boton}
              etiqueta=${m.poner_en_el_centro}
              accion="mapa-preguntar"
              clase="boton-principal"
            />
            <p className="pista-campo">${frase(m.necesita_conexion)}</p>
            <p className="pista-campo">${frase(centro)}</p>
          `
        : html`<${Boton}
            etiqueta=${m.estoy_aqui}
            accion="mapa-estoy-aqui"
            clase="boton-principal"
          />`
    }
    ${elegido ? html`<${Elegido} textos=${textos} elegido=${elegido} />` : null}
    <div className="barra-acciones">
      <${Boton} etiqueta=${acciones.volver} accion="mapa-volver" clase="boton-claro" />
    </div>
  `;
}

/** El elemento de React de esta pantalla, ya con sus propiedades puestas. */
export function pantallaDeMapa(propiedades) {
  return html`<${PantallaMapa}
    textos=${propiedades.textos}
    centrado=${propiedades.centrado}
    imagenes=${propiedades.imagenes}
    poligono=${propiedades.poligono}
    centro=${propiedades.centro}
    elegido=${propiedades.elegido}
    cargando=${propiedades.cargando}
    error=${propiedades.error}
  />`;
}
