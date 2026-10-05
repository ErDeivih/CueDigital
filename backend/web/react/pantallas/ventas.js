/*
 * ventas.js — «Lo que he vendido», escrita en React. **La pantalla del T12**: la entrega, la factura y el dinero.
 *
 * QUÉ CAMBIA CON EL T12, Y POR QUÉ NO SE PODÍA QUEDAR COMO ESTABA
 *
 * La pantalla era una lista de tarjetas: cada venta con su fecha, su producto y sus datos. Estaba bien
 * para lo que hacía —contestar «¿qué he vendido este año?»— y desde el T12 tiene que contestar a tres
 * preguntas más, que son las del contrato (§4, S12):
 *
 *  1. **Una tabla con cliente, producto, fecha, cantidad, importe conocido, vencimiento, cobrado y
 *     pendiente.** En el ordenador se miran de arriba abajo, y son ocho columnas: eso no cabe en una
 *     tarjeta y por eso la lista pasa a tabla en el ordenador y se queda en tarjetas en el móvil (las
 *     dos formas, el mismo HTML, el CSS decide: es la regla de `.solo-escritorio` / `.solo-movil`).
 *  2. **Un pie con la cuenta del conjunto filtrado**, no de lo que se ve. El contrato lo pide así:
 *     «las sumas no se calculan sobre la página visible: el servidor devuelve el agregado del conjunto
 *     filtrado». Por eso el pie **lo compone el servidor** y aquí solo se coloca.
 *  3. **Las cuatro cosas separadas**: la entrega (esta lista), la factura nuestra y el cobro tienen
 *     cada uno su pantalla, y desde aquí se llega a las otras dos.
 *
 * LO QUE ESTE COMPONENTE **NO** HACE, Y ES LO MÁS IMPORTANTE DE ÉL
 *
 *  · **No hace ni una cuenta de dinero.** Ni suma importes, ni resta lo cobrado, ni calcula un
 *    pendiente, ni formatea un euro. Todo eso llega ya hecho del servidor, en texto, porque **en
 *    JavaScript todo número es de coma flotante y `0,10 + 0,20` no da `0,30`**: la cuenta de la
 *    pantalla sería otra cuenta distinta de la del servidor, y un agricultor que vea dos cifras
 *    distintas para lo mismo deja de fiarse de las dos. Aquí se coloca lo que llega, tal cual.
 *  · **No decide qué está bien y qué está mal.** El estado de cada fila («falta el importe», «cobrada
 *    en parte», «vencida») lo dice el servidor con su palabra; el color, si lo lleva, es un adorno que
 *    va **además** de la palabra y nunca en su lugar.
 *  · **No compone ninguna frase.** Los textos llegan por propiedades, del servidor. Aquí no hay ni una
 *    palabra escrita a mano: lo comprueba una prueba (`test_las_ventas_no_llevan_ni_una_frase_escrita_a_mano`).
 */

import { Boton, Botones, frase, html } from "../componentes.js";
import { AccionesDeUnaFicha } from "../piezas/acciones_de_una_ficha.js";
import { Tabla } from "../piezas/tabla.js";

/**
 * La barra de buscar y filtrar.
 *
 * **El campo lleva su `id`** (`buscar_venta`) porque es lo que lee `app.js` para saber qué se ha
 * escrito: en el DOM de mentira de las pruebas de JavaScript no hay campos, así que esto solo se puede
 * comprobar de verdad en un navegador (y así se comprueba).
 *
 * Y los filtros **dicen cuántos hay con ese filtro puesto** con las palabras del servidor: un botón
 * que dice «SOLO LO QUE FALTA POR COBRAR» se pulsa cuando se sabe que hay algo que cobrar.
 */
