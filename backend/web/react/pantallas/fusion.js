import { html } from "../componentes.js";

/**
 * La fusión de dos fichas (Entrega 5, 14/10/2026).
 *
 * QUÉ HACE. El recorrido del contrato: *elegir origen y destino → ver la vista previa → confirmar y ejecutar*.
 * La vista previa **ya viene hecha del servidor** (`GET /api/contactos/{origen}/fusion/{destino}`): cuenta las once
 * tablas que cuelgan de cada ficha y dice **las colisiones** con su porqué y su qué-hacer. Esta pantalla **las
 * enseña**; no las resuelve por su cuenta.
 *
 * Y LO QUE TIENE QUE DECIR, porque si no se deduce o no se sabe:
 *
 *   1. **Qué se va a mover**, contado y por tabla. No «se van a juntar las fichas»: *cuántos papeles, cuántas notas,
 *      cuántas tareas, cuánto dinero*.
 *   2. **Qué colisiona y por qué.** Hay dos colisiones duras (el papel repetido y el canal principal), y una que
 *      **no puede decidir nadie por el agricultor**: **las dos fichas con notas escritas**, porque la nota es un
 *      campo único. Cuando pasa eso, la pantalla **para** y lo dice.
 *   3. **Que el origen NO se borra**: se queda remitiendo al destino, para que sus enlaces de siempre sigan teniendo
 *      sentido. Y que se puede **deshacer**, con lo que eso devuelve y lo que no.
 *   4. **Los dos saldos, separados**: la fusión no compensa lo que le debemos con lo que nos debe.
 */
export function PantallaDeLaFusion({
  contactos = [],
  origen_id = "",
  destino_id = "",
  previa = null,
  resultado = null,
  cargando = false,
  error = "",
  aviso = "",
  textos = {},
} = {}) {
  const t = textos.fusion || {};
  const frase = (algo) => (algo === undefined || algo === null ? "" : String(algo));
  const cuantos = (numero) => (numero === undefined || numero === null ? "0" : String(numero));

  // **Las colisiones que el contrato llama «que hay que decidir»**: se enseñan siempre, y las que no puede decidir
  // nadie paran la fusión.
  const colisiones = (previa && previa.colisiones) || [];
  const hay_que_parar = colisiones.some((una) => una && una.para_la_fusion);

  const opciones = (elegido) =>
    contactos.map(
      (contacto) =>
        html`<option value=${contacto.id} selected=${String(elegido) === String(contacto.id)}>${frase(contacto.nombre)}</option>`,
    );

  return html`
    <section className="pantalla">
      <h1>${frase(t.titulo)}</h1>
      <p className="pista">${frase(t.pista)}</p>

      ${error ? html`<p className="aviso-malo">${frase(error)}</p>` : null}
      ${aviso ? html`<p className="aviso">${frase(aviso)}</p>` : null}
      ${cargando ? html`<p className="pista">${frase(t.cargando)}</p>` : null}

      <div className="fusion-elegir">
        <label>
          ${frase(t.la_que_desaparece)}
          <select id="fusion-origen" defaultValue=${origen_id}>
            <option value="">${frase(t.elije_una)}</option>
            ${opciones(origen_id)}
          </select>
        </label>
        <label>
          ${frase(t.la_que_se_queda)}
          <select id="fusion-destino" defaultValue=${destino_id}>
            <option value="">${frase(t.elije_una)}</option>
            ${opciones(destino_id)}
          </select>
        </label>
        <button type="button" className="boton boton-claro" data-accion="fusion-ver">
          ${frase(t.ver_lo_que_pasa)}
        </button>
      </div>

      ${
        previa
          ? html`
              <div className="fusion-previa">
                <h2>${frase(t.esto_es_lo_que_pasa)}</h2>
                <table className="tabla">
                  <thead>
                    <tr>
                      <th>${frase(t.que)}</th>
                      <th>${frase(t.de_la_que_desaparece)}</th>
                      <th>${frase(t.de_la_que_se_queda)}</th>
                    </tr>
                  </thead>
                  <tbody>
                    ${Object.entries(previa.origen ? previa.origen.dinero || {} : {}).map(
                      ([tabla, cuantos_origen]) => html`
                        <tr>
                          <td>${frase(tabla)}</td>
                          <td>${cuantos(cuantos_origen)}</td>
                          <td>${cuantos(((previa.destino || {}).dinero || {})[tabla])}</td>
                        </tr>
                      `,
                    )}
                    ${Object.entries(previa.origen ? previa.origen.cuelgan || {} : {}).map(
                      ([tabla, cuantos_origen]) => html`
                        <tr>
                          <td>${frase(tabla)}</td>
                          <td>${cuantos(cuantos_origen)}</td>
                          <td>${cuantos(((previa.destino || {}).cuelgan || {})[tabla])}</td>
                        </tr>
                      `,
                    )}
                  </tbody>
                </table>

                ${
                  // **El dinero, separado y sin compensar.** Lo que le debemos no se resta de lo que nos debe.
                  previa.saldos
                    ? html`
                        <p className="pista">
                          ${frase(t.los_saldos_no_se_compensan)}:
                          ${frase(t.nos_debe)} ${frase(previa.saldos.nos_debe)} ·
                          ${frase(t.le_debemos)} ${frase(previa.saldos.le_debemos)}
                        </p>
                      `
                    : null
                }

                ${
                  colisiones.length === 0
                    ? html`<p className="pista">${frase(t.no_choca_nada)}</p>`
                    : html`
                        <div className="fusion-colisiones">
                          <h3>${frase(t.lo_que_choca)}</h3>
                          <ul>
                            ${colisiones.map(
                              (una) => html`
                                <li>
                                  <strong>${frase(una.que)}</strong> — ${frase(una.por_que)}
                                  <br />
                                  <span className="pista">${frase(una.que_hacer)}</span>
                                </li>
                              `,
                            )}
                          </ul>
                        </div>
                      `
                }

                ${
                  hay_que_parar
                    ? html`<p className="aviso-malo">${frase(t.esto_no_lo_puede_decidir_la_pantalla)}</p>`
                    : html`
                        <button
                          type="button"
                          className="boton boton-principal"
                          data-accion="fusion-hacer"
                          data-origen=${origen_id}
                          data-destino=${destino_id}
                        >
                          ${frase(t.fusionarlas)}
                        </button>
                      `
                }
                <p className="pista">${frase(t.el_origen_no_se_borra)}</p>
              </div>
            `
          : null
      }

      ${
        resultado
          ? html`
              <div className="fusion-hecha">
                <h2>${frase(t.hecho)}</h2>
                <p>${frase(resultado.aviso || "")}</p>
                <button
                  type="button"
                  className="boton boton-claro"
                  data-accion="fusion-deshacer"
                  data-destino=${resultado.destino_id || destino_id}
                >
                  ${frase(t.deshacer)}
                </button>
                <p className="pista">${frase(t.deshacer_devuelve_solo_lo_que_trajo)}</p>
              </div>
            `
          : null
      }
    </section>
  `;
}
