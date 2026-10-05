/*
 * revision_de_contactos.js — Los nombres que ya están escritos, y qué se propone con ellos (T11).
 *
 * **ESTA ES LA MITAD PELIGROSA DEL TICKET, Y POR ESO ESTÁ SOLA EN SU FICHERO.**
 *
 * En el cuaderno hay nombres escritos a mano desde el primer día: el proveedor de cada factura, el de
 * cada albarán, el comprador de cada venta, el laboratorio de cada análisis. Lo que aquí se enseña es
 * **una propuesta**: qué fichas se pueden apuntar a partir de ellos. Y la regla que gobierna la pantalla
 * entera es una:
 *
 *   > **Si no se puede asegurar que dos nombres son la misma persona, no se juntan. Se dice, y se
 *   > enseña, y el que decide es el agricultor.**
 *
 * De ahí salen las dos listas de esta pantalla, que son lo que la hace distinta de cualquier «limpiar
 * duplicados» de un programa de gestión:
 *
 *  1. **«Se pueden apuntar»**: nombres escritos **igual** en todas partes, o con el **mismo NIF**, que
 *     es una prueba y no una sospecha. Cada uno lleva su botón.
 *  2. **«Estos los tienes que mirar tú»**: los que **se parecen** (una tilde de menos, un «S.L.» de
 *     más, una letra cambiada) y los que tienen **el mismo nombre con dos NIF** —o sea, dos personas
 *     distintas que se llaman igual—. **Aquí no hay ningún botón de apuntar**, y no es un olvido: es la
 *     promesa del ticket. Un «APUNTAR» donde no se puede asegurar sería la forma de fusionar a un
 *     proveedor con su hermano de un toque, y eso no se puede deshacer.
 *
 * Y dos cosas más que se dicen en pantalla porque son verdad y no se ven: que **no se toca ni una letra
 * de sus papeles** (el nombre sigue escrito donde estaba y el enlace solo dice de quién es) y que
 * **todavía no se ha apuntado nada** hasta que él pulse el botón.
 *
 * El servidor se niega a apuntar una propuesta insegura **aunque se lo pidan** (contesta 409): lo que
 * se ve aquí es la explicación, no la única defensa.
 */

import { AvisoDeError, Boton, BotonSencillo, frase, html } from "../componentes.js";

/** Un nombre escrito, con de dónde es y cómo está escrito. Se usa en los dos bloques. */
function UnEscrito({ escrito }) {
  return html`
    <li>
      <strong>${frase(escrito.texto)}</strong>
      <p className="pista-campo">${frase(escrito.rotulo)}</p>
      ${escrito.aviso ? html`<p className="aviso">${frase(escrito.aviso)}</p>` : null}
    </li>
  `;
}

/** Una propuesta que **se puede apuntar**: su nombre, sus papeles y sus nombres escritos. */
function UnaPropuestaSegura({ propuesta, textos, enviando }) {
  const c = textos.contactos || {};
  return html`
    <li>
      <strong>${frase(propuesta.nombre)}</strong>
      <p className="pista-campo">${frase(propuesta.motivo_texto)}</p>
      ${propuesta.papeles_texto ? html`<p className="pista-campo">${frase(propuesta.papeles_texto)}</p>` : null}
      <p className="pista-campo">${frase(c.revision_nombres_escritos)}</p>
      <ul className="lista">
        ${propuesta.escritos.map(
          (escrito) => html`<${UnEscrito} key=${escrito.claveTarjeta} escrito=${escrito} />`,
        )}
      </ul>
      <button
        type="button"
        className="boton boton-principal"
        data-accion="contacto-migracion-apuntar"
        data-clave=${propuesta.clave}
        disabled=${enviando ? true : undefined}
      >
        ${frase(c.revision_apuntar)}
      </button>
    </li>
  `;
}

/**
 * Una propuesta que **no se puede apuntar**.
 *
 * **Sin botón de apuntar, y a propósito.** Lo que se enseña es el motivo, con los dos nombres delante, y
 * la salida que sí existe: apuntar una ficha a mano y enlazarle los nombres que el agricultor sepa que
 * son suyos. Es el mismo camino que el mensaje del servidor (`C3_eso_no_se_puede_juntar_solo`) dice con
 * palabras, y por eso el botón lleva a la ficha nueva y no a ninguna parte más.
 */
function UnaPropuestaParaMirar({ propuesta, textos }) {
  const c = textos.contactos || {};
  return html`
    <li>
      <strong>${frase(propuesta.nombre)}</strong>
      <div className="aviso">
        <p>${frase(propuesta.motivo_texto)}</p>
        <ul className="lista">
          ${propuesta.escritos.map(
            (escrito) => html`<${UnEscrito} key=${escrito.claveTarjeta} escrito=${escrito} />`,
          )}
        </ul>
        ${propuesta.nifs_texto ? html`<p>${frase(propuesta.nifs_texto)}</p>` : null}
        <${Boton} etiqueta=${c.anadir} accion="contacto-nuevo" clase="boton-principal" />
      </div>
    </li>
  `;
}

