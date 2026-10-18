/*
 * maquinaria.js — «Mi maquinaria»: la lista de máquinas y la ficha de una (S16, T14 / E8).
 *
 * POR QUÉ ESTA PANTALLA EXISTE, Y QUÉ ES LO QUE NO HACE
 *
 * El contrato la pide en su apartado 4 (`/maquinaria`, S16) con estas palabras: «Tabla: máquina, tipo,
 * matrícula/serie, propiedad/alquiler, horas, próxima revisión, documentación y disponibilidad. Ficha
 * separa ITV, ITEAF, mantenimiento, seguro y ROMA. Cada obligación tiene aplicabilidad, fuente, última
 * inspección, resultado, próxima fecha y documento. **No calcular plazo solo por "tractor" o
 * "sulfatadora"; pedir la clasificación técnica necesaria.** Avisos al planificar trabajo y registro de
 * averías».
 *
 * Esa frase del medio es la que manda en todo el fichero, y se ve en tres sitios:
 *
 *  1. **La ficha pregunta, y cuando no sabe lo dice.** Cada obligación lleva sus tres respuestas («sí le
 *     toca», «no le toca», «no lo sé») y, cuando falta la fecha de la próxima, escribe que **no se sabe
 *     cuándo toca** en vez de enseñar una fecha. Si falta la **clasificación técnica** —que es lo que
 *     dice de verdad a qué está obligada la máquina— la ficha lo dice con esas palabras y pide que se
 *     mire en el papel.
 *  2. **Ningún texto de aquí promete un cumplimiento.** La obligación que nadie ha declarado sale en
 *     «no se sabe si le toca», que es distinto de «no le toca», y el color no informa solo: cada estado
 *     va con su palabra.
 *  3. **La lista dice cuántas cosas faltan por saber.** La columna de la próxima revisión puede estar
 *     vacía: si además se callara cuántas obligaciones no tienen fecha, el agricultor creería que con la
 *     fecha que ve está todo mirado.
 *
 * Y una cosa que el fichero **no** hace, a propósito: no reutiliza `EquipoAplicacion`. Los equipos con
 * los que se echa producto viven en el cuaderno de la Junta (su hoja 1.3) y son **una parte** de la
 * maquinaria, no toda. Los que ya estaban apuntados se enseñan en la lista aparte, diciendo qué son, con
 * el botón para traerlos: así se completa lo que faltaba sin duplicar lo que ya había.
 *
 * CÓMO SE PASA LOS DATOS
 *
 * El componente es **puro**: no llama a `fetch`, no lee `localStorage` y no toca el DOM. Todo le llega
 * por propiedades, **ya preparado por `app.js`**, que es quien tiene los datos y el vocabulario: los
 * rótulos y las frases salen del servidor (`textos.py`, por `/api/interfaz`), y aquí no hay ni una frase
 * escrita a mano. Los campos del formulario llevan su `id` (`maquina-nombre`…), que es lo único que
 * `app.js` tiene para leer lo que el agricultor ha escrito; cambiarlos dejaría el formulario rellenándose
 * y guardándose vacío sin decir nada.
 */

import { AvisoDeError, Boton, BotonSencillo, frase, html, OpcionesParaElegir } from "../componentes.js";
import { Campo } from "../piezas/campo.js";
import { Tabla } from "../piezas/tabla.js";

/**
 * Las opciones de una obligación, con la elegida marcada.
 *
 * `elegido` va también como `data-elegido` (lo pone `OpcionesParaElegir`): así el agricultor lo ve
 * marcado **y** quien lea los datos sabe cuál está elegido sin mirar colores, que es la regla de la casa.
 */
function Opciones({ bloque, accion }) {
  if (!bloque) return null;
  return html`
    <${OpcionesParaElegir}
      rotulo=${bloque.etiqueta}
      pista=${bloque.pista}
      opciones=${bloque.opciones}
      accion=${accion}
      campo=${bloque.campo}
      datos=${bloque.datos}
      elegido=${bloque.elegido}
    />
    ${bloque.pista ? html`<p className="pista-campo">${frase(bloque.pista)}</p>` : null}
  `;
}

/**
 * Los campos de un formulario, tal y como los prepara `app.js`.
 *
 * Un bloque es de escribir (`{tipo, id, etiqueta, valor, pista}`) o de elegir
 * (`{tipo: "opciones", campo, etiqueta, opciones, elegido}`), y los dos se pintan aquí. **Un bloque con
 * un `tipo` que no se conoce se pinta como texto**: entre un campo de más y un campo que desaparece sin
 * decir nada, el de más.
 */
function Formulario({ formulario, guardando }) {
  if (!formulario) return null;
  return html`
    <h2>${frase(formulario.titulo)}</h2>
    ${formulario.pista ? html`<p className="pista">${frase(formulario.pista)}</p>` : null}
    ${(formulario.bloques || []).map((bloque, indice) =>
      bloque.tipo === "opciones"
        ? html`<${Opciones} key=${indice} bloque=${bloque} accion="maquina-elegir" />`
        : html`
            <${Campo}
              key=${indice}
              id=${bloque.id}
              etiqueta=${bloque.etiqueta}
              tipo=${bloque.tipo}
              valor=${bloque.valor}
              sufijo=${bloque.pista}
              unidad=${bloque.unidad}
              filas=${bloque.filas}
            />
          `,
    )}
    ${formulario.error ? html`<${AvisoDeError} texto=${formulario.error} />` : null}
    <div className="barra-acciones">
      <${Boton}
        etiqueta=${formulario.guardar}
        accion="maquina-guardar"
        datos=${formulario.datos}
        clase=""
      />
      <${BotonSencillo} etiqueta=${formulario.cancelar} accion="maquina-cancelar" />
    </div>
    ${guardando ? html`<p className="pista-campo">${frase(formulario.guardando)}</p>` : null}
  `;
}

/**
 * Los avisos de una máquina: lo que hay que mirar antes de contar con ella.
 *
 * Cada aviso lleva **su palabra de urgencia** además de su sitio y su color: «Míralo antes de usarla» o
 * «Míralo cuando puedas». Un aviso que solo se distinguiera por el color no se ve al sol y no se oye en
 * un lector de pantalla.
 */
