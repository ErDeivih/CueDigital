/*
 * tierra_versiones.js — Lo que ha sido una tierra: sus versiones, la comparación de dos años y el
 * ensayo de una importación, escritos en React (T06).
 *
 * POR QUÉ ESTA PANTALLA
 *
 * Es la pantalla que T05 dejó pedida y sin hacer. T05 construyó la tabla `versiones_de_recinto`, el
 * servicio que compara dos campañas y las cinco rutas (`/api/versiones`), y lo dijo con estas
 * palabras: «la ficha de una tierra con sus versiones y la previsualización de una importación
 * están por hacer en la interfaz, y son de T06. La API ya devuelve todo lo que hace falta».
 *
 * Lo que se enseña, y por qué cada cosa:
 *
 *  1. **Las versiones, por año y por quién lo dijo.** Una tierra puede tener varias versiones del
 *     mismo año si las dijo fuentes distintas (el SIGPAC y el agricultor, por ejemplo), y **eso no
 *     es un error**: es que dos cosas distintas se saben de la misma tierra.
 *  2. **Las tres áreas, cada una con su nombre y ninguna deducida de otra**: lo que mide la forma que
 *     vino, lo que dice el SIGPAC y lo que declara el agricultor. Cualquiera puede no saberse, y
 *     entonces se dice «No se sabe»: **un cero ahí afirmaría que mide cero hectáreas**.
 *  3. **Cómo está** cada versión, con la frase del servidor: «Sin forma: no ha venido el polígono»,
 *     «La referencia está a medias: falta el número de recinto», «Sin revisar»…
 *  4. **Comparar dos años**, con los cuatro estados del contrato (`igual`, `cambiado`,
 *     `desaparecido`, `nuevo`) y el porqué de cada uno. **Comparar no toca nada**: ni una hectárea ni
 *     un vértice.
 *  5. **Ensayar una importación**: se coge lo que esta tierra tenía en otro año y se pregunta al
 *     servidor **qué pasaría** si se le apuntara. El ensayo no escribe; solo se apunta si el
 *     agricultor pulsa el botón de apuntarlo, y ese botón solo sale cuando hay un ensayo delante.
 *
 * LO QUE ESTE COMPONENTE **NO** HACE
 *
 *  · **No llama a nada.** Es puro: todo le llega por propiedades, ya preparado por `app.js`. El
 *    `POST /api/versiones/previsualizar` y el `POST /api/versiones/aplicar` los hace `app.js` al
 *    pulsar un botón, y **son dos acciones distintas y separadas**, que es lo que hace que
 *    previsualizar no pueda escribir nada: el ensayo ni siquiera tiene un camino que escriba.
 *  · **No calcula ninguna cifra**: los cuatro recuentos de la comparación y del ensayo los da el
 *    servidor (`/api/versiones/comparar`, `/api/versiones/previsualizar`). Aquí se colocan.
 *  · **No monta frases**: lo que lleva un número dentro lo rellena `app.js`. Aquí solo se pinta lo
 *    que llega (ver `docs/REACT.md`, el apartado de las frases compuestas).
 *  · **Nada de `esc()` y nada de `style`**: React escapa solo y los colores viven en `:root`.
 */

import { AvisoDeError, Boton, BotonSencillo, OpcionesParaElegir, frase, html } from "../componentes.js";

