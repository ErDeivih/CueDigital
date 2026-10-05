/*
 * libro_del_almacen.js — «El libro del almacén» (T09), escrita en React.
 *
 * POR QUÉ ESTA PANTALLA, Y POR QUÉ ES OTRA PANTALLA DE ALMACÉN
 *
 * «Lo que tengo en el almacén» (`cesta.js`) contesta a la pregunta de todos los días —«¿me queda
 * producto para tratar la parcela?»— con lo comprado menos lo echado, y **no se toca**: lleva ahí
 * desde el principio. Lo que no se podía contestar era lo que pide una inspección y lo que pide el
 * contrato del CRM:
 *
 *   · **de qué lote salió** lo que se echó (si el fabricante avisa de una partida, ¿dónde se fue?);
 *   · **qué entró de verdad**, que no es lo mismo que lo que se compró: la mercancía entra el día
 *     que llega el camión, y eso lo dice el albarán, no la factura;
 *   · **qué se perdió o se contó distinto**, que no es ni un gasto ni una compra.
 *
 * El servidor de eso ya estaba hecho y verificado (`routers/almacen_api.py`). Lo que faltaba era la
 * puerta: hoy el agricultor no puede recibir un albarán desde el móvil ni mirar el libro.
 *
 * LO QUE ESTE COMPONENTE NO HACE, Y ES LO MÁS IMPORTANTE DEL FICHERO
 *
 *  1. **No calcula nada.** Ni un saldo, ni una resta, ni un total: los números —lo que queda, lo que
 *     entró, lo que salió, cuánto por hectárea— los calcula el servidor y llegan ya contados, con su
 *     etiqueta. Lo único que hace `app.js` es preparar las filas y pasar los textos del servidor.
 *  2. **Un dato que no se sabe no es un cero.** Un lote del que no consta la cantidad, o del que no
 *     se sabe en qué se mide, sale con su frase («No se puede saber lo que queda») y su motivo, nunca
 *     con un 0. Y una caducidad que no se ha mirado no se pinta como «en fecha»: son tres estados
 *     —caducado, en fecha y no se sabe— y los tres se dicen distintos.
 *  3. **Lo comprado que todavía no ha entrado se enseña aparte** y no se suma a las existencias, para
 *     que nadie crea que el programa le ha perdido el producto.
 *  4. **No hay ni una frase escrita aquí**: todo lo que se lee viene del servidor (`textos.py`) por
 *     propiedades, y las frases que llevan un número o un nombre dentro las monta `app.js`.
 *
 * El componente es PURO: no llama a `fetch`, no lee `localStorage` y no toca el DOM.
 */

import { AvisoDeError, Boton, Botones, frase, html } from "../componentes.js";

/**
 * Una fila de «lo que ha llegado»: el albarán, dicho en una línea, y el botón que lo abre.
 *
 * El número y el proveedor van arriba y la cuenta de lo que trajo debajo, que es el orden de siempre
 * en las listas de esta aplicación: lo importante primero, el detalle después. Y si el albarán está
 * anulado se dice **con palabras** además de en su etiqueta: el color solo no informa.
 */
function FichaDeUnAlbaran({ albaran, textos }) {
  const c = textos.cesta || {};
  return html`
    <li>
      <div className="apunte-cabecera">
        <strong>${frase(albaran.titulo)}</strong>
        <span>${frase(albaran.cuando)}</span>
      </div>
      ${albaran.proveedor ? html`<div className="apunte-detalle">${frase(albaran.proveedor)}</div>` : null}
      ${albaran.detalle ? html`<div className="apunte-detalle">${frase(albaran.detalle)}</div>` : null}
      ${
        albaran.anulado
          ? html`<span className="etiqueta-estado etiqueta-estado-mirar">${frase(albaran.anulado)}</span>`
          : null
      }
      ${
        // Un albarán sin número no se puede reconocer, así que el programa **no puede comprobar** si ya
        // estaba apuntado. Eso se dice aquí, en su fila, y no se calla: «no lo he podido comprobar» no
        // es «no estaba».
        albaran.aviso ? html`<p className="pista-campo">${frase(albaran.aviso)}</p>` : null
      }
      <div className="barra-acciones">
        <${Boton}
          etiqueta=${c.libro_abrir_albaran}
          accion="albaran-abrir"
          datos=${{ id: albaran.id }}
          clase="boton-claro"
        />
      </div>
    </li>
  `;
}

