/*
 * decir_cultivo.js — «¿Qué hay sembrado en esta tierra?», escrita en React.
 *
 * POR QUÉ ESTA PANTALLA
 *
 * Es la vigesimotercera que se pasa a React y **cierra el camino que empezó el aviso de «falta decir
 * qué cultivo»**: cuando el cuaderno le dice al agricultor que a una parcela le falta el cultivo, este
 * formulario es donde lo contesta. Sin él, ese aviso era una frase sin salida, que es justo lo que
 * este proyecto no permite.
 *
 * LO QUE SE CONSERVA A PROPÓSITO
 *
 *  1. **Los `id` de los cinco campos** (`cultivo-especie`, `cultivo-variedad`, `cultivo-sistema`,
 *     `cultivo-desde`, `cultivo-hasta`): los lee `guardarCultivo()` en `app.js`. Si uno cambia, el
 *     agricultor escribe la especie, guarda, y no se guarda nada.
 *  2. **Lo que el agricultor ya había escrito no se borra.** Cuando la pantalla se repinta por un
 *     aviso del servidor, los valores que había tecleado vuelven puestos: perder lo tecleado es la
 *     forma más rápida de que alguien abandone un formulario. Por eso el componente recibe los valores
 *     ya resueltos (lo que acaba de escribir y, si no, lo que ya estaba declarado).
 *  3. **El sistema viene elegido** (el de la parcela o el secano), y las fechas son fechas: en el móvil
 *     se eligen en un calendario, no se teclean.
 *  4. Nada de `esc()` y ninguna frase escrita aquí: los textos llegan por propiedades.
 *  5. **Sirve para dos cosas desde la ronda 93**: para decir qué hay sembrado en una tierra que no lo
 *     tiene dicho y para **cambiar lo que ya dijiste** (`ya_dicho`). Cuando se está cambiando, la
 *     pantalla lo dice arriba (la etiqueta «ESTÁS CAMBIANDO LO QUE DIJISTE», pegada a la pregunta, que es
 *     lo que se lee primero) y el botón de guardar dice «GUARDAR LOS CAMBIOS» en vez de «GUARDAR»: decirle
 *     a quien está arreglando un dato que está apuntando uno nuevo es la forma de que acabe con dos.
 *
 * El componente es PURO: no llama a `fetch`, no lee `localStorage` y no toca el DOM.
 */

import { AvisoDeError, Boton, frase, html } from "../componentes.js";

/**
 * La pantalla entera.
 *
 * Propiedades:
 *
 *  - `textos`: `{ cultivos, acciones, corregir }`, tal y como los sirve `/api/interfaz`. `corregir` se
 *    usa solo cuando se está cambiando lo que ya estaba dicho: de ahí sale el rótulo del botón de guardar
 *    («GUARDAR LOS CAMBIOS»), que **no se escribe aquí** para que sea el mismo en toda la aplicación.
 *  - `parcela`: `{ id, detalle }` de la tierra de la que se está diciendo el cultivo. Su detalle
 *    (nombre y hectáreas) va en la cabecera: es lo que deja claro de qué tierra se está hablando.
 *  - `valores`: lo que trae cada campo ya resuelto (`especie`, `variedad`, `desde`, `hasta`) y el
 *    `sistema` elegido.
 *  - `sistemas`: las opciones del sistema (`[{valor, texto, elegido}]`), del catálogo del servidor.
 *  - `ya_dicho`: si esa tierra **ya tiene** dicho qué hay sembrado este año. Es lo que cambia la pantalla
 *    de «decir» a «cambiar»: la etiqueta de arriba, el rótulo del botón de guardar y el botón de quitar.
 *  - `error`: lo que ha dicho el servidor (o vacío).
 */
