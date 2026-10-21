/*
 * analiticas.js — «Los análisis», escritos en React.
 *
 * POR QUÉ ESTA PANTALLA
 *
 * Es la duodécima que se pasa a React, y es de las que se miran de verdad: el boletín del
 * laboratorio es el papel que sostiene el plan de abono cuando alguien lo pregunta, y aquí es
 * donde el agricultor lo encuentra **con sus números y con el papel subido**.
 *
 * **Lo que NO hace este componente:** no formatea ni decide nada. Cada análisis le llega ya
 * preparado por `app.js`: el título («Análisis de La tierra de El Prado»), las filas de la ficha
 * (de dónde salió, cuándo se cogió, quién lo hizo, número de boletín), sus números y la línea del
 * informe. Las fechas y los textos con huecos se rellenan allí, porque es donde están los textos
 * del servidor y donde se escribe en el idioma de aquí.
 *
 * LO QUE SE CONSERVA A PROPÓSITO
 *
 *  1. Los `data-accion` y los `data-id` salen iguales que en la interfaz vieja: los clics los
 *     atiende un solo manejador delegado en `document` (`app.js`), y el informe se sube leyendo
 *     el fichero del `<input type="file">` **por su `id`** (`informe-<id>`). Ese `id` se conserva
 *     tal cual: si cambia, el botón de subir el boletín deja de encontrar el papel.
 *  2. Las mismas `className` que ya existen en `estilos.css` (`.lista`, `.resumen-dato`,
 *     `.pista-campo`, `.barra-acciones`, `.oculto`). Ni un `style`.
 *  3. Nada de `esc()`: React escapa solo.
 *  4. Ninguna frase escrita aquí: todas llegan por propiedades, del servidor.
 *
 * El componente es PURO: no llama a `fetch`, no lee `localStorage` y no toca el DOM.
 */

import { Boton, frase, html } from "../componentes.js";
import { AccionesDeUnaFicha } from "../piezas/acciones_de_una_ficha.js";

/**
 * La ficha de un análisis: qué es, de dónde salió, cuándo, qué números trae y su papel.
 *
 * El orden es el de la pantalla vieja y no se toca: primero la cabecera con el nombre, luego la
 * ficha con lo que se identifica el boletín, luego sus números y al final el papel.
 *
 * Tres cosas del diseño de Stitch de esta pantalla (ronda 90, `docs/stitch/rediseno/analiticas.png`):
 *
 *  1. **La edad del boletín, en su etiqueta** («De este año (2026)», «Hace 2 años (2024)»), al lado del
 *     nombre: un boletín viejo no vale lo mismo que uno de este año, y eso se tiene que ver sin leer la
 *     fecha.
 *  2. **Los números del boletín en su bloque y en dos columnas**, con el rótulo encima y el número
 *     grande: son ocho o nueve números y en una lista de renglones había que leerlos uno a uno.
 *  3. **El papel, con lo que hay que hacer al lado.** Cuando no hay papel subido, se dice **en su franja
 *     de aviso** y el botón de subirlo es el de color de acción: es lo único que falta en ese análisis.
 */