function Avisos({ avisos = [], textos = {} }) {
  if (!avisos.length) return html`<p className="pista-campo">${frase(textos.sin_avisos)}</p>`;
  return html`
    <ul className="lista">
      ${avisos.map(
        (aviso, indice) => html`
          <li key=${indice} className=${aviso.urgente ? "aviso aviso-error" : "aviso"}>
            <strong>${frase(aviso.urgente ? textos.urgente : textos.mirar_cuando_puedas)}</strong>
            <div className="apunte-detalle">${frase(aviso.texto)}</div>
          </li>
        `,
      )}
    </ul>
  `;
}

/**
 * Lo que el programa **todavía no sabe calcular**, dicho con lo que es y de quién depende.
 *
 * Es la receta de `AGENTS.md` para todo lo que no se puede hacer entero, y aquí es el trabajo legal
 * L07 (la clasificación técnica por máquina): mientras no esté transcrito, el programa no calcula plazos,
 * y el agricultor tiene que poder leer por qué en vez de pensar que se ha olvidado de avisarle.
 */
function LoQueFalta({ queFalta = [], textos = {} }) {
  if (!queFalta.length) return null;
  return html`
    <h2>${frase(textos.que_falta_titulo)}</h2>
    <p className="pista-campo">${frase(textos.que_falta_explica)}</p>
    <ul className="lista">
      ${queFalta.map(
        (lo, indice) => html`
          <li key=${indice}>
            <strong>${frase(lo.que)}</strong>
            ${
              // El rótulo y lo que dice van en **dos trozos separados** (su `strong` y su `span`) y no en
              // una frase pegada: así se leen como dos cosas —el nombre del dato y el dato—, y así la
              // prueba de «ni una frase escrita a mano» puede comprobar cada uno por su lado en vez de
              // encontrarse una frase montada que no está en ninguna parte del servidor.
              html`<div className="apunte-detalle">
                <strong>${frase(textos.que_falta_para_que)}</strong>
                <span> ${frase(lo.para_que)}</span>
              </div>`
            }
            <div className="apunte-detalle">
              <strong>${frase(textos.que_falta_depende)}</strong>
              <span> ${frase(lo.de_quien_depende)}</span>
            </div>
          </li>
        `,
      )}
    </ul>
  `;
}

/**
 * Un dato de la ficha: su rótulo y su valor. Un hueco se enseña **diciendo que está vacío**, nunca en
 * blanco: un renglón sin nada al lado parece un fallo del programa.
 */
function Dato({ rotulo, valor, vacio }) {
  if (!rotulo) return null;
  return html`
    <div className="apunte-detalle">
      <strong>${frase(rotulo)}</strong>
      ${valor ? ` ${frase(valor)}` : ` ${frase(vacio)}`}
    </div>
  `;
}

/** Una máquina de la lista, en el móvil: sus datos con el nombre delante y lo que hay que mirar. */
function Maquina({ maquina, textos }) {
  return html`
    <li>
      <strong>${frase(maquina.nombre)}</strong>
      <div className="apunte-detalle">${frase(maquina.detalle)}</div>
      ${maquina.proxima ? html`<div className="apunte-detalle">${frase(maquina.proxima)}</div>` : null}
      ${maquina.papeles ? html`<div className="apunte-detalle">${frase(maquina.papeles)}</div>` : null}
      ${maquina.disponibilidad ? html`<div className="apunte-detalle">${frase(maquina.disponibilidad)}</div>` : null}
      ${
        // Lo que hay que mirar de esta máquina, con sus palabras: es lo que hace que la lista sirva para
        // algo más que para mirarla.
        (maquina.avisos || []).map(
          (aviso, indice) => html`
            <div key=${indice} className=${aviso.urgente ? "aviso aviso-error" : "aviso"}>
              ${frase(aviso.texto)}
            </div>
          `,
        )
      }
      <div className="barra-acciones">
        <${BotonSencillo}
          etiqueta=${textos.abrir}
          accion="maquina-ver"
          datos=${{ id: maquina.id }}
        />
      </div>
    </li>
  `;
}

/**
 * La pantalla de la lista.
 *
 * Propiedades: `textos` (el vocabulario de la maquinaria y el de los botones), `cuantas` (la frase que
 * dice cuántas hay, ya en singular o plural), `filtro`, `tabla` (para el ordenador), `maquinas` (las
 * tarjetas del móvil), `equipos` (los equipos del cuaderno que no están en la lista), `queFalta`,
 * `formulario` y los dos avisos de la pantalla (`error` y `aviso`).
 */
