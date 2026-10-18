import { frase, html } from "../componentes.js";

/**
 * **El paquete preparatorio de la PAC, tierra por tierra** (CRM-09, 17/10/2026).
 *
 * *Lo que el contrato pide*: *«paquete preparatorio por recinto: referencias, superficie, cultivos, practica,
 * documentos y **cuestiones pendientes**. ***No envio directo ni garantia de elegibilidad***».*
 *
 * ***Y lo primero que se ve es lo que la respuesta dice de si misma***: *que **no hay ninguna fuente legal
 * cargada**, asi que **no se puede decir si algo es elegible**.* *Un paquete que no dice eso se lee como si
 * lo dijera, y el agricultor se presenta con el a la declaracion.*
 *
 * ***Y las incompletas van primero***, con lo que les falta escrito: *es lo que hay que resolver antes de
 * llevarlo al asesor, y enterrarlo entre las que ya estan es la forma de que no se resuelva.*
 */
export function PantallaElPaqueteDeLaPac({ paquete = null }) {
  const t = (paquete && paquete.textos) || {};
  const las = (paquete && paquete.las_tierras) || [];
  const elResumen = paquete && paquete.el_resumen;
  const anio = paquete && paquete.campana_anio;

  if (!paquete) {
    // *`null` es «todavia no se ha pedido», y no se pinta una tabla vacia:* **una tabla vacia dice «no hay
    // nada», y todavia no se sabe.**
    return html`<p>${frase(t.titulo)}</p>`;
  }

  return html`
    <h1>${frase(t.titulo)}${anio ? ` · ${anio}` : ""}</h1>
    <p className="pista">${frase(t.explica)}</p>

    ${
      // ***Y lo que NO se puede afirmar, lo primero***: *sin fuente legal no hay elegibilidad, y decirlo
      // despues de la tabla es decirlo tarde.*
      paquete.aviso_de_la_fuente
        ? html`<p className="aviso" role="status" data-aviso="sin-fuente">${frase(paquete.aviso_de_la_fuente)}</p>`
        : null
    }

    ${
      elResumen
        ? html`<section className="el-resumen">
            <h2>${frase(t.resumen)}</h2>
            <p data-porcentaje=${elResumen.porcentaje === null ? "no-se-sabe" : "si"}>
              ${
                // ***`null` no es cero***: *cero por ciento y «no se sabe» son cosas distintas, y un cero
                // pinta un mapa de verde que no es verdad.*
                elResumen.porcentaje === null || elResumen.porcentaje === undefined
                  ? frase(t.falta_superficie)
                  : `${elResumen.numerador} de ${elResumen.denominador} ${elResumen.unidad || "ha"} · ${elResumen.porcentaje} %`
              }
            </p>
            ${
              // ***Y las hectareas que se quedan fuera, dichas***: «tierra sin cultivo no desaparece para
              // pintar verde».
              elResumen.se_queda_fuera
                ? html`<p className="pista">${frase(t.sin_cultivo_aviso)} (${elResumen.se_queda_fuera} ha)</p>`
                : null
            }
          </section>`
        : null
    }

    ${
      las.length
        ? html`<ul className="lista">
            ${las.map(
              (una) => html`
                <li key=${una.parcela_id} className="fila-dato" data-completa=${una.completa ? "si" : "no"}>
                  <span className="tabla-dato">${frase(una.alias)}</span>
                  <span className="tabla-numero"
                    >${una.superficie_ha === null || una.superficie_ha === undefined ? frase(t.falta_superficie) : `${una.superficie_ha} ha`}</span
                  >
                  <span className="tabla-pista"
                    >${una.referencia ? frase(una.referencia) : frase(t.falta_referencia)}${
                      una.cultivo && una.cultivo.especie ? ` · ${frase(una.cultivo.especie)}` : ` · ${frase(t.falta_cultivo)}`
                    }${
                      // ***Lo que falta, con su palabra***: *es la pregunta del asesor -¿puedo llevar esto o me
                      // falta algo?-, y se contesta con las claves que manda el servidor.*
                      (una.falta || []).length ? ` · ${frase(t.incompleto)}` : ` · ${frase(t.completo)}`
                    }</span
                  >
                </li>
              `,
            )}
          </ul>`
        : html`<p className="pista">${frase(t.sin_tierras)}</p>`
    }

    ${
      // ***Y la advertencia, al pie y siempre***: *«no envio directo ni garantia de elegibilidad».*
      paquete.no_es_garantia
        ? html`<p className="pista-campo" data-aviso="no-es-garantia">${frase(paquete.no_es_garantia)}</p>`
        : null
    }
  `;
}
