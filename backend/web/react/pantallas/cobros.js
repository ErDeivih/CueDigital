/*
 * cobros.js — La lista de lo que me han pagado (T12).
 *
 * LA PANTALLA DEL CASO A06, VISTA DESDE EL DINERO
 *
 * «Factura 121 EUR, pago 40 EUR → pendiente 81». Aquí se ve lo que ha entrado, uno por uno, con **de qué
 * factura es cada uno** y **cuánto de ese cobro va contra ella**. Y hay una lista aparte, con su
 * explicación, para el dinero que ha entrado y **todavía no se sabe qué factura salda**: es lo que el
 * contrato pide en su panel de Economía («pagos sin factura quedan por conciliar»). Ese dinero no se
 * pierde: está apuntado y espera.
 *
 * Y UNA COSA QUE ESTA PANTALLA **NO** PUEDE HACER, NUNCA
 *
 * **Apuntar un cobro no crea ninguna factura.** El botón de aquí lleva a apuntar dinero que entra y a
 * decir contra qué factura va; no hay ninguna pantalla de esta sección que emita una factura a partir de
 * un pago. Es la segunda mitad del A06 («un segundo importe conciliado **no crea una segunda factura**») y
 * hay una prueba que cuenta las facturas antes y después para que siga siendo verdad.
 *
 * Lo que no hace: ni una cuenta (lo imputado, lo que sobra y lo que queda llegan calculados del servidor)
 * y ni una frase escrita a mano.
 */

import { Tabla } from "../piezas/tabla.js";
import { Boton, Botones, frase, html } from "../componentes.js";

/** Un cobro de la lista, con lo que va a la factura y lo que sobra. */
function FichaDeCobro({ cobro, textos }) {
  const c = textos.cobro || {};
  return html`
    <li>
      ${
        // La fecha con su rótulo del servidor y la forma de cobro, cada cosa en su sitio.
        cobro.fecha_linea ? html`<p className="pista-campo">${frase(cobro.fecha_linea)}</p>` : null
      }
      <strong>${frase(cobro.texto_importe)}</strong>
      <dl>
        ${
          // **Un cobro repartido entre varias deudas** (CRM-01, 11/10/2026): se enseña **a qué facturas va y
          // cuánto a cada una**. Hacía falta porque la ficha miraba `factura_numero`, que en un reparto va
          // vacío **a propósito** —el dinero vive en las aplicaciones—, así que un ingreso repartido decía
          // «sin factura»: justo lo contrario de lo que acaba de hacer el agricultor. Con una sola no cambia
          // nada, y sin ninguna sigue diciendo que no se sabe de cuál es, que es la verdad.
          (cobro.aplicaciones || []).length > 1
            ? html`<div className="resumen-dato">
                <dt>${frase(c.repartido_entre)}</dt>
                <dd>
                  ${cobro.aplicaciones.map(
                    (a) => html`<div key=${String(a.factura_emitida_id)}>
                      ${frase(a.factura_numero || "")} · ${frase(a.texto_importe)}
                    </div>`,
                  )}
                </dd>
              </div>`
            : html`<div className="resumen-dato">
                <dt>${frase(c.imputado)}</dt>
                <dd>${frase(cobro.factura_numero || c.sin_factura)}</dd>
              </div>`
        }
        ${
          cobro.texto_sin_asignar
            ? html`<div className="resumen-dato">
                <dt>${frase(c.sin_asignar)}</dt>
                <dd>${frase(cobro.texto_sin_asignar)}</dd>
              </div>`
            : null
        }
        <div className="resumen-dato">
          <dt>${frase(c.forma)}</dt>
          <dd>${frase(cobro.etiqueta_forma)}</dd>
        </div>
        <div className="resumen-dato">
          <dt>${frase(c.cliente)}</dt>
          <dd>${frase(cobro.cliente || "")}</dd>
        </div>
        <div className="resumen-dato">
          <dt>${frase(c.referencia)}</dt>
          <dd>${frase(cobro.referencia || "")}</dd>
        </div>
      </dl>
      <${Botones}
        botones=${[
          {
            etiqueta: cobro.factura_emitida_id ? c.deshacer : c.conciliar,
            accion: cobro.factura_emitida_id ? "cobro-desconciliar" : "cobro-conciliar",
            datos: { id: cobro.id },
            clase: "boton-claro",
            sencillo: true,
          },
          { etiqueta: c.anular, accion: "cobro-anular", datos: { id: cobro.id }, clase: "boton-claro", sencillo: true },
        ]}
        barra=${false}
      />
    </li>
  `;
}

/**
 * La tabla de los cobros, para el ordenador.
 *
 * **Se monta aquí, dentro del componente**, y no en `app.js`, por lo que se aprendió con la lista de contactos
 * (11/10/2026): montada allí y pasada como propiedad **no llegaba** —esta pantalla se repinta con los datos de
 * la caché del campo— y la tabla no se veía aunque estuviera construida. Con los cobros que ya recibe, da igual
 * por dónde venga el repintado.
 *
 * **Y el caso del reparto, que casi se me cuela**: un cobro repartido entre varias facturas **no lleva
 * `factura_numero`** —el dinero vive en las aplicaciones, que es como se hizo en CRM-01— y la primera versión
 * de esta tabla caía en el respaldo y escribía «Todavía no sé de qué factura es», **justo lo contrario de la
 * verdad**: sí se sabe, va a dos. Lo cazó una prueba de CRM-01 («un cobro repartido entre varias facturas dice
 * a cuáles va y cuánto a cada una»). Ahora la celda dice **a qué facturas va**, y los importes de cada una
 * siguen en la ficha, que es donde se leen.
 */
