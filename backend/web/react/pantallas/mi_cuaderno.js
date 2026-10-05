/*
 * mi_cuaderno.js — «Mi cuaderno»: el año entero del agricultor en una sola pantalla.
 *
 * POR QUÉ ESTA ES LA ÚLTIMA GRANDE, Y POR QUÉ ES UNA SOLA PANTALLA
 *
 * Es la pantalla que más se mira: aquí está lo que ha apuntado (los tratamientos), lo que le falta por
 * apuntar, lo que ha vendido, las medidas que hace sin echar producto, los análisis, el plan de abono, la
 * firma y las dos cosas de la Junta (su cuaderno y el registro electrónico).
 *
 * Sus bloques estaban escritos en `app.js` como siete funciones que devolvían HTML, y **se pasan de una
 * vez**: la pantalla es una sola, así que apuntarla a medias en la lista de pantallas migradas sería
 * mentir. Por eso vivía en «lo que queda» hasta hoy.
 *
 * LO QUE SE CONSERVA A PROPÓSITO, BLOQUE A BLOQUE
 *
 *  1. **Cada cosa que falta lleva el botón que la arregla** (si tiene pantalla propia). Es la regla del
 *     proyecto: decir «a El Prado le falta decir qué cultivo tiene» y no dar dónde contestarlo deja al
 *     agricultor mirando una frase sin salida. Ese botón va dentro de su `<li>`, con su barra.
 *  2. **El aviso de un bloque se pone rojo cuando de verdad hay algo mal** (un plan pasado de abono, las
 *     medidas sin declarar): mirar el color es lo que hace que se vea de un vistazo.
 *  3. **Cada aviso lleva su texto como lo llevaba**: unos dentro de un `<p>` y otros suelto. No es un
 *     descuido: el `<p>` añade aire por dentro, y cambiarlo habría movido la altura de media pantalla.
 *     Por eso el aviso tiene `enParrafo` en vez de decidirlo aquí.
 *  4. **Los botones salen donde salían**: la mayoría dentro de una `.barra-acciones`, pero el de firmar y
 *     el de hacer el plan (cuando todavía no hay plan) van **sueltos**, y así se quedan. Una barra con un
 *     solo botón no es lo mismo que un botón suelto.
 *  5. **El emoji de los botones de abajo va dentro del texto** («🖨️ VER EL CUADERNO EN PAPEL»), que es
 *     como estaba: esos tres botones no llevan el `<span class="icono">` de los demás.
 *
 * UNA UNIFICACIÓN, DECIDIDA A PROPÓSITO (la misma que en la oferta del SIGPAC): los dos botones sueltos
 * —Firmar y Hacer el plan— llevan ahora **la flecha de la casa**. Antes se escribían a mano sin ella y
 * eran los dos únicos caminos de la aplicación sin flecha; llevan a otra pantalla, así que la llevan.
 *
 * Y OTRA DEL REDISEÑO (ronda 79): **los apuntes de producto son tarjetas**, con la misma pieza que las
 * tierras del asistente y de «mis cosas» (`piezas/tarjeta.js`), cada dato con su nombre delante. Antes
 * eran renglones con «TRIGO BLANDO · 4,90 ha · 0,80 L/ha»: tres datos seguidos, sin decir cuál era cuál
 * y **sin la tierra donde se echó**, que es lo primero que se pregunta en una inspección.
 *
 * El componente es PURO: no llama a `fetch`, no lee `localStorage` y no toca el DOM. Todo lo que se
 * cuenta o se formatea (los números en castellano, las fechas, las frases con huecos, la línea de detalle
 * de cada apunte) llega **ya hecho** desde `app.js`.
 */

import { BotonSencillo, Botones, frase, html } from "../componentes.js";
import { Tarjeta } from "../piezas/tarjeta.js";
import { AccionesDeUnaFicha } from "../piezas/acciones_de_una_ficha.js";
import { Tabla } from "../piezas/tabla.js";

/**
 * Un aviso: su texto (o sus textos) y si va en rojo.
 *
 * `enParrafo` decide si cada texto va dentro de un `<p>`: unos bloques lo llevaban y otros no, y el aire
 * que añade el `<p>` se nota.
 */
function Aviso({ aviso }) {
  const textos = (aviso.textos || []).filter(Boolean);
  if (!textos.length) return null;
  const clase = aviso.error ? "aviso aviso-error" : "aviso";
  if (!aviso.enParrafo) return html`<div className=${clase}>${frase(textos[0])}</div>`;
  return html`
    <div className=${clase}>
      ${textos.map((texto, indice) => html`<p key=${indice}>${frase(texto)}</p>`)}
    </div>
  `;
}

