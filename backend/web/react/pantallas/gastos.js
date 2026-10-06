/*
 * gastos.js — «Las cuentas»: los gastos, las inversiones, los repartos y las ayudas (S13, T13 / E7).
 *
 * QUÉ PIDE EL CONTRATO, Y DÓNDE SE VE EN ESTA PANTALLA
 *
 * El contrato pide `/cuentas` (S13) con cinco vistas (ingresos y gastos registrados, vencimientos,
 * tesorería, inversiones y margen por cultivo y por tierra) y cuatro reglas que no se pueden saltar.
 * Las cuatro se ven aquí, y cada una en un sitio concreto:
 *
 *  1. **«Compra de activo no equivale automáticamente a gasto completo del cultivo. Mostrar costes
 *     directos, repartidos y sin asignar.»** Las inversiones van en **su propia tarjeta**, con su
 *     importe y lo que de ellas se ha llevado la campaña, y las tres columnas del coste van separadas
 *     y con su nombre. Nunca se suma la inversión al gasto del año: eso diría que el año en que se
 *     compró el tractor se perdió dinero y que los siguientes fueron gratis.
 *  2. **«Método de reparto confirmado (área, horas, consumo o manual) y suma exacta, con redondeo
 *     residual visible.»** La pantalla de repartir pregunta el método, y el céntimo del redondeo se
 *     enseña con el nombre del destino que lo lleva (`residual_en`), en vez de dejar un reparto que
 *     suma 99,99 de 100 sin decir dónde está el céntimo.
 *  3. **«Subvención prevista, concedida y cobrada son estados distintos. No sumar previsión al
 *     ingreso cobrado.»** La tarjeta de las ayudas enseña las tres cifras por separado y **la
 *     previsión con su palabra**, nunca dentro de lo cobrado.
 *  4. **«Margen operativo y caja tienen tarjetas distintas.»** Son dos tarjetas y no una: un
 *     agricultor puede tener un margen bueno y la caja vacía (todo vendido y sin cobrar), y las dos
 *     respuestas son verdad a la vez.
 *
 * Y la regla que cruza todas: **un importe que no consta no es cero**. Se ve en tres sitios:
 *
 *  · un gasto sin importe sale con su estado («sin importe») y su hueco en blanco, nunca con `0,00 €`;
 *  · el pie dice **cuántos** importes no se saben, para que un total no parezca completo sin serlo;
 *  · el margen de un cultivo al que le falta un coste **no se enseña como un número**: se enseña la
 *    frase que dice que está incompleto y por qué. Un margen calculado con datos que faltan sale más
 *    alto que el verdadero, y eso es lo único de esta pantalla que puede hacer tomar una decisión
 *    equivocada.
 *
 * CÓMO SE PASA LOS DATOS
 *
 * El componente es **puro**: no llama a `fetch`, no lee `localStorage` y no toca el DOM. Todo le llega
 * por propiedades, **ya preparado por `app.js`**, que es quien tiene los datos y el vocabulario. Y
 * aquí **no se hace ni una cuenta de dinero**: en el navegador todo número es de coma flotante, así
 * que las sumas, los repartos y los cuadres se calculan en el servidor con `Decimal` y llegan hechos
 * (`app/gastos.py`, con sus pruebas). Esta pantalla solo coloca lo que le dan.
 *
 * Los campos del formulario llevan su `id` (`gasto-concepto`…), que es lo único que `app.js` tiene
 * para leer lo que el agricultor ha escrito: cambiarlos dejaría el formulario rellenándose y
 * guardándose vacío sin decir nada.
 */

import { AvisoDeError, Boton, BotonSencillo, Botones, frase, html } from "../componentes.js";
import { Campo } from "../piezas/campo.js";
import { Tabla } from "../piezas/tabla.js";

/**
 * Una tarjeta de cifras: un rótulo y sus renglones, todos con su nombre delante.
 *
 * Existe porque esta pantalla tiene **cuatro tarjetas con la misma forma** (el coste, la caja, las
 * ayudas y el margen) y escribirlas cuatro veces es la forma más segura de que dentro de un mes tres
 * digan lo mismo y una no. No calcula nada: los números llegan escritos del servidor.
 */
