/*
 * mis_cosas.js — «Mis parcelas, productos y máquinas», escrita en React.
 *
 * POR QUÉ ESTA PANTALLA
 *
 * Es la tercera que se pasa a React (después de la de inicio y la de confirmación) y es la primera
 * que **enseña listas**: las siete secciones de lo que el agricultor tiene dado de alta —parcelas,
 * productos, abonos, aplicadores, asesores, máquinas y naves— más los cuatro atajos de abajo
 * (papeles, lo que tengo en el almacén, lo que hay sembrado y los grupos de parcelas).
 *
 * No tiene ni un campo que leer del DOM: es una pantalla de mirar y pulsar, y por eso se puede pasar
 * sin tocar nada de cómo se guardan los datos.
 *
 * **Lo que NO hace este componente, a propósito:** no sabe nada de `estado` ni de la API. La pantalla
 * recibe las secciones **ya preparadas** (`{tipo, titulo, pista, vacio, anadir, elementos}`), y quien
 * las prepara es `app.js`, que es quien tiene los datos del agricultor. Así el componente se puede
 * probar sin navegador y sin servidor, y el día que los datos vengan de otro sitio no hay que tocar
 * la pantalla.
 *
 * Los textos siguen viniendo del servidor (`textos.py` por `/api/interfaz`): el título, la
 * explicación, el aviso de «aquí todavía no hay nada», la palabra del botón de añadir y los cuatro
 * atajos. Aquí no hay ni una frase escrita a mano.
 *
 * LO QUE CAMBIÓ CON EL REDISEÑO (ronda 78)
 *
 * La sección de las tierras era **un muro de renglones iguales**: con cincuenta y una tierras dadas de
 * alta, «El Prado · 4,90 ha · secano» y «El Vallejo · 4,90 ha · secano» se leen igual, y no había nada
 * que hacer con ellos. Ahora esa sección sale con la pieza de la tarjeta
 * (`piezas/tarjeta.js`, ver `docs/stitch/rediseno/mis_tierras.png`): la forma de la tierra
 * como se ve en el SIGPAC, su pueblo, su referencia oficial y **lo que tiene sembrado este año** —y, si
 * le falta decirlo, el aviso y el camino para arreglarlo **dentro de la tarjeta**—. Tocar una tarjeta
 * abre lo que hay sembrado en esa tierra, que es lo único que se puede hacer con ella desde aquí.
 *
 * Las otras seis secciones se quedan como estaban: son listas de diez o doce cosas y se leen de un
 * tirón. Una tarjeta para cada abono sería más ruido que ayuda, y el rediseño no pide eso.
 */

import { Boton, DibujoDeLaParcela, frase, html } from "../componentes.js";
import { Tarjeta } from "../piezas/tarjeta.js";
import { AccionesDeUnaFicha } from "../piezas/acciones_de_una_ficha.js";
import { Tabla } from "../piezas/tabla.js";

/**
 * Una sección: su título, su explicación, lo que hay dentro y el botón de añadir.
 *
 * El aviso de que no hay nada **no es un adorno**: un agricultor que entra por primera vez ve siete
 * secciones vacías, y sin una frase que le diga qué va ahí no sabe si el programa está roto o si es
 * que todavía no ha apuntado nada.
 *
 * **Dos formas de lista, y la diferencia importa** (rediseño de la ronda 78). La sección de las tierras
 * puede venir con `tarjetas: true`, y entonces cada elemento es ya lo que espera `Tarjeta`: la
 * forma de la tierra en el SIGPAC, su pueblo y sus datos **con el nombre delante**. Con cincuenta y una
 * tierras, una lista de renglones iguales no se lee. Las demás secciones —productos, abonos, quién
 * aplica, máquinas— siguen con su lista de renglones: son diez o doce, se leen de un tirón, y una
 * tarjeta para cada una sería más ruido que ayuda.
 */