/**
 * Los apuntes del año: cuántos son y la lista, cada uno en su tarjeta y con sus dos botones.
 *
 * **Cada apunte es una tarjeta desde el rediseño (ronda 79)**, con la misma pieza que las tierras del
 * asistente (`piezas/tarjeta.js`, ver `docs/stitch/rediseno/mi_cuaderno.png`): su número, su fecha, y
 * cada dato **con su nombre delante** —tierra y parcela, hectáreas tratadas, cuánto por hectárea y el
 * cultivo—. Antes era un renglón con los tres datos seguidos («TRIGO BLANDO · 4,90 ha · 0,80 L/ha») y
 * sin decir cuál era cuál.
 *
 * Aquí la tarjeta va **sin acción**: un apunte no se toca para abrir nada, se lee. Lo que se toca son
 * los dos botones de debajo, y **desde la ronda 91 son suyos**: CORREGIR y BORRAR. Antes esta lista
 * era lo único que había y no se podía hacer nada con ella —un apunte mal metido se quedaba mal para
 * siempre—, que es justo lo que pidió el dueño del proyecto.
 *
 * **Por qué los botones van fuera de la tarjeta y no dentro**: la tarjeta, sin acción, es un `div` de
 * lectura; meterle dentro dos botones convertiría el conjunto en una caja que se toca pero no hace
 * nada, y el agricultor tocaría la tarjeta esperando algo. Van debajo, con la misma barra de acciones
 * que el resto de la aplicación, y a 64 px de alto: se pulsan con el pulgar y con guantes.
 */
function BloqueDeApuntes({ apuntes }) {
  return html`
    <h2>${frase(apuntes.titulo)}</h2>
    ${
      // **La tabla, solo en el ordenador** (30/09/2026): la misma lista de apuntes que las tarjetas de
      // abajo, con las mismas acciones. En el ordenador se mira de arriba abajo —qué se hizo, dónde,
      // cuántas hectáreas y cuándo— y se puede ordenar por cualquier columna; en el móvil, la tarjeta de
      // siempre. El CSS enseña una u otra según el ancho.
      apuntes.tabla ? html`<div className="solo-escritorio"><${Tabla} tabla=${apuntes.tabla} /></div>` : null
    }
    ${
      apuntes.hay
        ? html`
            <div className="tarjetas solo-movil">
              ${apuntes.filas.map(
                (fila, indice) => html`
                  <div className="tarjeta-con-acciones" key=${indice}>
                    <${Tarjeta}
                      etiqueta=${fila.etiqueta}
                      rotulo=${fila.rotulo}
                      lineas=${fila.lineas}
                      filas=${fila.filas}
                      marca=${false}
                    />
                    ${
                      (fila.acciones || []).length
                        ? html`<${AccionesDeUnaFicha} acciones=${fila.acciones} />`
                        : null
                    }
                  </div>
                `,
              )}
            </div>
          `
        : html`<p className="pista-campo">${frase(apuntes.vacio)}</p>`
    }
    <${Botones} botones=${apuntes.acciones} />
  `;
}

/** Lo que le falta al cuaderno, con el botón que lo arregla cuando lo hay. */
function BloqueDeLoQueFalta({ faltantes }) {
  return html`
    <h2>${frase(faltantes.titulo)}</h2>
    ${
      faltantes.pendientes.length
        ? html`
            <ul className="lista">
              ${faltantes.pendientes.map(
                (pendiente, indice) => html`
                  <li key=${indice}>
                    ${frase(pendiente.mensaje)}
                    ${
                      pendiente.accion
                        ? html`
                            <div className="barra-acciones">
                              <${BotonSencillo}
                                etiqueta=${pendiente.etiqueta}
                                accion=${pendiente.accion}
                                clase="boton-claro"
                              />
                            </div>
                          `
                        : null
                    }
                  </li>
                `,
              )}
            </ul>
          `
        : html`<p className="pista-campo">${frase(faltantes.vacio)}</p>`
    }
  `;
}

/**
 * Lo que se ha vendido: el resumen, las últimas cuatro y la puerta a todas.
 *
 * El resumen va en su línea destacada (`.cuantas`): «2 ventas apuntadas · 44.000 kg» se lee de un vistazo,
 * y con eso el agricultor ya sabe si le falta apuntar una entrega sin recorrer la lista.
 */
function BloqueDeVentas({ ventas }) {
  return html`
    <h2>${frase(ventas.titulo)}</h2>
    ${
      ventas.hay
        ? html`
            <p className="cuantas">${frase(ventas.resumen)}</p>
            <ul className="lista">
              ${ventas.filas.map(
                (fila, indice) => html`
                  <li key=${indice}>
                    <div className="apunte-cabecera">
                      <span>${frase(fila.fecha)}</span>
                      <span>${frase(fila.producto)}</span>
                    </div>
                    <div className="apunte-detalle">${frase(fila.detalle)}</div>
                  </li>
                `,
              )}
            </ul>
          `
        : html`<${Aviso} aviso=${{ textos: [ventas.sin_nada] }} />`
    }
    <${Botones} botones=${ventas.acciones} />
  `;
}