/**
 * El lote que se le manda al servidor para ensayar una importación, a partir de las versiones que ya
 * se conocen de esta tierra.
 *
 * **Por qué esto es una función pura y exportada.** Porque es la única parte del ensayo que se puede
 * comprobar sin un servidor delante, y porque tiene una trampa concreta: lo que se manda al servidor
 * es **lo que el agricultor ya tenía ese año**, así que hay que copiar los números de la referencia
 * tal y como vinieron y **no rellenar ninguno** (`versiones_de_recinto.numeros_de_la_referencia` es
 * el mismo criterio al otro lado). Un número inventado aquí daría de alta una tierra que no es.
 *
 * Lo que se manda, y nada más:
 *
 *  · `campana_id` — el año al que se trae (el que se está llevando).
 *  · `fuente` — la misma de la que salieron esas versiones: comparar el SIGPAC con el SIGPAC y lo que
 *    dijo el agricultor con lo que dijo el agricultor (`versiones_de_recinto.comparar_dos_campanas`).
 *  · `recintos` — con `parcela_id` (para que no dé de alta una tierra repetida), los siete números
 *    como vinieron, la forma y las dos áreas que dijo la fuente. **La declarada no se copia de la del
 *    SIGPAC**: se manda la que había, y si no había, no se manda.
 */
export function loteDesdeLasVersiones(versiones, { campanaId, fuente } = {}) {
  const recintos = (versiones || [])
    .filter((version) => version && version.fuente === fuente)
    .map((version) => {
      const recinto = {
        parcela_id: version.parcela_id,
        provincia: version.provincia,
        municipio: version.municipio,
        agregado: version.agregado,
        zona: version.zona,
        poligono: version.poligono,
        numero_parcela: version.numero_parcela,
        numero_recinto: version.numero_recinto,
        geometria: version.geometria,
        area_sigpac_ha: version.area_sigpac_ha,
        area_declarada_ha: version.area_declarada_ha,
        uso_sigpac: version.uso_sigpac,
      };
      // Los huecos **no se escriben**: un campo con `null` y un campo que no viene son cosas
      // distintas al otro lado (`CAMPOS_QUE_UNA_IMPORTACION_NO_BORRA`), y mandar `null` en la forma
      // de una versión que sí la tenía sería borrarla.
      return Object.fromEntries(
        Object.entries(recinto).filter(([, valor]) => valor !== null && valor !== undefined),
      );
    });
  return { campana_id: campanaId, fuente, recintos };
}

/** Los años de los que hay versiones de esta tierra, del más nuevo al más viejo, sin repetir. */
export function aniosConVersiones(versiones) {
  const porAnio = new Map();
  for (const version of versiones || []) {
    if (!version || version.anio === null || version.anio === undefined) continue;
    if (!porAnio.has(version.anio)) porAnio.set(version.anio, version.campana_id);
  }
  return [...porAnio.entries()]
    .sort(([uno], [otro]) => otro - uno)
    .map(([anio, campanaId]) => ({ anio, campana_id: campanaId }));
}

/** Una versión: su año y su fuente, cómo está y sus datos con el nombre delante. */
function Version({ version }) {
  return html`
    <article className="tarjeta t06-version">
      <h3 className="t06-subtitulo">${frase(version.titulo)}</h3>
      <p className="t06-como-esta">${frase(version.como_esta)}</p>
      <dl>
        ${(version.filas || []).map(
          (fila, indice) => html`
            <div className="resumen-dato" key=${indice}>
              <dt>${frase(fila.etiqueta)}</dt>
              <dd>${frase(fila.valor)}</dd>
            </div>
          `,
        )}
      </dl>
      ${(version.avisos || []).map(
        (aviso, indice) => html`<p className="tarjeta-aviso" key=${indice}>
          <span className="tarjeta-aviso-icono" aria-hidden="true">!</span>
          ${frase(aviso)}
        </p>`,
      )}
    </article>
  `;
}

/**
 * La pantalla entera.
 *
 * Propiedades (todo preparado en `app.js` a partir de `/api/versiones` y de sus dos rutas hermanas):
 *
 *  - `textos`: `{ versiones, mapa, acciones }`.
 *  - `tierra`: `{titulo, filas, forma}`, la ficha de la tierra.
 *  - `versiones`: las versiones ya preparadas para leerlas (`titulo`, `como_esta`, `filas`, `avisos`),
 *    de la más nueva a la más vieja.
 *  - `comparar`: `{anios, antes, despues, puede, falta, comparacion}`. `comparacion` es
 *    `{resumen, cuenta: [{etiqueta, valor}], cambios: [{titulo, estado_texto, clase, que_cambio}]}`.
 *  - `traer`: las opciones de ensayo: `[{etiqueta, pista, fuente, campana_id (texto), anio}]`.
 *  - `ensayo`: lo que ha devuelto `/api/versiones/previsualizar`, ya preparado, o vacío.
 *  - `aviso`: lo que ha dicho el servidor cuando algo no ha salido bien.
 */
