/*
 * movimiento_de_almacen.js — Apuntar una merma, un ajuste o una entrada sin papel (T09), en React.
 *
 * POR QUÉ ESTA PANTALLA
 *
 * El almacén no solo se mueve con albaranes y con lo que se echa en la tierra. Pasan tres cosas más, y
 * las tres tienen que poder apuntarse o el libro deja de cuadrar:
 *
 *  · **Se pierde producto**: un envase roto, algo que se ha estropeado. No es un gasto —no se ha
 *    echado en la tierra— pero tampoco está.
 *  · **Al contar sale otra cantidad**: el ajuste, con **la diferencia** (positiva si había de más,
 *    negativa si de menos). Así el saldo se hace siempre igual y no hay dos formas de apuntar lo mismo.
 *  · **Entra algo sin papel**: lo que ya estaba en el almacén antes de empezar a usar el programa. Sin
 *    esta puerta, ese producto no podría existir nunca en el libro.
 *
 * Y EL MOTIVO NO ES UN ADORNO
 *
 * En estas tres no hay ningún documento detrás: lo único que las explica es lo que escriba el
 * agricultor. Sin eso, dentro de dos años nadie sabe por qué faltan diez litros, y un cuaderno que no
 * se puede explicar no sirve en una inspección. Por eso el servidor lo exige y por eso aquí está
 * primero.
 *
 * LO QUE ESTA PANTALLA NO HACE
 *
 *  · **Una salida no se apunta por aquí.** Lo que sale del almacén sale de un trabajo, y tiene su
 *    camino (el botón «sacar de un envase» del apunte): si se pudiera restar producto «porque sí», el
 *    almacén dejaría de poder contestar a «¿esto dónde se fue?».
 *  · **No calcula nada**: la diferencia del conteo la escribe el agricultor, no la adivina el programa.
 *  · **No hay ni una frase escrita aquí**: los textos llegan por propiedades.
 *
 * Los `id` de los campos (`movimiento-articulo`, `movimiento-cantidad`…) son los que lee `app.js`.
 */

import { AvisoDeError, Boton, frase, html } from "../componentes.js";

/** Un campo de escribir con su etiqueta y su pista. */
function Campo({ id, etiqueta, pista, tipo = "texto", valor = "" }) {
  return html`
    <div className="campo">
      <label htmlFor=${id}>${frase(etiqueta)}</label>
      ${pista ? html`<p className="pista-campo">${frase(pista)}</p>` : null}
      ${
        tipo === "fecha"
          ? html`<input id=${id} type="date" defaultValue=${frase(valor)} />`
          : html`<input
              id=${id}
              type="text"
              inputMode=${tipo === "numero" ? "decimal" : undefined}
              defaultValue=${frase(valor)}
            />`
      }
    </div>
  `;
}

/**
 * La pantalla entera.
 *
 * Propiedades:
 *
 *  - `textos`: `{ cesta, acciones }` del servidor.
 *  - `borrador`: `{ tipo, titulo, pista, articulo_id, numero_lote, fecha, cantidad, unidad, motivo }`.
 *    El título y la pista dependen del tipo (merma, ajuste o entrada) y los prepara `app.js`, que es
 *    quien sabe con qué botón se ha entrado.
 *  - `articulos`: lo que hay dado de alta en el almacén, para elegir de qué es el movimiento.
 *  - `unidades`: en qué se puede medir, del catálogo del servidor. **El envase, y no un campo libre**:
 *    «litros» y «L» son la misma cosa, y dos formas de escribirla parten la cuenta de un envase.
 *  - `guardando`: si se está mandando (el botón se apaga y lo dice: sin eso, el mismo movimiento se
 *    puede mandar dos veces).
 *  - `error`: lo que ha dicho el servidor —por ejemplo que falta el motivo— o nada.
 */
export function PantallaMovimientoDeAlmacen({
  textos = {},
  borrador = {},
  articulos = [],
  unidades = [],
  guardando = false,
  error = "",
}) {
  const c = textos.cesta || {};
  return html`
    <h1>${frase(borrador.titulo)}</h1>
    <p className="pista">${frase(borrador.pista)}</p>
    <${AvisoDeError} texto=${error} />

    <div className="campo">
      <label htmlFor="movimiento-articulo">${frase(c.libro_movimiento_articulo)}</label>
      <p className="pista-campo">${frase(c.libro_movimiento_articulo_pista)}</p>
      <select id="movimiento-articulo" defaultValue=${String(borrador.articulo_id || "")}>
        ${articulos.map(
          (articulo) => html`
            <option value=${String(articulo.valor)} key=${String(articulo.valor)}>${frase(articulo.texto)}</option>
          `,
        )}
      </select>
    </div>

    <${Campo}
      id="movimiento-numero-lote"
      etiqueta=${c.libro_movimiento_lote}
      pista=${c.libro_movimiento_lote_pista}
      valor=${borrador.numero_lote}
    />

    <div className="campo-fila">
      <${Campo}
        id="movimiento-cantidad"
        etiqueta=${c.libro_movimiento_cantidad}
        pista=${c.libro_movimiento_cantidad_pista}
        tipo="numero"
        valor=${borrador.cantidad}
      />
      <div className="campo">
        <label htmlFor="movimiento-unidad">${frase(c.libro_movimiento_unidad)}</label>
        <select id="movimiento-unidad" defaultValue=${frase(borrador.unidad)}>
          <option value="">${frase(c.libro_movimiento_sin_unidad)}</option>
          ${unidades.map(
            (unidad) => html`<option value=${unidad.valor} key=${unidad.valor}>${frase(unidad.texto)}</option>`,
          )}
        </select>
      </div>
    </div>

    <${Campo}
      id="movimiento-fecha"
      etiqueta=${c.libro_movimiento_fecha}
      tipo="fecha"
      valor=${borrador.fecha}
    />

    <${Campo}
      id="movimiento-motivo"
      etiqueta=${c.libro_movimiento_motivo}
      pista=${c.libro_movimiento_motivo_pista}
      valor=${borrador.motivo}
    />

    <div className="barra-acciones">
      <button type="button" className="boton" data-accion="movimiento-guardar" disabled=${guardando}>
        ${frase(guardando ? c.libro_movimiento_guardando : c.libro_movimiento_guardar)}
      </button>
      <${Boton} etiqueta=${c.libro_volver_al_libro} accion="libro-ver" clase="boton-claro" />
    </div>
  `;
}

/** El elemento de React de esta pantalla, ya con sus propiedades puestas. */
export function pantallaDeMovimientoDeAlmacen(propiedades) {
  return html`
    <${PantallaMovimientoDeAlmacen}
      textos=${propiedades.textos}
      borrador=${propiedades.borrador}
      articulos=${propiedades.articulos}
      unidades=${propiedades.unidades}
      guardando=${propiedades.guardando}
      error=${propiedades.error}
    />
  `;
}
