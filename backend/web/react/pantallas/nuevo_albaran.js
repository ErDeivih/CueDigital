/*
 * nuevo_albaran.js — Apuntar el albarán que acaba de llegar (T09), escrita en React.
 *
 * POR QUÉ ESTA PANTALLA ES LA QUE MÁS FALTA HACÍA
 *
 * Hasta hoy, lo que entraba en el almacén se calculaba **de las facturas**, así que el día que llega
 * el camión no había dónde apuntarlo: el agricultor apuntaba la factura cuando le llegaba —a veces un
 * mes después— y hasta entonces su almacén no tenía nada. Y lo que no se podía apuntar tampoco se
 * podía decir: de qué lote era, cuándo caduca ni cuántos envases vinieron.
 *
 * Esta pantalla es la puerta del albarán, y el servidor la tiene hecha desde el primer día
 * (`POST /api/almacen/recepciones`): un albarán con sus líneas, que al guardarlo crea los lotes y las
 * entradas del libro, **una sola vez**.
 *
 * LOS TRES FINALES, QUE NO SON DOS
 *
 *  1. **Se guarda**: se dice, con lo que eso significa (la mercancía ya está en el almacén).
 *  2. **Falta un dato y se dice cuál**: el servidor contesta con su mensaje —«un albarán sin ninguna
 *     línea no apunta nada», «en esa línea no dices qué ha llegado»— y aquí se enseña tal cual. **Lo
 *     que no se hace es rellenarlo por nuestra cuenta.**
 *  3. **No se ha podido comprobar**: sin cobertura el albarán se queda apuntado en el móvil y se
 *     manda solo (con su clave de reenvío, que es lo que impide que el mismo albarán entre dos veces),
 *     y si el papel no trae número el programa **dice que no ha podido comprobar** si ya estaba.
 *
 * LO QUE NO SE HACE NUNCA
 *
 *  · **No se rellena un dato que falta.** El papel sin cantidad se apunta sin cantidad, y el almacén
 *    dirá que no puede saber lo que queda. Un 0 ahí sería afirmar que no llegó nada.
 *  · **No se calcula nada**: ni una suma, ni una conversión de unidades. Lo que se escribe se manda
 *    tal cual y el servidor decide.
 *  · **No hay ni una frase escrita aquí**: todo lo que se lee viene del servidor por propiedades.
 *
 * Los `id` de los campos (`albaran-fecha`, `albaran-0-cantidad`…) **no son decoración**: `app.js` lee
 * lo escrito por ese `id`, que es como lee esta aplicación todos sus formularios. Si uno cambia, el
 * albarán se guardaría con la línea vacía sin que salte nada.
 */

import { AvisoDeError, Boton, BotonSencillo, frase, html } from "../componentes.js";

