/*
 * semillas.js — Las semillas y lo que pone su etiqueta (T10, 03/10/2026), en React.
 *
 * POR QUÉ ESTAS PANTALLAS
 *
 * Una semilla tiene dos mitades y las dos hacen falta para poder sembrarla bien:
 *
 *  · **es un insumo del almacén** —se compra, entra por albarán, sale cuando se siembra—, y eso ya
 *    estaba resuelto por el T09;
 *  · **y trae un papel pegado al envase** —la etiqueta: la especie, la variedad, la casa, la dosis que
 *    recomienda el fabricante, el poder germinativo, la pureza y si viene tratada—, que es lo que
 *    aquí se apunta.
 *
 * La lista de semillas enseña **lo que queda de cada una**, contado por el servidor, y la ficha
 * enseña la etiqueta. La ficha es **la misma pantalla para dar de alta y para corregir**: corregir una
 * etiqueta es el mismo trabajo que escribirla.
 *
 * LAS DOS COSAS QUE NO SE PUEDEN ROMPER DE ESTA PANTALLA
 *
 *  1. **Lo que no viene en el papel se queda en blanco y se dice.** El poder germinativo y la pureza
 *     no vienen en todas las etiquetas; cuando no vienen, el campo va vacío y debajo pone «La etiqueta
 *     no lo dice». **Un cero ahí diría que la semilla no germina**, que es lo contrario de lo que pasa.
 *     Y «¿viene tratada?» tiene **tres** respuestas (sí, no y no lo sé), no dos.
 *  2. **Leer la foto no guarda nada.** Lo que el programa ha leído de la etiqueta se enseña **dentro
 *     del formulario, como valor de cada campo**, y pone claro que hasta que no se pulse GUARDAR LA
 *     SEMILLA no hay ninguna semilla apuntada. Por eso esta pantalla no escribe al servidor hasta ese
 *     botón: la foto es una propuesta.
 *
 * Los `id` de los campos (`semilla-nombre`, `semilla-dosis`…) son los que lee `app.js`, y **no se
 * pueden cambiar**: si cambian, el formulario se rellena y se guarda vacío sin que salte nada. Hay
 * pruebas que miran la lista entera de `id`.
 */

import { AvisoDeError, Boton, BotonSencillo, frase, html } from "../componentes.js";
import { Tarjeta } from "../piezas/tarjeta.js";

/** Un campo de escribir con su etiqueta y su pista. */
function Campo({ id, etiqueta, pista, tipo = "texto", valor = "" }) {
  return html`
    <div className="campo">
      <label htmlFor=${id}>${frase(etiqueta)}</label>
      ${pista ? html`<p className="pista-campo">${frase(pista)}</p>` : null}
      ${
        tipo === "fecha"
          ? html`<input id=${id} type="date" defaultValue=${frase(valor)} />`
          : html`<input
              id=${id}
              type="text"
              inputMode=${tipo === "numero" ? "decimal" : undefined}
              defaultValue=${frase(valor)}
            />`
      }
    </div>
  `;
}

/** Un desplegable con su etiqueta. `opciones` son `{valor, texto}` y `vacio` es la primera línea. */
function Elegir({ id, etiqueta, pista, opciones = [], elegido = "", vacio = "" }) {
  return html`
    <div className="campo">
      <label htmlFor=${id}>${frase(etiqueta)}</label>
      ${pista ? html`<p className="pista-campo">${frase(pista)}</p>` : null}
      <select id=${id} defaultValue=${frase(elegido)}>
        ${vacio ? html`<option value="">${frase(vacio)}</option>` : null}
        ${opciones.map(
          (opcion) => html`
            <option value=${String(opcion.valor)} key=${String(opcion.valor)}>${frase(opcion.texto)}</option>
          `,
        )}
      </select>
    </div>
  `;
}

/**
 * La lista de las semillas de la finca.
 *
 * Propiedades:
 *
 *  - `textos`: `{ semillas, acciones }` del servidor.
 *  - `tarjetas`: las semillas ya preparadas por `app.js` (nombre, lo que queda, sus avisos y la
 *    acción de abrir su ficha). **Aquí no se cuenta nada**: lo que queda lo ha contado el servidor.
 *  - `resumen`: cuántas hay, ya en singular o en plural («Tienes 1 semilla dada de alta»).
 *  - `error`, `cargando`, `acciones`: lo de siempre.
 */
