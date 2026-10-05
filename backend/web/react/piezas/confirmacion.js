/*
 * confirmacion.js — La pantalla que sale después de guardar algo, y las que ofrecen un camino.
 *
 * POR QUÉ ES UNA PIEZA Y NO CINCO PANTALLAS
 *
 * Hay **cinco pantallas de confirmación** (una venta guardada, un análisis guardado, un plan de abono
 * guardado, las medidas declaradas y la ficha de un maestro guardada) y las cinco son la misma cosa: un
 * título, una explicación que dice **para qué sirve** lo que se acaba de guardar, y dos botones (ir a
 * verlo o volver al inicio). Además hay dos pantallas que **ofrecen un camino** (traer la tierra del
 * SIGPAC o apuntarla a mano; el listado de papeles en texto) y son la misma forma sin la ayuda.
 *
 * Estaban escritas a mano en `app.js`, cada una con su cadena de HTML, y por eso cada una se acordaba de
 * cosas distintas. Aquí está **una vez**.
 *
 * Y una cosa que se conserva a propósito: **la ayuda dice para qué sirve lo que se ha guardado**. No es
 * un adorno —es lo que hace que el agricultor entienda que apuntar esto le sirve para algo—, y es el
 * texto que el servidor manda en dos trozos (`se_usa` y el suyo).
 *
 * El componente es PURO: no llama a `fetch` y no toca el DOM.
 */

import { Boton, BotonSencillo, AvisoDeError, frase, html } from "../componentes.js";

/**
 * Un bloque de ayuda: el título en negrita y la explicación debajo.
 *
 * Es el mismo bloque (`.ayuda-campo`) que usa el campo del asistente, y va con los dos textos del
 * servidor: el genérico («Dónde se usa:») y el de esa pantalla.
 */
function Ayuda({ ayuda }) {
  if (!ayuda) return null;
  return html`
    <div className="ayuda-campo">
      <p><strong>${frase(ayuda.titulo)}</strong></p>
      <p>${frase(ayuda.texto)}</p>
    </div>
  `;
}

/** Una lista de apuntes: cada uno con su cabecera y su detalle debajo (una parcela y su referencia). */
function Lista({ lista }) {
  return html`
    ${lista.titulo ? html`<h2>${frase(lista.titulo)}</h2>` : null}
    ${lista.pista ? html`<p className="pista-campo">${frase(lista.pista)}</p>` : null}
    <ul className="lista">
      ${(lista.elementos || []).map(
        (elemento, indice) => html`
          <li key=${indice}>
            <div className="apunte-cabecera"><span>${frase(elemento.cabecera)}</span></div>
            <div className="apunte-detalle">${frase(elemento.detalle)}</div>
          </li>
        `,
      )}
    </ul>
  `;
}

/**
 * El bloque para subir un fichero ahora mismo, con su pregunta.
 *
 * Lo usa la confirmación de un análisis: el boletín del laboratorio se puede subir justo después de
 * apuntarlo, que es cuando el agricultor lo tiene en la mano. El `id` del campo es el de siempre
 * (`informe-<id>`) porque `app.js` lo lee por ahí.
 */
function Archivo({ archivo }) {
  return html`
    <h2>${frase(archivo.titulo)}</h2>
    <p className="pista-campo">${frase(archivo.pista)}</p>
    <input type="file" id=${archivo.id} accept="application/pdf,image/*" />
  `;
}

/**
 * La pantalla entera.
 *
 * Propiedades, todas opcionales menos el título:
 *
 *  - `titulo`: lo que se dice arriba del todo (un `<h1>`).
 *  - `pregunta`: la línea de arriba **cuando lo que se pregunta es una pregunta** («¿Qué has hecho?»),
 *    con el mismo estilo grande que las preguntas del asistente. Es distinto de `pista`, que es para las
 *    pantallas que **explican** algo (ahí va pequeña y en gris). Una pantalla lleva una de las dos: las
 *    dos juntas serían un titular y una explicación, y eso ya es un título con su pista.
 *  - `pista`: la frase de debajo del título («se ha guardado»).
 *  - `ayuda`: `{ titulo, texto }` → el bloque que explica **para qué sirve** lo que se ha guardado.
 *  - `avisos`: los avisos que hagan falta, cada uno `{ texto, error }`. Con `error: true` sale en rojo y
 *    con `role="alert"`, que es lo que hace que un lector de pantalla lo lea en voz alta.
 *  - `contenido`: lo que va en medio, **ya montado** (una lista de números, una tabla…). Se compone en
 *    `app.js` con las piezas que ya hay, en vez de inventar aquí una forma para cada pantalla.
 *  - `listas`: listas de apuntes (`[{ titulo, pista, elementos: [{cabecera, detalle}] }]`).
 *  - `archivo`: `{ titulo, pista, id }` → el bloque para subir un fichero (el boletín de un análisis).
 *  - `acciones`: los botones de abajo, con la misma forma que los demás (`etiqueta`, `icono`, `accion`,
 *    `datos`, `clase`). Si un botón lleva `sencillo: true` se pinta **sin icono y sin flecha**, que es
 *    como estaban los de estas pantallas.
 */
export function Confirmacion({
  titulo = "",
  pregunta = "",
  pista = "",
  ayuda = null,
  avisos = [],
  contenido = null,
  listas = [],
  archivo = null,
  acciones = [],
}) {
  return html`
    ${titulo ? html`<h1>${frase(titulo)}</h1>` : null}
    ${pregunta ? html`<p className="pregunta">${frase(pregunta)}</p>` : null}
    ${pista ? html`<p className="pista">${frase(pista)}</p>` : null}
    <${Ayuda} ayuda=${ayuda} />
    ${avisos.map(
      (aviso, indice) =>
        aviso.error
          ? html`<${AvisoDeError} key=${indice} texto=${aviso.texto} />`
          : html`<div className="aviso" key=${indice}><p>${frase(aviso.texto)}</p></div>`,
    )}
    ${contenido}
    ${listas.map((lista, indice) => html`<${Lista} key=${indice} lista=${lista} />`)}
    ${archivo ? html`<${Archivo} archivo=${archivo} />` : null}
    <div className="barra-acciones">
      ${acciones.map(
        (accion, indice) =>
          accion.sencillo
            ? html`
                <${BotonSencillo}
                  key=${indice}
                  etiqueta=${accion.etiqueta}
                  accion=${accion.accion}
                  datos=${accion.datos}
                  clase=${accion.clase || "boton-claro"}
                />
              `
            : html`
                <${Boton}
                  key=${indice}
                  etiqueta=${accion.etiqueta}
                  icono=${accion.icono}
                  accion=${accion.accion}
                  datos=${accion.datos}
                  clase=${accion.clase || "boton-claro"}
                />
              `,
      )}
    </div>
  `;
}

/** El elemento de React de esta pantalla, ya con sus propiedades puestas. */
export function confirmacion(propiedades) {
  return html`
    <${Confirmacion}
      titulo=${propiedades.titulo}
      pregunta=${propiedades.pregunta}
      pista=${propiedades.pista}
      ayuda=${propiedades.ayuda}
      avisos=${propiedades.avisos}
      contenido=${propiedades.contenido}
      listas=${propiedades.listas}
      archivo=${propiedades.archivo}
      acciones=${propiedades.acciones}
    />
  `;
}