function Tarjeta({ rotulo, filas = [], pista = "" }) {
  const conDatos = (filas || []).filter(Boolean);
  if (!conDatos.length) return null;
  return html`
    <div className="tarjeta">
      <h2>${frase(rotulo)}</h2>
      ${pista ? html`<p className="pista-campo">${frase(pista)}</p>` : null}
      <dl>
        ${conDatos.map(
          (fila, indice) => html`
            <div className="resumen-dato" key=${indice}>
              <dt>${frase(fila.etiqueta)}</dt>
              <dd>
                ${frase(fila.valor)}
                ${fila.aviso ? html`<span className="pista-campo"> ${frase(fila.aviso)}</span>` : null}
              </dd>
            </div>
          `,
        )}
      </dl>
    </div>
  `;
}

/**
 * El cuadre de un reparto, que es la comprobación central del ticket.
 *
 * Enseña los cuatro números —el gasto, lo repartido, lo sin asignar y lo que falta— y, cuando el
 * cuadre no cierra, **lo dice con la cifra que falta**: un gasto de 100 € con 60 € repartidos tiene
 * 40 € que no están en ningún sitio, y callarlo es lo que hace que un coste desaparezca entre dos
 * pantallas sin que nadie se entere.
 */
function CuadreDelReparto({ cuadre = {}, textos = {} }) {
  const g = textos.gasto || {};
  if (!cuadre || cuadre.entero === undefined) return null;
  return html`
    <div className="aviso">
      <p className="pista-campo">${frase(g.cuadre_titulo)}</p>
      <dl>
        <div className="resumen-dato">
          <dt>${frase(g.cuadre_entero)}</dt>
          <dd>${frase(cuadre.entero ? cuadre.texto_entero : g.no_se_sabe)}</dd>
        </div>
        <div className="resumen-dato">
          <dt>${frase(g.cuadre_repartido)}</dt>
          <dd>${frase(cuadre.texto_repartido)}</dd>
        </div>
        <div className="resumen-dato">
          <dt>${frase(g.cuadre_sin_asignar)}</dt>
          <dd>${frase(cuadre.texto_sin_asignar)}</dd>
        </div>
      </dl>
      ${
        // **Y lo que falta, solo cuando falta algo.** Un renglón de «no falta nada» en todos los
        // gastos sería ruido; el renglón que importa es el que aparece cuando hay 40 € sin dueño.
        cuadre.cuadra
          ? null
          : html`<p className="pista-campo">
              <span>${frase(g.cuadre_no_cierra)}</span>
              <span>${frase(cuadre.texto_falta)}</span>
            </p>`
      }
      ${
        cuadre.texto_sin_asignar && cuadre.texto_sin_asignar !== "0,00 €"
          ? html`<p className="pista-campo">${frase(g.sin_asignar_explica)}</p>`
          : null
      }
    </div>
  `;
}

/** El reparto de un gasto, trozo a trozo, con su método y el botón para quitarlo. */
function SusRepartos({ gasto = {}, textos = {} }) {
  const g = textos.gasto || {};
  if (!gasto.repartos || !gasto.repartos.length) {
    return html`<p className="pista-campo">${frase(g.todavia_sin_reparto)}</p>`;
  }
  return html`
    <ul className="lista">
      ${gasto.repartos.map((reparto, indice) => {
        const quitar = { id: gasto.id, reparto: reparto.id };
        return html`
          <li key=${indice}>
            <strong>${frase(reparto.etiqueta_destino || reparto.destino)}</strong>
            <span className="pista-campo"> ${frase(reparto.texto_importe)}</span>
            <p className="pista-campo">
              <span>${frase(g.reparto_metodo)}</span>
              <span>${frase(g[`metodo_${reparto.metodo}`])}</span>
            </p>
            <${Botones}
              botones=${[
                {
                  etiqueta: g.reparto_quitar,
                  accion: "gasto-reparto-quitar",
                  datos: quitar,
                  clase: "boton-claro",
                  sencillo: true,
                },
              ]}
              barra=${false}
            />
          </li>
        `;
      })}
    </ul>
  `;
}

