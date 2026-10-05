/*
 * traer_del_sigpac.js — Traer la tierra del SIGPAC: buscar el recinto oficial y apuntarlo sin teclear
 * ocho datos a mano.
 *
 * POR QUÉ ES UNA PANTALLA Y NO UNA PIEZA
 *
 * Es el sitio donde el agricultor **encuentra su tierra en el mapa oficial** en vez de copiarla de un
 * papel: se elige la provincia, se busca el pueblo por las primeras letras, se dice el polígono y la
 * parcela (o se pega la referencia tal y como venga), y el programa pregunta al SIGPAC por los recintos
 * de esa tierra. Cada recinto se enseña con su superficie, su uso y su pendiente, y **se marca el que se
 * quiera traer**: con cuarenta parcelas, esta pantalla es la diferencia entre empezar y abandonar.
 *
 * Se migró como **pantalla** (no con las piezas del asistente) porque tiene cosas que no tiene ningún
 * otro paso: un desplegable, botones dentro de un campo, listas de `li` y el dibujo de cada recinto. Es
 * un paso del asistente de dar de alta una tierra, pero es una pantalla entera metida en un paso.
 *
 * LO QUE NO SE PUEDE ROMPER
 *
 *  1. **Los `id` de los campos son los de siempre** (`provincia_sigpac`, `municipio_sigpac`,
 *     `poligono_sigpac`, `parcela_sigpac`, `ref_sigpac`, `alias_sigpac`): `app.js` los lee por ahí
 *     (`recogeElSigpac`). Si cambia uno, el agricultor rellena el formulario y se guarda vacío.
 *  2. **Las acciones son las de siempre** (`buscar-pueblo`, `elegir-pueblo`, `buscar-trozos`,
 *     `marcar-trozo`, `traer-marcados`), que es lo que lee el manejador de clics.
 *  3. **Los textos y las frases compuestas vienen de `app.js`**: aquí no se junta un texto con otro.
 *
 * El componente es PURO: no llama a `fetch` y no toca el DOM.
 */

import { Boton, frase, html } from "../componentes.js";

/** Un campo de escribir del formulario, con su `id` y su etiqueta. */
function CampoDeTexto({ id, etiqueta, valor, placeholder, pista, tipo = "texto" }) {
  return html`
    <div className="campo">
      <label htmlFor=${id}>${frase(etiqueta)}</label>
      <input
        id=${id}
        type="text"
        inputMode=${tipo === "entero" ? "numeric" : null}
        placeholder=${placeholder || null}
        defaultValue=${valor}
      />
      ${pista ? html`<p className="pista-campo">${frase(pista)}</p>` : null}
    </div>
  `;
}

/** Un recinto del SIGPAC: su botón para marcarlo y su referencia debajo. */
function Recinto({ trozo }) {
  return html`
    <li>
      <${Boton}
        etiqueta=${trozo.etiqueta}
        pista=${trozo.pista}
        accion="marcar-trozo"
        datos=${{ referencia: trozo.referencia }}
        clase=${trozo.marcado ? "boton-elegido" : "boton-claro"}
      />
      <div className="apunte-detalle">${frase(trozo.referencia)}</div>
    </li>
  `;
}

/**
 * La pantalla entera.
 *
 * Propiedades:
 *
 *  - `textos`: los bloques del servidor que usa esta pantalla (`{ sigpac, municipios }`).
 *  - `datos`: lo que el agricultor ya tiene puesto y lo que ha traído el SIGPAC, **ya preparado**: las
 *    provincias del desplegable, el pueblo buscado, los recintos que han salido y los valores de cada
 *    campo. Las frases compuestas (el detalle de un recinto, el nombre del pueblo con su provincia) las
 *    monta `app.js`, que es quien conoce los números y las fechas.
 *  - `acciones`: los dos rótulos que vienen del bloque de acciones del servidor, si hicieran falta.
 */