function BarraDeFiltros({ textos, filtros = {}, cuantos = {} }) {
  const v = textos.venta || {};
  const acciones = textos.acciones || {};
  return html`
    <div className="franja-filtros">
      <div className="campo-fila">
        <div className="campo">
          <label htmlFor="buscar_venta">${frase(v.buscar)}</label>
          <p className="pista-campo">${frase(v.buscar_pista)}</p>
          <input id="buscar_venta" type="search" defaultValue=${frase(filtros.q || "")} />
        </div>
        <div className="barra-acciones">
          <button type="button" className="boton" data-accion="ventas-buscar">
            ${frase(v.buscar_boton)}
          </button>
          ${
            filtros.q || filtros.solo
              ? html`<button type="button" className="boton boton-claro" data-accion="ventas-ver-todas">
                  ${frase(v.buscar_limpiar)}
                </button>`
              : null
          }
        </div>
      </div>
      <${Botones}
        botones=${[
          {
            etiqueta: `${v.solo_pendientes}${cuantos.por_cobrar ? ` (${cuantos.por_cobrar})` : ""}`,
            accion: "ventas-solo-pendientes",
            clase: filtros.solo === "pendientes" ? "boton" : "boton-claro",
            sencillo: true,
          },
          {
            etiqueta: `${v.solo_sin_importe}${cuantos.sin_importe ? ` (${cuantos.sin_importe})` : ""}`,
            accion: "ventas-solo-sin-importe",
            clase: filtros.solo === "sin_importe" ? "boton" : "boton-claro",
            sencillo: true,
          },
        ]}
        barra=${false}
      />
    </div>
  `;
}

/**
 * Una entrega, en tarjeta: la forma del móvil.
 *
 * **Los datos salen con su nombre**, como en el resto de la aplicación desde la ronda 86: «1.839,50 €»
 * no dice si es lo que vale o lo que falta por cobrar, y en una pantalla de dinero eso es la mitad del
 * dato. Cada fila trae su rótulo del servidor.
 */
function Tarjeta({ fila, textos }) {
  const v = textos.venta || {};
  const datos = [
    // **«A quién», en la tarjeta del móvil**, que es como lo pregunta el resto de la aplicación al apuntar
    // una venta («¿A quién se lo has vendido?») y como lo llama el bloque de «mi cuaderno». En la tabla del
    // ordenador la columna se llama «Cliente», que es el nombre del contrato (§4, S12): son dos vistas del
    // mismo dato, con el rótulo que le corresponde en cada sitio, y los dos vienen del servidor.
    [v.tabla_quien, fila.cliente],
    [v.tabla_cantidad, fila.cantidad],
    [v.tabla_importe, fila.importe],
    [v.tabla_vencimiento, fila.vencimiento],
    [v.tabla_cobrado, fila.cobrado],
    [v.tabla_pendiente, fila.pendiente],
    [v.tabla_lote, fila.partida],
    [v.tabla_albaran, fila.albaran],
    [v.tabla_donde, fila.donde],
  ].filter(([, valor]) => valor);
  return html`
    <li>
      ${
        // La fecha con su rótulo («Fecha: 10/07/2026») y el estado **cada uno en su renglón**, y los dos
        // compuestos por el servidor: aquí no se junta ni una frase. El estado va con su palabra y no
        // solo con un color: al sol, «Cobrada en parte» se lee y un fondo ámbar no.
        fila.fecha_linea ? html`<p className="pista-campo">${frase(fila.fecha_linea)}</p>` : null
      }
      ${fila.estado ? html`<p className="pista-campo"><strong>${frase(fila.estado)}</strong></p>` : null}
      <strong>${frase(fila.producto)}</strong>
      <dl>
        ${datos.map(
          (par, indice) => html`
            <div className="resumen-dato" key=${indice}>
              <dt>${frase(par[0])}</dt>
              <dd>${frase(par[1])}</dd>
            </div>
          `,
        )}
      </dl>
      ${
        fila.cosecha_linea
          ? html`<p className="pista-campo">${frase(fila.cosecha_linea)}</p>`
          : null
      }
      <${AccionesDeUnaFicha} acciones=${fila.acciones} />
    </li>
  `;
}

/**
 * La pantalla entera.
 *
 * Propiedades:
 *
 *  - `textos`: `{ venta, acciones }`, tal y como los sirve `/api/interfaz`.
 *  - `tabla`: lo que devuelve `/api/ventas/tabla` ya preparado por `app.js`: sus columnas (con el
 *    rótulo y por cuál se puede ordenar), sus filas (con las celdas ya escritas), el pie del conjunto
 *    filtrado y los avisos.
 *  - `filtros`: `{q, solo}` para que la barra sepa qué está puesto.
 *  - `resumen`: la línea de cuántas hay, con su palabra (singular y plural los elige el servidor).
 */