/** Un gasto de la lista, en el móvil: su concepto, su importe, lo pagado y lo que queda. */
function FichaDeUnGasto({ gasto = {}, textos = {} }) {
  const g = textos.gasto || {};
  const abrir = { id: gasto.id };
  return html`
    <li>
      <strong>${frase(gasto.concepto)}</strong>
      ${
        gasto.proveedor
          ? html`<p className="pista-campo">
              <span>${frase(g.proveedor)}</span>
              <span>${frase(gasto.proveedor)}</span>
            </p>`
          : null
      }
      <dl>
        <div className="resumen-dato">
          <dt>${frase(g.importe)}</dt>
          <dd>
            ${
              // **Un importe que no consta se enseña en blanco, con la palabra que lo dice.** Un
              // `0,00 €` aquí sería decir que el gasto salió gratis.
              gasto.importe ? frase(gasto.texto_importe) : frase(g.no_se_sabe)
            }
          </dd>
        </div>
        <div className="resumen-dato">
          <dt>${frase(g.pagado)}</dt>
          <dd>${frase(gasto.texto_pagado)}</dd>
        </div>
        <div className="resumen-dato">
          <dt>${frase(g.pendiente)}</dt>
          <dd>${gasto.pendiente ? frase(gasto.texto_pendiente) : frase(g.no_se_sabe)}</dd>
        </div>
        <div className="resumen-dato">
          <dt>${frase(g.como_esta)}</dt>
          <dd>${frase(g[`estado_${gasto.estado}`])}</dd>
        </div>
        <div className="resumen-dato">
          <dt>${frase(g.su_tierra)}</dt>
          <dd>
            ${frase(
              // **A dónde va lo dice el servidor** (`va_a`, 06/10/2026): su tierra o su cultivo —el
              // «coste directo» del ticket— o su primer reparto. Antes esto miraba solo los repartos,
              // así que un gasto apuntado **con su tierra** salía como «Sin asignar», y decía lo
              // contrario de lo que el agricultor acababa de escribir.
              gasto.va_a || g.sin_asignar_corto,
            )}
          </dd>
        </div>
      </dl>
      <${Botones}
        botones=${[{ etiqueta: g.abrir, accion: "gasto-abrir", datos: abrir, clase: "boton-claro" }]}
        barra=${false}
      />
    </li>
  `;
}

/**
 * Los campos de un formulario, tal y como los prepara `app.js`.
 *
 * Un bloque es de escribir (`{tipo, id, etiqueta, valor, pista}`), de elegir
 * (`{tipo: "opciones", campo, etiqueta, opciones, elegido}`) o de **marcar** (`{tipo: "marcas", campo,
 * etiqueta, opciones: [{clave, texto, marcada}], todas}`). Un bloque con un `tipo` que no se conoce se
 * pinta como texto: entre un campo de más y un campo que desaparece sin decir nada, el de más.
 *
 * **Las marcas son las tierras del reparto** (06/10/2026): marcar y desmarcar es lo que dice entre qué
 * tierras se reparte un gasto, y lleva su botón de «TODAS» porque repartir el gasóleo entre todas las
 * tierras de la finca es lo que se hace casi siempre.
 */
