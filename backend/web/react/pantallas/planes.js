/*
 * planes.js — «El plan de abono del año», escrito en React.
 *
 * POR QUÉ ESTA PANTALLA
 *
 * Es la decimoséptima que se pasa a React, y es la sección que la Junta pide con el nombre de
 * «Recomendación de nutrientes»: lo que el agricultor **tenía previsto** echar, frente a lo que
 * **lleva echado** y lo que **le queda**. Lo que de verdad sirve de esta pantalla no es el apunte:
 * es que cuando lleva más de lo previsto se vea, porque abonar de más tiene consecuencias en el agua
 * y en la PAC.
 *
 * **Lo que NO hace este componente:** no calcula nada. Cada plan le llega ya contado desde `app.js`:
 * sus tres filas (N, P y K) con lo previsto, lo aplicado y lo que queda, el nombre de la parcela, si
 * se ha pasado, y el análisis en el que se apoya (con sus números ya preparados). El componente solo
 * decide **qué se enseña cuando falta un dato**: no se pinta una fila vacía ni un hueco con un
 * rótulo.
 *
 * LO QUE SE CONSERVA A PROPÓSITO
 *
 *  1. El aviso de «te has pasado» va en su bloque y **en rojo** cuando de verdad se ha pasado; si no,
 *     en el aviso normal. Antes se miraba el signo de lo que queda, y ahora lo dice el servidor con
 *     `se_ha_pasado`, que es quien tiene las cuentas.
 *  2. Las mismas `data-accion` (`plan-hacer`, `inicio` con `data-ir`) y las mismas clases.
 *  3. Nada de `esc()` y ninguna frase escrita aquí: los textos llegan por propiedades.
 *
 * El componente es PURO: no llama a `fetch`, no lee `localStorage` y no toca el DOM.
 */

import { Boton, frase, html } from "../componentes.js";
import { AccionesDeUnaFicha } from "../piezas/acciones_de_una_ficha.js";

/** Una fila de la tabla: un nutriente, lo previsto, lo aplicado y lo que queda. */
function Fila({ fila }) {
  return html`
    <div className="resumen-dato">
      <dt>${frase(fila.nombre)}</dt>
      <dd>${frase(fila.texto)}</dd>
    </div>
  `;
}

/** Un plan de abono: de qué parcela es, cómo va y en qué se apoya. */
function Plan({ plan, textos }) {
  const p = textos.plan || {};

  return html`
    <div className="apunte-cabecera">
      <h2>${frase(plan.titulo)}</h2>
      ${
        // El veredicto del plan, en su etiqueta (diseño de Stitch de esta pantalla, ronda 90): «En regla»
        // o «Alerta: exceso». Es la primera pregunta al abrir esto —«¿voy bien?»— y antes había que
        // leerse la tabla entera para contestarla.
        plan.estado && plan.estado.texto
          ? html`<span className=${`etiqueta-estado etiqueta-estado-${plan.estado.tipo || "bien"}`}
              >${frase(plan.estado.texto)}</span
            >`
          : null
      }
    </div>
    <p className="pista-campo">${frase(plan.detalle)}</p>
    ${plan.precedente ? html`<p className="pista-campo">${frase(plan.precedente)}</p>` : null}
    ${plan.herramienta ? html`<p className="pista-campo">${frase(plan.herramienta)}</p>` : null}
    <div className=${plan.se_ha_pasado ? "aviso aviso-error" : "aviso"}>
      <p>${frase(plan.mensaje)}</p>
    </div>
    ${
      // En qué se apoya. Si el plan no se apoya en ningún análisis se dice, en vez de dejar el
      // hueco: «sin análisis» es una decisión del agricultor, no un dato que falte.
      plan.analisis
        ? html`<h3>${frase(p.se_basa_en)}</h3>
            <p className="pista-campo">${frase(plan.analisis.titulo)}</p>
            <dl>
              ${plan.analisis.numeros.map(
                ([etiqueta, valor], indice) => html`
                  <div className="resumen-dato" key=${indice}>
                    <dt>${frase(etiqueta)}</dt>
                    <dd>${frase(valor)}</dd>
                  </div>
                `,
              )}
            </dl>`
        : html`<p className="pista-campo">${frase(p.sin_analisis)}</p>`
    }
    <dl>
      <div className="resumen-dato">
        <dt></dt>
        <dd>${frase(plan.cabecera)}</dd>
      </div>
      ${plan.filas.map((fila, indice) => html`<${Fila} key=${indice} fila=${fila} />`)}
    </dl>
    ${
      // **CORREGIR y BORRAR el plan** (ronda 93). Un plan **no es un apunte, es una previsión**, y por eso
      // se puede cambiar sin problema —si a mitad de campaña cambia el precio del abono, el plan se
      // ajusta—; lo que no se toca nunca son los apuntes de abono, que esos sí son registro obligatorio.
      // El plan se corrige con el mismo asistente con el que se hace.
      html`<${AccionesDeUnaFicha} acciones=${plan.acciones} />`
    }
  `;
}

/**
 * La pantalla entera.
 *
 * Propiedades:
 *
 *  - `textos`: `{ plan, acciones }`, tal y como los sirve `/api/interfaz`.
 *  - `planes`: los planes del año, ya preparados (o vacío, que es el caso del agricultor que todavía
 *    no ha hecho ninguno).
 *  - `obligatorio`: desde cuándo es obligatorio el plan, del servidor. Va arriba, en su aviso.
 */
export function PantallaPlanes({ textos = {}, planes = [], obligatorio = "" }) {
  const p = textos.plan || {};
  const acciones = textos.acciones || {};

  return html`
    <h1>${frase(p.titulo)}</h1>
    <p className="pista">${frase(p.explica)}</p>
    ${
      // **Cuándo es obligatorio el plan**, en su aviso y arriba (diseño de Stitch de esta pantalla):
      // contesta a «¿esto me hace falta?», que es lo primero que se pregunta quien entra aquí. El texto
      // llevaba desde la ronda 60 en el vocabulario **sin que lo leyera ninguna pantalla**.
      obligatorio
        ? html`
            <p className="tarjeta-aviso tarjeta-aviso-grande">
              <span className="tarjeta-aviso-icono" aria-hidden="true">!</span>
              ${frase(obligatorio)}
            </p>
          `
        : null
    }
    ${
      planes.length === 0
        ? html`<div className="aviso">${frase(p.sin_planes)}</div>`
        : planes.map((plan, indice) => html`<${Plan} key=${indice} plan=${plan} textos=${textos} />`)
    }
    <div className="barra-acciones">
      <${Boton} etiqueta=${p.hacer} accion="plan-hacer" />
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
export function pantallaDePlanes(propiedades) {
  return html`<${PantallaPlanes}
    textos=${propiedades.textos}
    planes=${propiedades.planes}
    obligatorio=${propiedades.obligatorio}
  />`;
}