/** Un campo de escribir, con su etiqueta, su pista y su valor de partida. */
function Campo({ id, etiqueta, pista, tipo = "texto", valor = "", filas = null }) {
  return html`
    <div className="campo">
      <label htmlFor=${id}>${frase(etiqueta)}</label>
      ${pista ? html`<p className="pista-campo">${frase(pista)}</p>` : null}
      ${
        tipo === "area"
          ? html`<textarea id=${id} rows=${filas || null} defaultValue=${frase(valor)}></textarea>`
          : tipo === "fecha"
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
 * Una línea del albarán: qué venía, cuánto, en qué se mide y de qué envase era.
 *
 * **El papel manda.** Se puede elegir el producto de la lista —es lo que hace que el almacén hable de
 * lo mismo que el resto del cuaderno— **o escribir el nombre tal y como sale en el albarán**, para lo
 * que todavía no está dado de alta. Y todo lo que no ponga el papel se deja en blanco: un dato que no
 * se sabe se apunta como que no se sabe.
 */
function Linea({ linea, indice, opciones, unidades, textos }) {
  const c = textos.cesta || {};
  const id = (nombre) => `albaran-${indice}-${nombre}`;
  return html`
    <li className="linea-albaran" data-linea=${indice}>
      <strong>${frase(linea.titulo)}</strong>
      <div className="campo">
        <label htmlFor=${id("articulo")}>${frase(c.libro_linea_que_es)}</label>
        <p className="pista-campo">${frase(c.libro_linea_que_es_pista)}</p>
        <select id=${id("articulo")} defaultValue=${frase(linea.articulo)}>
          ${(opciones || []).map(
            (opcion) => html`
              <option value=${opcion.valor} key=${opcion.valor || "libre"}>${frase(opcion.texto)}</option>
            `,
          )}
        </select>
      </div>
      <${Campo}
        id=${id("nombre")}
        etiqueta=${c.libro_linea_nombre}
        valor=${linea.nombre}
      />
      <div className="campo-fila">
        <${Campo}
          id=${id("cantidad")}
          etiqueta=${c.libro_linea_cantidad}
          pista=${c.libro_linea_cantidad_pista}
          tipo="numero"
          valor=${linea.cantidad}
        />
        <div className="campo">
          <label htmlFor=${id("unidad")}>${frase(c.libro_linea_unidad)}</label>
          <p className="pista-campo">${frase(c.libro_linea_unidad_pista)}</p>
          <select id=${id("unidad")} defaultValue=${frase(linea.unidad)}>
            <option value="">${frase(c.libro_linea_sin_unidad)}</option>
            ${(unidades || []).map(
              (unidad) => html`<option value=${unidad.valor} key=${unidad.valor}>${frase(unidad.texto)}</option>`,
            )}
          </select>
        </div>
      </div>
      <div className="campo-fila">
        <${Campo}
          id=${id("lote")}
          etiqueta=${c.libro_linea_numero_lote}
          pista=${c.libro_linea_numero_lote_pista}
          valor=${linea.numero_lote}
        />
        <${Campo}
          id=${id("caducidad")}
          etiqueta=${c.libro_linea_caducidad}
          pista=${c.libro_linea_caducidad_pista}
          tipo="fecha"
          valor=${linea.fecha_caducidad}
        />
      </div>
      <div className="campo-fila">
        <${Campo}
          id=${id("envase")}
          etiqueta=${c.libro_linea_envase}
          pista=${c.libro_linea_envase_pista}
          valor=${linea.presentacion}
        />
        <${Campo}
          id=${id("contenido")}
          etiqueta=${c.libro_linea_contenido}
          tipo="numero"
          valor=${linea.contenido_por_envase}
        />
      </div>
      <${Campo}
        id=${id("donde")}
        etiqueta=${c.libro_linea_donde}
        pista=${c.libro_linea_donde_pista}
        valor=${linea.ubicacion}
      />
      <div className="barra-acciones">
        <${BotonSencillo}
          etiqueta=${c.libro_albaran_quitar_linea}
          accion="albaran-linea-menos"
          datos=${{ indice }}
          clase="boton-claro"
        />
      </div>
    </li>
  `;
}

/**
 * La pantalla entera.
 *
 * Propiedades:
 *
 *  - `textos`: `{ cesta, acciones }` del servidor.
 *  - `borrador`: la cabecera y las líneas, tal y como están ahora mismo (lo que ya se ha escrito, para
 *    que añadir una línea o corregir algo no borre lo demás).
 *  - `opciones`: lo que se puede elegir en la lista de «¿qué ha llegado?»: sus productos, sus abonos,
 *    lo que ya está dado de alta en el almacén y la opción de escribir el nombre del papel.
 *  - `unidades`: en qué se puede medir, del catálogo del servidor (`unidades_producto`). Es una lista y
 *    no un campo libre **a propósito**: «litros» y «L» son la misma cosa, y dos formas de escribirla
 *    parten la cuenta de un envase en dos.
 *  - `guardando`: si se está mandando (el botón se apaga y lo dice: sin eso, el mismo albarán se puede
 *    mandar dos veces).
 *  - `error`: lo que ha dicho el servidor, o nada.
 */
export function PantallaNuevoAlbaran({
  textos = {},
  borrador = {},
  opciones = [],
  unidades = [],
  guardando = false,
  error = "",
}) {
  const c = textos.cesta || {};
  const lineas = borrador.lineas || [];
  return html`
    <h1>${frase(c.libro_albaran_titulo)}</h1>
    <p className="pista">${frase(c.libro_albaran_explica)}</p>
    <${AvisoDeError} texto=${error} />

    <${Campo}
      id="albaran-fecha"
      etiqueta=${c.libro_fecha_albaran}
      tipo="fecha"
      valor=${borrador.fecha}
    />
    <${Campo}
      id="albaran-proveedor"
      etiqueta=${c.libro_proveedor}
      valor=${borrador.proveedor}
    />
    <${Campo}
      id="albaran-numero"
      etiqueta=${c.libro_numero_albaran}
      pista=${c.libro_numero_albaran_pista}
      valor=${borrador.numero_albaran}
    />

    <h2>${frase(c.libro_lineas)}</h2>
    <ul className="lista">
      ${lineas.map(
        (linea, indice) => html`
          <${Linea}
            key=${indice}
            linea=${linea}
            indice=${indice}
            opciones=${opciones}
            unidades=${unidades}
            textos=${textos}
          />
        `,
      )}
    </ul>
    <${BotonSencillo}
      etiqueta=${c.libro_albaran_anadir_linea}
      accion="albaran-linea-mas"
      clase="boton-claro"
    />

    <${Campo}
      id="albaran-notas"
      etiqueta=${c.libro_notas_albaran}
      tipo="area"
      filas="3"
      valor=${borrador.notas}
    />

    <div className="barra-acciones">
      <button type="button" className="boton" data-accion="albaran-guardar" disabled=${guardando}>
        ${frase(guardando ? c.libro_albaran_guardando : c.libro_albaran_guardar)}
      </button>
      <${Boton} etiqueta=${c.libro_volver_al_libro} accion="libro-ver" clase="boton-claro" />
    </div>
  `;
}

/** El elemento de React de esta pantalla, ya con sus propiedades puestas. */
export function pantallaDeNuevoAlbaran(propiedades) {
  return html`
    <${PantallaNuevoAlbaran}
      textos=${propiedades.textos}
      borrador=${propiedades.borrador}
      opciones=${propiedades.opciones}
      unidades=${propiedades.unidades}
      guardando=${propiedades.guardando}
      error=${propiedades.error}
    />
  `;
}