function Formulario({ formulario, guardando }) {
  if (!formulario) return null;
  return html`
    <h2>${frase(formulario.titulo)}</h2>
    ${formulario.pista ? html`<p className="pista">${frase(formulario.pista)}</p>` : null}
    ${(formulario.bloques || []).map((bloque, indice) =>
      bloque.tipo === "opciones"
        ? html`
            <div className="campo" key=${indice}>
              <p className="etiqueta-campo">${frase(bloque.etiqueta)}</p>
              ${bloque.pista ? html`<p className="pista-campo">${frase(bloque.pista)}</p>` : null}
              <div className="barra-acciones">
                ${(bloque.opciones || []).map((opcion) => {
                  const elegido = String(bloque.elegido) === String(opcion.valor);
                  const datos = { campo: bloque.campo, valor: String(opcion.valor) };
                  return html`
                    <button
                      key=${String(opcion.valor)}
                      type="button"
                      className=${`boton ${elegido ? "boton-elegido" : "boton-claro"}`}
                      data-accion="gasto-elegir"
                      data-campo=${datos.campo}
                      data-valor=${datos.valor}
                      data-elegido=${elegido ? "1" : "0"}
                    >
                      ${frase(opcion.texto)}
                    </button>
                  `;
                })}
              </div>
            </div>
          `
        : bloque.tipo === "marcas"
          ? html`
              <div className="campo" key=${indice}>
                <p className="etiqueta-campo">${frase(bloque.etiqueta)}</p>
                ${bloque.pista ? html`<p className="pista-campo">${frase(bloque.pista)}</p>` : null}
                <div className="barra-acciones">
                  ${(bloque.opciones || []).map(
                    (opcion) => html`
                      <button
                        key=${String(opcion.clave)}
                        type="button"
                        className=${`boton ${opcion.marcada ? "boton-elegido" : "boton-claro"}`}
                        data-accion="gasto-marcar"
                        data-clave=${String(opcion.clave)}
                        data-marcada=${opcion.marcada ? "1" : "0"}
                        aria-pressed=${opcion.marcada ? "true" : "false"}
                      >
                        ${frase(opcion.texto)}
                      </button>
                    `,
                  )}
                  ${
                    // **TODAS**, porque es lo que se hace casi siempre: el gasóleo del tractor va a
                    // todas las tierras. Ahorra marcar una por una en una finca de 64 tierras.
                    bloque.todas
                      ? html`<button
                          type="button"
                          className="boton boton-claro"
                          data-accion="gasto-marcar-todas"
                        >
                          ${frase(bloque.todas)}
                        </button>`
                      : null
                  }
                </div>
              </div>
            `
          : html`
            <${Campo}
              key=${indice}
              id=${bloque.id}
              etiqueta=${bloque.etiqueta}
              tipo=${bloque.tipo}
              valor=${bloque.valor}
              sufijo=${bloque.pista}
              unidad=${bloque.unidad}
              placeholder=${bloque.placeholder}
              filas=${bloque.filas}
            />
          `,
    )}
    ${formulario.error ? html`<${AvisoDeError} texto=${formulario.error} />` : null}
    <div className="barra-acciones">
      <${Boton}
        etiqueta=${formulario.guardar}
        accion="gasto-guardar"
        datos=${formulario.datos}
        clase=""
      />
      <${BotonSencillo} etiqueta=${formulario.cancelar} accion="gasto-cancelar" />
    </div>
    ${guardando ? html`<p className="pista-campo">${frase(formulario.guardando)}</p>` : null}
  `;
}

/** La pantalla de anular: pide el motivo, porque sin motivo el rastro no sirve para nada. */
function Anulando({ anulando, textos = {} }) {
  const g = textos.gasto || {};
  if (!anulando) return null;
  return html`
    <h2>${frase(anulando.titulo)}</h2>
    <p className="pista">${frase(anulando.pista)}</p>
    <${Campo} id=${anulando.id} etiqueta=${g.anular_motivo} valor="" />
    ${anulando.error ? html`<${AvisoDeError} texto=${anulando.error} />` : null}
    <div className="barra-acciones">
      <${Boton}
        etiqueta=${anulando.confirmar}
        accion="gasto-anular-confirmar"
        datos=${anulando.datos}
        clase=""
      />
      <${BotonSencillo} etiqueta=${anulando.cancelar} accion="gasto-cancelar" />
    </div>
  `;
}

/** Las tres columnas del coste, que el contrato pide enseñar **por separado**. */
function CostePorClase({ coste = {}, textos = {} }) {
  const g = textos.gasto || {};
  return html`
    <${Tarjeta}
      rotulo=${g.coste_titulo}
      pista=${g.coste_explica}
      filas=${[
        { etiqueta: g.coste_directo, valor: coste.texto_directos },
        { etiqueta: g.coste_repartido, valor: coste.texto_repartidos },
        {
          etiqueta: g.coste_sin_asignar,
          valor: coste.texto_sin_asignar,
          aviso: coste.texto_sin_asignar_cuantos,
        },
        { etiqueta: g.coste_total_conocido, valor: coste.texto_total_conocido },
        // **Cuántos importes no se saben.** Sin este renglón, el total parecería completo. La frase
        // la compone el servidor, con su singular y su plural.
        {
          etiqueta: g.cuantos_sin_importe,
          valor: coste.texto_sin_importe,
          aviso: coste.sin_importe ? g.sin_importe_explica : "",
        },
      ]}
    />
  `;
}

