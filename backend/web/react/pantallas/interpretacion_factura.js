/*
 * interpretacion_factura.js — Lo que el programa ha leído de una factura, para que el agricultor lo
 * confirme. Escrita en React.
 *
 * POR QUÉ ESTA PANTALLA, Y POR QUÉ ES LA MÁS IMPORTANTE DEL APARTADO
 *
 * Es la vigesimoprimera que se pasa a React y es **la pantalla que hace que leer una factura se pueda
 * usar sin jugarse un dato del cuaderno**. Lo que el programa saca de una foto es **una propuesta**:
 * el agricultor la mira, la corrige y da el visto bueno. Si esto fuera un «ya está guardado», el
 * programa estaría metiendo en el cuaderno lo que ha adivinado de una foto, y eso es justo lo que no
 * se puede hacer.
 *
 * Y no es una precaución teórica: una foto hecha con el móvil siempre trae alguna errata (el lector de
 * letras de este ordenador, por ejemplo, solo tiene el idioma inglés y las palabras con eñe salen
 * cambiadas). Por eso **todo lo leído está en un campo editable**, y por eso se dice de dónde sale la
 * lectura y qué avisos hay.
 *
 * LO QUE SE CONSERVA A PROPÓSITO
 *
 *  1. **Los `id` de todos los campos**, que son los que lee `guardarFactura()` al confirmar: los ocho
 *     de la cabecera (`factura-proveedor`, `factura-proveedor-nif`, `factura-numero`, `factura-fecha`,
 *     `factura-base`, `factura-cuota`, `factura-tipo-iva`, `factura-total`) y los seis de cada línea
 *     (`factura-<n>-descripcion`, `-cantidad`, `-unidad`, `-precio`, `-importe`, `-producto`).
 *  2. Los campos van con su valor puesto (`defaultValue`, no `value`): así el agricultor ve lo leído,
 *     lo puede cambiar, y React no se pelea con lo que escribe.
 *  3. **El botón de guardar dice «Guardando la factura…» mientras guarda**, y no se puede volver a
 *     pulsar: sin eso, la misma factura se puede guardar dos veces.
 *  4. Los avisos de la lectura van en su bloque, con el aviso de la línea que no cuadra en su línea y
 *     en rojo: son la mitad del valor de esta pantalla.
 *  5. Nada de `esc()` y ninguna frase escrita aquí: los textos llegan por propiedades.
 *
 * El componente es PURO: no llama a `fetch`, no calcula y no toca el DOM. Los números y los textos con
 * huecos (`Es este: {producto}`) vienen ya preparados de `app.js`.
 */

import { AvisoDeError, Boton, frase, html } from "../componentes.js";

/** Un campo del formulario, con su etiqueta, su pista y lo que trae leído. */
function Campo({ campo }) {
  return html`
    <div className="campo">
      <label htmlFor=${campo.id}>${frase(campo.etiqueta)}</label>
      ${campo.pista ? html`<p className="pista-campo">${frase(campo.pista)}</p>` : null}
      <input
        id=${campo.id}
        type=${campo.tipo || "text"}
        inputMode=${campo.tipo === "text" ? undefined : "decimal"}
        defaultValue=${frase(campo.valor)}
      />
    </div>
  `;
}

/** Una línea de la factura, entera editable: lo leído se puede corregir campo a campo. */
function Linea({ linea, indice, textos }) {
  const f = textos.facturas || {};
  const id = (nombre) => `factura-${indice}-${nombre}`;

  return html`
    <li className="linea-factura" data-linea=${indice}>
      ${
        // **La etiqueta de la línea que hay que revisar** (diseño de Stitch de esta pantalla, ronda 90): cuando
        // la cuenta de una línea no cuadra, el aviso va al final de la línea, y con tres o cuatro líneas se
        // acaba leyendo la pantalla entera para saber cuál es. La etiqueta lo dice arriba y de un vistazo.
        linea.no_cuadra
          ? html`<span className="etiqueta-estado etiqueta-estado-mirar">${frase(f.revisar_numeros)}</span>`
          : null
      }
      <div className="campo">
        <label htmlFor=${id("descripcion")}>${frase(f.linea_descripcion)}</label>
        <input id=${id("descripcion")} type="text" defaultValue=${frase(linea.descripcion)} />
      </div>
      <div className="campo-fila">
        <div className="campo">
          <label htmlFor=${id("cantidad")}>${frase(f.linea_cantidad)}</label>
          <input
            id=${id("cantidad")}
            type="text"
            inputMode="decimal"
            defaultValue=${frase(linea.cantidad)}
          />
        </div>
        <div className="campo">
          <label htmlFor=${id("unidad")}>${frase(f.linea_unidad)}</label>
          <input id=${id("unidad")} type="text" defaultValue=${frase(linea.unidad)} />
        </div>
      </div>
      <div className="campo-fila">
        <div className="campo">
          <label htmlFor=${id("precio")}>${frase(f.linea_precio)}</label>
          <input
            id=${id("precio")}
            type="text"
            inputMode="decimal"
            defaultValue=${frase(linea.precio)}
          />
        </div>
        <div className="campo">
          <label htmlFor=${id("importe")}>${frase(f.linea_importe)}</label>
          <input
            id=${id("importe")}
            type="text"
            inputMode="decimal"
            defaultValue=${frase(linea.importe)}
          />
        </div>
      </div>
      <div className="campo">
        <label htmlFor=${id("producto")}>${frase(f.linea_producto)}</label>
        <select id=${id("producto")}>
          ${linea.opciones.map(
            (opcion) => html`
              <option value=${opcion.valor} selected=${opcion.elegido} key=${opcion.valor}>
                ${frase(opcion.texto)}
              </option>
            `,
          )}
        </select>
      </div>
      ${
        // Lo que el programa ha entendido de esa línea, para que se vea de dónde sale cada número. Va en su
        // franja de aviso, con su señal: es «algo que hay que mirar».
        linea.no_cuadra
          ? html`
              <p className="tarjeta-aviso">
                <span className="tarjeta-aviso-icono" aria-hidden="true">!</span>
                ${frase(f.linea_no_cuadra)}
              </p>
            `
          : null
      }
      ${
        linea.sugerida
          ? html`<p className="pista-campo">${frase(linea.sugerida)}</p>`
          : null
      }
      ${
        linea.registro
          ? html`<p className="pista-campo">${frase(linea.registro)}</p>`
          : null
      }
    </li>
  `;
}

