/*
 * hecho.js — La pantalla que sale después de apuntar algo, escrita en React.
 *
 * POR QUÉ ESTA PANTALLA ES LA SEGUNDA
 *
 * Después de la de inicio, esta es la que más veces ve el agricultor en un día: sale cada vez que
 * apunta un producto, un abono o un trabajo. Y es la más fácil de pasar a React **sin riesgo**,
 * porque no tiene ni un campo de formulario: la pantalla vieja leía los datos del DOM por su `id` y
 * esta no lee nada. Todo lo que necesita son los datos del apunte que se acaba de guardar.
 *
 * QUÉ SE CONSERVA A PROPÓSITO (igual que en `inicio.js`)
 *
 *  1. Los mismos `data-accion`, `data-tipo` y `data-id`: los clics los despacha **un solo manejador
 *     delegado** en `document` que lee `elemento.dataset.accion`. Si cambia un `data-accion`, el
 *     botón deja de hacer nada.
 *  2. Las mismas `className` de `estilos.css` (`.aviso`, `.ayuda-campo`, `.barra-acciones`,
 *     `.boton`, `.boton-peligro`). Aquí no hay ni un `style`.
 *  3. **Los avisos que bloquean no se enseñan aquí**: si algo bloquea, el apunte no se ha guardado y
 *     esta pantalla no sale. Se filtran, como en la interfaz vieja, para no decir dos cosas a la vez.
 *  4. Los textos vienen del servidor (`textos.py` por `GET /api/interfaz`) y se piden a los mismos
 *     bloques que usaba la pantalla vieja: `aviso` para «Apuntado…», `mensajes` para el aviso sin
 *     cobertura y para los días de espera, y `acciones` para las palabras de los botones.
 *  5. **Nada de `esc()`**: React escapa solo.
 *
 * Y una cosa que **no** se copia: la frase de los días de espera se rellena con `rellena()` de
 * `nucleo.js`, que es el mismo que usa el resto del programa. Copiar aquí un `replace` propio sería
 * tener dos formas de rellenar un hueco, y un día se cambiaría una y no la otra.
 */

import { formateaFecha, rellena } from "../../nucleo.js";

/** React, tal y como lo ha dejado el fichero de `vendor`. */
function react() {
  const React = globalThis.React;
  if (!React) throw new Error("faltan los ficheros de React de web/vendor");
  return React;
}

/** La plantilla `html` de htm, atada a React. Se arma la primera vez que hace falta. */
let plantilla = null;

function html(cadenas, ...valores) {
  if (!plantilla) {
    if (typeof globalThis.htm !== "function") {
      throw new Error("faltan los ficheros de React de web/vendor");
    }
    plantilla = globalThis.htm.bind(react().createElement);
  }
  return plantilla(cadenas, ...valores);
}

/** Un texto del servidor, en texto. Lo que no viene, no se escribe. */
function frase(valor) {
  return valor === null || valor === undefined ? "" : String(valor);
}

/**
 * La pantalla de confirmación.
 *
 * Propiedades:
 *
 *  - `textos`: los bloques del servidor que usa esta pantalla (`{ aviso, mensajes, acciones }`).
 *  - `resultado`: lo que ha contestado el servidor al guardar: `{ id, datos, avisos, encolado }`.
 *  - `tipo`: de qué es el apunte («tratamiento», «fertilizacion», «labor»…). Va en el `data-tipo` del
 *    botón de deshacer, que es lo que el manejador necesita para saber qué deshacer.
 */