export function PantallaDeLasSemillas({
  textos = {},
  tarjetas = [],
  resumen = "",
  aviso = "",
  error = "",
  cargando = false,
}) {
  const s = textos.semillas || {};
  return html`
    <h1>${frase(s.titulo)}</h1>
    <p className="pista">${frase(s.explica)}</p>
    <${AvisoDeError} texto=${error} />
    ${aviso ? html`<div className="aviso"><strong>${frase(aviso)}</strong></div>` : null}
    ${cargando ? html`<p className="pista">${frase(s.buscando)}</p>` : null}

    ${
      tarjetas.length === 0
        ? html`<p className="aviso">${frase(s.vacia)}</p>`
        : html`<p className="pista">${frase(resumen)}</p>`
    }

    ${tarjetas.map(
      (tarjeta) => html`
        <${Tarjeta}
          key=${String(tarjeta.id)}
          etiqueta=${tarjeta.etiqueta}
          rotulo=${tarjeta.rotulo}
          lineas=${tarjeta.lineas}
          filas=${tarjeta.filas}
          avisos=${tarjeta.avisos}
          marca=${false}
          accion="semilla-abrir"
          datos=${{ id: tarjeta.id }}
          textos=${{ elegida: "" }}
        />
      `,
    )}

    <h2>${frase(s.que_se_puede_hacer)}</h2>
    <div className="barra-acciones">
      <${Boton}
        etiqueta=${s.anadir}
        pista=${s.anadir_pista}
        accion="semilla-nueva"
        clase="boton-principal"
      />
      <${BotonSencillo} etiqueta=${s.ver_las_siembras} accion="siembras-ver" clase="" />
      <${BotonSencillo} etiqueta=${s.volver_al_inicio} accion="ir-inicio" clase="" />
    </div>
  `;
}

/**
 * La ficha de una semilla: para darla de alta, para corregirla o para **confirmar lo que se ha leído
 * de la foto de su etiqueta**.
 *
 * Propiedades:
 *
 *  - `borrador`: lo que hay que enseñar en los campos. Al dar de alta va vacío; al leer una foto
 *    lleva **lo que el programa ha leído**; al corregir, lo que ya estaba guardado.
 *  - `propuesta`: `null` cuando se escribe a mano. Cuando se ha leído una foto lleva `campos_leidos`,
 *    `como_se_leyo`, `avisos` y `dudas` —lo que el papel dice y no se puede apuntar tal cual—. **Es lo
 *    que convierte la lectura en algo que se revisa en vez de en algo que se cree.**
 *  - `articulos`: los insumos del almacén que todavía no tienen etiqueta, para enganchar la semilla a
 *    uno que ya entró por albarán en vez de crear otro con el mismo nombre.
 *  - `unidades_dosis`, `unidades_cantidad`: las listas del servidor (son nuestras, y se dice en la
 *    pantalla de dónde salen solo cuando hace falta).
 *  - `corrigiendo`: si lo que se está haciendo es corregir una que ya existe (cambia el título y el
 *    botón, y entonces también se puede subir la foto).
 */