export function PantallaDeLaMaquinaria({
  textos = {},
  cuantas = "",
  filtro = "",
  tabla = null,
  maquinas = [],
  equipos = [],
  queFalta = [],
  formulario = null,
  guardando = false,
  error = "",
  aviso = "",
}) {
  const m = textos.maquinaria || {};
  const acciones = textos.acciones || {};

  return html`
    <h1>${frase(m.titulo)}</h1>
    <p className="pista">${frase(m.explica)}</p>
    <${AvisoDeError} texto=${error} />
    ${aviso ? html`<div className="aviso">${frase(aviso)}</div>` : null}
    ${cuantas ? html`<p className="cuantas">${frase(cuantas)}</p>` : null}

    ${
      // El buscador, con su botón: la lista de maquinaria se lee de un tirón, pero con quince aperos el
      // buscador es lo que evita recorrerla entera.
      html`
        <div className="campo">
          <label htmlFor="maquinaria-buscar">${frase(m.buscar)}</label>
          <input id="maquinaria-buscar" type="search" defaultValue=${filtro || ""} />
          <p className="pista-campo">${frase(m.buscar_pista)}</p>
        </div>
        <div className="barra-acciones">
          <${BotonSencillo} etiqueta=${m.buscar} accion="maquinaria-buscar" />
          ${filtro ? html`<${BotonSencillo} etiqueta=${m.ver_todas} accion="maquinaria-ver-todas" />` : null}
        </div>
      `
    }

    ${
      // **La tabla, en el ordenador**: las ocho columnas del contrato. Y si la lista está filtrada, el pie
      // lo dice: un filtro sin decir qué está filtrando deja al agricultor creyendo que ha perdido máquinas.
      //
      // Va dentro de `.tabla-scroll` —como la tabla del dinero (T12)—: con nueve columnas, a 1024 px la
      // tabla no cabe a lo ancho, y sin este contenedor **la página entera se sale** (medido: 1.621 px
      // dentro de un hueco de 1.024) y el agricultor tiene que desplazar la pantalla entera para ver el
      // último dato. Con él, se desplaza solo la tabla y la pantalla se queda quieta.
      tabla && tabla.filas.length
        ? html`<div className="solo-escritorio tabla-scroll"><${Tabla} tabla=${tabla} /></div>`
        : null
    }

    ${
      maquinas.length
        ? html`<ul className="lista solo-movil">
            ${maquinas.map((maquina, indice) => html`<${Maquina} key=${indice} maquina=${maquina} textos=${{ ...m, abrir: m.abrir }} />`)}
          </ul>`
        : html`<p className="pista-campo">${frase(filtro ? m.sin_resultados : m.sin_maquinas)}</p>`
    }

    ${
      // **Los equipos del cuaderno que todavía no están en esta lista.** Se enseñan con su explicación y
      // con el botón de traerlos, porque lo que ya estaba apuntado no puede desaparecer de la vista (es
      // media puerta de calidad de este ticket).
      equipos.length
        ? html`
            <h2>${frase(m.equipos_sin_ficha)}</h2>
            <p className="pista-campo">${frase(m.equipos_explica)}</p>
            <ul className="lista">
              ${equipos.map(
                (equipo, indice) => html`
                  <li key=${indice}>
                    <strong>${frase(equipo.nombre)}</strong>
                    ${equipo.detalle ? html`<div className="apunte-detalle">${frase(equipo.detalle)}</div>` : null}
                    <div className="barra-acciones">
                      <${BotonSencillo}
                        etiqueta=${m.traer_equipo}
                        accion="maquina-traer-equipo"
                        datos=${{ id: equipo.id }}
                      />
                    </div>
                  </li>
                `,
              )}
            </ul>
          `
        : null
    }

    <${Formulario} formulario=${formulario} guardando=${guardando} />

    ${
      // El botón de apuntar una máquina: **abajo y siempre**, también cuando la lista está vacía. Decirle
      // al agricultor que no tiene ninguna máquina y no darle dónde apuntarla es dejarlo sin salida, y eso
      // ya estuvo mal una vez en este programa.
      formulario
        ? null
        : html`<div className="barra-acciones">
            <${Boton} etiqueta=${m.nueva} accion="maquina-nueva" clase="" />
          </div>`
    }

    <${LoQueFalta} queFalta=${queFalta} textos=${m} />

    <div className="barra-acciones">
      <${BotonSencillo} etiqueta=${acciones.volver} accion="ir-inicio" clase="" />
    </div>
  `;
}

/**
 * Una obligación de la ficha: las cinco cosas que hay que separar.
 *
 * Lo que enseña, y por qué cada cosa está: la **aplicabilidad** con sus tres respuestas (y la pregunta de
 * **de dónde sale**), la **última inspección** con su **resultado**, la **próxima fecha** tal y como venía
 * del papel, el **papel** que la demuestra, la **fuente** de la obligación (la norma que tenemos, o lo que
 * falta) y los botones para apuntar una inspección de esa obligación.
 *
 * Y cuando algo no se sabe, se dice con palabras: «No se sabe si le toca», «No hay ninguna apuntada», «No
 * se sabe cuándo toca la próxima». Ninguna de esas frases se puede confundir con un «está bien».
 */