/** El margen de cada cultivo, **incompleto y diciéndolo** cuando le falta un importe. */
function LosMargenes({ margenes = {}, textos = {} }) {
  const g = textos.gasto || {};
  const claves = Object.keys(margenes || {});
  if (!claves.length) return null;
  return html`
    <div className="tarjeta">
      <h2>${frase(g.margen_titulo)}</h2>
      <p className="pista-campo">${frase(g.margen_explica)}</p>
      <ul className="lista">
        ${claves.map((clave, indice) => html`
          <li key=${indice}>
            <strong>${frase(clave)}</strong>
            <dl>
              <div className="resumen-dato">
                <dt>${frase(g.ingresos)}</dt>
                <dd>${frase(margenes[clave].texto_ingresos || g.no_se_sabe)}</dd>
              </div>
              <div className="resumen-dato">
                <dt>${frase(g.coste_conocido)}</dt>
                <dd>${frase(margenes[clave].texto_coste_conocido)}</dd>
              </div>
            </dl>
            ${
              // **El margen solo se enseña si se puede calcular.** Con un importe que falta, lo que
              // sale es la frase que lo explica: un número calculado con datos incompletos sale más
              // alto que el verdadero y se toma una decisión con él.
              margenes[clave].completo
                ? html`<p className="pista-campo">
                    <span>${frase(g.margen)}</span>
                    <span>${frase(margenes[clave].texto_margen)}</span>
                  </p>`
                : html`<p className="aviso">${frase(g.margen_incompleto)}</p>`
            }
          </li>
        `)}
      </ul>
    </div>
  `;
}

/** La caja: el dinero que ha entrado y salido de verdad, **aparte del margen**. */
function LaCaja({ caja = {}, textos = {} }) {
  const g = textos.gasto || {};
  return html`
    <${Tarjeta}
      rotulo=${g.caja_titulo}
      pista=${g.caja_explica}
      filas=${[
        { etiqueta: g.caja_entrado, valor: caja.texto_entrado },
        { etiqueta: g.caja_salido, valor: caja.texto_salido },
        { etiqueta: g.caja_saldo, valor: caja.texto_saldo },
        { etiqueta: g.caja_por_pagar, valor: caja.texto_por_pagar },
        { etiqueta: g.ayudas_cobradas, valor: caja.texto_ayudas_cobradas },
        {
          // **La previsión va aparte y con su palabra, y no se suma a lo que ha entrado.**
          etiqueta: g.ayudas_previstas,
          valor: caja.texto_ayudas_previstas,
          aviso: g.prevision_no_es_ingreso,
        },
      ]}
    />
  `;
}

/** Las inversiones: lo que costó el bien y lo que de él se ha llevado la campaña. */
function LasInversiones({ inversiones = [], textos = {} }) {
  const g = textos.gasto || {};
  if (!inversiones.length) return null;
  return html`
    <div className="tarjeta">
      <h2>${frase(g.inversiones_titulo)}</h2>
      <p className="pista-campo">${frase(g.inversiones_explica)}</p>
      <ul className="lista">
        ${inversiones.map(
          (inversion, indice) => html`
            <li key=${indice}>
              <strong>${frase(inversion.concepto)}</strong>
              <dl>
                <div className="resumen-dato">
                  <dt>${frase(g.importe)}</dt>
                  <dd>${inversion.importe ? frase(inversion.texto_importe) : frase(g.no_se_sabe)}</dd>
                </div>
                <div className="resumen-dato">
                  <dt>${frase(g.inversion_en_la_campana)}</dt>
                  <dd>${frase(inversion.texto_repartido)}</dd>
                </div>
                <div className="resumen-dato">
                  <dt>${frase(g.coste_sin_asignar)}</dt>
                  <dd>${frase(inversion.texto_sin_asignar || g.no_se_sabe)}</dd>
                </div>
              </dl>
              ${inversion.anulada ? html`<p className="aviso">${frase(g.esta_anulada)}</p>` : null}
            </li>
          `,
        )}
      </ul>
    </div>
  `;
}

/** Las ayudas, con **sus tres cifras separadas** y lo que cuenta como ingreso dicho. */
function LasAyudas({ subvenciones = [], textos = {} }) {
  const g = textos.gasto || {};
  if (!subvenciones.length) return null;
  return html`
    <div className="tarjeta">
      <h2>${frase(g.ayudas_titulo)}</h2>
      <p className="pista-campo">${frase(g.ayudas_explica)}</p>
      <ul className="lista">
        ${subvenciones.map(
          (ayuda, indice) => html`
            <li key=${indice}>
              <strong>${frase(ayuda.concepto)}</strong>
              <p className="pista-campo">${frase(g[`ayuda_estado_${ayuda.estado}`])}</p>
              <dl>
                <div className="resumen-dato">
                  <dt>${frase(g.ayuda_prevista)}</dt>
                  <dd>${frase(ayuda.texto_previsto || g.no_se_sabe)}</dd>
                </div>
                <div className="resumen-dato">
                  <dt>${frase(g.ayuda_concedida)}</dt>
                  <dd>${frase(ayuda.texto_concedido || g.no_se_sabe)}</dd>
                </div>
                <div className="resumen-dato">
                  <dt>${frase(g.ayuda_cobrada)}</dt>
                  <dd>${frase(ayuda.texto_cobrado || g.no_se_sabe)}</dd>
                </div>
              </dl>
            </li>
          `,
        )}
      </ul>
    </div>
  `;
}