export function PantallaVersionesDeUnaTierra({
  textos = {},
  tierra = {},
  versiones = [],
  comparar = {},
  traer = [],
  ensayo = null,
  aviso = "",
}) {
  const t = textos.versiones || {};
  const comparacion = comparar.comparacion || null;
  return html`
    <h1>${frase(t.titulo)}</h1>
    <p className="pista">${frase(t.explica)}</p>
    <${AvisoDeError} texto=${aviso} />
    <section className="t06-ficha">
      <h2 className="t06-titulo-seccion">${frase(tierra.titulo)}</h2>
      <dl>
        ${(tierra.filas || []).map(
          (fila, indice) => html`
            <div className="resumen-dato" key=${indice}>
              <dt>${frase(fila.etiqueta)}</dt>
              <dd>${frase(fila.valor)}</dd>
            </div>
          `,
        )}
      </dl>
    </section>
    <section className="t06-versiones">
      ${
        versiones.length
          ? versiones.map((version, indice) => html`<${Version} key=${indice} version=${version} />`)
          : html`<p className="pista">${frase(t.sin_versiones)}</p>`
      }
    </section>
    <section className="t06-comparar">
      <h2 className="t06-titulo-seccion">${frase(t.comparar_titulo)}</h2>
      <p className="pista">${frase(t.comparar_explica)}</p>
      ${
        comparar.puede
          ? html`
              <${OpcionesParaElegir}
                rotulo=${t.comparar_antes}
                opciones=${comparar.anios}
                accion="t06-comparar-antes"
                elegido=${comparar.antes}
              />
              <${OpcionesParaElegir}
                rotulo=${t.comparar_despues}
                opciones=${comparar.anios}
                accion="t06-comparar-despues"
                elegido=${comparar.despues}
              />
              <div className="barra-acciones">
                <${Boton} etiqueta=${t.comparar_boton} accion="t06-comparar" clase="boton-principal" />
              </div>
            `
          : html`<p className="pista-campo">${frase(comparar.sin_datos || t.comparar_sin_datos)}</p>`
      }
      ${
        // **Los cuatro estados, cada uno con su palabra y su número.** El color solo no informa: el
        // `estado_texto` que trae el servidor es el que dice qué es cada uno.
        comparacion
          ? html`
              <p className="t06-resumen-comparacion">${frase(comparacion.resumen)}</p>
              <dl className="t06-cuenta">
                ${(comparacion.cuenta || []).map(
                  (una, indice) => html`
                    <div className="resumen-dato" key=${indice}>
                      <dt>${frase(una.etiqueta)}</dt>
                      <dd>
                        <span className=${`etiqueta-estado etiqueta-estado-${una.clase}`}>
                          ${frase(String(una.valor))}
                        </span>
                      </dd>
                    </div>
                  `,
                )}
              </dl>
              <ul className="t06-cambios">
                ${(comparacion.cambios || []).map(
                  (cambio, indice) => html`
                    <li key=${indice} className=${`t06-cambio t06-cambio-${cambio.clase}`}>
                      <span className=${`etiqueta-estado etiqueta-estado-${cambio.clase}`}>
                        ${frase(cambio.estado_texto)}
                      </span>
                      <span className="t06-cambio-tierra">${frase(cambio.titulo)}</span>
                      <span className="tabla-pista">${frase(cambio.que_cambio)}</span>
                    </li>
                  `,
                )}
              </ul>
            `
          : null
      }
    </section>
    <section className="t06-traer">
      <h2 className="t06-titulo-seccion">${frase(t.traer_titulo)}</h2>
      <p className="pista">${frase(t.traer_explica)}</p>
      ${
        traer.length
          ? traer.map(
              (opcion, indice) => html`
                <p className="t06-traer-opcion" key=${indice}>
                  <${BotonSencillo}
                    etiqueta=${t.ensayar}
                    accion="t06-ensayar"
                    datos=${{ fuente: opcion.fuente, campana: opcion.campana }}
                    clase="boton-claro"
                  />
                  <span className="pista-campo">${frase(opcion.pista)}</span>
                </p>
              `,
            )
          : null
      }
      ${
        ensayo
          ? html`
              <p className="t06-ensayo-titulo">${frase(ensayo.titulo)}</p>
              <dl>
                ${(ensayo.filas || []).map(
                  (fila, indice) => html`
                    <div className="resumen-dato" key=${indice}>
                      <dt>${frase(fila.etiqueta)}</dt>
                      <dd>${frase(fila.valor)}</dd>
                    </div>
                  `,
                )}
              </dl>
              <ul className="t06-cambios">
                ${(ensayo.detalle || []).map(
                  (linea, indice) => html`
                    <li key=${indice} className=${`t06-cambio t06-cambio-${linea.clase}`}>
                      <span className=${`etiqueta-estado etiqueta-estado-${linea.clase}`}>
                        ${frase(linea.estado_texto)}
                      </span>
                      <span className="t06-cambio-tierra">${frase(linea.titulo)}</span>
                      <span className="tabla-pista">${frase(linea.que_cambio)}</span>
                    </li>
                  `,
                )}
              </ul>
              ${(ensayo.avisos || []).map(
                (grupo, indice) => html`
                  <div className="t06-aviso-de-ensayo" key=${indice}>
                    <h3 className="t06-subtitulo">${frase(grupo.titulo)}</h3>
                    <ul>
                      ${(grupo.lineas || []).map(
                        (linea, posicion) => html`<li key=${posicion}>${frase(linea)}</li>`,
                      )}
                    </ul>
                  </div>
                `,
              )}
              ${
                // **La frase que dice que el ensayo no ha escrito nada**, y el botón de apuntarlo, que
                // solo sale cuando hay un ensayo delante. Son dos acciones distintas y separadas: el
                // ensayo no tiene ningún camino que escriba.
                ensayo.apuntado
                  ? html`<p className="pista-campo">${frase(ensayo.apuntado)}</p>`
                  : html`
                      <p className="pista-campo">${frase(ensayo.sin_apuntar)}</p>
                      <div className="barra-acciones">
                        <${Boton}
                          etiqueta=${ensayo.apuntando ? t.apuntando_el_lote : t.apuntarlo}
                          accion="t06-apuntar-lote"
                          clase="boton-principal"
                        />
                      </div>
                    `
              }
            `
          : null
      }
    </section>
    <div className="barra-acciones">
      <${Boton} etiqueta=${t.volver_a_las_tierras} accion="t06-volver" clase="boton-claro" />
      <${Boton}
        etiqueta=${tierra.abrir_en_el_mapa}
        accion="t06-abrir-en-el-mapa"
        datos=${{ id: tierra.id }}
        clase="boton-claro"
      />
    </div>
  `;
}

/** El elemento de React de esta pantalla, ya con sus propiedades puestas. */
export function pantallaDeLasVersionesDeUnaTierra(propiedades) {
  return html`<${PantallaVersionesDeUnaTierra}
    textos=${propiedades.textos}
    tierra=${propiedades.tierra}
    versiones=${propiedades.versiones}
    comparar=${propiedades.comparar}
    traer=${propiedades.traer}
    ensayo=${propiedades.ensayo}
    aviso=${propiedades.aviso}
  />`;
}
