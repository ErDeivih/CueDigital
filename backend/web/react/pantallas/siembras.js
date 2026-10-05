/*
 * siembras.js — Asignar una semilla a una siembra (T10, 03/10/2026), en React.
 *
 * POR QUÉ ESTAS DOS PANTALLAS
 *
 * «En esta tierra sembré esta semilla» es un hecho del cuaderno, y de él salen dos cosas a la vez:
 * **el apunte** (qué se sembró, dónde y cuándo) y **el descuento del almacén** (esa semilla sale de su
 * saco). Las dos van juntas porque separarlas es lo que hace que un almacén deje de cuadrar: aquí se
 * apunta una vez y el libro se mueve una vez.
 *
 * LO QUE ESTAS PANTALLAS NO HACEN, Y ES LO QUE MÁS IMPORTA
 *
 *  1. **No calculan nada.** La cantidad total, la dosis por hectárea y lo que queda en el almacén
 *     **llegan contados del servidor**, con su unidad. Aquí solo se pintan: la cuenta
 *     `dosis × hectáreas` vive en un solo sitio, y así la pantalla no puede decir un número distinto
 *     del que se guardó.
 *  2. **No confunden las dos cifras.** Son **dos campos separados, cada uno con su unidad y con su
 *     nombre**: «Cuánto se siembra en cada hectárea» y «Cuánto se ha gastado en total». Y cuando el
 *     servidor dice que una la ha calculado él, sale la palabra «Lo ha calculado el programa» con su
 *     explicación, porque un número calculado se revisa y uno inventado no.
 *  3. **No convierten litros en kilos.** Cuando las unidades no se pueden comparar, lo dice el
 *     servidor y aquí se enseña tal cual.
 *
 * Y una cosa que se conserva a propósito: **la siembra se apunta desde la semilla** (se entra por
 * «SEMBRAR ESTA SEMILLA» en su ficha), así que la semilla de la que sale todo —y sus envases— ya está
 * elegida y no hay dos desplegables que puedan contradecirse.
 *
 * Los `id` de los campos (`siembra-superficie`, `siembra-dosis`…) son los que lee `app.js`, y no se
 * pueden cambiar: si cambian, el formulario se rellena y se guarda vacío sin que salte nada.
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

/** Un desplegable con su etiqueta. */
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

/** Una fila de «nombre y valor», para lo que ya está decidido y no se elige aquí. */
function Fila({ etiqueta, valor }) {
  return html`
    <span className="tarjeta-fila">
      <span className="tarjeta-fila-etiqueta">${frase(etiqueta)}</span>
      <span className="tarjeta-fila-valor">${frase(valor)}</span>
    </span>
  `;
}

/**
 * La lista de lo que se ha sembrado.
 *
 * Propiedades: `tarjetas` (ya preparadas por `app.js`: la tierra, la semilla, las dos cifras cada una
 * con su nombre, y si descontó del almacén) y `resumen` (cuántas hay, en singular o en plural).
 */
