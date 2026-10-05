/*
 * ayuda.js — «No sé qué pulsar», la pantalla de ayuda, escrita en React.
 *
 * POR QUÉ ESTA PANTALLA
 *
 * Es la séptima que se pasa a React y **la más importante para quien no sabe de informática**: es a
 * donde va el agricultor cuando no entiende algo. Tiene seis partes, y cada una contesta a una
 * pregunta distinta:
 *
 *  1. **Lo que dice la ley** sobre llevar el cuaderno, y qué manda la norma que se entregue y qué no.
 *  2. **Los porqués**: para qué sirve apuntar cada cosa, en cristiano. Se enseñan **todos** los que
 *     sirva el servidor, en su orden, sin escribir aquí ni uno.
 *  3. **Las fichas de cada campo**: qué es, por qué se pide.
 *  4. **Las reglas del abono en zonas de nitratos**, con su cifra, y qué hace el programa con cada
 *     una (avisar, consultarla o no poder).
 *  5. **Los aportes máximos de nitrógeno y los periodos prohibidos**, en dos bloques que se abren al
 *     pulsarlos: son tablas largas y no tienen que tapar lo demás.
 *  6. **Lo que todavía falta por confirmar**, dicho tal cual.
 *
 * **Lo que NO hace este componente:** no elige textos ni decide nada. Recibe los bloques ya
 * preparados por `app.js` (incluido el orden de los porqués, que es el que trae el servidor) y los
 * pinta. Ni una frase escrita aquí.
 *
 * Y una decisión de accesibilidad que viene de la pantalla vieja: los dos bloques largos van con
 * `<details>`, que es lo que ya sabe abrir y cerrar un lector de pantalla **sin una línea de
 * JavaScript**. Cambiarlo por un botón propio sería más bonito y funcionaría peor.
 */

import { Boton, frase, html } from "../componentes.js";

/** Un bloque con título, explicación y una lista de cosas. */
function Bloque({ titulo, intro, elementos, abrible = false }) {
  if (!elementos || !elementos.length) return null;
  const contenido = html`
    ${intro ? html`<p className="pista">${frase(intro)}</p>` : null}
    <ul className="lista">
      ${elementos.map((elemento, indice) => html`<li key=${indice}>${elemento}</li>`)}
    </ul>
  `;
  if (!abrible) {
    return html`
      <h2>${frase(titulo)}</h2>
      ${contenido}
    `;
  }
  return html`
    <details>
      <summary>${frase(titulo)}</summary>
      ${contenido}
    </details>
  `;
}

/**
 * Las frases del bloque de la ley, cada una con su nombre.
 *
 * **Esto cambió en la ronda 83.** Eran seis párrafos largos seguidos bajo un solo rótulo y se leían como un
 * muro: no se sabía dónde acababa uno y empezaba el siguiente, y para encontrar «lo de mandarlo a la Junta»
 * había que leerlos todos. Ahora cada uno es una cosa con su título delante, y se va derecho al que
 * interesa.
 *
 * **Y en la ronda 90, la etiqueta de sí o no** (del diseño de Stitch de esta pantalla): dos de los seis
 * puntos contestan a la pregunta con la que se entra aquí —«¿esto tengo que mandarlo?»— y su respuesta
 * («Sí es obligatorio», «Es voluntario») se lee en la etiqueta, sin leer el párrafo. Los otros cuatro no
 * son obligación ni voluntad: son explicaciones, y no llevan etiqueta porque no la tienen.
 */
function LoQueDiceLaLey({ titulo, filas }) {
  if (!filas || !filas.length) return null;
  return html`
    <h2>${frase(titulo)}</h2>
    <ul className="lista">
      ${filas.map(
        (fila, indice) => html`
          <li key=${indice}>
            <div className="apunte-cabecera">
              <strong>${frase(fila.titulo)}</strong>
              ${fila.etiqueta
                ? html`<span className=${`etiqueta-estado etiqueta-estado-${fila.tipo || "voluntario"}`}
                    >${frase(fila.etiqueta)}</span
                  >`
                : null}
            </div>
            <div className="apunte-detalle">${frase(fila.texto)}</div>
          </li>
        `,
      )}
    </ul>
  `;
}