function Obligacion({ obligacion, textos }) {
  const m = textos;
  return html`
    <li>
      <h3>${frase(obligacion.nombre)}</h3>
      <p className="pista-campo">${frase(obligacion.que_es)}</p>
      <div className="apunte-detalle">
        <strong>${frase(m.situacion)}</strong> ${frase(obligacion.situacion_texto)}
      </div>
      <${Opciones} bloque=${obligacion.opciones_aplicabilidad} accion="maquina-declarar" />
      ${
        // **Y de dónde sale lo que ha contestado.** «No le toca» sin decir quién lo dice no vale nada
        // delante de una inspección, así que la pregunta va aquí, pegada a la respuesta.
        obligacion.opciones_origen
          ? html`<${Opciones} bloque=${obligacion.opciones_origen} accion="maquina-declarar" />`
          : null
      }
      <div className="apunte-detalle">
        <strong>${frase(m.documento_de_la_aplicabilidad)}</strong>
        ${
          // **El papel que demuestra QUE LE TOCA, y de cuándo es** (CRM-07, 14/10/2026), pegado a la
          // respuesta de «de dónde sale», porque es eso lo que demuestra. **No es el mismo papel que el
          // de la última inspección**, que dice cómo salió y va más abajo: son dos cosas distintas y las
          // dos son creíbles, así que se llaman distinto.
          obligacion.papel_de_la_aplicabilidad
            ? ` ${frase(obligacion.papel_de_la_aplicabilidad)}`
            : ` ${frase(m.sin_papel)}`
        }
      </div>
      ${
        // **Y se puede decir CUÁL es y DE CUÁNDO**, que era la mitad que faltaba del contrato
        // («aplicabilidad con evidencia y fecha»): antes la obligación afirmaba salir de un documento y
        // **no había forma de decir cuál**. El papel se elige como los demás datos de esta ficha —**en
        // línea, y guarda al elegir**—, y la fecha viaja con él: si el campo está vacío **no se manda**,
        // así que la que hubiera se queda (la regla A1, la del #2 de semillas).
        obligacion.opciones_documento
          ? html`<${Opciones} bloque=${obligacion.opciones_documento} accion="maquina-declarar" />`
          : null
      }
      <div className="campo">
        <label htmlFor=${`obligacion-fecha-${obligacion.tipo}`}>${frase(m.fecha_de_la_evidencia)}</label>
        <input
          id=${`obligacion-fecha-${obligacion.tipo}`}
          type="date"
          data-campo="fecha_de_la_evidencia"
          defaultValue=${obligacion.fecha_de_la_evidencia_iso}
        />
        <p className="pista-campo">${frase(m.fecha_de_la_evidencia_pista)}</p>
      </div>
      ${
        // **Y QUIÉN LO DECIDIÓ, Y CUÁNDO** (CRM-07 #6): la ficha decía qué le toca y de dónde sale, pero
        // **no decía quién lo había decidido**. Se enseña con las palabras de siempre —«falta decirlo»,
        // como los demás huecos de esta ficha—, nunca con un renglón en blanco ni con un `null` a la vista,
        // que es lo que parece un fallo del programa. **El autor lo pone el servidor**: aquí solo se lee.
        html`<${Dato} rotulo=${m.decidido_por} valor=${obligacion.decidido_por} vacio=${m.sin_decir} />`
      }
      <${Dato} rotulo=${m.decidido_en} valor=${obligacion.decidido_en_texto} vacio=${m.sin_fecha_apuntada} />
      ${
        // **Y la fecha se escribe en su hueco**, igual que la del papel: vacío es «no consta» y **no se
        // manda**, así que la que hubiera se queda en vez de borrarse sola por no volver a escribirla.
        html`<div className="campo">
          <label htmlFor=${`obligacion-decidido-en-${obligacion.tipo}`}>${frase(m.decidido_en)}</label>
          <input
            id=${`obligacion-decidido-en-${obligacion.tipo}`}
            type="date"
            data-campo="decidido_en"
            defaultValue=${obligacion.decidido_en_iso}
          />
          <p className="pista-campo">${frase(m.decidido_en_pista)}</p>
        </div>`
      }
      ${obligacion.ultima_texto ? html`<div className="apunte-detalle">${frase(obligacion.ultima_texto)}</div>` : null}
      <${Dato} rotulo=${m.resultado} valor=${obligacion.resultado_texto} vacio=${m.resultado_no_consta} />
      <${Dato} rotulo=${m.proxima_fecha} valor=${obligacion.proxima_texto} vacio=${m.sin_fecha_apuntada} />
      <div className="apunte-detalle">
        <strong>${frase(m.documento)}</strong>
        ${obligacion.papel ? ` ${frase(obligacion.papel)}` : ` ${frase(m.sin_papel)}`}
      </div>
      ${
        // **Y el papel se puede abrir**, que es lo que se hace con él: en una inspección lo que se enseña
        // es el certificado. Antes la ficha decía «Con su papel» y no decía cuál ni dejaba verlo.
        obligacion.papel_id
          ? html`<div className="barra-acciones">
              <${BotonSencillo}
                etiqueta=${m.ver_papel}
                accion="papel-ver"
                datos=${{ id: obligacion.papel_id }}
              />
            </div>`
          : null
      }
      ${
        // **La fuente de la obligación**, con su norma si la tenemos y con lo que falta si no. Es lo que
        // convierte «esto te toca» en algo que se puede comprobar, y lo que evita que un plazo inventado
        // se confunda con uno que está en el BOE.
        obligacion.fuente
          ? html`<div className="apunte-detalle">
              <strong>${frase(m.lo_que_dice_la_norma)}</strong>
              ${obligacion.fuente.norma ? ` ${frase(obligacion.fuente.norma)}` : ` ${frase(obligacion.fuente.que_falta)}`}
              ${
                // **Y la VIGENCIA, que el programa NO conoce y lo dice** (revision del dueño, 14/10/2026).
                // El informe pide «fuente normativa **y vigencia**», y la casa ya decidio que esa
                // clasificacion **no se rellena a ojo** -seria inventar una clasificacion legal-. Aqui no
                // se inventa: se dice que no consta. Y solo se dice cuando **hay norma localizada**,
                // porque decir «no se ha revisado si esta en vigor» de algo que no tenemos transcrito
                // seria hablar de una norma que no se ha ensenado.
                obligacion.fuente.norma
                  ? html` <span className="pista-campo">${frase(m.lo_que_dice_la_norma_vigencia)}</span>`
                  : null
              }
              ${
                obligacion.fuente.url
                  ? html` <a href=${obligacion.fuente.url} target="_blank" rel="noopener">${frase(obligacion.fuente.url)}</a>`
                  : null
              }
            </div>`
          : null
      }
      ${
        // La clasificación técnica que falta: el programa **pide el dato** en vez de deducirlo, que es
        // exactamente lo que el contrato manda.
        obligacion.clasificacion_falta
          ? html`<div className="aviso">${frase(m.clasificacion_falta)}</div>`
          : null
      }
      <div className="barra-acciones">
        <${BotonSencillo}
          etiqueta=${m.apuntar_inspeccion}
          accion="maquina-inspeccion-nueva"
          datos=${{ tipo: obligacion.tipo }}
        />
      </div>
    </li>
  `;
}

/** Una inspección apuntada, con lo que traía el papel y sus dos salidas (corregir y borrar). */
function Inspeccion({ inspeccion, textos }) {
  const m = textos;
  return html`
    <li className=${inspeccion.anulado ? "anulado" : ""}>
      <strong>${frase(inspeccion.titulo)}</strong>
      <div className="apunte-detalle">${frase(inspeccion.fecha_texto)}</div>
      <div className="apunte-detalle">${frase(inspeccion.resultado_texto)}</div>
      <div className="apunte-detalle">${frase(inspeccion.proxima_texto)}</div>
      <div className="apunte-detalle">${frase(inspeccion.papel_texto)}</div>
      ${
        inspeccion.papel_id
          ? html`<div className="barra-acciones">
              <${BotonSencillo}
                etiqueta=${textos.ver_papel}
                accion="papel-ver"
                datos=${{ id: inspeccion.papel_id }}
              />
            </div>`
          : null
      }
      ${inspeccion.motivo_anulacion ? html`<div className="apunte-detalle">${frase(inspeccion.motivo_anulacion)}</div>` : null}
      ${
        inspeccion.anulado
          ? null
          : html`<div className="barra-acciones">
              <${BotonSencillo}
                etiqueta=${textos.corregir}
                accion="maquina-inspeccion-corregir"
                datos=${{ id: inspeccion.id }}
              />
              <${BotonSencillo}
                etiqueta=${textos.anular}
                accion="maquina-anular"
                datos=${{ que: "inspeccion", id: inspeccion.id }}
              />
              <${BotonSencillo}
                etiqueta=${textos.borrar}
                accion="maquina-inspeccion-borrar"
                datos=${{ id: inspeccion.id }}
              />
            </div>`
      }
    </li>
  `;
}