/** Los pagos, y **el dinero que todavía no se sabe a qué va**, en su lista aparte. */
function LosPagos({ pagos = [], sinConciliar = [], textos = {} }) {
  const g = textos.gasto || {};
  return html`
    <div className="tarjeta">
      <h2>${frase(g.pagos_titulo)}</h2>
      <p className="pista-campo">${frase(g.pagos_explica)}</p>
      ${
        pagos.length
          ? html`<ul className="lista">
              ${pagos.map((pago, indice) => {
                const conciliar = { id: pago.id };
                const anular = { id: pago.id, clase: "pago" };
                return html`
                  <li key=${indice}>
                    <strong>${frase(pago.texto_importe)}</strong>
                    <p className="pista-campo">${frase(pago.fecha || g.no_se_sabe)}</p>
                    <dl>
                      <div className="resumen-dato">
                        <dt>${frase(g.pago_aplicado)}</dt>
                        <dd>${frase(pago.texto_aplicado)}</dd>
                      </div>
                      <div className="resumen-dato">
                        <dt>${frase(g.pago_sin_conciliar)}</dt>
                        <dd>${frase(pago.texto_sin_conciliar)}</dd>
                      </div>
                    </dl>
                    <${Botones}
                      botones=${[
                        {
                          etiqueta: g.pago_conciliar,
                          accion: "gasto-pago-conciliar",
                          datos: conciliar,
                          clase: "boton-claro",
                          sencillo: true,
                        },
                        {
                          etiqueta: g.anular,
                          accion: "gasto-anular",
                          datos: anular,
                          clase: "boton-claro",
                          sencillo: true,
                        },
                      ]}
                      barra=${false}
                    />
                  </li>
                `;
              })}
            </ul>`
          : html`<p className="pista-campo">${frase(g.sin_pagos)}</p>`
      }
      ${
        // **El dinero sin conciliar no se pierde y se dice**: está apuntado y espera a saber contra
        // qué gasto va. Es lo mismo que el contrato pide en el panel de Economía para los cobros.
        sinConciliar.length
          ? html`
              <h3>${frase(g.sin_conciliar_titulo)}</h3>
              <p className="pista-campo">${frase(g.sin_conciliar_explica)}</p>
            `
          : null
      }
    </div>
  `;
}

/** Lo que este programa todavía no calcula, con lo que es y de quién depende. */
function LoQueFalta({ queFalta = [], textos = {} }) {
  const g = textos.gasto || {};
  if (!queFalta.length) return null;
  return html`
    <div className="aviso">
      <h2>${frase(g.que_falta_titulo)}</h2>
      <p className="pista-campo">${frase(g.que_falta_explica)}</p>
      <ul className="lista">
        ${queFalta.map(
          (uno, indice) => html`
            <li key=${indice}>
              <strong>${frase(uno.que)}</strong>
              <dl>
                <div className="resumen-dato">
                  <dt>${frase(g.que_falta_para_que)}</dt>
                  <dd>${frase(uno.para_que)}</dd>
                </div>
                <div className="resumen-dato">
                  <dt>${frase(g.que_falta_depende)}</dt>
                  <dd>${frase(uno.de_quien_depende)}</dd>
                </div>
              </dl>
            </li>
          `,
        )}
      </ul>
    </div>
  `;
}

/**
 * La pantalla de las cuentas (S13).
 *
 * Propiedades:
 *
 *  - `textos`: `{gasto, acciones, tabla}` del servidor.
 *  - `cuentas`: lo que devuelve `GET /api/gastos` **ya calculado** (las cinco listas, las tres
 *    columnas del coste, la caja, el margen y lo que falta).
 *  - `tabla`: la tabla del ordenador, preparada por `app.js` (columnas, filas y resumen), o `null`.
 *  - `resumen`, `filtro`, `formulario`, `anulando`, `guardando`, `error`, `aviso`.
 */