function tablaDeLosCobros(cobros, c) {
  const aQueFacturas = (cobro) => {
    const suyas = cobro.aplicaciones || [];
    if (suyas.length) {
      const numeros = suyas.map((aplicacion) => aplicacion.factura_numero).filter(Boolean);
      return numeros.length ? numeros.join(" y ") : c.tabla_repartido || "Varias facturas";
    }
    return cobro.factura_numero || c.sin_factura || "";
  };
  return {
    columnas: [
      { texto: c.fecha, clase: "" },
      { texto: c.cuanto, clase: "tabla-numero" },
      { texto: c.imputado, clase: "" },
      { texto: c.cliente, clase: "" },
      { texto: c.forma, clase: "" },
      { texto: c.tabla_acciones || "Acciones", clase: "tabla-acciones" },
    ],
    filas: cobros.map((cobro) => ({
      celdas: [
        { texto: cobro.fecha_linea || cobro.fecha || "" },
        { texto: cobro.texto_importe || "" },
        { texto: aQueFacturas(cobro) },
        { texto: cobro.cliente || "" },
        { texto: cobro.etiqueta_forma || "" },
      ],
      acciones: [
        {
          accion: cobro.factura_emitida_id ? "cobro-desconciliar" : "cobro-conciliar",
          texto: cobro.factura_emitida_id ? c.deshacer : c.conciliar,
          datos: { id: cobro.id },
        },
        { accion: "cobro-anular", texto: c.anular, datos: { id: cobro.id } },
      ],
    })),
  };
}

/**
 * La pantalla entera.
 *
 * Propiedades:
 *
 *  - `textos`: `{ cobro, acciones }` del servidor.
 *  - `cobros`: todos los cobros, del más nuevo al más viejo, con su imputación ya calculada.
 *  - `sin_asignar`: solo los que no se sabe de qué factura son (los mismos, para su lista aparte).
 *  - `resumen`: cuántos hay, en singular o plural (lo elige `app.js`).
 *  - `error`: lo que ha dicho el servidor, o nada.
 */
export function PantallaCobros({
  textos = {},
  cobros = [],
  sin_asignar = [],
  resumen = "",
  error = "",
  // ***Y si la carga fallo*** (21/10/2026, D03): *«no hay cobros» es una afirmacion sobre la finca; «no se pudieron
  // cargar», sobre la red. **No se puede afirmar lo primero sin haber podido preguntar.***
  noSePudoCargar = false,
}) {
  const c = textos.cobro || {};
  const acciones = textos.acciones || {};
  // **La tabla, en el ordenador**: medido, esta pantalla pintaba **una tarjeta por cobro** y ninguna tabla,
  // donde un programa de gestión enseña filas. Se monta con los cobros que ya recibe.
  const laTabla = cobros.length ? tablaDeLosCobros(cobros, c) : null;
  return html`
    <h1>${frase(c.titulo)}</h1>
    <p className="pista">${frase(c.explica)}</p>
    ${error ? html`<p className="aviso-error" role="alert">${frase(error)}</p>` : null}
    ${resumen ? html`<p className="cuantas">${frase(resumen)}</p>` : null}

    ${
      laTabla
        ? html`<div className="solo-escritorio tabla-scroll"><${Tabla} tabla=${laTabla} /></div>`
        : null
    }

    ${
      cobros.length === 0
        ? noSePudoCargar
          ? // ***No se repite el «no hay»***: *seria mentira; arriba ya se dice cual fallo y se ofrece reintentar.*
            html`<div className="aviso aviso-error">${frase(c.sin_cobros_fallo)}</div>`
          : html`<div className="aviso">${frase(c.sin_nada)}</div>`
        : html`<ul className="lista">
            ${cobros.map(
              (cobro, indice) => html`<${FichaDeCobro} key=${indice} cobro=${cobro} textos=${textos} />`,
            )}
          </ul>`
    }

    ${
      // El dinero que ha entrado y no se sabe a qué va, **dicho aparte y con su explicación**: no se
      // pierde, solo está esperando a saber contra qué factura va.
      sin_asignar.length
        ? html`
            <h2>${frase(c.sin_asignar_titulo)}</h2>
            <p className="pista-campo">${frase(c.sin_asignar_explica)}</p>
          `
        : null
    }

    <div className="barra-acciones">
      <${Boton} etiqueta=${c.nuevo} accion="cobro-nuevo" />
      <${Boton} etiqueta=${acciones.volver} accion="ventas-ver" clase="boton-claro" />
    </div>
  `;
}

/** El elemento de React de esta pantalla, ya con sus propiedades puestas. */
export function pantallaDeCobros(propiedades) {
  return html`<${PantallaCobros}
    textos=${propiedades.textos}
    cobros=${propiedades.cobros}
    sin_asignar=${propiedades.sin_asignar}
    resumen=${propiedades.resumen}
    error=${propiedades.error}
  />`;
}