/**
 * La pantalla entera.
 *
 * Propiedades (todas preparadas por `app.js`):
 *
 *  - `textos`: `{ pantalla, acciones }`, tal y como los sirve `/api/interfaz`.
 *  - `ley`: los puntos de lo que dice la ley, **cada uno con su título** (`{titulo, texto}`).
 *  - `porques`: las explicaciones, **cada una con su título**, en el orden que traiga el servidor.
 *  - `campos`: las fichas de cada campo (`{titulo, que_es, por_que}`).
 *  - `reglas`, `aportes`, `periodos`, `limites`: los cuatro bloques de abajo.
 */
export function PantallaAyuda({
  textos = {},
  ley = [],
  porques = [],
  campos = [],
  reglas = [],
  aportes = [],
  periodos = [],
  limites = [],
}) {
  const pantalla = textos.pantalla || {};
  const acciones = textos.acciones || {};

  const fichas = campos.map(
    (campo) => html`
      <strong>${frase(campo.titulo)}</strong>
      <div className="apunte-detalle">${frase(campo.que_es)}</div>
      <div className="apunte-detalle">${frase(campo.por_que)}</div>
    `,
  );
  const deLasReglas = reglas.map(
    (regla) => html`
      <strong>${frase(regla.que)}</strong>
      ${
        regla.texto_valor
          ? html`<div className="apunte-detalle">${frase(regla.con_numero)} ${frase(regla.texto_valor)}</div>`
          : null
      }
      <div className="apunte-detalle">${frase(regla.como_lo_hace)}</div>
    `,
  );
  const deLosAportes = aportes.map(
    (fila) => html`
      <strong>${frase(fila.cultivo)}</strong>
      <div className="apunte-detalle">${frase(fila.secano)}</div>
      <div className="apunte-detalle">${frase(fila.regadio)}</div>
    `,
  );
  const deLosPeriodos = periodos.map(
    (fila) => html`
      <strong>${frase(fila.grupo_cultivos)}</strong>
      <div className="apunte-detalle">${frase(fila.organicos)}</div>
      <div className="apunte-detalle">${frase(fila.minerales)}</div>
    `,
  );

  return html`
    <h1>${frase(pantalla.titulo)}</h1>
    <p className="pista">${frase(pantalla.intro)}</p>
    <div className="ayuda-campo">${frase(pantalla.repetir_no_se)}</div>

    <${LoQueDiceLaLey} titulo=${pantalla.ley_titulo} filas=${ley} />

    <h2>${frase(pantalla.porques_titulo)}</h2>
    <!-- Los porqués salen **todos**, con su nombre y en el orden del servidor: aquí no se elige ninguno. -->
    <ul className="lista">
      ${porques.map(
        (fila, indice) => html`
          <li key=${indice}>
            <strong>${frase(fila.titulo)}</strong>
            <div className="apunte-detalle">${frase(fila.texto)}</div>
          </li>
        `,
      )}
    </ul>

    <${Bloque} titulo=${pantalla.campos_titulo} elementos=${fichas} />
    <${Bloque}
      titulo=${pantalla.reglas_titulo}
      intro=${pantalla.reglas_intro}
      elementos=${deLasReglas}
    />
    <${Bloque}
      titulo=${pantalla.aportes_titulo}
      intro=${pantalla.aportes_pista}
      elementos=${deLosAportes}
      abrible=${true}
    />
    <${Bloque}
      titulo=${pantalla.periodos_titulo}
      intro=${pantalla.periodos_pista}
      elementos=${deLosPeriodos}
      abrible=${true}
    />
    <${Bloque}
      titulo=${pantalla.lo_que_falta_titulo}
      intro=${pantalla.lo_que_falta_intro}
      elementos=${limites.map((texto) => html`${frase(texto)}`)}
    />

    <${Boton} etiqueta=${acciones.volver} accion="ir-inicio" clase="boton-claro" />
  `;
}

/** El elemento de React de esta pantalla, ya con sus propiedades puestas. */
export function pantallaDeAyuda(propiedades) {
  return html`
    <${PantallaAyuda}
      textos=${propiedades.textos}
      ley=${propiedades.ley}
      porques=${propiedades.porques}
      campos=${propiedades.campos}
      reglas=${propiedades.reglas}
      aportes=${propiedades.aportes}
      periodos=${propiedades.periodos}
      limites=${propiedades.limites}
    />
  `;
}