/**
 * Un envase (un lote), con su número, su caducidad, lo que queda y **su desglose**.
 *
 * Lo que hace útil esta ficha es la última parte: los movimientos de ese envase, uno debajo de otro.
 * Es lo que contesta a «¿y estos litros de dónde salen?» sin salir de la pantalla, y cada movimiento
 * dice **si cuenta o no y por qué** (un movimiento anulado, o cuyo apunte está anulado, sigue en el
 * libro pero no entra en la cuenta).
 */
function FichaDeUnLote({ lote, textos }) {
  const c = textos.cesta || {};
  return html`
    <li>
      <div className="apunte-cabecera">
        <strong>${frase(lote.titulo)}</strong>
        ${lote.estado ? html`<span className="etiqueta-estado etiqueta-estado-${lote.estado.tipo}">${frase(lote.estado.texto)}</span>` : null}
      </div>
      ${lote.pista ? html`<p className="pista-campo">${frase(lote.pista)}</p>` : null}
      <dl>
        <div className="resumen-dato">
          <dt>${frase(c.libro_caducidad)}</dt>
          <dd>${frase(lote.caducidad)}</dd>
        </div>
        ${
          // **Lo que queda, y el motivo cuando no se sabe.** Es la fila que se viene a mirar: si el
          // saldo no se puede calcular, aquí va la frase del servidor con su porqué, nunca un 0.
          html`
            <div className="resumen-dato resumen-destacado">
              <dt>${frase(c.libro_queda)}</dt>
              <dd><span className="dato-grande">${frase(lote.queda)}</span></dd>
            </div>
          `
        }
        ${(lote.filas || []).map(
          (fila, indice) => html`
            <div className="resumen-dato" key=${indice}>
              <dt>${frase(fila.etiqueta)}</dt>
              <dd>${frase(fila.valor)}</dd>
            </div>
          `,
        )}
      </dl>
      ${
        // Los avisos del envase, cada uno en su franja: el motivo cuando no se puede saber lo que queda
        // (o cuando sale en negativo), que la caducidad no se ha mirado —no es que no caduque— y que
        // este envase está pasado de fecha. Los tres son «algo que hay que mirar», y en esta aplicación
        // eso va con su señal y con palabras.
        (lote.avisos || []).map(
          (aviso, indice) => html`
            <p className="tarjeta-aviso" key=${indice}>
              <span className="tarjeta-aviso-icono" aria-hidden="true">!</span>
              ${frase(aviso)}
            </p>
          `,
        )
      }
      <${DesgloseDelLote} movimientos=${lote.movimientos} textos=${textos} />
      <${Botones} botones=${lote.acciones} />
    </li>
  `;
}

/** Los movimientos de un envase, en su lista pequeña. Sin movimientos se dice, no se deja el hueco. */
function DesgloseDelLote({ movimientos = [], textos }) {
  const c = textos.cesta || {};
  if (!movimientos.length) return html`<p className="pista-campo">${frase(c.libro_sin_movimientos)}</p>`;
  return html`
    <ul className="lista">
      ${movimientos.map(
        (movimiento, indice) => html`
          <li key=${indice}>
            <div className="apunte-detalle">${frase(movimiento.texto)}</div>
            ${
              movimiento.no_cuenta
                ? html`<div className="apunte-detalle">${frase(c.libro_no_cuenta)}: ${frase(movimiento.no_cuenta)}</div>`
                : null
            }
          </li>
        `,
      )}
    </ul>
  `;
}

/**
 * Un artículo del almacén: lo que queda en total, sus cuentas y **sus envases uno por uno**.
 *
 * Las cuatro cuentas (entró, salió, se perdió, conteo distinto) solo se enseñan si hay algo apuntado:
 * una lista de ceros no dice nada y hace creer que el programa ha contado algo que nadie ha apuntado.
 * El saldo del artículo **no se suma** si sus envases están en unidades que no se pueden comparar: en
 * ese caso el servidor manda el motivo y aquí se enseña.
 */
