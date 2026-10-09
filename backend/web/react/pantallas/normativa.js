/**
 * La normativa: la pantalla.
 *
 * **Lo que se enseña no se decide aquí**: las diez reglas salen de `GET /api/normativa`, que a su vez sale de
 * `docs/MATRIZ_NORMATIVA_CRM.md`. Esta pantalla **sólo pinta**, y las palabras las pide al servidor: aquí no
 * hay ni una frase escrita a mano.
 *
 * Y una cosa que sí decide, porque es de sentido común: cuando una regla **no está clasificada**, lo dice. Una
 * obligación y una recomendación no se leen igual, y callarse sería lo peor de las dos opciones.
 *
 * Propiedades:
 *
 *  - `textos`: el bloque `normativa` de `/api/interfaz`.
 *  - `reglas`: lo que contestó `GET /api/normativa` (o `[]` si todavía no ha llegado).
 *  - `error`: si la puerta falló, lo que hay que decir.
 */

import { frase, html } from "../componentes.js";

export function PantallaNormativa({ textos = {}, reglas = [], error = "" }) {
  const t = textos.normativa || {};
  const lasReglas = reglas || [];

  return html`
    <h1>${frase(t.titulo)}</h1>
    <p className="pista">${frase(t.pista)}</p>

    ${error ? html`<p className="aviso">${frase(error)}</p>` : null}

    ${!error && !lasReglas.length ? html`<p className="pista">${frase(t.sin_normativa)}</p>` : null}

    <ul className="lista-de-normativa">
      ${lasReglas.map(
        (una) => html`
          <li key=${una.codigo} className="regla-de-normativa">
            <h2>${una.codigo} · ${una.titulo}</h2>
            ${una.tipo ? null : html`<p className="pista">${frase(t.sin_tipo)}</p>`}
            <p className="texto-de-la-regla">${una.ayuda}</p>
            <p className="pista">${frase(t.como_se_lee)}</p>
            <p className="pista">${frase((una.fuentes || []).length > 1 ? t.fuentes : t.fuente)}</p>
            <ul className="fuentes-de-la-regla">
              ${(una.fuentes || []).map(
                (fuente) => html`
                  <li key=${fuente.enlace}>
                    <a href=${fuente.enlace} target="_blank" rel="noopener noreferrer">${fuente.nombre}</a>
                  </li>
                `,
              )}
            </ul>
          </li>
        `,
      )}
    </ul>
  `;
}

// Y con el nombre que usa el armazon, como las demas pantallas.
export { PantallaNormativa as pantallaDeLaNormativa };
