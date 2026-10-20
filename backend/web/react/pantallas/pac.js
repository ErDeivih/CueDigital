import { frase, html } from "../componentes.js";

/**
 * **La preparación de la PAC: el paquete, el escenario y las fotos** (CRM-09, 18/10/2026, segunda entrega).
 *
 * ### ***El recorrido, que es el del agricultor***
 *
 *   campaña objetivo → cultivos hipotéticos → comparación → datos pendientes → **guardar versión** →
 *   historial → exportación
 *
 * ### ***Y tres capas que no se mezclan, dichas cada una en su sitio***
 *
 *   · ***LO QUE CONSTA***: *la superficie, la referencia y el cultivo de la campaña. Es el paquete, y **no
 *     cambia** porque se evalúe nada.*
 *   · ***LA HIPÓTESIS***: *el escenario del año que viene. Se calcula, se compara **y no toca la finca**.*
 *   · ***LOS TRABAJOS REALIZADOS***: *lo que se hizo de verdad en la campaña. **No es una hipótesis ni una
 *     declaración**, y se enseña aparte para que nadie los confunda.*
 *
 * ***«Persistir un borrador no lo convierte en una declaración oficial ni en un trabajo realizado»***: *por eso
 * lo que se guarda se llama **foto** y lleva su capa escrita.*
 *
 * ***Y lo que NO se afirma, que es lo primero***: *sin fuente legal cargada no se puede decir si algo es
 * elegible. La pantalla lo dice arriba, no al pie.*
 */

// ***`defaultValue` y no `value` en los campos***: *con `value` y sin `onChange`, React **revierte lo que se
// teclea** y el agricultor no puede escribir. Lo dijo `test_los_campos_se_pueden_escribir`, y tenia razon.*

// *Las especies que se pueden proponer. **No es una lista legal**: es lo que la pantalla sabe escribir, y se
// puede dejar en blanco -que es «no propongo nada»- o escribir otra a mano en el campo de al lado.*
const LAS_ESPECIES = ["", "trigo", "cebada", "girasol", "maiz", "alfalfa", "veza", "barbecho"];