export function PantallaHecho({ textos = {}, resultado = {}, tipo = "", queEs = "", filas = [] }) {
  const aviso = textos.aviso || {};
  const mensajes = textos.mensajes || {};
  const acciones = textos.acciones || {};
  const corregir = textos.corregir || {};
  const datos = resultado.datos || {};

  // Solo los avisos que **no** bloquean. Los que bloquean significan que el apunte no se ha
  // guardado, y entonces esta pantalla no se habría abierto: enseñarlos aquí sería contradecirse.
  const avisos = (resultado.avisos || []).filter((uno) => !uno.bloquea);

  // **Esta pantalla sirve para dos cosas distintas desde la ronda 91**: para decir «apuntado» y para
  // decir «corregido». Lo dice el servidor de la aplicación (`resultado.corregido`), no se adivina por
  // los datos: decirle «Apuntado» a quien acaba de cambiar un apunte le haría pensar que tiene dos.
  const corregido = Boolean(resultado.corregido);

  // La fecha va en el formato de aquí (`07/10/2026`), no como la manda el servidor (`2026-10-07`):
  // el agricultor lee la primera. Se formatea con el mismo `formateaFecha` que usa todo el programa.
  const espera = datos.fecha_fin_plazo_seguridad
    ? rellena(frase(mensajes.V8_dias_de_espera), {
        fin: formateaFecha(datos.fecha_fin_plazo_seguridad),
      })
    : "";

  return html`
    <h1>${frase(corregido ? corregir.hecho_titulo : aviso.apuntado_ok)}</h1>
    ${corregido && corregir.hecho ? html`<p className="pista">${frase(corregir.hecho)}</p>` : null}
    ${
      resultado.encolado
        ? html`<div className="aviso">${frase(mensajes.sin_cobertura)}</div>`
        : null
    }
    ${avisos.map(
      (uno, indice) => html`<div className="aviso" key=${indice}>${frase(uno.mensaje)}</div>`,
    )}
    ${
      // **Lo que se acaba de apuntar** (diseño de Stitch de la lámina de piezas, ronda 90): la pantalla decía
      // «Apuntado» y nada más, así que el agricultor no podía comprobar que se había entendido lo que él
      // quería apuntar. Va en una ficha de dos columnas, como las cuentas del almacén y los datos de una venta.
      filas.length
        ? html`
            ${queEs ? html`<h2>${frase(queEs)}</h2>` : null}
            <dl>
              ${filas.map(
                (fila, indice) => html`
                  <div className="resumen-dato" key=${indice}>
                    <dt>${frase(fila.etiqueta)}</dt>
                    <dd>${frase(fila.valor)}</dd>
                  </div>
                `,
              )}
            </dl>
          `
        : null
    }
    ${
      // **El plazo de espera, en su franja de aviso** (diseño de Stitch de esta pantalla, ronda 90): es el
      // dato que puede costarle la cosecha —«con lo que has echado hoy, hasta tal día no la puedes
      // coger»— y estaba en un párrafo suelto, del mismo aspecto que el resto. Con la franja y su señal
      // se lee antes que nada, que es lo que tiene que pasar.
      espera
        ? html`
            <p className="tarjeta-aviso tarjeta-aviso-grande">
              <span className="tarjeta-aviso-icono" aria-hidden="true">!</span>
              ${espera}
            </p>
          `
        : null
    }
    ${
      // Y los botones, con el diseño de Stitch: primero el que se pulsa el 99 % de las veces (volver al
      // inicio) y **debajo el de deshacer**, con su explicación («por si te has confundido de tierra,
      // producto o dosis»). Antes iban en la misma fila y en el otro orden, así que el botón de deshacer
      // —el único que puede borrar algo— era el primero que encontraba el dedo.
      html`
        <div className="barra-acciones">
          <button type="button" className="boton boton-principal" data-accion="ir-inicio">
            ${frase(acciones.volver)}
            <span className="flecha" aria-hidden="true">→</span>
          </button>
        </div>
      `
    }
    ${
      // **CORREGIRLO, justo debajo de volver** (ronda 91): la mitad de las equivocaciones se ven aquí
      // —el agricultor acaba de leer el resumen en el móvil y se da cuenta de la dosis o de la tierra—,
      // y hasta esta ronda la única salida era DESHACER, que anula el apunte entero y lo deja tachado en
      // el cuaderno. Corregir es lo que de verdad quiere: cambiar ese dato, no borrar el apunte.
      resultado.id
        ? html`
            <button
              type="button"
              className="boton boton-claro"
              data-accion="hecho-corregir"
              data-tipo=${frase(tipo)}
              data-id=${String(resultado.id)}
            >
              <span className="texto">
                <span>${frase(corregir.boton)}</span>
                ${
                  corregir.boton_mejor_corregirlo
                    ? html`<span className="pista-boton">${frase(corregir.pista)}</span>`
                    : null
                }
              </span>
              <span className="flecha" aria-hidden="true">→</span>
            </button>
          `
        : null
    }
    ${
      // Y el de deshacer, el último y en rojo: es el único botón de la aplicación que puede quitar algo
      // del cuaderno sin dejar nada en su sitio. **Después de corregir no se enseña**: el apunte que se
      // acaba de cambiar ya no es «lo último que he apuntado», y ofrecer ahí «DESHACER» invitaría a
      // anular un apunte que el agricultor acaba de dejar bien. Para quitarlo está BORRAR, en su ficha.
      resultado.id && !corregido
        ? html`
            <button
              type="button"
              className="boton boton-peligro"
              data-accion="deshacer"
              data-tipo=${frase(tipo)}
              data-id=${String(resultado.id)}
            >
              <span className="texto">
                <span>${frase(acciones.deshacer)}</span>
                ${
                  aviso.deshacer_pista
                    ? html`<span className="pista-boton">${frase(aviso.deshacer_pista)}</span>`
                    : null
                }
              </span>
              <span className="flecha" aria-hidden="true">→</span>
            </button>
          `
        : null
    }
  `;
}

/** El elemento de React de esta pantalla, ya con sus propiedades puestas. */
export function pantallaDeHecho(propiedades) {
  return html`
    <${PantallaHecho}
      textos=${propiedades.textos}
      resultado=${propiedades.resultado}
      tipo=${propiedades.tipo}
      queEs=${propiedades.queEs}
      filas=${propiedades.filas}
    />
  `;
}