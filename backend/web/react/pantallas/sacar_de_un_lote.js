/*
 * sacar_de_un_lote.js — Sacar del almacén lo que se gastó en un apunte (T09), escrita en React.
 *
 * POR QUÉ ESTA PANTALLA, Y POR QUÉ NO PUEDE SER UN BOTÓN MÁS
 *
 * Un tratamiento o un abono descuentan del almacén **solo** por aquí: el apunte dice cuánto se gastó, y
 * aquí se dice de qué envase salió. Esa unión es lo que permite contestar la única pregunta que importa
 * cuando el fabricante avisa de una partida —«¿esto dónde se fue?»— y lo que permite **revertirlo**: si
 * un día se anula el tratamiento, su salida deja de contar sola, sin tocar el libro.
 *
 * LAS DOS CUENTAS NO SE MEZCLAN, Y ESO ES EL CORAZÓN DE ESTA PANTALLA
 *
 * *Dos litros* puede ser lo que se echa en cada hectárea o el total que se ha gastado, y confundirlos es
 * un error de diez veces. Por eso la cantidad **la dice el apunte** (el servidor la copia, no se teclea
 * otra vez: teclearla es la forma de que un día digan cosas distintas) y por eso, cuando el apunte solo
 * trae lo que se echa por hectárea, el programa **pide el total en vez de multiplicarlo por su cuenta**.
 * Y en el resultado salen las dos, cada una con su nombre.
 *
 * LOS TRES FINALES DE SIEMPRE, EN ESTA PANTALLA
 *
 *  · **Se apunta**: y se dice qué se ha sacado, con su total y su por hectárea.
 *  · **Falta un dato y se dice cuál**: el apunte sin cantidad total (el servidor contesta qué pasa y
 *    aquí se pone el campo para escribirla).
 *  · **No se puede hacer sin preguntar**: si lo que sale deja el envase en negativo, se avisa con los
 *    números —lo que queda y lo que se saca— y el agricultor decide: corregirlo, o decir que la
 *    diferencia es de verdad. Lo que no se hace **nunca** es apuntarlo a escondidas ni impedirle
 *    registrar lo que pasó.
 *
 * Y lo que no se sabe, no se inventa: un envase del que no consta lo que queda se puede elegir igual,
 * diciendo que no se sabe. Ni una frase escrita aquí: todo llega por propiedades.
 */

import { AvisoDeError, Boton, Botones, frase, html } from "../componentes.js";