function Ficha({ analisis, textos }) {
  const a = textos.analitica || {};

  return html`
    <div className="apunte-cabecera">
      <h2>${frase(analisis.titulo)}</h2>
      ${
        analisis.estado && analisis.estado.texto
          ? html`<span className=${`etiqueta-estado etiqueta-estado-${analisis.estado.tipo || "bien"}`}
              >${frase(analisis.estado.texto)}</span
            >`
          : null
      }
    </div>
    <dl>
      ${analisis.filas.map(
        ([etiqueta, valor], indice) => html`
          <div className="resumen-dato" key=${indice}>
            <dt>${frase(etiqueta)}</dt>
            <dd>${frase(valor)}</dd>
          </div>
        `,
      )}
    </dl>
    ${
      // Un boletín puede estar guardado sin los números copiados («solo está guardado el
      // boletín»). Se dice, en vez de enseñar una lista vacía que parece un fallo del programa.
      analisis.numeros.length === 0
        ? html`
            <p className="tarjeta-aviso">
              <span className="tarjeta-aviso-icono" aria-hidden="true">!</span>
              ${frase(a.sin_numeros)}
            </p>
          `
        : html`
            <p className="pista-campo">${frase(a.numeros_titulo)}</p>
            <ul className="numeros">
              ${analisis.numeros.map(
                ([etiqueta, texto], indice) => html`
                  <li key=${indice}>
                    <span className="numero-etiqueta">${frase(etiqueta)}</span>
                    <span className="dato-grande">${frase(texto)}</span>
                  </li>
                `,
              )}
            </ul>
          `
    }
    ${
      // El papel del laboratorio. Sin papel, la frase va en su franja de aviso y **el botón de subirlo es
      // el de color de acción**: es lo único que le falta a este análisis. Con papel, se dice que ya está
      // y se ofrecen los dos caminos (volver a subirlo, si la foto salió mal, y descargarlo).
      analisis.tiene_informe
        ? html`<p className="pista-campo">${frase(analisis.linea_informe)}</p>`
        : html`
            <p className="tarjeta-aviso">
              <span className="tarjeta-aviso-icono" aria-hidden="true">!</span>
              ${frase(analisis.linea_informe)}
            </p>
          `
    }
    <div className="barra-acciones">
      <${Boton}
        etiqueta=${a.subir_informe}
        accion="analisis-informe-subir"
        datos=${{ id: analisis.id }}
        clase=${analisis.tiene_informe ? "boton-claro" : "boton-principal"}
      />
      ${
        // El botón de descargar solo sale si de verdad hay un papel guardado: un botón que no
        // lleva a ninguna parte es peor que no tenerlo.
        analisis.tiene_informe
          ? html`<${Boton}
              etiqueta=${a.descargar_informe}
              accion="analisis-informe-bajar"
              datos=${{ id: analisis.id }}
              clase="boton-claro"
            />`
          : null
      }
    </div>
    <input
      type="file"
      id=${`informe-${analisis.id}`}
      accept="application/pdf,image/*"
      className="oculto"
    />
    ${
      // **CORREGIR y BORRAR el análisis** (ronda 93), al final de su ficha. Un número copiado mal del
      // boletín se arregla aquí —y ese número es el que después lee el plan de abono—, y un análisis que
      // se apuntó por error se puede quitar. Si algún plan se apoya en él, el servidor no deja borrarlo
      // y lo dice: ese plan se quedaría sin saber de dónde salieron sus números.
      html`<${AccionesDeUnaFicha} acciones=${analisis.acciones} />`
    }
  `;
}

/**
 * La pantalla entera.
 *
 * Propiedades:
 *
 *  - `textos`: `{ analitica, acciones }`, tal y como los sirve `/api/interfaz`.
 *  - `analisis`: los análisis del año, ya preparados por `app.js` (título, filas, números, nota y
 *    la línea del informe).
 */
export function PantallaAnaliticas({
  textos = {},
  analisis = [],
  // ***Y si la carga fallo*** (21/10/2026, D03): *«no hay analisis» es una afirmacion sobre la finca; «no se pudo
  // cargar», sobre la red.*
  noSePudoCargar = false,
  noSePudoCargarTexto = "",
}) {
  const a = textos.analitica || {};
  const acciones = textos.acciones || {};

  return html`
    <h1>${frase(a.titulo)}</h1>
    <p className="pista">${frase(a.explica)}</p>
    ${
      analisis.length === 0
        ? noSePudoCargar
          ? html`<div className="aviso aviso-error">${frase(noSePudoCargarTexto)}</div>`
          : html`<div className="aviso">${frase(a.sin_analisis)}</div>`
        : analisis.map(
            (uno, indice) => html`<${Ficha} key=${indice} analisis=${uno} textos=${textos} />`,
          )
    }
    <p className="pista-campo">${frase(a.sin_oficial)}</p>
    <div className="barra-acciones">
      <${Boton} etiqueta=${a.anadir} accion="analisis-nuevo" />
      <${Boton}
        etiqueta=${acciones.volver}
        accion="inicio"
        datos=${{ ir: "mi_cuaderno" }}
        clase="boton-claro"
      />
    </div>
  `;
}

/** El elemento de React de esta pantalla, ya con sus propiedades puestas. */
export function pantallaDeAnaliticas(propiedades) {
  return html`<${PantallaAnaliticas}
    textos=${propiedades.textos}
    analisis=${propiedades.analisis}
    noSePudoCargar=${propiedades.noSePudoCargar}
    noSePudoCargarTexto=${propiedades.noSePudoCargarTexto}
  />`;
}