function FichaDeUnArticulo({ articulo, textos }) {
  const c = textos.cesta || {};
  return html`
    <li>
      <div className="apunte-cabecera">
        <strong>${frase(articulo.nombre)}</strong>
        <span>${frase(articulo.categoria)}</span>
      </div>
      <dl>
        <div className="resumen-dato resumen-destacado">
          <dt>${frase(c.libro_queda)}</dt>
          <dd><span className="dato-grande">${frase(articulo.queda)}</span></dd>
        </div>
        ${(articulo.filas || []).map(
          (fila, indice) => html`
            <div className="resumen-dato" key=${indice}>
              <dt>${frase(fila.etiqueta)}</dt>
              <dd>${frase(fila.valor)}</dd>
            </div>
          `,
        )}
      </dl>
      ${
        articulo.motivo
          ? html`
              <p className="tarjeta-aviso">
                <span className="tarjeta-aviso-icono" aria-hidden="true">!</span>
                ${frase(articulo.motivo)}
              </p>
            `
          : null
      }
      <h3>${frase(c.libro_lotes_de)}</h3>
      ${
        articulo.lotes.length
          ? html`<ul className="lista">
              ${articulo.lotes.map(
                (lote, indice) => html`<${FichaDeUnLote} key=${indice} lote=${lote} textos=${textos} />`,
              )}
            </ul>`
          : html`<p className="pista-campo">${frase(c.libro_sin_lotes)}</p>`
      }
      <${Botones} botones=${articulo.acciones} />
    </li>
  `;
}

/** Un movimiento del libro: qué pasó, de qué era, cuánto y de dónde viene. */
function FilaDeUnMovimiento({ movimiento, textos }) {
  const c = textos.cesta || {};
  return html`
    <li>
      <div className="apunte-cabecera">
        <strong>${frase(movimiento.titulo)}</strong>
        <span>${frase(movimiento.cuando)}</span>
      </div>
      ${movimiento.detalle ? html`<div className="apunte-detalle">${frase(movimiento.detalle)}</div>` : null}
      ${movimiento.motivo ? html`<div className="apunte-detalle">${frase(movimiento.motivo)}</div>` : null}
      ${
        // Un movimiento anulado —o cuyo apunte está anulado— **sigue en el libro** (nada se borra) pero
        // no entra en la cuenta. Sin esta línea, una resta que no cuadra a ojo sería inexplicable.
        movimiento.no_cuenta
          ? html`<p className="pista-campo">${frase(c.libro_no_cuenta)}: ${frase(movimiento.no_cuenta)}</p>`
          : null
      }
    </li>
  `;
}

/**
 * La pantalla entera.
 *
 * Propiedades (todas preparadas por `app.js`, que es quien conoce los datos):
 *
 *  - `textos`: `{ cesta, acciones, facturas }`, tal y como los sirve `/api/interfaz`. Las palabras del
 *    libro viven dentro del bloque del almacén (`cesta`), y el porqué está escrito en `textos.py`.
 *  - `albaranes`: lo que ha llegado, ya contado y con su botón de abrir.
 *  - `articulos`: las existencias por artículo y por envase, con lo que queda en cada uno.
 *  - `movimientos`: el libro, movimiento a movimiento.
 *  - `compras`: lo que está comprado por factura y **todavía no ha entrado**, con su frase.
 *  - `resumen_albaranes` / `resumen_articulos`: cuántos hay, en singular o en plural.
 *  - `error`: lo que ha dicho el servidor cuando algo ha fallado, o nada.
 *  - `cargando`: si se están buscando los datos (la pantalla se abre sola y avisa).
 *  - `acciones`: los botones del pie (volver).
 */