export function PantallaDecirCultivo({
  textos = {},
  parcela = {},
  valores = {},
  sistemas = [],
  ya_dicho = false,
  error = "",
}) {
  const c = textos.cultivos || {};
  const acciones = textos.acciones || {};
  const corregir = textos.corregir || {};

  return html`
    <h1>${frase(c.la_especie)}</h1>
    <p className="pista">${frase(parcela.detalle)}</p>
    ${
      // Lo que se está haciendo, pegado a la pregunta: el agricultor que llega aquí desde el botón
      // CAMBIARLO tiene que ver de un vistazo que está arreglando lo que ya dijo, y no diciéndolo otra vez.
      ya_dicho
        ? html`<span className="etiqueta-estado etiqueta-estado-mirar">${frase(c.corrigiendo)}</span>`
        : null
    }
    <${AvisoDeError} texto=${error} />
    ${
      // **Lo que hay que hacer y la tranquilidad de que nada es obligatorio salvo el cultivo** (diseño de
      // Stitch de esta pantalla, ronda 90). Sin esto, un formulario de cinco casillas parece un examen, y el
      // agricultor que no sabe la variedad o la fecha exacta se queda mirándolo.
      c.rellenar_aviso
        ? html`
            <p className="tarjeta-aviso">
              <span className="tarjeta-aviso-icono" aria-hidden="true">!</span>
              ${frase(c.rellenar_aviso)}
            </p>
          `
        : null
    }
    ${
      // Las preguntas, **numeradas** (diseño de Stitch): son cinco y, sin números, no se sabe cuánto queda.
      // El número lo pone el CSS con un contador, así que cada rótulo sigue siendo el del servidor.
      html`
        <ol className="campos-numerados">
          <li>
            <div className="campo">
              <label htmlFor="cultivo-especie">${frase(c.la_especie)}</label>
              ${
                c.imprescindible
                  ? html`<span className="etiqueta-estado etiqueta-estado-obligatorio"
                      >${frase(c.imprescindible)}</span
                    >`
                  : null
              }
              <p className="pista-campo">${frase(c.la_especie_pista)}</p>
              <input
                id="cultivo-especie"
                type="text"
                autoComplete="off"
                defaultValue=${frase(valores.especie)}
              />
            </div>
          </li>
          <li>
            <div className="campo">
              <label htmlFor="cultivo-variedad">${frase(c.variedad)}</label>
              <p className="pista-campo">${frase(c.variedad_pista)}</p>
              <input
                id="cultivo-variedad"
                type="text"
                autoComplete="off"
                defaultValue=${frase(valores.variedad)}
              />
            </div>
          </li>
          <li>
            <div className="campo">
              <label htmlFor="cultivo-sistema">${frase(c.sistema)}</label>
              <select id="cultivo-sistema">
                ${sistemas.map(
                  (opcion) => html`
                    <option value=${opcion.valor} selected=${opcion.elegido} key=${opcion.valor}>
                      ${frase(opcion.texto)}
                    </option>
                  `,
                )}
              </select>
            </div>
          </li>
          <li>
            <div className="campo">
              <label htmlFor="cultivo-desde">${frase(c.desde_cuando)}</label>
              <p className="pista-campo">${frase(c.fechas_pista)}</p>
              <input id="cultivo-desde" type="date" defaultValue=${frase(valores.desde)} />
            </div>
          </li>
          <li>
            <div className="campo">
              <label htmlFor="cultivo-hasta">${frase(c.hasta_cuando)}</label>
              <input id="cultivo-hasta" type="date" defaultValue=${frase(valores.hasta)} />
            </div>
          </li>
        </ol>
      `
    }
    <div className="barra-acciones">
      <${Boton}
        etiqueta=${ya_dicho ? corregir.boton_guardar : acciones.guardar}
        accion="cultivo-guardar"
        datos=${{ id: parcela.id }}
      />
      <${Boton} etiqueta=${acciones.volver} accion="cultivo-ver-todos" clase="boton-claro" />
    </div>
    ${
      // **Quitar lo que dijiste, que no es lo mismo que cambiarlo** (diseño de Stitch de la ronda 91: el
      // botón que quita algo del cuaderno no puede ser el que más apetezca pulsar). Va **fuera de la barra
      // y debajo**, con su explicación, para que no se pulse por ir a guardar. Solo sale si esa tierra ya
      // tiene dicho qué hay sembrado este año: en una a la que le falta decirlo no hay nada que quitar.
      ya_dicho
        ? html`
            <${Boton}
              etiqueta=${c.quitar}
              accion="cultivo-quitar"
              datos=${{ id: parcela.id }}
              clase="boton-peligro"
            />
            <p className="pista-campo">${frase(c.quitar_pista)}</p>
          `
        : null
    }
  `;
}

/** El elemento de React de esta pantalla, ya con sus propiedades puestas. */
export function pantallaDeDecirCultivo(propiedades) {
  return html`<${PantallaDecirCultivo}
    textos=${propiedades.textos}
    parcela=${propiedades.parcela}
    valores=${propiedades.valores}
    sistemas=${propiedades.sistemas}
    ya_dicho=${propiedades.ya_dicho}
    error=${propiedades.error}
  />`;
}