function Seccion({ seccion }) {
  return html`
    <h2>${frase(seccion.titulo)}</h2>
    <p className="pista-campo">${frase(seccion.pista)}</p>
    ${seccion.cuantas ? html`<p className="cuantas">${frase(seccion.cuantas)}</p>` : null}
    ${
      // ***El puente a la vista completa*** (21/10/2026, D04): *la pantalla de `#/tierras/mapa` **no tenia puerta**:
      // solo se llegaba escribiendo la direccion. Se pasa desde la lista, que es donde el agricultor se pregunta
      // «y esto, ¿donde esta?». **No es una segunda puerta**: es el camino a la canonica.*
      seccion.verEnElMapa
        ? html`<p className="barra-acciones">
            <${Boton} etiqueta=${seccion.verEnElMapa} accion="tierras-al-mapa" clase="boton-claro" />
          </p>`
        : null
    }
    ${seccion.buscar || null}
    ${
      // **La tabla, solo en el ordenador** (30/09/2026). Es la misma lista de tierras que las tarjetas de
      // abajo y con los mismos botones: el CSS enseña una u otra según el ancho (`solo-escritorio` /
      // `solo-movil`). Con 64 tierras, en una pantalla ancha lo que se quiere es verlas de arriba abajo y
      // comparar las hectáreas; en el móvil, la tarjeta de siempre.
      seccion.tabla && seccion.elementos.length
        ? html`<div className="solo-escritorio"><${Tabla} tabla=${seccion.tabla} /></div>`
        : null
    }
    ${
      seccion.elementos.length
        ? seccion.tarjetas
          ? html`
              <div className="tarjetas solo-movil">
                ${seccion.elementos.map(
                  (tierra, indice) =>
                    html`
                      <div className="tarjeta-con-acciones" key=${indice}>
                        <${Tarjeta}
                          etiqueta=${tierra.etiqueta}
                          rotulo=${tierra.rotulo}
                          lineas=${tierra.lineas}
                          filas=${tierra.filas}
                          dibujo=${tierra.dibujo}
                          avisos=${tierra.avisos}
                          pendiente=${tierra.pendiente}
                          accionTexto=${tierra.accionTexto}
                          marca=${tierra.marca}
                          elegida=${tierra.elegida}
                          accion=${tierra.accion}
                          datos=${tierra.datos}
                          textos=${tierra.textos}
                        />
                        ${
                          // **CORREGIR y BORRAR la tierra** (ronda 92), debajo de su tarjeta y con la
                          // misma pieza que en todas las listas. Van fuera de la tarjeta porque la
                          // tarjeta **hace otra cosa** (desde el 07/10/2026, abrir la ficha de esa tierra:
                          // lo mismo que hace la fila en el ordenador).
                          //
                          // **Y aquí no sale el botón de «su historia»**: en el móvil la tarjeta entera
                          // abre ya esa ficha, así que un botón que hace lo mismo justo debajo sobra. En
                          // el panel del ordenador sí sigue estando, porque allí la fila abre el panel y
                          // el botón es la forma de entrar. Por eso se quita **aquí** y no en la lista de
                          // acciones.
                          html`<${AccionesDeUnaFicha}
                            acciones=${(tierra.acciones || []).filter(
                              (una) => una.accion !== "tierra-historia",
                            )}
                          />`
                        }
                      </div>
                    `,
                )}
              </div>
            `
          : html`
              <ul className="lista solo-movil">
                ${seccion.elementos.map(
                  (elemento, indice) => html`
                    <li key=${indice}>
                      <strong>${frase(elemento.nombre)}</strong>
                      ${
                        elemento.detalle
                          ? html`<div className="apunte-detalle">${frase(elemento.detalle)}</div>`
                          : null
                      }
                      <${DibujoDeLaParcela}
                        dibujo=${elemento.dibujo}
                        etiqueta=${seccion.etiquetaDelDibujo}
                      />
                      ${
                        // **Y sus dos botones** (ronda 93): las fichas de lo que se usa —productos,
                        // abonos, quién aplica, asesores, máquinas y naves— se corrigen y se borran
                        // igual que las tierras. Un abono apuntado con la riqueza equivocada se
                        // arregla aquí, sin borrarlo y volverlo a escribir.
                        html`<${AccionesDeUnaFicha} acciones=${elemento.acciones} />`
                      }
                    </li>
                  `,
                )}
              </ul>
            `
        : seccion.sinResultados
          ? html`
              <div className="aviso">
                <p>${frase(seccion.sinResultados.texto)}</p>
                ${
                  seccion.sinResultados.pista
                    ? html`<p className="pista-campo">${frase(seccion.sinResultados.pista)}</p>`
                    : null
                }
              </div>
              <${Boton}
                etiqueta=${seccion.sinResultados.boton.etiqueta}
                accion=${seccion.sinResultados.boton.accion}
                clase=${seccion.sinResultados.boton.clase}
              />
            `
          : html`<p className="pista-campo">${frase(seccion.vacio)}</p>`
    }
    <${Boton}
      etiqueta=${seccion.anadir}
      accion="anadir-maestro"
      datos=${{ tipo: seccion.tipo }}
      clase="boton-claro"
    />
  `;
}

/** Un atajo de los de abajo: un título, su explicación y un botón para entrar. */
function Atajo({ atajo }) {
  return html`
    <h2>${frase(atajo.titulo)}</h2>
    <p className="pista-campo">${frase(atajo.explica)}</p>
    <${Boton} etiqueta=${atajo.titulo} icono=${atajo.icono} accion=${atajo.accion} clase="boton-claro" />
  `;
}

/**
 * La pantalla entera.
 *
 * Propiedades:
 *
 *  - `textos`: `{ maestros, acciones }`, tal y como los sirve `/api/interfaz`.
 *  - `secciones`: las siete secciones, ya preparadas por `app.js`. Cada una lleva `{tipo, titulo,
 *    pista, vacio, anadir, elementos}` y, si es la de las tierras, además `cuantas` (la frase que dice
 *    cuántas hay) y `tarjetas: true`, con los elementos ya en la forma que espera `Tarjeta`.
 *  - `atajos`: los cuatro de abajo (papeles, almacén, sembrado y grupos).
 */
export function PantallaMisCosas({ textos = {}, secciones = [], atajos = [] }) {
  const maestros = textos.maestros || {};
  const acciones = textos.acciones || {};

  return html`
    <h1>${frase(maestros.titulo)}</h1>
    <p className="pista">${frase(maestros.intro)}</p>
    ${secciones.map((seccion) => html`<${Seccion} key=${seccion.tipo} seccion=${seccion} />`)}
    ${atajos.map((atajo) => html`<${Atajo} key=${atajo.accion} atajo=${atajo} />`)}
    <button type="button" className="boton" data-accion="ir-inicio">
      ${frase(acciones.volver)}
      <span className="flecha" aria-hidden="true">→</span>
    </button>
  `;
}

/** El elemento de React de esta pantalla, ya con sus propiedades puestas. */
export function pantallaDeMisCosas(propiedades) {
  return html`
    <${PantallaMisCosas}
      textos=${propiedades.textos}
      secciones=${propiedades.secciones}
      atajos=${propiedades.atajos}
    />
  `;
}