export function PantallaVentas({ textos = {}, tabla = {}, filtros = {}, resumen = "", aviso = "" }) {
  const v = textos.venta || {};
  const acciones = textos.acciones || {};
  const filas = tabla.filas || [];
  const totales = tabla.totales || {};
  return html`
    <h1>${frase(v.titulo)}</h1>
    <p className="pista">${frase(v.explica)}</p>
    <p className="pista-campo">${frase(v.lo_que_se_separa)}</p>

    <${BarraDeFiltros} textos=${textos} filtros=${filtros} cuantos=${totales} />

    ${
      // Lo que se acaba de hacer, con las palabras del servidor («Importe apuntado», «Apunte añadido. El
      // importe de la entrega ya lo tiene en cuenta»): volver a la lista sin decir nada deja al
      // agricultor dudando de si se ha guardado. Va en su propio renglón y **no** en el hueco de los
      // fallos, que diría lo mismo con otras palabras.
      aviso ? html`<p className="cuantas" data-aviso="ventas">${frase(aviso)}</p>` : null
    }

    ${
      // **El pie del conjunto filtrado, del servidor.** Camino de `cuantas` para que se lea como el
      // resto de resúmenes de la aplicación, y con su `data-` propio para poder comprobarlo en un
      // navegador de verdad (es el número que tiene que cuadrar con la suma de las filas).
      tabla.pie ? html`<p className="cuantas" data-pie="ventas">${frase(tabla.pie)}</p>` : null
    }
    ${
      // Y lo que **no** entra en esas cuentas, dicho: un total que suma lo que hay y calla que le
      // faltan importes parece que cuadra, y no cuadra. Es el caso A08 del contrato.
      (tabla.avisos || []).map(
        (aviso, indice) => html`<p className="tarjeta-aviso" key=${indice}>
          <span className="tarjeta-aviso-icono" aria-hidden="true">!</span>${frase(aviso)}
        </p>`,
      )
    }
    ${resumen ? html`<p className="pista-campo">${frase(resumen)}</p>` : null}

    ${
      filas.length === 0
        ? html`<div className="aviso">${frase(filtros.q || filtros.solo ? v.vacio_filtro : v.sin_nada)}</div>`
        : html`
            ${
              // **La tabla del ordenador va dentro de su contenedor de desplazamiento**, y no es un adorno:
              // con ocho columnas y sus botones, a 1024 px la tabla mide más que la pantalla, y sin el
              // contenedor lo que se desplaza es **la página entera** (medido: 2.488 px de ancho en un hueco
              // de 1.024). El contrato pide que a 1024 px «ninguna acción quede fuera por desplazamiento
              // horizontal sin indicación»: con el contenedor, la tabla se desplaza dentro de su caja y los
              // botones se alcanzan, y el resto de la pantalla se queda quieta.
              html`<div className="solo-escritorio tabla-scroll"><${Tabla} tabla=${tabla} /></div>`
            }
            <ul className="lista solo-movil">
              ${filas.map((fila, indice) => html`<${Tarjeta} key=${indice} fila=${fila} textos=${textos} />`)}
            </ul>
          `
    }

    <p className="pista-campo">${frase(v.dinero_fuera)}</p>
    <div className="barra-acciones">
      <${Boton} etiqueta=${v.anadir} accion="ventas-nueva" />
      <${Boton} etiqueta=${v.facturas_abrir} accion="facturas-emitidas-ver" clase="boton-claro" />
      <${Boton} etiqueta=${v.cobros_abrir} accion="cobros-ver" clase="boton-claro" />
      <${Boton} etiqueta=${acciones.volver} accion="inicio" datos=${{ ir: "mi_cuaderno" }} clase="boton-claro" />
    </div>
  `;
}

/** El elemento de React de esta pantalla, ya con sus propiedades puestas. */
export function pantallaDeVentas(propiedades) {
  return html`<${PantallaVentas}
    textos=${propiedades.textos}
    tabla=${propiedades.tabla}
    filtros=${propiedades.filtros}
    resumen=${propiedades.resumen}
    aviso=${propiedades.aviso}
  />`;
}