/** Un envase del que se puede sacar, con lo que queda y su botón. */
function EnvaseDelQueSacar({ lote, textos }) {
  const c = textos.cesta || {};
  return html`
    <li>
      <div className="apunte-cabecera">
        <strong>${frase(lote.titulo)}</strong>
        ${lote.estado ? html`<span className="etiqueta-estado etiqueta-estado-${lote.estado.tipo}">${frase(lote.estado.texto)}</span>` : null}
      </div>
      <div className="apunte-detalle">${frase(c.libro_caducidad)}: ${frase(lote.caducidad)}</div>
      <div className="apunte-detalle">${frase(c.libro_queda)}: ${frase(lote.queda)}</div>
      ${
        lote.motivo
          ? html`
              <p className="tarjeta-aviso">
                <span className="tarjeta-aviso-icono" aria-hidden="true">!</span>
                ${frase(lote.motivo)}
              </p>
            `
          : null
      }
      <div className="barra-acciones">
        <${Boton}
          etiqueta=${c.libro_salida_lote}
          accion="salida-guardar"
          datos=${{ lote: lote.lote_id }}
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
 *  - `apunte`: de qué apunte sale esto (un título y su detalle: la fecha, dónde se hizo y qué se echó),
 *    para que el agricultor vea que está sacando del almacén **lo que apuntó**, y no otra cosa.
 *  - `articulos`: los envases que pueden ser los de ese producto —los del artículo que el apunte
 *    engancha— con lo que queda en cada uno. Vacío es «de esto no hay nada en el almacén», y entonces
 *    la pantalla lo dice con su salida (apuntar el albarán cuando llegue).
 *  - `pidiendo_cantidad`: el identificador del envase que se estaba eligiendo cuando el apunte solo trae
 *    lo que se echa por hectárea. Es «hay que escribir el total» y, a la vez, de qué envase era.
 *  - `descuadre`: si lo que sale deja el envase en negativo, el aviso del servidor (con los números
 *    dentro) y, aparte, el envase del que se estaba sacando.
 *  - `resultado`: lo que ha quedado apuntado, con **el total y lo que va por hectárea, cada uno con su
 *    nombre**. Es lo que hace imposible confundir los dos números.
 *  - `aviso`: lo que se dice cuando el apunte se ha quedado en el móvil por no haber cobertura.
 *  - `error`: lo que ha dicho el servidor, o nada.
 */
export function PantallaSacarDeUnLote({
  textos = {},
  apunte = {},
  articulos = [],
  pidiendo_cantidad = null,
  descuadre = "",
  lote_del_descuadre = null,
  resultado = null,
  avisos = [],
  aviso = "",
  error = "",
  guardando = false,
  cargando = false,
}) {
  const c = textos.cesta || {};
  return html`
    <h1>${frase(c.libro_salida_titulo)}</h1>
    <p className="pista">${frase(c.libro_salida_explica)}</p>
    <${AvisoDeError} texto=${error} />
    <div className="ayuda-campo">
      <p><strong>${frase(apunte.titulo)}</strong></p>
      <p>${frase(apunte.detalle)}</p>
    </div>
    ${aviso ? html`<div className="aviso">${frase(aviso)}</div>` : null}
    ${
      // Mientras se busca lo que hay en el almacén se dice: elegir un envase de una lista vacía parece
      // que no hay nada, y no es eso.
      cargando ? html`<div className="aviso">${frase(c.libro_cargando)}</div>` : null
    }
    ${(avisos || []).map(
      (suyo, indice) => html`<div className="aviso" key=${indice}>${frase(suyo)}</div>`,
    )}

    ${
      resultado
        ? html`
            <div className="aviso">
              <p><strong>${frase(c.libro_salida_guardada)}</strong></p>
            </div>
            <dl>
              ${
                // **El total, y lo que va por hectárea, cada uno con su nombre.** Es la decisión que
                // sostiene toda esta pantalla: dos litros por hectárea no son dos litros gastados, y
                // juntarlos sin decir cuál es cuál es el error de diez veces que hay que evitar.
                html`
                  <div className="resumen-dato resumen-destacado">
                    <dt>${frase(c.libro_salida_total)}</dt>
                    <dd><span className="dato-grande">${frase(resultado.total)}</span></dd>
                  </div>
                `
              }
              ${(resultado.filas || []).map(
                (fila, indice) => html`
                  <div className="resumen-dato" key=${indice}>
                    <dt>${frase(fila.etiqueta)}</dt>
                    <dd>${frase(fila.valor)}</dd>
                  </div>
                `,
              )}
            </dl>
            <p className="pista-campo">${frase(c.libro_salida_total_pista)}</p>
            <${Botones} botones=${resultado.acciones} />
          `
        : html`
            <h2>${frase(c.libro_salida_de_que_lote)}</h2>
            ${
              articulos.length
                ? articulos.map(
                    (articulo, indice) => html`
                      <div key=${indice}>
                        <h3>${frase(articulo.nombre)}</h3>
                        <ul className="lista">
                          ${articulo.lotes.map(
                            (lote, otro) => html`
                              <${EnvaseDelQueSacar} key=${otro} lote=${lote} textos=${textos} />
                            `,
                          )}
                        </ul>
                      </div>
                    `,
                  )
                : html`
                    <div className="aviso">${frase(c.libro_sin_articulos_de_eso)}</div>
                    <${Boton} etiqueta=${c.libro_ver_el_libro} accion="libro-ver" clase="boton-claro" />
                  `
            }
            ${
              // El apunte solo trae lo que se echa por hectárea: se pide el total, con su explicación, y
              // se manda con la misma puerta (el botón lleva el envase que se estaba eligiendo).
              pidiendo_cantidad
                ? html`
                    <div className="campo">
                      <label htmlFor="salida-cantidad">${frase(c.libro_salida_cantidad)}</label>
                      <p className="pista-campo">${frase(c.libro_salida_cantidad_pista)}</p>
                      <input id="salida-cantidad" type="text" inputMode="decimal" />
                    </div>
                    <div className="barra-acciones">
                      <button
                        type="button"
                        className="boton"
                        data-accion="salida-guardar"
                        data-lote=${pidiendo_cantidad}
                        disabled=${guardando}
                      >
                        ${frase(c.libro_movimiento_guardar)}
                      </button>
                    </div>
                  `
                : null
            }
            ${
              // El envase se quedaría en negativo: se dice con los números (el mensaje del servidor los
              // trae) y se dan las dos salidas. La tercera —apuntar la entrada que falta— la explica el
              // propio mensaje, y se hace desde el libro.
              descuadre
                ? html`
                    <div className="aviso aviso-error">${frase(descuadre)}</div>
                    <div className="barra-acciones">
                      <${Boton}
                        etiqueta=${c.libro_salida_descuadre_si}
                        accion="salida-descuadre-si"
                        datos=${{ lote: lote_del_descuadre }}
                        clase="boton-peligro"
                      />
                      <${Boton} etiqueta=${c.libro_salida_corregir} accion="libro-ver" clase="boton-claro" />
                    </div>
                  `
                : null
            }
            <${Botones} botones=${apunte.acciones} />
          `
    }
  `;
}

/** El elemento de React de esta pantalla, ya con sus propiedades puestas. */
export function pantallaDeSacarDeUnLote(propiedades) {
  return html`
    <${PantallaSacarDeUnLote}
      textos=${propiedades.textos}
      apunte=${propiedades.apunte}
      articulos=${propiedades.articulos}
      pidiendo_cantidad=${propiedades.pidiendo_cantidad}
      descuadre=${propiedades.descuadre}
      lote_del_descuadre=${propiedades.lote_del_descuadre}
      resultado=${propiedades.resultado}
      avisos=${propiedades.avisos}
      aviso=${propiedades.aviso}
      error=${propiedades.error}
      guardando=${propiedades.guardando}
      cargando=${propiedades.cargando}
    />
  `;
}
