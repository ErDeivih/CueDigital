/**
 * **Lo que hay que hacer**: la lista de próximas acciones, cruzando fichas (Entrega 3, 13/10/2026).
 *
 * POR QUÉ UNA PANTALLA Y NO SOLO LA FICHA. En la ficha del contacto se ve lo que hay **con ese contacto**, y eso
 * está bien para cuando se está hablando con él. Pero la pregunta del agricultor por la mañana es otra: **«¿qué
 * tengo que hacer hoy?»** — y esa cruza fichas, se filtra por responsable y por vencimiento, y tiene que poder
 * mirarse sin entrar en la ficha de nadie.
 *
 * **Los filtros van en la dirección** (igual que en las tierras y en la búsqueda): así la lista **se puede enlazar y
 * se puede recargar**, y volver a ella deja al agricultor donde estaba. Es lo que pide el encargo al hablar de
 * «lista con filtros» y lo que hará falta cuando se revise el recorrido entero.
 *
 * **Lo que la pantalla NO decide**: qué es una tarea vencida. Eso lo dice el servidor (`vencida` viene calculado) y
 * la pantalla solo lo pinta. Es a propósito: las comparaciones de fechas en dos sitios acaban diciendo cosas
 * distintas, y el agricultor se fía de lo que ve.
 */

import { BotonSencillo, frase, html } from "../componentes.js";

/** El enlace a la ficha de un contacto, que es donde se ve todo lo demás de esa persona. */
const suFicha = (contactoId) => `#/contactos/${contactoId}`;

export function PantallaDeLasTareas({
  textos = {},
  tareas = [],
  filtros = {},
  contactos = {},
  cargando = false,
  error = "",
  aviso = "",
}) {
  const t = textos.tareas || {};
  const acciones = textos.acciones || {};
  const vencimiento = filtros.vencimiento || "";
  return html`
    <h1>${frase(t.titulo)}</h1>
    <p className="pista">${frase(t.pista)}</p>
    ${error ? html`<div className="aviso aviso-de-error">${frase(error)}</div>` : null}
    ${aviso ? html`<div className="aviso">${frase(aviso)}</div>` : null}

    ${
      // **Las dos vistas que se piden**: lo de hoy y lo vencido. Son dos filtros, no dos pantallas distintas —lo que
      // cambia es el trozo de la dirección—, y por eso se marcan como elegidas cuando lo están.
      html`
        <div className="barra-de-filtros">
          <${BotonSencillo}
            etiqueta=${t.todas}
            accion="tareas-ver"
            datos=${{ vencimiento: "" }}
            clase=${vencimiento ? "boton-claro" : ""}
          />
          <${BotonSencillo}
            etiqueta=${t.de_hoy}
            accion="tareas-ver"
            datos=${{ vencimiento: "hoy" }}
            clase=${vencimiento === "hoy" ? "" : "boton-claro"}
          />
          <${BotonSencillo}
            etiqueta=${t.vencidas}
            accion="tareas-ver"
            datos=${{ vencimiento: "vencidas" }}
            clase=${vencimiento === "vencidas" ? "" : "boton-claro"}
          />
          <${BotonSencillo}
            etiqueta=${t.sin_fecha}
            accion="tareas-ver"
            datos=${{ vencimiento: "sin_fecha" }}
            clase=${vencimiento === "sin_fecha" ? "" : "boton-claro"}
          />
        </div>
      `
    }

    ${
      cargando
        ? html`<p className="pista">${frase(t.cargando)}</p>`
        : tareas.length
          ? html`
              <table className="tabla" data-tabla="tareas">
                <thead>
                  <tr>
                    <th>${frase(t.que)}</th>
                    <th>${frase(t.cuando)}</th>
                    <th>${frase(t.quien)}</th>
                    <th>${frase(t.con_quien)}</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  ${tareas.map(
                    (tarea) => html`
                      <tr key=${String(tarea.id)} className=${tarea.vencida ? "fila-vencida" : ""}>
                        <td>
                          ${frase(tarea.titulo)}
                          ${tarea.vencida ? html` <strong>${frase(t.vencida)}</strong>` : null}
                        </td>
                        <td>${frase(tarea.fecha_texto)}</td>
                        <td>${frase(tarea.responsable || "")}</td>
                        <td>
                          ${
                            // **El enlace al contacto**, que es lo que pide el encargo: desde la lista se va a la
                            // ficha, y desde la ficha se vuelve (tiene dirección desde la Entrega 1).
                            contactos[tarea.contacto_id]
                              ? html`<a href=${suFicha(tarea.contacto_id)}>${frase(contactos[tarea.contacto_id])}</a>`
                              : html`<a href=${suFicha(tarea.contacto_id)}>${frase(t.ver_la_ficha)}</a>`
                          }
                        </td>
                        <td>
                          ${
                            tarea.estado === "pendiente"
                              ? html`
                                  <${BotonSencillo}
                                    etiqueta=${t.hecha}
                                    accion="tarea-completar"
                                    datos=${{ tarea: tarea.id, id: tarea.contacto_id }}
                                  />
                                  <${BotonSencillo}
                                    etiqueta=${t.cancelar}
                                    accion="tarea-cancelar"
                                    datos=${{ tarea: tarea.id, id: tarea.contacto_id }}
                                  />
                                `
                              : html`<span className="pista">${frase(tarea.estado === "hecha" ? t.ya_hecha : t.ya_cancelada)}</span>`
                          }
                        </td>
                      </tr>
                    `,
                  )}
                </tbody>
              </table>
            `
          : html`<p className="pista">${frase(t.no_hay_ninguna)}</p>`
    }

    <div className="barra-acciones">
      <${BotonSencillo} etiqueta=${acciones.volver} accion="contactos-ver" />
    </div>
  `;
}

/**
 * **El envoltorio de esta pantalla.** Reenvía **todo** lo que la pantalla necesita, y eso no es adorno: una propiedad
 * que no se reenvíe aquí **no llega nunca a la pantalla** por mucho que `app.js` la mande. Es el fallo que tuvo el
 * saldo (D1) y el que tuvo la tabla, y por eso esta lista se escribe entera: si mañana se añade una propiedad, tiene
 * que añadirse **también aquí**.
 */
export function pantallaDeLasTareas(propiedades) {
  return html`<${PantallaDeLasTareas}
    textos=${propiedades.textos}
    tareas=${propiedades.tareas}
    filtros=${propiedades.filtros}
    contactos=${propiedades.contactos}
    cargando=${propiedades.cargando}
    error=${propiedades.error}
    aviso=${propiedades.aviso}
  />`;
}