export function PantallaLibroDelAlmacen({
  textos = {},
  albaranes = [],
  articulos = [],
  movimientos = [],
  compras = { hay: false, filas: [] },
  resumen_albaranes = "",
  resumen_articulos = "",
  error = "",
  cargando = false,
  acciones = [],
}) {
  const c = textos.cesta || {};
  return html`
    <h1>${frase(c.libro_titulo)}</h1>
    <p className="pista">${frase(c.libro_explica)}</p>
    <p className="pista-campo">${frase(c.libro_como_funciona)}</p>
    <${AvisoDeError} texto=${error} />
    ${
      // Mientras se buscan los datos se dice, en vez de enseñar una pantalla vacía que parece un
      // almacén sin nada.
      cargando ? html`<div className="aviso">${frase(c.libro_cargando)}</div>` : null
    }

    <h2>${frase(c.libro_recepciones)}</h2>
    ${
      // Cuántos albaranes hay, con su palabra: «Tienes 1 albaranes apuntados» es lo primero que hace
      // desconfiar de un programa (el singular lo elige el servidor con `con_cuenta`).
      resumen_albaranes ? html`<p className="cuantas">${frase(resumen_albaranes)}</p>` : null
    }
    ${
      albaranes.length
        ? html`
            <ul className="lista">
              ${albaranes.map(
                (albaran, indice) => html`<${FichaDeUnAlbaran} key=${indice} albaran=${albaran} textos=${textos} />`,
              )}
            </ul>
          `
        : html`<p className="pista-campo">${frase(c.libro_recepciones_vacio)}</p>`
    }
    <${Boton}
      etiqueta=${c.libro_nuevo_albaran}
      pista=${c.libro_nuevo_albaran_pista}
      icono="📋"
      accion="albaran-nuevo"
    />

    <h2>${frase(c.libro_existencias_titulo)}</h2>
    <p className="pista-campo">${frase(c.libro_existencias_pista)}</p>
    ${
      // **Lo comprado que todavía no ha entrado.** Va aquí, delante de las existencias y aparte de
      // ellas: es la respuesta a «¿por qué mi almacén sale vacío si yo he comprado?», y sin ella el
      // silencio parecería que el programa ha perdido el producto. No se suma nunca a lo que queda.
      compras.hay
        ? html`
            <div className="aviso">
              <p><strong>${frase(compras.texto)}</strong></p>
              <ul className="lista">
                ${compras.filas.map(
                  (fila, indice) => html`<li key=${indice}>${frase(fila.detalle)}</li>`,
                )}
              </ul>
            </div>
          `
        : null
    }
    ${resumen_articulos ? html`<p className="cuantas">${frase(resumen_articulos)}</p>` : null}
    ${
      articulos.length
        ? html`
            <ul className="lista">
              ${articulos.map(
                (articulo, indice) => html`<${FichaDeUnArticulo} key=${indice} articulo=${articulo} textos=${textos} />`,
              )}
            </ul>
          `
        : html`<div className="aviso">${frase(c.libro_sin_articulos)}</div>`
    }

    <h2>${frase(c.libro_movimientos_titulo)}</h2>
    <p className="pista-campo">${frase(c.libro_movimientos_pista)}</p>
    ${
      movimientos.length
        ? html`
            <ul className="lista">
              ${movimientos.map(
                (movimiento, indice) => html`<${FilaDeUnMovimiento} key=${indice} movimiento=${movimiento} textos=${textos} />`,
              )}
            </ul>
          `
        : html`<p className="pista-campo">${frase(c.libro_sin_movimientos_ninguno)}</p>`
    }

    <div className="ayuda-campo">
      <p><strong>${frase(c.libro_para_que)}</strong></p>
    </div>
    <${Boton} etiqueta=${c.libro_ver_la_cesta} accion="cesta-ver" clase="boton-claro" />
    <${Botones} botones=${acciones} />
  `;
}

/** El elemento de React de esta pantalla, ya con sus propiedades puestas. */
export function pantallaDelLibroDelAlmacen(propiedades) {
  return html`
    <${PantallaLibroDelAlmacen}
      textos=${propiedades.textos}
      albaranes=${propiedades.albaranes}
      articulos=${propiedades.articulos}
      movimientos=${propiedades.movimientos}
      compras=${propiedades.compras}
      resumen_albaranes=${propiedades.resumen_albaranes}
      resumen_articulos=${propiedades.resumen_articulos}
      error=${propiedades.error}
      cargando=${propiedades.cargando}
      acciones=${propiedades.acciones}
    />
  `;
}