/** Las medidas que se hacen sin echar producto. */
function BloqueDeMedidas({ medidas }) {
  return html`
    <h2>${frase(medidas.titulo)}</h2>
    ${
      medidas.declarada
        ? html`
            <${Aviso}
              aviso=${{
                textos: [medidas.mensaje],
                error: !medidas.aplicadas.length,
                enParrafo: true,
              }}
            />
            ${
              medidas.aplicadas.length
                ? html`
                    <ul className="lista">
                      ${medidas.aplicadas.map(
                        (nombre, indice) => html`<li key=${indice}>${frase(nombre)}</li>`,
                      )}
                    </ul>
                  `
                : null
            }
          `
        : html`
            <${Aviso} aviso=${{ textos: [medidas.sin_declarar] }} />
            <p className="pista-campo">${frase(medidas.explica)}</p>
          `
    }
    <${Botones} botones=${medidas.acciones} />
  `;
}

/** Los análisis: cuántos hay (en su línea destacada) y los tres últimos, con sus números. */
function BloqueDeAnaliticas({ analiticas }) {
  return html`
    <h2>${frase(analiticas.titulo)}</h2>
    ${
      analiticas.hay
        ? html`
            <p className="cuantas">${frase(analiticas.resumen)}</p>
            <ul className="lista">
              ${analiticas.filas.map(
                (fila, indice) => html`
                  <li key=${indice}>
                    <div className="apunte-cabecera">
                      <span>${frase(fila.titulo)}</span>
                      <span>${frase(fila.fecha)}</span>
                    </div>
                    ${
                      fila.detalle
                        ? html`<div className="apunte-detalle">${frase(fila.detalle)}</div>`
                        : null
                    }
                  </li>
                `,
              )}
            </ul>
          `
        : html`
            <${Aviso} aviso=${{ textos: [analiticas.sin_analisis] }} />
            <p className="pista-campo">${frase(analiticas.apunta_primero)}</p>
          `
    }
    <${Botones} botones=${analiticas.acciones} />
  `;
}

/** El plan de abono del año: lo previsto contra lo aplicado. */
function BloqueDePlan({ plan }) {
  return html`
    <h2>${frase(plan.titulo)}</h2>
    ${
      plan.hay
        ? html`
            <${Aviso}
              aviso=${{ textos: [plan.mensaje], error: plan.se_ha_pasado, enParrafo: true }}
            />
            <${Botones} botones=${plan.acciones} />
          `
        : html`
            <${Aviso} aviso=${{ textos: [plan.sin_planes] }} />
            <p className="pista-campo">${frase(plan.obligatorio)}</p>
            <${Botones} botones=${plan.botones} barra=${false} />
          `
    }
  `;
}

/** La firma del cuaderno. Sin los datos de la firma, el bloque no se pinta. */
function BloqueDeFirma({ firma }) {
  if (!firma.hay) return null;
  return html`
    <h2>${frase(firma.titulo)}</h2>
    <${Aviso}
      aviso=${{
        textos: [firma.mensaje, firma.puede ? "" : firma.no_puede_firmar],
        error: firma.cambiado,
        enParrafo: true,
      }}
    />
    <p className="pista-campo">${frase(firma.explicacion)}</p>
    <${Botones} botones=${firma.botones} barra=${false} />
  `;
}

/**
 * El cuaderno de la Junta: sacarlo relleno y decir qué falta para tenerlo completo.
 *
 * **El bloque verde es lo del rediseño (ronda 80)** y tiene su porqué: es lo único de esta pantalla que
 * se hace **con alguien delante** —el inspector, en el campo, esperando—, así que tiene que encontrarse
 * sin leer nada. Por eso va con fondo verde oscuro (el único bloque oscuro de la pantalla, como en
 * `docs/stitch/rediseno/mi_cuaderno.png`) y con su botón dentro. La lista de lo que falta va **fuera del
 * verde**, debajo y en blanco: eso se lee con calma, no con alguien esperando.
 */
function BloqueDelCuadernoDeLaJunta({ cuaderno }) {
  if (!cuaderno.hay) return null;
  return html`
    <div className="bloque-junta">
      <h2>${frase(cuaderno.titulo)}</h2>
      <p className="pista">${frase(cuaderno.explica)}</p>
      <p className="pista-campo">${frase(cuaderno.hojas)}</p>
      <${Botones} botones=${cuaderno.acciones} />
    </div>
    <h3>${frase(cuaderno.falta_titulo)}</h3>
    <p className="pista-campo">${frase(cuaderno.falta_pista)}</p>
    ${
      cuaderno.faltan.length
        ? html`
            <ul className="lista">
              ${cuaderno.faltan.map(
                (falta, indice) => html`
                  <li key=${indice}>
                    <div className="apunte-detalle">${frase(falta.que_falta)}</div>
                    <div className="apunte-detalle">${frase(falta.donde)}</div>
                    <div className="apunte-detalle">${frase(falta.hoja)}</div>
                  </li>
                `,
              )}
            </ul>
          `
        : html`<p className="pista-campo">${frase(cuaderno.todo_completo)}</p>`
    }
  `;
}