export function PantallaDeLasSiembras({
  textos = {},
  tarjetas = [],
  resumen = "",
  puedeSembrar = true,
  aviso = "",
  calculado = null,
  avisos = [],
  error = "",
  cargando = false,
}) {
  const s = textos.semillas || {};
  return html`
    <h1>${frase(s.siembras_titulo)}</h1>
    <p className="pista">${frase(s.siembras_explica)}</p>
    <${AvisoDeError} texto=${error} />
    ${aviso ? html`<div className="aviso"><strong>${frase(aviso)}</strong></div>` : null}
    ${
      // **Lo que el servidor ha dicho al guardar se lee aquí.** El aviso solo existe en la respuesta de
      // guardar (al volver a leer la siembra ya no viene), así que si no se enseña aquí no lo lee
      // nadie: el agricultor vería un total que él no ha escrito como si lo hubiera escrito él.
      calculado
        ? html`
            <div className="aviso">
              <strong>${frase(s.calculado)}</strong>
              <p>${frase(s.calculado_pista)}</p>
              ${calculado.cantidad_total ? html`<p>${frase(calculado.total_en_palabras)}</p>` : null}
              ${calculado.dosis_por_ha ? html`<p>${frase(calculado.dosis_en_palabras)}</p>` : null}
            </div>
          `
        : null
    }
    ${(avisos || []).map(
      // Los demás avisos del servidor (por ejemplo que no se ha podido descontar del almacén).
      (texto, indice) =>
        calculado && (calculado.avisos || []).includes(texto)
          ? null
          : html`<div className="aviso" key=${"av" + indice}><p>${frase(texto)}</p></div>`,
    )}
    ${cargando ? html`<p className="pista">${frase(s.buscando)}</p>` : null}

    ${
      tarjetas.length === 0
        ? html`<p className="aviso">${frase(s.siembras_vacia)}</p>`
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
          accion="siembra-abrir"
          datos=${{ id: tarjeta.id }}
          textos=${{ elegida: "" }}
        />
      `,
    )}

    ${
      // **Un aviso nunca deja sin salida** (regla de la casa): si no hay ninguna semilla dada de alta,
      // el aviso va con el botón que lo arregla.
      puedeSembrar
        ? null
        : html`
            <div className="aviso">
              <p>${frase(s.sin_semillas)}</p>
              <div className="barra-acciones">
                <${Boton} etiqueta=${s.anadir} accion="semilla-nueva" clase="boton-principal" />
              </div>
            </div>
          `
    }

    <div className="barra-acciones">
      <${BotonSencillo} etiqueta=${s.volver_a_las_semillas} accion="semillas-ver" clase="" />
      <${BotonSencillo} etiqueta=${s.volver_al_inicio} accion="ir-inicio" clase="" />
    </div>
  `;
}

/**
 * Asignar una semilla a una siembra, o corregir una que ya está apuntada.
 *
 * Propiedades:
 *
 *  - `borrador`: lo que va en los campos (la tierra, la fecha, la superficie, la dosis con su unidad,
 *    el total con su unidad, el envase y las notas).
 *  - `semilla`: el nombre de la semilla de la que sale todo. **No es un desplegable a propósito**: se
 *    entra por la ficha de la semilla, así que lo que queda y los envases son los suyos.
 *  - `tierras` y `envases`: para elegir la tierra y el saco del que sale.
 *  - `quedar`: lo que queda de esa semilla, ya contado por el servidor (o `null` si no se puede saber).
 *  - `calculado`: `{total_en_palabras, dosis_en_palabras}` con lo que el servidor ha calculado. Las
 *    frases las monta `app.js` con los textos del servidor (`docs/REACT.md`).
 *  - `corrigiendo`: si es corregir (entonces hay ANULAR con su motivo).
 */
export function PantallaDeUnaSiembra({
  textos = {},
  borrador = {},
  semilla = "",
  tierras = [],
  envases = [],
  unidades_dosis = [],
  unidades_cantidad = [],
  calculado = null,
  quedar = null,
  corrigiendo = false,
  guardando = false,
  descuadre = false,
  error = "",
}) {
  const s = textos.semillas || {};
  const valor = (clave) => (borrador[clave] == null ? "" : borrador[clave]);
  return html`
    <h1>${frase(corrigiendo ? s.siembra_titulo_corregir : s.siembra_titulo)}</h1>
    <p className="pista">${frase(s.siembra_explica)}</p>
    <${AvisoDeError} texto=${error} />

    <div className="aviso">
      <${Fila} etiqueta=${s.siembra_semilla} valor=${semilla} />
      ${
        quedar
          ? html`
              <${Fila}
                etiqueta=${s.lo_que_queda}
                valor=${quedar.saldo === null || quedar.saldo === undefined
                  ? s.sin_saber_lo_que_queda
                  : `${quedar.saldo} ${quedar.unidad || ""}`}
              />
              ${quedar.motivo ? html`<p>${frase(quedar.motivo)}</p>` : null}
            `
          : null
      }
    </div>

    <${Elegir}
      id="siembra-tierra"
      etiqueta=${s.siembra_tierra}
      opciones=${tierras}
      elegido=${valor("parcela_id")}
      vacio=${s.siembra_elige_la_tierra}
    />
    <${Campo} id="siembra-fecha" etiqueta=${s.siembra_fecha} tipo="fecha" valor=${valor("fecha")} />
    <${Campo}
      id="siembra-superficie"
      etiqueta=${s.siembra_superficie}
      pista=${s.siembra_superficie_pista}
      tipo="numero"
      valor=${valor("superficie_ha")}
    />

    <div className="campo-fila">
      <${Campo}
        id="siembra-dosis"
        etiqueta=${s.siembra_dosis}
        pista=${s.siembra_dosis_pista}
        tipo="numero"
        valor=${valor("dosis_por_ha")}
      />
      <${Elegir}
        id="siembra-unidad-dosis"
        etiqueta=${s.unidad_de_la_dosis}
        opciones=${unidades_dosis}
        elegido=${valor("unidad_dosis")}
        vacio=${s.sin_decir}
      />
    </div>

    <div className="campo-fila">
      <${Campo}
        id="siembra-cantidad"
        etiqueta=${s.siembra_cantidad_total}
        pista=${s.siembra_cantidad_total_pista}
        tipo="numero"
        valor=${valor("cantidad_total")}
      />
      <${Elegir}
        id="siembra-unidad-cantidad"
        etiqueta=${s.siembra_unidad_total}
        opciones=${unidades_cantidad}
        elegido=${valor("unidad_cantidad")}
        vacio=${s.sin_decir}
      />
    </div>

    ${
      // **El número que ha calculado el programa se dice, y con su explicación**: el agricultor tiene
      // que poder revisarlo. Sin esto, un total que él no ha escrito parece un dato del papel.
      calculado
        ? html`
            <div className="aviso">
              <strong>${frase(s.calculado)}</strong>
              <p>${frase(s.calculado_pista)}</p>
              ${calculado.cantidad_total ? html`<p>${frase(calculado.total_en_palabras)}</p>` : null}
              ${calculado.dosis_por_ha ? html`<p>${frase(calculado.dosis_en_palabras)}</p>` : null}
            </div>
          `
        : null
    }

    <${Elegir}
      id="siembra-envase"
      etiqueta=${s.siembra_envase}
      pista=${s.siembra_envase_pista}
      opciones=${envases}
      elegido=${valor("lote_id")}
      vacio=${s.siembra_sin_envase}
    />
    <${Campo} id="siembra-notas" etiqueta=${s.siembra_notas} valor=${valor("notas")} />

    ${
      corrigiendo
        ? html`
            <div className="campo">
              <label htmlFor="siembra-motivo">${frase(s.siembra_motivo_anulacion)}</label>
              <p className="pista-campo">${frase(s.siembra_motivo_anulacion_pista)}</p>
              <input id="siembra-motivo" type="text" defaultValue=${frase(valor("motivo_anulacion"))} />
            </div>
          `
        : null
    }

    <div className="barra-acciones">
      <button
        type="button"
        className="boton boton-principal"
        data-accion="siembra-guardar"
        disabled=${guardando}
      >
        ${frase(guardando ? s.guardando_siembra : s.guardar_siembra)}
      </button>
      ${
        // **La salida cuando lo que sale deja el envase en negativo** (el servidor contesta 409): el
        // agricultor dice que la diferencia es de verdad y se apunta, que es lo mismo que hace el
        // almacén en «sacar de un envase». Lo que no se hace nunca es apuntarlo a escondidas.
        descuadre
          ? html`
              <button
                type="button"
                className="boton"
                data-accion="siembra-aceptar-descuadre"
                disabled=${guardando}
              >
                ${frase((textos.almacen || {}).libro_salida_descuadre_si)}
              </button>
            `
          : null
      }
      ${
        corrigiendo
          ? html`
              <button
                type="button"
                className="boton boton-claro"
                data-accion="siembra-anular"
                disabled=${guardando}
              >
                ${frase(s.siembra_anular)}
              </button>
            `
          : null
      }
      <${Boton} etiqueta=${s.volver_a_las_siembras} accion="siembras-ver" clase="boton-claro" />
    </div>
  `;
}

/** El elemento de React de la lista. */
export function pantallaDeLasSiembras(propiedades) {
  return html`
    <${PantallaDeLasSiembras}
      textos=${propiedades.textos}
      tarjetas=${propiedades.tarjetas}
      resumen=${propiedades.resumen}
      puedeSembrar=${propiedades.puedeSembrar}
      aviso=${propiedades.aviso}
      calculado=${propiedades.calculado}
      avisos=${propiedades.avisos}
      error=${propiedades.error}
      cargando=${propiedades.cargando}
    />
  `;
}

/** Y el de la siembra. */
export function pantallaDeUnaSiembra(propiedades) {
  return html`
    <${PantallaDeUnaSiembra}
      textos=${propiedades.textos}
      borrador=${propiedades.borrador}
      semilla=${propiedades.semilla}
      tierras=${propiedades.tierras}
      envases=${propiedades.envases}
      unidades_dosis=${propiedades.unidades_dosis}
      unidades_cantidad=${propiedades.unidades_cantidad}
      calculado=${propiedades.calculado}
      quedar=${propiedades.quedar}
      corrigiendo=${propiedades.corrigiendo}
      guardando=${propiedades.guardando}
      descuadre=${propiedades.descuadre}
      error=${propiedades.error}
    />
  `;
}