/**
 * La pantalla de la revisión.
 *
 * Propiedades:
 *
 *  - `resumen`: los números del servidor (cuántas fichas se proponen, cuántos nombres escritos, cuántos
 *    se parecen y cuántos son homónimos). **No se cuentan aquí.**
 *  - `seguras` y `paraMirar`: las dos listas, ya separadas por `app.js` a partir de lo que contestó el
 *    servidor. Separarlas allí y no aquí es lo que deja comprobar en una prueba que **la lista de las
 *    que se pueden apuntar no lleva ni una dudosa**.
 *  - `sePuedeDeshacer`: si hay fichas que apuntó la migración y todavía se pueden quitar.
 *  - `enviando`: hay una petición en el aire. **Los botones de apuntar se apagan mientras tanto**, y
 *    eso no es cosmética: sin esto, un doble toque (con guantes, con el móvil lento) manda la misma
 *    confirmación dos veces. El servidor la contesta sin duplicar nada —y ahora, además, devolviendo
 *    su resultado en vez de decir que la lista ha cambiado—, pero un botón que se puede pulsar dos
 *    veces para lo mismo invita al agricultor a dudar de si lo ha apuntado.
 */
export function PantallaDeLaRevisionDeLosNombres({
  textos = {},
  seguras = [],
  paraMirar = [],
  resumenTexto = "",
  hayYaEnlazados = false,
  yaEnlazadosTexto = "",
  sePuedeDeshacer = false,
  enviando = false,
  apuntado = "",
  deshecho = "",
  aviso = "",
  error = "",
  cargando = false,
}) {
  const c = textos.contactos || {};
  const nada = seguras.length === 0 && paraMirar.length === 0;
  return html`
    <h1>${frase(c.revision_titulo)}</h1>
    <p className="pista">${frase(c.revision_explica)}</p>
    <${AvisoDeError} texto=${error} />
    ${apuntado ? html`<div className="aviso"><strong>${frase(apuntado)}</strong></div>` : null}
    ${deshecho ? html`<div className="aviso"><strong>${frase(deshecho)}</strong></div>` : null}
    ${aviso ? html`<div className="aviso"><strong>${frase(aviso)}</strong></div>` : null}
    ${cargando ? html`<p className="pista">${frase(c.buscando)}</p>` : null}

    <h2>${frase(c.revision_que_se_hace)}</h2>
    <p className="pista">${frase(c.revision_que_se_hace_explica)}</p>
    ${resumenTexto ? html`<p className="pista">${frase(resumenTexto)}</p>` : null}
    ${
      hayYaEnlazados
        ? html`<p className="pista-campo">${frase(yaEnlazadosTexto)}</p>`
        : null
    }

    ${nada ? html`<p className="aviso">${frase(c.revision_nada)}</p>` : null}

    ${
      seguras.length
        ? html`
            <h2>${frase(c.revision_seguras)}</h2>
            <p className="pista-campo">${frase(c.revision_seguras_pista)}</p>
            <ul className="lista">
              ${seguras.map(
                (propuesta) => html`<${UnaPropuestaSegura}
                  key=${propuesta.clave}
                  propuesta=${propuesta}
                  textos=${textos}
                  enviando=${enviando}
                />`,
              )}
            </ul>
            <div className="barra-acciones">
              <button
                type="button"
                className="boton boton-principal"
                data-accion="contacto-migracion-todas"
                disabled=${enviando ? true : undefined}
              >
                ${frase(c.revision_apuntar_todas)}
              </button>
            </div>
          `
        : null
    }

    ${
      paraMirar.length
        ? html`
            <h2>${frase(c.revision_mirar)}</h2>
            <p className="pista-campo">${frase(c.revision_mirar_pista)}</p>
            <ul className="lista">
              ${paraMirar.map(
                (propuesta) => html`<${UnaPropuestaParaMirar}
                  key=${propuesta.clave}
                  propuesta=${propuesta}
                  textos=${textos}
                />`,
              )}
            </ul>
          `
        : null
    }

    <div className="barra-acciones">
      <${Boton} etiqueta=${c.revision_volver} accion="contactos-ver" clase="boton-claro" />
      ${
        sePuedeDeshacer
          ? html`<button
              type="button"
              className="boton boton-claro"
              data-accion="contacto-migracion-deshacer"
            >
              ${frase(c.revision_deshacer)}
            </button>`
          : null
      }
      <${BotonSencillo} etiqueta=${c.volver_al_inicio} accion="ir-inicio" clase="" />
    </div>
    ${
      sePuedeDeshacer
        ? html`<p className="pista-campo">${frase(c.revision_deshacer_pista)}</p>`
        : null
    }
  `;
}

/** El elemento de React de esta pantalla, ya con sus propiedades puestas. */
export function pantallaDeLaRevisionDeLosNombres(propiedades) {
  return html`
    <${PantallaDeLaRevisionDeLosNombres}
      textos=${propiedades.textos}
      seguras=${propiedades.seguras}
      paraMirar=${propiedades.paraMirar}
      resumenTexto=${propiedades.resumenTexto}
      hayYaEnlazados=${propiedades.hayYaEnlazados}
      yaEnlazadosTexto=${propiedades.yaEnlazadosTexto}
      sePuedeDeshacer=${propiedades.sePuedeDeshacer}
      enviando=${propiedades.enviando}
      apuntado=${propiedades.apuntado}
      deshecho=${propiedades.deshecho}
      aviso=${propiedades.aviso}
      error=${propiedades.error}
      cargando=${propiedades.cargando}
    />
  `;
}