/**
 * La pantalla entera.
 *
 * Propiedades:
 *
 *  - `textos`: `{ facturas, acciones }`, tal y como los sirve `/api/interfaz`.
 *  - `leida`: lo que ha devuelto el servidor, ya preparado por `app.js`: de dónde sale la lectura,
 *    los avisos, los ocho campos de la cabecera y las líneas con sus opciones de producto.
 *  - `error`: lo que ha dicho el servidor (o vacío).
 *  - `guardando`: si se está guardando ahora mismo.
 *  - `corrigiendo`: si lo que se enseña **no es lo que se acaba de leer sino lo que ya está guardado**
 *    (ronda 93). Cambia tres cosas y ninguna más: el título (no se ha leído nada, se está arreglando una
 *    factura que ya está en el cuaderno), la pista (dice que lo de antes queda apuntado) y el botón de
 *    volver (a la lista de facturas, no a «añadir una factura», que es de donde se viene al leer). Los
 *    campos y las líneas se pintan igual a propósito: **corregir una factura es el mismo trabajo** que
 *    confirmar una lectura.
 */
export function PantallaInterpretacionDeLaFactura({
  textos = {},
  leida = {},
  error = "",
  guardando = false,
  corrigiendo = false,
}) {
  const f = textos.facturas || {};
  const cabecera = Array.isArray(leida.cabecera) ? leida.cabecera : [];
  const lineas = Array.isArray(leida.lineas) ? leida.lineas : [];

  return html`
    <h1>${frase(corrigiendo ? f.corregir_titulo : f.interpretacion_titulo)}</h1>
    <p className="pista">${frase(corrigiendo ? f.corregir_pista : f.interpretacion_pista)}</p>
    ${
      // De dónde sale la lectura: es lo que explica por qué puede haber erratas en las palabras. La
      // frase viene montada de `app.js` **porque son dos textos del servidor unidos**: dentro de un
      // componente, una frase compuesta es una frase escrita a mano.
      leida.de_donde
        ? html`<p className="pista-campo">${frase(leida.de_donde)}</p>`
        : null
    }
    ${
      leida.avisos && leida.avisos.length
        ? html`<h2>${frase(f.avisos_titulo)}</h2>
            ${leida.avisos.map(
              (aviso, indice) => html`<p className="aviso" key=${indice}>${frase(aviso)}</p>`,
            )}`
        : null
    }
    <${AvisoDeError} texto=${error} />
    ${cabecera.map((campo, indice) => html`<${Campo} key=${indice} campo=${campo} />`)}
    <h2>${frase(f.lineas_titulo)}</h2>
    <p className="pista-campo">${frase(f.lineas_pista)}</p>
    <ul className="lista">
      ${lineas.map(
        (linea, indice) => html`<${Linea} key=${indice} linea=${linea} indice=${indice} textos=${textos} />`,
      )}
    </ul>
    <div className="barra-acciones">
      <button type="button" className="boton" data-accion="factura-guardar" disabled=${guardando}>
        ${frase(
          guardando
            ? f.guardando
            : corrigiendo
              ? f.corregir_confirmar
              : f.confirmar,
        )}
      </button>
      <${Boton}
        etiqueta=${corrigiendo ? f.corregir_volver : f.volver}
        accion=${corrigiendo ? "facturas-abrir" : "factura-nueva"}
        clase="boton-claro"
      />
    </div>
  `;
}

/** El elemento de React de esta pantalla, ya con sus propiedades puestas. */
export function pantallaDeInterpretacionDeLaFactura(propiedades) {
  return html`<${PantallaInterpretacionDeLaFactura}
    textos=${propiedades.textos}
    leida=${propiedades.leida}
    error=${propiedades.error}
    guardando=${propiedades.guardando}
    corrigiendo=${propiedades.corrigiendo}
  />`;
}