export function PantallaDeLasCuentas({
  textos = {},
  cuentas = {},
  tabla = null,
  resumen = "",
  filtro = "",
  formulario = null,
  anulando = null,
  guardando = false,
  error = "",
  aviso = "",
}) {
  const g = textos.gasto || {};
  const acciones = textos.acciones || {};
  const gastos = cuentas.gastos || [];
  return html`
    <h1>${frase(g.titulo)}</h1>
    <p className="pista">${frase(g.explica)}</p>
    ${error ? html`<${AvisoDeError} texto=${error} />` : null}
    ${aviso ? html`<div className="aviso">${frase(aviso)}</div>` : null}

    ${formulario ? html`<${Formulario} formulario=${formulario} guardando=${guardando} />` : null}
    ${anulando ? html`<${Anulando} anulando=${anulando} textos=${textos} />` : null}

    <div className="campo">
      <label htmlFor="gastos-buscar">${frase(g.buscar)}</label>
      <p className="pista-campo">${frase(g.buscar_pista)}</p>
      <input id="gastos-buscar" type="text" defaultValue=${frase(filtro)} />
    </div>
    <div className="barra-acciones">
      <${BotonSencillo} etiqueta=${g.ver_todas} accion="gastos-ver-todas" />
    </div>

    ${resumen ? html`<p className="cuantas">${frase(resumen)}</p>` : null}

    ${
      // **La tabla del ordenador y la lista del móvil son la misma lista**, y las dos se pintan: el
      // CSS enseña una u otra según el ancho (`.solo-escritorio` y `.solo-movil`).
      tabla ? html`<div className="solo-escritorio tabla-scroll"><${Tabla} tabla=${tabla} /></div>` : null
    }

    ${
      gastos.length
        ? html`<ul className="lista solo-movil">
            ${gastos.map(
              (gasto, indice) => html`<${FichaDeUnGasto} key=${indice} gasto=${gasto} textos=${textos} />`,
            )}
          </ul>`
        : html`<div className="aviso">${frase(filtro ? g.sin_resultados : g.sin_gastos)}</div>`
    }

    <${CostePorClase} coste=${cuentas.coste_por_clase || {}} textos=${textos} />
    <${LaCaja} caja=${cuentas.caja || {}} textos=${textos} />
    <${LasInversiones} inversiones=${cuentas.inversiones || []} textos=${textos} />
    <${LasAyudas} subvenciones=${cuentas.subvenciones || []} textos=${textos} />
    <${LosPagos}
      pagos=${cuentas.pagos || []}
      sinConciliar=${cuentas.sin_conciliar || []}
      textos=${textos}
    />
    <${LosMargenes} margenes=${cuentas.margenes || {}} textos=${textos} />
    <${LoQueFalta} queFalta=${cuentas.que_falta || []} textos=${textos} />

    <div className="barra-acciones">
      <${Boton} etiqueta=${g.nuevo} accion="gasto-nuevo" />
      <${Boton} etiqueta=${g.nuevo_pago} accion="gasto-pago-nuevo" clase="boton-claro" />
      <${Boton} etiqueta=${g.nueva_inversion} accion="gasto-inversion-nueva" clase="boton-claro" />
      <${Boton} etiqueta=${g.nueva_ayuda} accion="gasto-ayuda-nueva" clase="boton-claro" />
      <${Boton} etiqueta=${g.los_bancos} accion="bancos-ver" clase="boton-claro" />
      <${Boton} etiqueta=${acciones.volver} accion="ir-inicio" clase="boton-claro" />
    </div>
  `;
}

/**
 * La ficha de un gasto: lo que costó, a quién va, cuánto se ha pagado y qué queda.
 *
 * Es donde se completa el recorrido del gasto: **repartirlo** a tierras, cultivos o máquinas (o
 * dejarlo sin asignar diciéndolo), y **quitarlo de donde estaba**. Y enseña el cuadre con sus cuatro
 * números, que es lo que hace que el agricultor pueda comprobar que el céntimo está donde tiene que
 * estar.
 */