/** Una avería apuntada, con lo que pasó y si ya está arreglada. */
function Averia({ averia, textos }) {
  return html`
    <li className=${averia.anulado ? "anulado" : ""}>
      <strong>${frase(averia.titulo)}</strong>
      <div className="apunte-detalle">${frase(averia.fecha_texto)}</div>
      <div className="apunte-detalle">${frase(averia.resuelta_texto)}</div>
      ${
        // **El taller** (CRM-07 #7, 14/10/2026). Se ensena **siempre**, tambien cuando no consta: una
        // averia sin taller es lo mas normal del mundo, y callarlo dejaria al agricultor sin saber si
        // el programa no lo sabe o si se lo esta guardando. La palabra es la de la casa (`sin_decir`).
        html`<div className="apunte-detalle">${frase(averia.taller_texto)}</div>`
      }
      ${
        // **Y el papel de la averia** (CRM-07 #7): el parte, la factura o el presupuesto. Se dice tambien
        // cuando no consta, por lo mismo que el taller: una averia sin papel es lo mas normal del mundo, y
        // callarlo dejaria al agricultor sin saber si el programa no lo sabe o se lo esta guardando.
        html`<div className="apunte-detalle">${frase(averia.papel_texto)}</div>`
      }
      ${
        // **Y lo que costo esta averia** (CRM-07 #7). Tambien se dice cuando no consta, por lo mismo:
        // una averia sin ningun gasto apuntado **no ha costado cero**, y el agricultor tiene que poder
        // distinguir «no lo se» de «fue gratis».
        html`<div className="apunte-detalle">${frase(averia.coste_frase)}</div>`
      }
      ${averia.notas ? html`<div className="apunte-detalle">${frase(averia.notas)}</div>` : null}
      ${
        averia.anulado
          ? null
          : html`<div className="barra-acciones">
              <${BotonSencillo}
                etiqueta=${textos.corregir}
                accion="maquina-averia-corregir"
                datos=${{ id: averia.id }}
              />
              <${BotonSencillo}
                etiqueta=${textos.anular}
                accion="maquina-anular"
                datos=${{ que: "averia", id: averia.id }}
              />
              <${BotonSencillo}
                etiqueta=${textos.borrar}
                accion="maquina-averia-borrar"
                datos=${{ id: averia.id }}
              />
            </div>`
      }
    </li>
  `;
}

/** Una reserva de la máquina: cuándo la vas a coger, cómo va y para qué. */
function Reserva({ reserva, textos, puedeModificar = true }) {
  return html`
    <li className=${reserva.anulada ? "anulado" : ""}>
      <strong>${frase(reserva.cuando_texto)}</strong>
      <div className="apunte-detalle">${frase(reserva.estado_texto)}</div>
      ${
        // **El responsable y la tarea se ensenan SIEMPRE, tambien cuando no constan**: *una reserva sin
        // decir quien la coge es lo mas normal del mundo, y callarlo dejaria al agricultor sin saber si el
        // programa no lo sabe o si se lo esta guardando.* La frase la monta `app.js` -«sin decir quien la
        // coge»-, que es donde vive el texto.
        html`<div className="apunte-detalle">${frase(reserva.responsable_texto)}</div>`
      }
      ${html`<div className="apunte-detalle">${frase(reserva.tarea_texto)}</div>`}
      ${reserva.notas ? html`<div className="apunte-detalle">${frase(reserva.notas)}</div>` : null}
      ${
        // **Anular no es borrar**: la reserva se queda **tachada, con su motivo**, y deja de ocupar la
        // maquina. Es el mismo trato que una averia o una lectura anulada.
        reserva.anulada
          ? html`<div className="apunte-detalle">${frase(textos.reserva_anulada)}: ${frase(reserva.motivo_anulacion)}</div>`
          : null
      }
      ${
        // **Y si esta cuenta no puede modificar, los botones NO se ofrecen** (17/10/2026):
        // *corregir y anular una reserva son escribir. Si alguien llega a mano por la URL o por un
        // identificador, **la puerta contesta 403 igual**: esto es no ofrecer, no autorizar.*
        reserva.anulada || !puedeModificar
          ? null
          : html`<div className="barra-acciones">
              <${BotonSencillo}
                etiqueta=${textos.corregir_reserva}
                accion="maquina-reserva-corregir"
                datos=${{ id: reserva.id }}
              />
              <${BotonSencillo}
                etiqueta=${textos.anular_reserva}
                accion="maquina-anular"
                datos=${{ que: "reserva", id: reserva.id }}
              />
            </div>`
      }
    </li>
  `;
}

/**
 * La ficha de una máquina: sus datos, sus cinco obligaciones, sus inspecciones, sus averías y sus avisos.
 *
 * Propiedades: `textos`, `maquina` (los datos ya con sus fechas en texto), `avisos`, `obligaciones` (las
 * cinco, en el orden de la ficha), `inspecciones`, `averias`, `formulario`, `anulando` (la pregunta del
 * motivo) y los dos avisos de la pantalla.
 */