/**
 * El registro electrónico: qué es, desde cuándo y los sitios oficiales.
 *
 * Este bloque existe porque David preguntó «¿a qué se refiere con registro electrónico? ¿dónde debo
 * registrar los apuntes?». La respuesta va dentro de la aplicación, y de paso deja a mano la dirección
 * de cada sitio oficial: cuando hay que traer un dato de fuera, el enlace va aquí y no en un papel
 * aparte. **Qué sitios son y qué se dice de ellos no se decide aquí**: llega de `textos.py`.
 */
function BloqueDelRegistroElectronico({ registro }) {
  if (!registro.hay) return null;
  return html`
    <h2>${frase(registro.titulo)}</h2>
    <p>${frase(registro.que_es)}</p>
    <p>${frase(registro.donde)}</p>
    <p>${frase(registro.desde_cuando)}</p>
    <p className="pista-campo">${frase(registro.es_voluntario)}</p>
    <h3>${frase(registro.enlaces_titulo)}</h3>
    <ul className="lista">
      ${registro.enlaces.map(
        (enlace, indice) => html`
          <li key=${indice}>
            <a href=${enlace.url} target="_blank" rel="noopener">${frase(enlace.texto)}</a>
          </li>
        `,
      )}
    </ul>
  `;
}

/**
 * La pantalla entera.
 *
 * Propiedades: los textos que le faltan al componente (`{ cuaderno, acciones }`) y **un objeto por cada
 * bloque**, ya preparado por `app.js`, que es quien conoce los datos: los apuntes de producto, lo que
 * falta, las ventas, las medidas, los análisis, el plan, la firma, el cuaderno de la Junta, el registro
 * electrónico y la barra de botones del final.
 *
 * Cada bloque lleva dentro si tiene algo que enseñar (`hay`, o `declarada` en las medidas): el que no lo
 * tiene, **no se pinta entero**. Es lo que hace que esta pantalla no sea una lista de huecos con un
 * rótulo delante cuando el agricultor acaba de empezar, ni cuando al servidor le falta un dato (la firma
 * y el cuaderno de la Junta solo están si el servidor los ha mandado).
 */
export function PantallaMiCuaderno({
  textos = {},
  apuntes,
  faltantes,
  ventas,
  medidas,
  analiticas,
  plan,
  firma,
  cuaderno,
  registro,
  acciones = [],
}) {
  return html`
    <h1>${frase((textos.cuaderno || {}).titulo)}</h1>
    ${
      // «Te falta 1 cosa por apuntar» / «No te falta nada por apuntar»: lo primero que se lee, y lo que
      // contesta a la pregunta con la que se abre esta pantalla. Viene del servidor y **solo está si el
      // servidor ha contestado** (ver `datosDelCuaderno`): si no, no se dice nada.
      faltantes.resumen ? html`<p className="cuantas">${frase(faltantes.resumen)}</p>` : null
    }
    <${BloqueDeApuntes} apuntes=${apuntes} />
    <${BloqueDeLoQueFalta} faltantes=${faltantes} />
    <${BloqueDeVentas} ventas=${ventas} />
    <${BloqueDeMedidas} medidas=${medidas} />
    <${BloqueDeAnaliticas} analiticas=${analiticas} />
    <${BloqueDePlan} plan=${plan} />
    <${BloqueDeFirma} firma=${firma} />
    <${BloqueDelCuadernoDeLaJunta} cuaderno=${cuaderno} />
    <${BloqueDelRegistroElectronico} registro=${registro} />
    <p className="pista-campo">${frase((textos.cuaderno || {}).ley_pista)}</p>
    <${Botones} botones=${acciones} />
  `;
}

/** El elemento de React de esta pantalla, ya con sus propiedades puestas. */
export function pantallaDeMiCuaderno(propiedades) {
  return html`
    <${PantallaMiCuaderno}
      textos=${propiedades.textos}
      apuntes=${propiedades.apuntes}
      faltantes=${propiedades.faltantes}
      ventas=${propiedades.ventas}
      medidas=${propiedades.medidas}
      analiticas=${propiedades.analiticas}
      plan=${propiedades.plan}
      firma=${propiedades.firma}
      cuaderno=${propiedades.cuaderno}
      registro=${propiedades.registro}
      acciones=${propiedades.acciones}
    />
  `;
}