export function PantallaTraerDelSigpac({ textos = {}, datos = {} }) {
  const s = textos.sigpac || {};
  const m = textos.municipios || {};
  const pueblos = datos.pueblos || [];
  const trozos = datos.trozos || [];
  const sistemas = datos.sistemas || [];

  return html`
    <p className="pista-campo">${frase(s.explica)}</p>

    ${
      // **El camino rápido, primero** (diseño de Stitch de esta pantalla, ronda 90): pegar la referencia ahorra
      // teclear seis datos, y estaba abajo del todo, **después** de los seis campos que ahorra. Se lee el
      // camino corto antes que el largo.
      html`
        <h2>${frase(s.camino_rapido)}</h2>
        <${CampoDeTexto}
          id="ref_sigpac"
          etiqueta=${s.referencia_como_sea}
          valor=${datos.ref_sigpac || ""}
          placeholder=${s.referencia_ejemplo}
          pista=${s.referencia_como_sea_pista}
        />
      `
    }

    <h2>${frase(s.o_por_partes)}</h2>
    ${
      // Los seis datos del camino largo, **numerados** (diseño de Stitch): el número lo pone el CSS con un
      // contador, así que cada rótulo sigue siendo el del servidor.
      html`
        <ol className="campos-numerados">
          <li>
            <div className="campo">
              <label htmlFor="provincia_sigpac">${frase(s.provincia_parcela)}</label>
              <select id="provincia_sigpac">
                <option value="">${frase(m.cualquiera)}</option>
                ${(datos.provincias || []).map(
                  (provincia) => html`
                    <option value=${provincia.valor} selected=${provincia.elegido ? true : null}>
                      ${frase(provincia.etiqueta)}
                    </option>
                  `,
                )}
              </select>
            </div>
          </li>
          <li>
            <div className="campo">
              <label htmlFor="municipio_sigpac">${frase(m.elegir)}</label>
              <input
                id="municipio_sigpac"
                type="text"
                defaultValue=${datos.municipio || ""}
                placeholder=${m.pista || null}
              />
              <${Boton} etiqueta=${m.buscar} accion="buscar-pueblo" clase="boton-claro" />
            </div>
          </li>
          <li>
            <${CampoDeTexto}
              id="poligono_sigpac"
              etiqueta=${s.poligono}
              valor=${datos.poligono || ""}
              tipo="entero"
            />
          </li>
          <li>
            <${CampoDeTexto}
              id="parcela_sigpac"
              etiqueta=${s.parcela}
              valor=${datos.parcela || ""}
              tipo="entero"
            />
          </li>
          <li>
            <${CampoDeTexto} id="alias_sigpac" etiqueta=${s.alias} valor=${datos.alias || ""} />
          </li>
          <li>
            <div className="campo">
              <label>${frase(s.sistema)}</label>
              ${sistemas.map(
                (sistema, indice) => html`
                  <${Boton}
                    key=${indice}
                    etiqueta=${sistema.etiqueta}
                    accion="elegir"
                    datos=${{ campo: "sistema", valor: sistema.valor }}
                    clase=${sistema.elegido ? "boton-elegido" : "boton-claro"}
                  />
                `,
              )}
            </div>
          </li>
        </ol>
      `
    }

    ${
      pueblos.length
        ? html`
            <ul className="lista">
              ${pueblos.map(
                (pueblo, indice) => html`
                  <li key=${indice}>
                    <${Boton}
                      etiqueta=${pueblo.etiqueta}
                      pista=${pueblo.pista}
                      accion="elegir-pueblo"
                      datos=${{ nombre: pueblo.nombre, provincia: pueblo.provincia }}
                      clase=${pueblo.elegido ? "boton-elegido" : "boton-claro"}
                    />
                  </li>
                `,
              )}
            </ul>
          `
        : null
    }

    <${Boton} etiqueta=${s.buscar} accion="buscar-trozos" clase="boton-principal" />

    ${
      trozos.length
        ? html`
            <h3>${frase(s.buscar_titulo)}</h3>
            <p className="pista-campo">${frase(s.buscar_explica)}</p>
            <ul className="lista">
              ${trozos.map((trozo, indice) => html`<${Recinto} key=${indice} trozo=${trozo} />`)}
            </ul>
            <${Boton} etiqueta=${s.traer_los_marcados} accion="traer-marcados" clase="boton-principal" />
          `
        : null
    }
  `;
}

/** El elemento de React de esta pantalla, ya con sus propiedades puestas. */
export function pantallaTraerDelSigpac(propiedades) {
  return html`
    <${PantallaTraerDelSigpac}
      textos=${propiedades.textos}
      datos=${propiedades.datos}
      acciones=${propiedades.acciones}
    />
  `;
}