export function PantallaDeUnaMaquina({
  textos = {},
  maquina = null,
  avisos = [],
  obligaciones = [],
  inspecciones = [],
  averias = [],
  // **El cuenta-horas** (CRM-07 #8): las lecturas y las frases ya hechas de la cuenta. El envoltorio
  // reparte las props, asi que no hay que anadirlas alli (ver la nota de `pantallaDeUnaMaquina`).
  lecturas = [],
  contador = null,
  // **Las reservas** (CRM-07 #9, 17/10/2026): *cuando esta reservada la maquina, que es lo que la cola
  // pide con «reserva para planificar no es consumo».* **Y el envoltorio reparte las props**, asi que no
  // hay que anadirlas alli (ver la nota de `pantallaDeUnaMaquina`).
  //
  // ***Y `null` NO es `[]`***, que es la distincion de la casa -esta escrita para los papeles-:
  //   · **`null`** es «**todavia no se han pedido**»: *la seccion **no se pinta**, y con ella **no se
  //     pinta el boton de reservar**.* Asi, mientras `app.js` no traiga las reservas, la ficha no ofrece
  //     un boton que no lleva a ninguna parte.
  //   · **`[]`** es «**se pidieron y no hay ninguna**»: *se dice «no has reservado esta maquina para
  //     nada» y se ofrece reservarla, que es lo que hace falta.*
  reservas = null,
  // **Lo que ha costado tenerla parada** (CRM-07 #7, 14/10/2026): lo calcula el servidor y lo trae
  // `app.js`. `null` es «no se pudo traer», y entonces no se ensena ninguna cifra en vez de un cero:
  // no saberlo y ser cero no son lo mismo.
  coste = null,
  // **Si el coste no se pudo traer** (CRM-07 #7): la ficha lo dice en vez de dejar el hueco en blanco.
  // Se recibe aqui **y** en el que llama: cambiar solo uno de los dos es el fallo de manual de esta
  // misma entrega (`ReferenceError: coste is not defined`).
  costeError = "",
  formulario = null,
  anulando = null,
  guardando = false,
  error = "",
  aviso = "",
  // **Lo que esta cuenta puede hacer** (Entrega 4, 17/10/2026). Por defecto, **si**: la pantalla no
  // parpadea, y esconder de mas dejaria al agricultor sin botones que si puede usar. *La autorizacion,
  // en todo caso, la da la puerta.* ***Y va AQUI, antes de usarla, y no dentro de un `html`.***
  puede_modificar = true,
}) {
  const m = textos.maquinaria || {};
  const acciones = textos.acciones || {};
  if (!maquina) return html`<${AvisoDeError} texto=${error} />`;

  return html`
    <h1>${frase(maquina.nombre)}</h1>
    <${AvisoDeError} texto=${error} />
    ${aviso ? html`<div className="aviso">${frase(aviso)}</div>` : null}

    <h2>${frase(m.seccion_datos)}</h2>
    <${Dato} rotulo=${m.clase} valor=${maquina.clase_texto} vacio=${m.sin_decir} />
    ${
      // **La clasificación técnica, con su aviso cuando falta.** Es el dato del que depende lo que le
      // toca a la máquina, y el programa no lo deduce: lo pide.
      html`<div className="apunte-detalle">
        <strong>${frase(m.clasificacion)}</strong>
        ${maquina.clasificacion ? ` ${frase(maquina.clasificacion)}` : ` ${frase(m.sin_clasificacion)}`}
      </div>`
    }
    ${maquina.clasificacion_falta ? html`<div className="aviso">${frase(m.clasificacion_falta)}</div>` : null}
    <${Dato} rotulo=${m.matricula} valor=${maquina.matricula} vacio=${m.sin_decir} />
    <${Dato} rotulo=${m.numero_serie} valor=${maquina.numero_serie} vacio=${m.sin_decir} />
    <${Dato} rotulo=${m.numero_roma} valor=${maquina.numero_roma} vacio=${m.sin_decir} />
    <${Dato} rotulo=${m.marca} valor=${maquina.marca} vacio=${m.sin_decir} />
    <${Dato} rotulo=${m.modelo} valor=${maquina.modelo} vacio=${m.sin_decir} />
    ${maquina.anio_texto ? html`<${Dato} rotulo=${m.anio} valor=${maquina.anio_texto} />` : null}
    <${Dato} rotulo=${m.propiedad} valor=${maquina.propiedad_texto} vacio=${m.propiedad_no_se} />
    <${Dato} rotulo=${m.horas} valor=${maquina.horas_texto} vacio=${m.sin_decir} />
    <${Dato} rotulo=${m.disponibilidad} valor=${maquina.disponibilidad_texto} vacio=${m.disponibilidad_no_se} />
    ${
      // Si esta máquina es uno de los equipos del cuaderno, se dice: es lo que evita que parezca que el
      // pulverizador está apuntado dos veces.
      maquina.es_el_equipo_del_cuaderno
        ? html`<p className="pista-campo">${frase(m.es_el_equipo_del_cuaderno_pista)}</p>`
        : null
    }
    <div className="barra-acciones">
      <${BotonSencillo} etiqueta=${textos.corregir} accion="maquina-corregir" />
    </div>

    <h2>${frase(m.avisos_titulo)}</h2>
    <${Avisos} avisos=${avisos} textos=${m} />

    <h2>${frase(m.seccion_obligaciones)}</h2>
    <p className="pista-campo">${frase(m.seccion_obligaciones_explica)}</p>
    ${
      // **Cada obligación es un renglón de la lista, y no una «tarjeta».** Se probó con la clase de las
      // tarjetas de las tierras y **la pantalla se salía de lo ancho** (medido: 1.287 px dentro de un hueco
      // de 390): esa clase es una fila flexible que no parte, y aquí dentro van cinco renglones de datos y
      // siete botones. El renglón de una lista sí los coloca uno debajo de otro y reparte los botones de dos
      // en dos, que es lo que se ve bien en el móvil.
      html`<ul className="lista">
        ${obligaciones.map(
          (obligacion, indice) => html`<${Obligacion} key=${indice} obligacion=${obligacion} textos=${m} />`,
        )}
      </ul>`
    }

    <h2>${frase(m.seccion_inspecciones)}</h2>
    ${
      // **Y el aviso de los papeles, que es una obligación de la ley**: «los registros y documentos se
      // conservarán al menos durante los 3 años siguientes a su fecha de emisión» (artículo 16.3 del RD
      // 1311/2012). Estaba escrito en `textos.py` y **no se leía en ninguna pantalla** (lo encontró la
      // revisión del ticket), y este es su sitio: debajo de las inspecciones, que son los papeles de los
      // que habla.
      html`<p className="pista-campo"><strong>${frase(m.papeles_titulo)}</strong> ${frase(m.guarda_el_papel)}</p>`
    }
    ${
      inspecciones.length
        ? html`<ul className="lista">
            ${inspecciones.map(
              (inspeccion, indice) => html`<${Inspeccion} key=${indice} inspeccion=${inspeccion} textos=${{ ...m, corregir: textos.corregir, borrar: textos.borrar }} />`,
            )}
          </ul>`
        : html`<p className="pista-campo">${frase(m.sin_inspecciones)}</p>`
    }

    <h2>${frase(m.seccion_contador)}</h2>
    ${
      // **El cuenta-horas** (CRM-07 #8). Tres casos y ninguno se confunde: sin lecturas se dice que no se
      // sabe -***nunca un «0 h»***-, con una se sabe lo que marca pero no lo que ha subido, y con dos o
      // mas se dice lo que ha subido **y los tramos que no se pueden medir**. Las frases vienen hechas de
      // `app.js` (`elCuentaHorasDeLaMaquina`).
      !contador
        ? null
        : contador.sinLecturas
          ? html`<p className="pista-campo">${frase(m.contador_sin_lecturas)}</p>`
          : html`
              <p className="apunte-detalle">${frase(contador.marca_texto)}</p>
              ${contador.subido_texto
                ? html`<p className="apunte-detalle"><strong>${frase(contador.subido_texto)}</strong></p>`
                : null}
              ${contador.incidencias_texto
                ? html`<p className="pista-campo">${frase(contador.incidencias_texto)}</p>`
                : null}
              ${contador.noSeSabeTexto
                ? html`<p className="pista-campo">${frase(contador.noSeSabeTexto)}</p>`
                : null}
              ${contador.aviso ? html`<p className="pista-campo">${frase(contador.aviso)}</p>` : null}
            `
    }
    ${lecturas.length
      ? html`<ul className="lista">
          ${lecturas.map(
            (lectura, indice) => html`<li key=${indice} className="apunte-detalle">
              ${frase(lectura.texto)}
              ${
                // **Una lectura anulada no se corrige ni se anula otra vez**: se queda tachada con su
                // motivo y sus botones desaparecen. Es el mismo trato que las averias.
                //
                // **Y si esta cuenta no puede modificar, tampoco se ofrecen** (17/10/2026):
                // *corregir y anular son escribir. Si alguien llega a mano por la URL, la puerta
                // contesta 403 igual: esto es **no ofrecer**, no autorizar.*
                lectura.anulado || !puede_modificar
                  ? null
                  : html`<div className="barra-acciones">
                      <${BotonSencillo}
                        etiqueta=${m.corregir_lectura}
                        accion="maquina-lectura-corregir"
                        datos=${{ id: lectura.id }}
                      />
                      <${BotonSencillo}
                        etiqueta=${m.anular_lectura_boton}
                        accion="maquina-lectura-anular"
                        datos=${{ id: lectura.id }}
                      />
                    </div>`
              }
            </li>`,
          )}
        </ul>`
      : null}

    ${
      // **Apuntar una lectura es escribir** (17/10/2026). *Si esta cuenta solo mira, el boton **no se
      // ofrece** -y el formulario tampoco, porque es el boton el que lo abre-. **La autorizacion la da la
      // puerta del servidor**, que es la que contesta 403: esto es no ofrecer, no autorizar.*
      puede_modificar
        ? html`<div className="barra-acciones">
      <${BotonSencillo} etiqueta=${m.apuntar_lectura} accion="maquina-lectura-nueva" />
    </div>`
        : null
    }

    ${
      // ***La seccion entera solo si las reservas SE HAN PEDIDO*** (`reservas !== null`). *Y esto no es
      // un detalle: es lo que evita que la ficha ofrezca un boton de reservar que no lleva a ninguna
      // parte mientras `app.js` no traiga los datos. **No ofrecer de mas no es no ofrecer**: mientras no
      // se sabe, no se ofrece.*
      reservas === null
        ? null
        : html`
    <h2>${frase(m.seccion_reservas)}</h2>
    ${
      // ***Reservar no gasta nada***, y decirlo es la mitad de la seccion: *el agricultor que duda entre
      // «reservar» y «apuntar» tiene que poder saber que reservar **no toca el cuenta-horas ni el
      // dinero**.* Es la frase de la cola -«Reserva para planificar no es consumo»-.
      html`<p className="pista-campo">${frase(m.reserva_no_gasta)}</p>`
    }
    ${
      reservas.length
        ? html`<ul className="lista">
            ${reservas.map(
              (reserva, indice) => html`<${Reserva} key=${indice} reserva=${reserva} textos=${m} puedeModificar=${puede_modificar} />`,
            )}
          </ul>`
        : html`<p className="pista-campo">${frase(m.sin_reservas)}</p>`
    }
    ${
      // **Reservar es escribir** (CRM-07 #9): *si esta cuenta solo mira, el boton **no se ofrece** -y el
      // formulario tampoco, porque es el boton el que lo abre-. **La autorizacion la da la puerta.**
      puede_modificar
        ? html`<div className="barra-acciones">
      <${BotonSencillo} etiqueta=${m.apuntar_reserva} accion="maquina-reserva-nueva" />
    </div>`
        : null
    }
    `
    }

    <h2>${frase(m.seccion_averias)}</h2>
    ${
      // **Y si no se pudo traer, se dice.** El motivo tecnico va en un `data-motivo` para poder medirlo;
      // el agricultor lee la frase que le dice que hacer.
      costeError
        ? html`<p className="pista-campo" data-motivo=${costeError}>${frase(m.coste_no_se_pudo)}</p>`
        : null
    }
    ${
      // **Lo que ha costado tenerla parada** (CRM-07 #7, 14/10/2026), que es lo que pide el informe.
      // Tres avisos distintos y ninguno se calla: si no hay ningun gasto apuntado se dice eso -y no
      // «0,00 €», porque no saberlo y ser cero no son lo mismo-, el total lo calcula el servidor, y si
      // algun gasto no tiene importe se dice cuantos (esa frase la monta `app.js`, no este fichero).
      !coste
        ? null
        : !coste.gastos
          ? html`<p className="pista-campo">${frase(m.coste_de_la_maquina_sin_gastos)}</p>`
          : html`<p className="apunte-detalle"><strong>${frase(coste.frase)}</strong></p>`
    }
    ${
      averias.length
        ? html`<ul className="lista">
            ${averias.map(
              (averia, indice) => html`<${Averia} key=${indice} averia=${averia} textos=${{ ...m, corregir: textos.corregir, borrar: textos.borrar }} />`,
            )}
          </ul>`
        : html`<p className="pista-campo">${frase(m.sin_averias)}</p>`
    }
    <div className="barra-acciones">
      <${BotonSencillo} etiqueta=${m.apuntar_averia} accion="maquina-averia-nueva" />
    </div>

    <${Formulario} formulario=${formulario} guardando=${guardando} />

    ${
      // La pregunta del motivo, para anular. **Anular no es borrar** y la pantalla lo dice: lo anulado se
      // queda en el cuaderno, tachado, y deja de contar para la última inspección.
      anulando
        ? html`
            <h2>${frase(anulando.titulo)}</h2>
            <p className="pista-campo">${frase(anulando.pista)}</p>
            <div className="campo">
              <label htmlFor="anular-motivo">${frase(m.motivo_anulacion)}</label>
              <input id="anular-motivo" type="text" defaultValue="" />
            </div>
            <div className="barra-acciones">
              <${BotonSencillo}
                etiqueta=${m.anular_confirmar}
                accion="maquina-anular-confirmar"
                datos=${{ que: anulando.que, id: anulando.id }}
              />
              <${BotonSencillo} etiqueta=${acciones.volver} accion="maquina-anular-cancelar" />
            </div>
          `
        : null
    }

    <${LoQueFalta} queFalta=${maquina.que_falta || []} textos=${m} />

    <div className="barra-acciones">
      <${BotonSencillo} etiqueta=${acciones.volver} accion="maquinaria-ver" clase="" />
    </div>
  `;
}