export function PantallaElPaqueteDeLaPac({
  paquete = null,
  anio = "",
  cambios = {},
  escenario = null,
  comparacion = null,
  historial = null,
  trabajos = null,
  guardando = false,
  conflicto = null,
  error = "",
  aviso = "",
} = {}) {
  const t = (paquete && paquete.textos) || {};
  const las = (paquete && paquete.las_tierras) || [];
  const elResumen = paquete && paquete.el_resumen;
  const elAnio = anio || (paquete && paquete.campana_anio ? paquete.campana_anio + 1 : "");

  if (!paquete) {
    // *`null` es «todavía no se ha pedido»: **una tabla vacía diría que no hay nada**, y todavía no se sabe.*
    return html`<p>${frase(t.titulo)}</p>`;
  }

  const losIncompletos = las.filter((una) => !una.completa);
  const lasFotos = (historial && historial.las_fotos) || [];

  return html`
    <h1>${frase(t.titulo)}${paquete.campana_anio ? ` · ${paquete.campana_anio}` : ""}</h1>
    <p className="pista">${frase(t.explica)}</p>

    ${
      // ***Lo que no se puede afirmar, lo primero***: *decirlo después de la tabla es decirlo tarde.*
      paquete.aviso_de_la_fuente
        ? html`<p className="aviso" role="status" data-aviso="sin-fuente">${frase(paquete.aviso_de_la_fuente)}</p>`
        : null
    }
    ${error ? html`<p className="aviso-malo" role="alert" data-aviso="error">${frase(error)}</p>` : null}
    ${aviso ? html`<p className="aviso" role="status" data-aviso="aviso">${frase(aviso)}</p>` : null}

    <!-- ============================ LA CAMPAÑA OBJETIVO ============================ -->
    <section className="bloque" data-paso="campana-objetivo">
      <h2>La campaña que se quiere preparar</h2>
      <p className="pista">
        Se prepara **un año**, y no se toca el que está abierto: lo de ${paquete.campana_anio || "la campaña"} sigue
        como está.
      </p>
      <label>
        Año
        <input id="pac-anio" type="number" min="2000" max="2100" defaultValue=${elAnio} />
      </label>
      <button type="button" className="boton boton-claro" data-accion="pac-evaluar">EVALUAR ESE AÑO</button>
    </section>

    <!-- ============================ LO QUE CONSTA (no cambia) ============================ -->
    <section className="bloque" data-capa="consta">
      <h2>Lo que consta</h2>
      <p className="pista">**Esto no es una hipótesis**: es lo que hay en la finca y en su cuaderno.</p>
      ${elResumen
        ? html`<p data-porcentaje=${elResumen.porcentaje === null ? "no-se-sabe" : "si"}>
            ${
              // ***`null` no es cero***: *cero por ciento y «no se sabe» son cosas distintas.*
              elResumen.porcentaje === null || elResumen.porcentaje === undefined
                ? frase(t.falta_superficie)
                : `${elResumen.numerador} de ${elResumen.denominador} ${elResumen.unidad || "ha"} · ${elResumen.porcentaje}%`
            }
          </p>`
        : null}
      ${elResumen && elResumen.se_queda_fuera
        ? html`<p className="pista">${frase(t.sin_cultivo_aviso)} (${elResumen.se_queda_fuera} ha)</p>`
        : null}
    </section>

    <!-- ============================ LA HIPÓTESIS ============================ -->
    <section className="bloque" data-capa="hipotesis" data-paso="cultivos-hipoteticos">
      <h2>Lo que se propone sembrar</h2>
      <p className="pista">
        **Es una hipótesis**: no siembra nada, no declara nada y no toca el cuaderno. Se puede quitar.
      </p>
      <ul className="lista">
        ${las.map((una) => {
          const elPropuesto = (cambios[una.parcela_id] || {}).cultivo || {};
          return html`
            <li key=${una.parcela_id} className="fila-dato" data-completa=${una.completa ? "si" : "no"}>
              <span className="tabla-dato">${frase(una.alias)}</span>
              <span className="tabla-pista">
                consta: ${una.cultivo && una.cultivo.especie ? frase(una.cultivo.especie) : frase(t.falta_cultivo)}
                · ${(una.falta || []).length ? frase(t.incompleto) : frase(t.completo)}
              </span>
              <select id=${`pac-cultivo-${una.parcela_id}`} data-parcela=${una.parcela_id}>
                ${LAS_ESPECIES.map(
                  (especie) =>
                    html`<option value=${especie} selected=${String(elPropuesto.especie || "") === especie}>
                      ${especie || "(no propongo nada)"}
                    </option>`,
                )}
              </select>
              <button
                type="button"
                className="boton boton-claro"
                data-accion="pac-proponer"
                data-parcela=${una.parcela_id}
              >
                PROPONER
              </button>
            </li>
          `;
        })}
      </ul>
      <button type="button" className="boton boton-claro" data-accion="pac-comparar">COMPARAR CON LO DE AHORA</button>
    </section>

    <!-- ============================ EL ESCENARIO CALCULADO ============================ -->
    ${escenario
      ? html`
          <section className="bloque" data-capa="escenario" data-paso="comparacion">
            <h2>El escenario de ${escenario.anio}</h2>
            <p className="pista" data-aviso="es-hipotesis">
              **Es una hipótesis, no lo declarado ni lo realizado.** No se envía nada y no promete elegibilidad.
            </p>
            <p>
              ${escenario.el_resumen && escenario.el_resumen.porcentaje !== null
                ? `${escenario.el_resumen.numerador} de ${escenario.el_resumen.denominador} ha · ${escenario.el_resumen.porcentaje}%`
                : frase(t.falta_superficie)}
            </p>
            ${comparacion
              ? html`<div data-paso="diferencias">
                  <h3>Qué cambia</h3>
                  ${
                    comparacion.cuantas === 0
                      ? html`<p className="pista">Con lo propuesto no cambia nada.</p>`
                      : html`<ul className="lista">
                          ${comparacion.las_diferencias.map(
                            (una) => html`
                              <li className="fila-dato">
                                <span className="tabla-dato">${frase(una.alias)}</span>
                                <span className="tabla-pista">
                                  ${una.en_uno && una.en_uno.especie ? frase(una.en_uno.especie) : "(sin cultivo)"}
                                  → ${una.en_otro && una.en_otro.especie ? frase(una.en_otro.especie) : "(sin cultivo)"}
                                </span>
                              </li>
                            `,
                          )}
                        </ul>`
                  }
                </div>`
              : null}
          </section>
        `
      : null}

    <!-- ============================ LOS DATOS PENDIENTES ============================ -->
    <section className="bloque" data-capa="pendientes" data-paso="datos-pendientes">
      <h2>Lo que falta por saber</h2>
      ${
        losIncompletos.length === 0
          ? html`<p className="pista">${frase(t.completo)}</p>`
          : html`<ul className="lista">
              ${losIncompletos.map(
                (una) => html`
                  <li className="fila-dato" data-completa="no">
                    <span className="tabla-dato">${frase(una.alias)}</span>
                    <span className="tabla-pista">${(una.falta || []).map((clave) => frase(t[clave] || clave)).join(" · ")}</span>
                  </li>
                `,
              )}
            </ul>`
      }
    </section>

    <!-- ============================ GUARDAR LA VERSIÓN ============================ -->
    <section className="bloque" data-capa="guardar" data-paso="guardar-version">
      <h2>Guardar esta versión</h2>
      <p className="pista">
        Se guarda **una foto de lo que estás viendo**, con su número y su fecha. No es una declaración: si luego
        cambia la finca, la foto sigue diciendo lo que decía.
      </p>
      ${
        conflicto
          ? html`<div className="aviso-malo" role="alert" data-aviso="conflicto">
              <p>${frase(conflicto.mensaje || "")}</p>
              <p>${frase(conflicto.no_se_ha_guardado_nada || "")}</p>
              <button type="button" className="boton boton-claro" data-accion="pac-recalcular">
                RECALCULAR CON LO DE AHORA Y GUARDAR
              </button>
            </div>`
          : null
      }
      <button
        type="button"
        className="boton boton-principal"
        data-accion="pac-guardar"
        disabled=${guardando || !escenario}
      >
        ${guardando ? "GUARDANDO…" : "GUARDAR VERSIÓN"}
      </button>
    </section>

    <!-- ============================ EL HISTORIAL ============================ -->
    <section className="bloque" data-capa="historial" data-paso="historial">
      <h2>Las versiones guardadas</h2>
      <button type="button" className="boton boton-claro" data-accion="pac-historial">VER EL HISTORIAL</button>
      ${
        lasFotos.length === 0
          ? html`<p className="pista">Todavía no se ha guardado ninguna.</p>`
          : html`<ul className="lista">
              ${lasFotos.map(
                (una) => html`
                  <li className="fila-dato" data-foto=${una.id}>
                    <span className="tabla-dato">${una.anio} · versión ${una.version}</span>
                    <span className="tabla-pista">${frase(una.creada_en)}</span>
                    <button
                      type="button"
                      className="boton boton-claro"
                      data-accion="pac-exportar"
                      data-anio=${una.anio}
                      data-version=${una.version}
                    >
                      EXPORTAR
                    </button>
                  </li>
                `,
              )}
            </ul>`
      }
    </section>

    <!-- ============================ LOS TRABAJOS REALIZADOS (aparte) ============================ -->
    <section className="bloque" data-capa="realizado" data-paso="trabajos">
      <h2>Los trabajos realizados</h2>
      <p className="pista">
        **Esto no es una hipótesis ni una declaración**: es lo que se ha hecho de verdad en la campaña.
      </p>
      ${
        trabajos === null
          ? html`<p className="pista">Sin datos de la campaña.</p>`
          : trabajos.length === 0
            ? html`<p className="pista">En esta campaña no hay trabajos apuntados.</p>`
            : html`<ul className="lista">
                ${trabajos.slice(0, 12).map(
                  (uno) => html`
                    <li className="fila-dato">
                      <span className="tabla-dato">${frase(uno.tipo || "")} ${frase(uno.subtipo || "")}</span>
                      <span className="tabla-pista">${frase(uno.fecha || "")}</span>
                    </li>
                  `,
                )}
              </ul>`
      }
    </section>

    ${
      // ***Y la advertencia, al pie y siempre***: *«no envío directo ni garantía de elegibilidad».*
      paquete.no_es_garantia
        ? html`<p className="pista-campo" data-aviso="no-es-garantia">${frase(paquete.no_es_garantia)}</p>`
        : null
    }
  `;
}