export function PantallaDeUnaSemilla({
  textos = {},
  borrador = {},
  propuesta = null,
  articulos = [],
  unidades_dosis = [],
  unidades_cantidad = [],
  semillaId = "",
  corrigiendo = false,
  guardando = false,
  error = "",
}) {
  const s = textos.semillas || {};
  const leido = (clave) => (propuesta && propuesta[clave] != null ? propuesta[clave] : "");
  const valor = (clave) => (borrador[clave] == null ? "" : borrador[clave]);
  return html`
    <h1>${frase(corrigiendo ? s.ficha_titulo_corregir : s.ficha_titulo)}</h1>
    <p className="pista">${frase(propuesta ? s.ficha_explica_propuesta : s.ficha_explica)}</p>
    <${AvisoDeError} texto=${error} />

    ${
      // **Lo que se ha leído de la foto, contado con sus palabras.** Sin esto, unos campos rellenos
      // solos parecen cosa del programa y no una lectura que hay que revisar. Las frases compuestas
      // («Leído de la foto de la etiqueta», «He podido leer 6 datos») **las monta `app.js`** con los
      // textos del servidor: aquí no se une ni una palabra (`docs/REACT.md`).
      propuesta
        ? html`
            <div className="aviso">
              <strong>${frase(propuesta.como_se_leyo_texto)}</strong>
              ${propuesta.resumen_campos ? html`<p>${frase(propuesta.resumen_campos)}</p>` : null}
              ${propuesta.idioma_texto ? html`<p>${frase(propuesta.idioma_texto)}</p>` : null}
              <p>${frase(s.no_confirmada)}</p>
              ${(propuesta.avisos || []).map(
                (aviso, indice) => html`<p key=${"av" + indice}>${frase(aviso)}</p>`,
              )}
            </div>
          `
        : null
    }
    ${
      // **Lo que el papel dice y no se puede apuntar tal cual** (una caducidad de mes y año, una
      // dosis sin decir si es por hectárea). Es distinto de un hueco: aquí hay un dato delante.
      propuesta && (propuesta.dudas || []).length
        ? html`
            <div className="aviso aviso-error">
              <strong>${frase(s.lo_que_dice_el_papel)}</strong>
              <p>${frase(s.lo_que_dice_el_papel_explica)}</p>
              ${propuesta.dudas.map((duda, indice) => html`<p key=${"d" + indice}>${frase(duda)}</p>`)}
            </div>
          `
        : null
    }

    ${
      // Elegir un insumo que ya está en el almacén: es lo que impide que la etiqueta de una semilla
      // que ya entró por albarán cree un segundo artículo con el mismo nombre.
      !corrigiendo
        ? html`
            <${Elegir}
              id="semilla-articulo"
              etiqueta=${s.articulo_del_almacen}
              pista=${s.articulo_del_almacen_pista}
              opciones=${articulos}
              vacio=${s.articulo_nuevo}
            />
          `
        : null
    }

    <${Campo}
      id="semilla-nombre"
      etiqueta=${s.nombre_del_articulo}
      pista=${s.nombre_del_articulo_pista}
      valor=${valor("nombre")}
    />
    <${Campo} id="semilla-especie" etiqueta=${s.especie} pista=${s.especie_pista} valor=${valor("especie")} />
    <${Campo} id="semilla-variedad" etiqueta=${s.variedad} pista=${s.variedad_pista} valor=${valor("variedad")} />
    <${Campo}
      id="semilla-casa"
      etiqueta=${s.casa_comercial}
      pista=${s.casa_comercial_pista}
      valor=${valor("casa_comercial")}
    />
    <${Campo}
      id="semilla-proveedor"
      etiqueta=${s.proveedor}
      pista=${s.proveedor_pista}
      valor=${valor("proveedor")}
    />
    <${Campo}
      id="semilla-lote"
      etiqueta=${s.numero_lote_proveedor}
      pista=${s.numero_lote_proveedor_pista}
      valor=${valor("numero_lote_proveedor")}
    />

    <div className="campo-fila">
      <${Campo}
        id="semilla-dosis"
        etiqueta=${s.dosis_recomendada}
        pista=${s.dosis_recomendada_pista}
        tipo="numero"
        valor=${valor("dosis_recomendada_por_ha")}
      />
      <${Elegir}
        id="semilla-unidad-dosis"
        etiqueta=${s.unidad_de_la_dosis}
        opciones=${unidades_dosis}
        elegido=${valor("unidad_dosis")}
        vacio=${s.sin_decir}
      />
    </div>

    <${Campo}
      id="semilla-envasado"
      etiqueta=${s.fecha_envasado}
      tipo="fecha"
      valor=${valor("fecha_envasado")}
    />
    <${Campo}
      id="semilla-caducidad"
      etiqueta=${s.fecha_caducidad}
      pista=${s.fecha_caducidad_pista}
      tipo="fecha"
      valor=${valor("fecha_caducidad")}
    />

    <div className="campo-fila">
      <${Campo}
        id="semilla-germinativo"
        etiqueta=${s.poder_germinativo}
        pista=${s.poder_germinativo_pista}
        tipo="numero"
        valor=${valor("poder_germinativo_pct")}
      />
      <${Campo}
        id="semilla-pureza"
        etiqueta=${s.pureza}
        pista=${s.pureza_pista}
        tipo="numero"
        valor=${valor("pureza_pct")}
      />
    </div>
    ${
      // **«La etiqueta no lo dice» es una respuesta**, y por eso se enseña debajo de los dos campos:
      // si el poder germinativo no viene, el agricultor tiene que saber que dejarlo en blanco es lo
      // correcto y no un descuido suyo.
      html`<p className="pista-campo">${frase(s.no_lo_dice)}</p>`
    }

    <${Elegir}
      id="semilla-tratada"
      etiqueta=${s.tratada}
      pista=${s.tratada_pista}
      opciones=${[
        { valor: "si", texto: s.tratada_si },
        { valor: "no", texto: s.tratada_no },
        { valor: "no_se", texto: s.tratada_no_se },
      ]}
      elegido=${valor("tratada")}
    />

    <${Elegir}
      id="semilla-categoria"
      etiqueta=${s.categoria_semilla}
      pista=${s.categoria_semilla_pista}
      opciones=${[
        { valor: "", texto: s.categoria_semilla_no_consta },
        { valor: "no_certificada", texto: s.categoria_semilla_no_certificada },
        { valor: "base", texto: s.categoria_semilla_base },
        { valor: "certificada", texto: s.categoria_semilla_certificada },
        { valor: "r1", texto: s.categoria_semilla_r1 },
        { valor: "r2", texto: s.categoria_semilla_r2 },
      ]}
      elegido=${valor("categoria_semilla")}
    />

    <${Elegir}
      id="semilla-procedencia"
      etiqueta=${s.procedencia}
      pista=${s.procedencia_pista}
      opciones=${[
        { valor: "", texto: s.procedencia_no_consta },
        { valor: "comprada", texto: s.procedencia_comprada },
        { valor: "propia", texto: s.procedencia_propia },
      ]}
      elegido=${valor("procedencia")}
    />

    ${
      // **La foto se lee aquí y no guarda nada**: se sube, el programa dice lo que ha entendido y los
      // campos de arriba se rellenan con eso para que el agricultor los revise. Hasta que no pulse
      // GUARDAR LA SEMILLA no hay ninguna semilla apuntada. Cuando la semilla ya existe (corrigiendo),
      // hay además un botón para **guardar el papel** con ella.
      html`
        <div className="campo">
          <label htmlFor="semilla-foto">${frase(s.leer_etiqueta)}</label>
          <input id="semilla-foto" type="file" accept=".pdf,image/*" />
          <p className="pista-campo">${frase(s.leer_etiqueta_pista)}</p>
        </div>
        <div className="barra-acciones">
          <button
            type="button"
            className="boton"
            data-accion="semilla-leer-foto"
            disabled=${guardando}
          >
            ${frase(s.leer_lo_que_pone)}
          </button>
          ${
            corrigiendo
              ? html`
                  <button
                    type="button"
                    className="boton boton-claro"
                    data-accion="semilla-subir-foto"
                    disabled=${guardando}
                  >
                    ${frase(s.subir_la_foto)}
                  </button>
                  <${BotonSencillo} etiqueta=${s.ver_la_foto} accion="semilla-ver-foto" clase="" />
                `
              : null
          }
        </div>
      `
    }

    <div className="barra-acciones">
      <button
        type="button"
        className="boton boton-principal"
        data-accion="semilla-guardar"
        disabled=${guardando}
      >
        ${frase(guardando ? s.guardando : s.guardar)}
      </button>
      ${
        // **La puerta para sembrarla.** Sin este botón no había forma de llegar al formulario de la
        // siembra desde ninguna pantalla: el manejador de clics atendía `siembra-nueva`, el texto
        // estaba escrito y la pantalla existía, pero **no la pintaba nadie** — es la familia de fallo
        // que este proyecto persigue («un dato que existe y una puerta que falta»). Se pinta solo
        // cuando la semilla ya existe (no se puede sembrar lo que todavía no está guardado).
        semillaId
          ? html`
              <${Boton}
                etiqueta=${s.sembrar_esta}
                pista=${s.sembrar_esta_pista}
                accion="siembra-nueva"
                datos=${{ id: semillaId }}
              />
            `
          : null
      }
      <${Boton} etiqueta=${s.volver_a_las_semillas} accion="semillas-ver" clase="boton-claro" />
    </div>
  `;
}

/** El elemento de React de la lista, ya con sus propiedades puestas. */
export function pantallaDeLasSemillas(propiedades) {
  return html`
    <${PantallaDeLasSemillas}
      textos=${propiedades.textos}
      tarjetas=${propiedades.tarjetas}
      resumen=${propiedades.resumen}
      aviso=${propiedades.aviso}
      error=${propiedades.error}
      cargando=${propiedades.cargando}
    />
  `;
}

/** Y el de la ficha. */
export function pantallaDeUnaSemilla(propiedades) {
  return html`
    <${PantallaDeUnaSemilla}
      textos=${propiedades.textos}
      borrador=${propiedades.borrador}
      propuesta=${propiedades.propuesta}
      articulos=${propiedades.articulos}
      unidades_dosis=${propiedades.unidades_dosis}
      unidades_cantidad=${propiedades.unidades_cantidad}
      semillaId=${propiedades.semillaId}
      corrigiendo=${propiedades.corrigiendo}
      guardando=${propiedades.guardando}
      error=${propiedades.error}
    />
  `;
}