/** El elemento de React de la lista, ya con sus propiedades puestas. */
export function pantallaDeLaMaquinaria(propiedades) {
  return html`
    <${PantallaDeLaMaquinaria}
      textos=${propiedades.textos}
      cuantas=${propiedades.cuantas}
      filtro=${propiedades.filtro}
      tabla=${propiedades.tabla}
      maquinas=${propiedades.maquinas}
      equipos=${propiedades.equipos}
      queFalta=${propiedades.queFalta}
      formulario=${propiedades.formulario}
      guardando=${propiedades.guardando}
      error=${propiedades.error}
      aviso=${propiedades.aviso}
    />
  `;
}

/** Y el de la ficha de una máquina. */
export function pantallaDeUnaMaquina(propiedades) {
  // **Se pasan TODAS las props de una vez, con reparto** (14/10/2026). Antes este envoltorio las
  // reconstruia **una por una**, y eso significa que ***cualquier prop que no se nombre aqui se pierde
  // aunque el que llama la mande***: sin aviso, sin error y sin rastro.
  // Costo SEIS rondas: la averia si ensenaba su coste -`averias` estaba en la lista- y la linea del total
  // no salia, y desde fuera las dos cosas parecian lo mismo. Se probaron la cache, el service worker, la
  // navegacion por fragmento y el propio fichero, y el fallo estaba en **una lista escrita a mano**.
  // Con el reparto, este envoltorio **no puede** perder una prop: pasa lo que le den.
  return html`
    <${PantallaDeUnaMaquina} ...${propiedades} />
  `;
}

