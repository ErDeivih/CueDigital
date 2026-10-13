import { html } from "../componentes.js";

/**
 * Los servicios a terceros (CRM-04, 14/10/2026).
 *
 * QUÉ ES. El recorrido del contrato: *cliente → propuesta de trabajo → aceptación → parte realizado →
 * venta/documento → cobro*. Esta pantalla hace los cuatro primeros pasos; el cobro vive en el saldo del contacto,
 * que es donde está el dinero de todos los documentos de esta casa.
 *
 * Y LAS DOS COSAS QUE LA PANTALLA TIENE QUE DECIR, porque si no el agricultor las deduce o no las sabe:
 *
 *   1. **De quién es el insumo.** El del cliente **no** descuenta su almacén; el suyo sí. No es un detalle: es la
 *      diferencia entre que le cuadre el gasoil o no.
 *   2. **Si el coste consta.** Un trabajo sin coste apuntado **no es un trabajo que costó cero**: es uno del que no
 *      se sabe el coste, y el margen tiene que marcarlo. Aquí se dice con esas palabras.
 *
 * La superficie y la ubicación se enseñan **como lo que son**: de un tercero. Nunca suman a las tierras propias.
 */
export function PantallaDeLosTrabajosATerceros({
  trabajos = [],
  contactos = [],
  cargando = false,
  a_medias = null,
  textos = {},
} = {}) {
  const t = textos.trabajos_a_terceros || {};
  const frase = (algo) => (algo === undefined || algo === null ? "" : String(algo));
  const dinero = (cantidad) =>
    cantidad === null || cantidad === undefined || cantidad === ""
      ? frase(t.no_consta)
      : `${Number(cantidad).toFixed(2)} €`;

  const estados = {
    propuesto: frase(t.propuesto),
    aceptado: frase(t.aceptado),
    hecho: frase(t.hecho),
    cancelado: frase(t.cancelado),
  };

  return html`
    <section className="pantalla">
      <h1>${frase(t.titulo)}</h1>
      <p className="pista">${frase(t.pista)}</p>

      ${
        cargando
          ? html`<p className="pista">${frase(t.cargando)}</p>`
          : html`
              <div className="alta-rapida-de-trabajo">
                <label>
                  ${frase(t.para_quien)}
                  <select id="trabajo-cliente" defaultValue=${(a_medias || {}).contacto_id || ""}>
                    <option value="">${frase(t.elije_el_cliente)}</option>
                    ${contactos.map(
                      (contacto) =>
                        html`<option value=${contacto.id} selected=${String((a_medias || {}).contacto_id) === String(contacto.id)}>
                          ${frase(contacto.nombre)}
                        </option>`,
                    )}
                  </select>
                </label>
                <label>
                  ${frase(t.que_se_le_hace)}
                  <input id="trabajo-titulo" type="text" defaultValue=${(a_medias || {}).titulo || ""} />
                </label>
                <label>
                  ${frase(t.donde)}
                  <input id="trabajo-ubicacion" type="text" defaultValue=${(a_medias || {}).ubicacion || ""} />
                </label>
                <label>
                  ${frase(t.cuantas_hectareas)}
                  <input id="trabajo-superficie" type="text" inputMode="decimal" defaultValue=${(a_medias || {}).superficie_ha || ""} />
                </label>
                <label>
                  ${frase(t.de_quien_es_el_insumo)}
                  <select id="trabajo-insumo" defaultValue=${(a_medias || {}).de_quien_es_el_insumo || "propio"}>
                    <option value="propio">${frase(t.insumo_propio)}</option>
                    <option value="cliente">${frase(t.insumo_del_cliente)}</option>
                  </select>
                </label>
                <label>
                  ${frase(t.a_cuanto_la_hora)}
                  <input id="trabajo-tarifa" type="text" inputMode="decimal" defaultValue=${(a_medias || {}).tarifa_por_hora || ""} />
                </label>
                <button type="button" className="boton boton-principal" data-accion="trabajo-proponer">
                  ${frase(t.proponer)}
                </button>
                <p className="pista">${frase(t.la_superficie_no_es_tuya)}</p>
              </div>
            `
      }

      ${
        trabajos.length === 0
          ? html`<p className="pista">${frase(t.no_hay_ninguno)}</p>`
          : html`
              <table className="tabla">
                <thead>
                  <tr>
                    <th>${frase(t.para_quien)}</th>
                    <th>${frase(t.que_se_le_hace)}</th>
                    <th>${frase(t.donde_y_cuanto)}</th>
                    <th>${frase(t.insumo)}</th>
                    <th>${frase(t.tarifa)}</th>
                    <th>${frase(t.coste)}</th>
                    <th>${frase(t.estado)}</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  ${trabajos.map(
                    (trabajo) => html`
                      <tr data-trabajo=${trabajo.id}>
                        <td>
                          <a href="#/contactos/${trabajo.cliente.id}">${frase(trabajo.cliente.nombre)}</a>
                        </td>
                        <td>${frase(trabajo.titulo)}</td>
                        <td>
                          ${frase(trabajo.ubicacion)}
                          ${trabajo.superficie_ha ? html` · ${dinero(trabajo.superficie_ha)} ha` : null}
                        </td>
                        <td>
                          ${
                            trabajo.de_quien_es_el_insumo === "propio"
                              ? frase(t.insumo_propio)
                              : html`<strong>${frase(t.insumo_del_cliente)}</strong>`
                          }
                        </td>
                        <td>
                          ${
                            // **La tarifa que manda es la aceptada.** Se enseña la aceptada cuando la hay, porque es
                            // la que se pactó: la de la lista puede haber cambiado y no cambia este trabajo.
                            trabajo.tarifa_aceptada !== null && trabajo.tarifa_aceptada !== undefined
                              ? html`${dinero(trabajo.tarifa_aceptada)} <span className="pista">${frase(t.aceptada_esta)}</span>`
                              : dinero(trabajo.tarifa_por_hora)
                          }
                        </td>
                        <td>
                          ${
                            // **Y si el coste no consta, se dice.** El contrato: el margen tiene que marcarlo.
                            trabajo.coste_conocido_o_no
                              ? dinero(trabajo.coste_conocido)
                              : html`<em>${frase(t.coste_no_consta)}</em>`
                          }
                        </td>
                        <td>${estados[trabajo.estado] || frase(trabajo.estado)}</td>
                        <td>
                          ${
                            trabajo.estado === "propuesto"
                              ? html`<button type="button" className="boton boton-claro" data-accion="trabajo-aceptar" data-id=${trabajo.id}>
                                  ${frase(t.aceptar)}
                                </button>`
                              : null
                          }
                          ${
                            trabajo.estado === "aceptado"
                              ? html`<button type="button" className="boton boton-claro" data-accion="trabajo-parte" data-id=${trabajo.id}>
                                  ${frase(t.apuntar_el_parte)}
                                </button>`
                              : null
                          }
                          ${
                            trabajo.estado === "propuesto" || trabajo.estado === "aceptado"
                              ? html`<button type="button" className="boton boton-claro" data-accion="trabajo-cancelar" data-id=${trabajo.id}>
                                  ${frase(t.cancelar)}
                                </button>`
                              : null
                          }
                        </td>
                      </tr>
                    `,
                  )}
                </tbody>
              </table>
            `
      }
    </section>
  `;
}

/** El envoltorio: la pantalla, con lo que le llega del estado. */
export function pantallaDeLosTrabajosATerceros(propiedades) {
  return html`<${PantallaDeLosTrabajosATerceros} ...${propiedades} />`;
}