export function PantallaDeUnGasto({
  textos = {},
  gasto = {},
  pagos = [],
  formulario = null,
  repartiendo = null,
  anulando = null,
  guardando = false,
  error = "",
  aviso = "",
}) {
  const g = textos.gasto || {};
  const acciones = textos.acciones || {};
  const repartir = { id: gasto.id };
  const sinAsignar = { id: gasto.id };
  const corregir = { id: gasto.id };
  const anular = { id: gasto.id, clase: "gasto" };
  return html`
    <h1>${frase(gasto.concepto)}</h1>
    <p className="pista">${frase(gasto.proveedor || "")}</p>
    ${error ? html`<${AvisoDeError} texto=${error} />` : null}
    ${aviso ? html`<div className="aviso">${frase(aviso)}</div>` : null}
    ${gasto.anulado ? html`<p className="aviso">${frase(g.esta_anulado)}</p>` : null}

    ${formulario ? html`<${Formulario} formulario=${formulario} guardando=${guardando} />` : null}
    ${anulando ? html`<${Anulando} anulando=${anulando} textos=${textos} />` : null}

    <${Tarjeta}
      rotulo=${g.su_cuenta}
      filas=${[
        { etiqueta: g.importe, valor: gasto.importe ? gasto.texto_importe : g.no_se_sabe },
        { etiqueta: g.pagado, valor: gasto.texto_pagado },
        { etiqueta: g.pendiente, valor: gasto.pendiente ? gasto.texto_pendiente : g.no_se_sabe },
        { etiqueta: g.como_esta, valor: g[`estado_${gasto.estado}`] },
      ]}
    />

    <${CuadreDelReparto} cuadre=${gasto.cuadre_del_reparto || {}} textos=${textos} />
    <${SusRepartos} gasto=${gasto} textos=${textos} />

    ${
      // El formulario de repartir: el método lo confirma el agricultor, y los cuatro se ofrecen con
      // su nombre. Va aparte del de apuntar el gasto porque se puede repetir las veces que haga falta.
      repartiendo
        ? html`<${Formulario} formulario=${repartiendo} guardando=${guardando} />`
        : html`
            <div className="barra-acciones">
              <${Boton} etiqueta=${g.repartir} accion="gasto-repartir" datos=${repartir} />
              <${Boton}
                etiqueta=${g.dejarlo_sin_asignar}
                accion="gasto-sin-asignar"
                datos=${sinAsignar}
                clase="boton-claro"
              />
            </div>
          `
    }

    ${
      pagos.length
        ? html`
            <h2>${frase(g.sus_pagos)}</h2>
            <ul className="lista">
              ${pagos.map((pago, indice) => {
                const datos = { id: pago.id, aplicacion: pago.aplicacion_id };
                return html`
                  <li key=${indice}>
                    <strong>${frase(pago.texto_importe)}</strong>
                    <p className="pista-campo">${frase(pago.texto_aplicado)}</p>
                    <${Botones}
                      botones=${[
                        {
                          etiqueta: g.pago_deshacer,
                          accion: "gasto-pago-deshacer",
                          datos: datos,
                          clase: "boton-claro",
                          sencillo: true,
                        },
                      ]}
                      barra=${false}
                    />
                  </li>
                `;
              })}
            </ul>
          `
        : null
    }

    <div className="barra-acciones">
      <${Boton} etiqueta=${g.corregir} accion="gasto-nuevo" datos=${corregir} />
      <${Boton}
        etiqueta=${g.anular}
        accion="gasto-anular"
        datos=${anular}
        clase="boton-claro"
      />
      <${BotonSencillo} etiqueta=${acciones.volver} accion="gastos-ver" />
    </div>
  `;
}

/** El elemento de React de esta pantalla, ya con sus propiedades puestas. */
export function pantallaDeLasCuentas(propiedades) {
  return html`<${PantallaDeLasCuentas}
    textos=${propiedades.textos}
    cuentas=${propiedades.cuentas}
    tabla=${propiedades.tabla}
    resumen=${propiedades.resumen}
    filtro=${propiedades.filtro}
    formulario=${propiedades.formulario}
    anulando=${propiedades.anulando}
    guardando=${propiedades.guardando}
    error=${propiedades.error}
    aviso=${propiedades.aviso}
  />`;
}

/** Y la ficha de un gasto. */
export function pantallaDeUnGasto(propiedades) {
  return html`<${PantallaDeUnGasto}
    textos=${propiedades.textos}
    gasto=${propiedades.gasto}
    pagos=${propiedades.pagos}
    formulario=${propiedades.formulario}
    repartiendo=${propiedades.repartiendo}
    anulando=${propiedades.anulando}
    guardando=${propiedades.guardando}
    error=${propiedades.error}
    aviso=${propiedades.aviso}
  />`;
}