/**
 * **Las máquinas que se pueden ELEGIR para trabajar** (CRM-07 #7, 14/10/2026).
 *
 * El informe del dueño lo pide con estas palabras: «**máquina indisponible no se ofrece como
 * disponible**». Y la casa ya tenía escrito qué hacer con los tres estados (`app/maquinaria.py`):
 *
 *   «Si se puede contar con ella para trabajar. Tres estados otra vez, y `NO_SE` de partida: una máquina
 *    de la que nadie ha dicho nada **no está "disponible", está "sin decir"**.»
 *
 * Así que aquí **se quita solo `no_disponible`**, y `no_se` **se queda**: quitarla sería convertir «sin
 * decir» en «no», que es justo lo que este programa no hace en ningún sitio —es la misma regla de
 * `resuelta` (`True`/`False`/`None`) y de la aplicabilidad de una obligación—.
 *
 * **Dónde se usa y dónde no**: esto es para las listas donde se **elige una máquina para trabajar** —el
 * formulario de un trabajo y el reparto de un gasto—, que son las dos que **comparten** esta lista y no
 * dos que puedan decir cosas distintas. **La pantalla de maquinaria NO la usa**: allí tienen que estar
 * todas, porque es donde el agricultor la ve **y la arregla**. Y el aviso `M1` sigue saliendo donde salía.
 *
 * **Y vive aquí, en el módulo de la pantalla, y no en `app.js`**: los componentes son **puros y con
 * `export`**, así que `tests_js` los carga y los prueba; `app.js` necesita un DOM y **no tiene pruebas**.
 * Una regla que se puede probar y otra que no: **la regla va donde se prueba**.
 */
export function lasMaquinasParaElegir(tabla) {
  return (tabla.maquinas || [])
    .filter((una) => una.disponibilidad !== "no_disponible")
    .map((una) => ({ valor: una.id, texto: una.nombre }));
}
