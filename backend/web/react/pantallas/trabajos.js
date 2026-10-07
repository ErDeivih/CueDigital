/*
 * trabajos.js — La agenda de los trabajos, la ficha de uno y la historia de una tierra (T15, 05/10/2026).
 *
 * POR QUÉ ESTAS TRES PANTALLAS EN UN FICHERO
 *
 * Son el mismo asunto mirado de tres maneras, y el contrato las pide juntas (§4, S03/S04/S05): **la
 * agenda** (qué está previsto y qué se ha hecho), **el trabajo** (planificarlo, marcar lo que de verdad
 * se hizo, cambiarlo de día, corregirlo o anularlo) y **la historia de una tierra** (todo lo que ha
 * pasado en ella, con su estado de hoy). La ficha se abre desde la agenda y la historia se abre desde la
 * tierra, y las tres enseñan los mismos hechos.
 *
 * LO QUE ESTAS PANTALLAS NO HACEN, Y ES LO QUE MÁS IMPORTA
 *
 *  1. **No calculan nada.** Los días que faltan, las hectáreas, las horas, lo que gastaría un trabajo
 *     previsto y lo que hay sembrado **llegan contados del servidor**. Aquí solo se pintan. Es la regla
 *     del encargo —«el cuaderno y los paneles usan los mismos hechos»— y el motivo de que se pueda
 *     comprobar: la cuenta vive en un solo sitio (`app/trabajos.py`) y la pantalla no puede decir un
 *     número distinto del que se guardó.
 *  2. **No arman sus propias frases.** Las listas y las fichas llegan **ya preparadas por `app.js`**
 *     (como en «lo que he sembrado» y en «mi cuaderno»): cada línea trae su título, su fecha escrita y
 *     sus filas con el rótulo delante, montadas desde `textos.py`. Aquí no hay ni una frase escrita a
 *     mano, que es la regla de la casa y lo que hace que el test de jerga cubra también esta pantalla.
 *  3. **No deducen nada del tiempo.** Si el servidor dice que no consta la nascencia, aquí se enseña «No
 *     consta si ha nacido» con su explicación; la pantalla **no** convierte una lluvia en una nascencia
 *     ni un apero en una siembra.
 *  4. **No rellenan los huecos con ceros.** Un trabajo sin hectáreas, sin horas o sin máquina se enseña
 *     diciendo que no lo dice, nunca con un «0 ha»: eso diría que se trabajaron cero hectáreas.
 *  5. **No esconden lo anulado.** Sale tachado, con su motivo y con la palabra que dice que no cuenta.
 *
 * Y una decisión de la pantalla, que es la otra mitad del ticket: **lo previsto y lo hecho van en dos
 * listas separadas**, cada una con su título. Juntarlos en una sola lista con una etiqueta de color es
 * exactamente lo que hace que un plan parezca un trabajo hecho, y ese es el defecto que este ticket
 * existe para no cometer. Por el mismo motivo, cuando se marca lo que de verdad se hizo, **lo que se
 * había pensado se enseña al lado**: se apunta el hecho, no el plan.
 *
 * LOS `data-accion` Y LOS `id`, QUE SON LO QUE HACE QUE ESTO FUNCIONE
 *
 * El manejador de clics es **uno solo** y vive en `app.js`: los botones de aquí llevan `data-accion` con
 * el nombre de la acción, y el formulario lleva los `id` que `app.js` lee para recoger lo escrito
 * (`trabajo-fecha`, `trabajo-superficie`, `trabajo-horas`…). Si un `id` cambia, el formulario se guarda
 * vacío sin que salte nada; si una acción no está atendida, el botón se pinta y no hace nada. Las
 * acciones que esta pantalla puede pintar están listadas en el informe del ticket, una por una, con lo
 * que tiene que hacer cada una.
 */

import { AvisoDeError, Boton, Botones, BotonSencillo, frase, html } from "../componentes.js";
// `rellena` (para la frase que dice cuántos gastos no traen el importe) vive en el núcleo, como en las
// demás pantallas que rellenan un hueco de una frase del servidor.
import { rellena } from "../../nucleo.js";

/** Un campo de escribir con su etiqueta y su pista. */
function Campo({ id, etiqueta, pista, tipo = "texto", valor = "", soloLectura = false }) {
  return html`
    <div className="campo">
      <label htmlFor=${id}>${frase(etiqueta)}</label>
      ${pista ? html`<p className="pista-campo">${frase(pista)}</p>` : null}
      ${
        tipo === "fecha"
          ? html`<input id=${id} type="date" defaultValue=${frase(valor)} readOnly=${soloLectura} />`
          : html`<input
              id=${id}
              type="text"
              inputMode=${tipo === "numero" ? "decimal" : undefined}
              defaultValue=${frase(valor)}
              readOnly=${soloLectura}
            />`
      }
    </div>
  `;
}

/** Un desplegable con su etiqueta. Las opciones las prepara `app.js` desde `textos.py`. */
function Elegir({ id, etiqueta, pista, opciones = [], elegido = "", vacio = "", soloLectura = false }) {
  return html`
    <div className="campo">
      <label htmlFor=${id}>${frase(etiqueta)}</label>
      ${pista ? html`<p className="pista-campo">${frase(pista)}</p>` : null}
      <select id=${id} defaultValue=${frase(elegido)} disabled=${soloLectura}>
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

/** Una fila de «nombre y valor», para lo que ya está decidido. */
function Fila({ etiqueta, valor }) {
  return html`
    <span className="tarjeta-fila">
      <span className="tarjeta-fila-etiqueta">${frase(etiqueta)}</span>
      <span className="tarjeta-fila-valor">${frase(valor)}</span>
    </span>
  `;
}

/**
 * Lo que no consta, con su frase y **su explicación de por qué no se deduce**.
 *
 * Es la mitad del ticket: aquí se dice que una lluvia no acredita que la planta haya nacido, que un
 * rodillo no borra la siembra y que después de la cosecha no se sabe lo que quedó. Si esto se callara,
 * el hueco parecería un olvido del programa y alguien lo rellenaría con lo que le parece.
 */
function LoQueNoConsta({ textos = {}, avisos = [] }) {
  const a = textos.agenda || {};
  if (!avisos.length) return null;
  return html`
    <div className="aviso">
      <strong>${frase(a.no_consta)}</strong>
      ${avisos.map(
        (aviso, indice) => html`
          <p key=${"a" + indice}>
            ${frase(aviso.texto)}${aviso.cuantos ? html` <strong>${frase(String(aviso.cuantos))}</strong>` : null}
          </p>
        `,
      )}
    </div>
  `;
}

/**
 * La agenda: **lo previsto y lo hecho, en dos listas y sin mezclarse** (S04).
 *
 * Propiedades (todo preparado por `app.js`):
 *
 *  - `textos`: `{agenda, acciones}` del servidor. Nada escrito aquí.
 *  - `previstos`: los trabajos planificados, cada uno con su título, su «cuándo» ya escrito (con los días
 *    que faltan, o diciendo que no tiene día), su tierra y lo que gastaría, si se puede estimar. Y los que
 *    **ya se cumplieron** traen `cuando_lo_hice` (el día del hecho, ya escrito): con eso la lista sigue
 *    enseñando lo que se pensó **sin ofrecer un botón que ya no puede funcionar**.
 *  - `hechos`: lo que se ha hecho, con su día, su tierra, su máquina, sus horas y sus insumos. **Los
 *    anulados vienen dentro**, marcados: no se esconden.
 *  - `lo_que_no_se_sabe`: los huecos, con su frase y cuántos son.
 *  - `resumen`, `sin_decir`, `aviso`, `error`, `cargando`: lo que el servidor dice de la lista.
 *  - `puedePlanificar`: si hay tierras dadas de alta (si no, el aviso trae el botón que lo arregla).
 */
export function PantallaDeLosTrabajos({
  textos = {},
  previstos = [],
  hechos = [],
  resumen = "",
  sin_decir = "",
  aviso = "",
  avisos = [],
  lo_que_no_se_sabe = [],
  error = "",
  cargando = false,
  puedePlanificar = true,
}) {
  const a = textos.agenda || {};
  const acciones = textos.acciones || {};
  return html`
    <h1>${frase(a.titulo)}</h1>
    <p className="pista">${frase(a.explica)}</p>
    <${AvisoDeError} texto=${error} />
    ${aviso ? html`<div className="aviso"><strong>${frase(aviso)}</strong></div>` : null}
    ${(avisos || []).map(
      (linea, indice) => html`<div className="aviso" key=${"av" + indice}><p>${frase(linea)}</p></div>`,
    )}
    ${cargando ? html`<p className="pista">${frase(a.buscando)}</p>` : null}

    <h2>${frase(a.previstos_titulo)}</h2>
    <p className="pista-campo">${frase(a.previstos_explica)}</p>
    ${
      previstos.length === 0
        ? html`<div className="aviso">${frase(a.previstos_vacio)}</div>`
        : html`<ul className="lista">
            ${previstos.map(
              (linea, indice) => html`
                <li key=${"p" + indice}>
                  <strong>${frase(linea.titulo)}</strong>
                  <p className="pista-campo">${frase(linea.cuando)}</p>
                  ${linea.tierra ? html`<p>${frase(linea.tierra)}</p>` : null}
                  ${
                    // Lo que gastaría, **dicho como estimación**. Si no se puede estimar porque falta la
                    // dosis o las hectáreas, se dice lo que falta en vez de enseñar un número inventado.
                    linea.gastaria ? html`<p className="pista-campo">${frase(linea.gastaria)}</p>` : null
                  }
                  ${
                    // Y la frase que impide el malentendido de todo el ticket: esto **no** ha gastado nada.
                    linea.no_gasta ? html`<p className="pista-campo">${frase(linea.no_gasta)}</p>` : null
                  }
                  ${
                    // **Un plan ya cumplido lo dice, y no ofrece volver a cumplirlo.** Se encontró
                    // pulsando: la lista de lo pensado trae también los planes que ya se hicieron (y tiene
                    // que traerlos: el plan sigue siendo lo que se pensó), pero la pantalla les pintaba
                    // «YA LO HE HECHO» otra vez. El agricultor lo pulsaba, rellenaba la ficha y el
                    // servidor contestaba **409** («este trabajo ya estaba apuntado»): un botón que no
                    // puede funcionar. El hecho ya está en la otra lista, con su CORREGIRLO y su ANULARLO,
                    // así que aquí solo se dice cuándo se hizo. La frase la lee la pantalla de su propio
                    // vocabulario, y el día llega ya escrito porque quien cruza las dos listas es `app.js`.
                    linea.cuando_lo_hice
                      ? html`<p className="pista-campo">${frase(a.ya_esta_hecho)} ${frase(linea.cuando_lo_hice)}</p>`
                      : html`<${Botones}
                          botones=${[
                            {
                              etiqueta: a.ya_lo_he_hecho,
                              accion: "trabajo-hecho",
                              datos: { id: linea.id },
                              clase: "boton-principal",
                              sencillo: true,
                            },
                            {
                              etiqueta: a.cambiarlo_de_dia,
                              accion: "trabajo-abrir",
                              datos: { id: linea.id },
                              clase: "boton-claro",
                              sencillo: true,
                            },
                            {
                              etiqueta: a.cancelarlo,
                              accion: "trabajo-cancelar",
                              datos: { id: linea.id },
                              clase: "boton-claro",
                              sencillo: true,
                            },
                          ]}
                          barra=${false}
                        />`
                  }
                </li>
              `,
            )}
          </ul>`
    }
    ${
      // **Un aviso nunca deja sin salida** (regla de la casa): sin tierras no se puede planificar, y el
      // aviso trae el botón que lo arregla.
      puedePlanificar
        ? html`<div className="barra-acciones">
            <${Boton} etiqueta=${a.planificar} accion="trabajo-planificar" clase="boton-principal" />
          </div>`
        : html`
            <div className="aviso">
              <p>${frase(a.sin_tierras)}</p>
              <div className="barra-acciones">
                <${Boton} etiqueta=${a.anadir_tierra} accion="t06-ver-mis-tierras" clase="boton-principal" />
              </div>
            </div>
          `
    }

    <h2>${frase(a.hechos_titulo)}</h2>
    <p className="pista-campo">${frase(a.hechos_explica)}</p>
    ${
      hechos.length === 0
        ? html`<div className="aviso">${frase(a.hechos_vacio)}</div>`
        : html`<ul className="lista">
            ${hechos.map(
              (hecho, indice) => html`
                <li key=${"h" + indice}>
                  <strong>${frase(hecho.titulo)}</strong>
                  <p className="pista-campo">${frase(hecho.cuando)}</p>
                  ${hecho.tierra ? html`<p>${frase(hecho.tierra)}</p>` : null}
                  ${
                    // **Los huecos se enseñan como huecos**: «no dice las horas» es un dato, y poner un
                    // cero diría que no se estuvo ninguna hora.
                    (hecho.faltan || []).map(
                      (falta, numero) => html`<p className="pista-campo" key=${"f" + numero}>${frase(falta)}</p>`,
                    )
                  }
                  ${
                    hecho.anulado
                      ? html`
                          <div className="aviso">
                            <p><strong>${frase(hecho.no_cuenta)}</strong></p>
                            <p>${frase(hecho.motivo_anulacion || "")}</p>
                          </div>
                        `
                      : null
                  }
                  <${Botones}
                    botones=${[
                      {
                        etiqueta: a.corregirlo,
                        accion: "trabajo-corregir",
                        datos: { id: hecho.id },
                        clase: "boton-claro",
                        sencillo: true,
                      },
                      {
                        etiqueta: a.anularlo,
                        accion: "trabajo-anular",
                        datos: { id: hecho.id },
                        clase: "boton-claro",
                        sencillo: true,
                      },
                    ]}
                    barra=${false}
                  />
                </li>
              `,
            )}
          </ul>`
    }
    ${resumen ? html`<p className="cuantas">${frase(resumen)}</p>` : null}
    ${sin_decir ? html`<p className="pista-campo">${frase(sin_decir)}</p>` : null}

    <${LoQueNoConsta} textos=${textos} avisos=${lo_que_no_se_sabe} />

    <div className="barra-acciones">
      <${BotonSencillo} etiqueta=${acciones.volver || ""} accion="ir-inicio" clase="" />
      <${BotonSencillo} etiqueta=${a.ver_el_cuaderno} accion="cuaderno-abrir" clase="" />
    </div>
  `;
}

/**
 * La ficha de un trabajo (S05): planificarlo, **marcar lo que de verdad se hizo**, cambiarlo de día,
 * corregirlo o anularlo.
 *
 * Propiedades (preparadas por `app.js`):
 *
 *  - `modo`: `"planificar"` | `"reprogramar"` | `"hecho"` | `"corregir"` | `"anular"`. Lo que cambia es el
 *    título, lo que se puede escribir y **qué acción guarda**:
 *      · `planificar` → `trabajo-previsto-guardar` (nace un plan, y no gasta nada),
 *      · `reprogramar` → `trabajo-reprogramar` (solo el día, y el anterior queda escrito),
 *      · `hecho` → `trabajo-hecho-guardar` (nace el hecho, y se descuenta del almacén),
 *      · `corregir` → `trabajo-guardar` (la misma fila, con el rastro de lo que decía),
 *      · `anular` → `trabajo-anular-confirmar` (el motivo, y lo que salió vuelve a contar).
 *  - `borrador`: lo que va en los campos.
 *  - `tipos`, `subtipos`, `tierras`, `maquinas`, `insumos`, `unidades`: las opciones, del servidor.
 *  - `previsto`: el plan del que sale, cuando se está marcando lo hecho. **Se enseña al lado**: lo que se
 *    había pensado y lo que de verdad pasó son dos cosas distintas, y verlas juntas es lo que evita
 *    apuntar el plan como si fuera el hecho.
 *  - `repaso`: lo que el servidor ha comprobado o lo que falta, antes de guardar.
 */
export function PantallaDeUnTrabajo({
  textos = {},
  modo = "planificar",
  borrador = {},
  tipos = [],
  subtipos = [],
  tierras = [],
  maquinas = [],
  insumos = [],
  unidades = [],
  previsto = null,
  repaso = [],
  guardando = false,
  error = "",
}) {
  const a = textos.agenda || {};
  const valor = (clave) => (borrador[clave] == null ? "" : borrador[clave]);
  const esPlan = modo === "planificar" || modo === "reprogramar";
  const soloElDia = modo === "reprogramar";
  const esAnular = modo === "anular";

  const titulo =
    modo === "planificar"
      ? a.planificar_titulo
      : modo === "reprogramar"
        ? a.reprogramar_titulo
        : modo === "hecho"
          ? a.hecho_titulo
          : modo === "anular"
            ? a.anular_titulo
            : a.corregir_titulo;
  const explicacion =
    modo === "reprogramar"
      ? a.reprogramar_explica
      : esPlan
        ? a.planificar_explica
        : esAnular
          ? a.anular_explica
          : a.hecho_explica;
  const etiquetaDeGuardar =
    modo === "planificar"
      ? a.guardar_previsto
      : modo === "reprogramar"
        ? a.cambiar_el_dia
        : modo === "hecho"
          ? a.guardar_trabajo
          : modo === "anular"
            ? a.anular_confirmar
            : a.guardar_correccion;

  return html`
    <h1>${frase(titulo)}</h1>
    <p className="pista">${frase(explicacion)}</p>
    <${AvisoDeError} texto=${error} />

    ${
      previsto
        ? html`
            <div className="aviso">
              <strong>${frase(a.lo_que_estaba_previsto)}</strong>
              ${(previsto.filas || []).map(
                (fila, indice) =>
                  html`<${Fila} key=${"pf" + indice} etiqueta=${fila.etiqueta} valor=${fila.valor} />`,
              )}
              <p>${frase(a.lo_previsto_no_gasta)}</p>
            </div>
          `
        : null
    }

    ${
      (repaso || []).length
        ? html`
            <div className="aviso">
              <strong>${frase(a.repaso)}</strong>
              ${repaso.map((linea, indice) => html`<p key=${"r" + indice}>${frase(linea)}</p>`)}
            </div>
          `
        : null
    }

    ${
      esAnular
        ? html`
            <${Campo}
              id="trabajo-motivo"
              etiqueta=${a.motivo_anulacion}
              pista=${a.motivo_anulacion_pista}
              valor=${valor("motivo_anulacion")}
            />
          `
        : html`
            <${Elegir}
              id="trabajo-tipo"
              etiqueta=${a.tipo}
              pista=${a.tipo_pista}
              opciones=${tipos}
              elegido=${valor("tipo")}
              vacio=${a.elige_el_trabajo}
              soloLectura=${soloElDia || modo === "corregir"}
            />
            <${Elegir}
              id="trabajo-subtipo"
              etiqueta=${a.subtipo}
              pista=${a.subtipo_pista}
              opciones=${subtipos}
              elegido=${valor("subtipo")}
              vacio=${a.sin_decir}
              soloLectura=${soloElDia || modo === "corregir"}
            />
            <${Elegir}
              id="trabajo-tierra"
              etiqueta=${a.tierra}
              opciones=${tierras}
              elegido=${valor("parcela_id")}
              vacio=${a.elige_la_tierra}
              soloLectura=${soloElDia}
            />
            <${Campo}
              id=${esPlan ? "trabajo-fecha-prevista" : "trabajo-fecha"}
              etiqueta=${esPlan ? a.dia_previsto : a.dia}
              pista=${esPlan ? a.dia_previsto_pista : a.dia_pista}
              tipo="fecha"
              valor=${esPlan ? valor("fecha_prevista") : valor("fecha")}
            />
            <${Campo}
              id="trabajo-superficie"
              etiqueta=${esPlan ? a.hectareas_previstas : a.hectareas}
              pista=${a.hectareas_pista}
              tipo="numero"
              valor=${valor("superficie_ha")}
              soloLectura=${soloElDia}
            />
            <${Campo}
              id="trabajo-horas"
              etiqueta=${esPlan ? a.horas_previstas : a.horas}
              pista=${a.horas_pista}
              tipo="numero"
              valor=${valor("horas")}
              soloLectura=${soloElDia}
            />
            <${Elegir}
              id="trabajo-maquina"
              etiqueta=${a.maquina}
              pista=${a.maquina_pista}
              opciones=${maquinas}
              elegido=${valor("equipo_id")}
              vacio=${a.sin_maquina}
              soloLectura=${soloElDia}
            />
            <${Elegir}
              id="trabajo-insumo"
              etiqueta=${a.insumo}
              pista=${esPlan ? a.insumo_previsto_pista : a.insumo_pista}
              opciones=${insumos}
              elegido=${valor("lote_id")}
              vacio=${a.sin_insumo}
              soloLectura=${soloElDia}
            />
            <${Campo}
              id="trabajo-cantidad"
              etiqueta=${a.cantidad}
              pista=${a.cantidad_pista}
              tipo="numero"
              valor=${valor("cantidad")}
              soloLectura=${soloElDia}
            />
            <${Elegir}
              id="trabajo-unidad"
              etiqueta=${a.unidad}
              opciones=${unidades}
              elegido=${valor("unidad")}
              vacio=${a.sin_decir}
              soloLectura=${soloElDia}
            />
            <${Campo}
              id="trabajo-observaciones"
              etiqueta=${a.observaciones}
              valor=${valor("observaciones")}
            />
          `
    }

    <div className="barra-acciones">
      ${
        // **La acción va escrita en cada rama, y no en una variable.** Es un poco más largo y es a
        // propósito: el guardián que comprueba que **todo botón tiene quien lo atienda** lee las acciones
        // del código, y una acción puesta por variable no se puede leer —así que un botón que no hiciera
        // nada pasaría desapercibido—. Escrita así, la lista de acciones que hay que atender sale entera
        // de la prueba, y el informe del ticket puede decir una por una qué tiene que hacer cada una.
        modo === "planificar"
          ? html`<${BotonSencillo}
              etiqueta=${guardando ? a.guardando : etiquetaDeGuardar}
              accion="trabajo-previsto-guardar"
              clase="boton-principal"
              deshabilitado=${guardando}
            />`
          : modo === "reprogramar"
            ? html`<${BotonSencillo}
                etiqueta=${guardando ? a.guardando : etiquetaDeGuardar}
                accion="trabajo-reprogramar"
                clase="boton-principal"
                deshabilitado=${guardando}
              />`
            : modo === "hecho"
              ? html`<${BotonSencillo}
                  etiqueta=${guardando ? a.guardando : etiquetaDeGuardar}
                  accion="trabajo-hecho-guardar"
                  clase="boton-principal"
                  deshabilitado=${guardando}
                />`
              : modo === "anular"
                ? html`<${BotonSencillo}
                    etiqueta=${guardando ? a.guardando : etiquetaDeGuardar}
                    accion="trabajo-anular-confirmar"
                    clase="boton-principal"
                    deshabilitado=${guardando}
                  />`
                : html`<${BotonSencillo}
                    etiqueta=${guardando ? a.guardando : etiquetaDeGuardar}
                    accion="trabajo-guardar"
                    clase="boton-principal"
                    deshabilitado=${guardando}
                  />`
      }
      <${BotonSencillo} etiqueta=${a.volver_a_los_trabajos} accion="trabajos-ver" clase="boton-claro" />
    </div>
  `;
}

/**
 * La historia de una tierra: **todo lo que ha pasado, y qué hay hoy** (S03).
 *
 * Propiedades (preparadas por `app.js`):
 *
 *  - `tierra`: `{nombre, superficie}` de la tierra, ya resuelta.
 *  - `historial`: las líneas del servidor por orden, **con las anuladas dentro** (marcadas, con su motivo)
 *    y cada una con sus filas ya montadas.
 *  - `estado`: qué tiene sembrado, qué se ha hecho y qué queda previsto.
 *  - `no_consta`: las frases de lo que no se puede saber, con su explicación (la nascencia de una lluvia,
 *    lo que quedó en el suelo después de la cosecha).
 */
export function PantallaDeLaTierra({
  textos = {},
  tierra = {},
  historial = [],
  estado = null,
  costes = null,
  no_consta = [],
  error = "",
}) {
  const a = textos.agenda || {};
  const cultivo = (estado && estado.cultivo_declarado) || null;
  return html`
    <h1>${frase(a.historia_titulo)}</h1>
    ${tierra.nombre ? html`<p className="pista">${frase(tierra.nombre)}</p>` : null}
    <${AvisoDeError} texto=${error} />

    <h2>${frase(a.que_hay_hoy)}</h2>
    ${
      cultivo
        ? html`
            <div className="aviso">
              <${Fila} etiqueta=${a.lo_que_esta_sembrado} valor=${cultivo.cultivo || a.sin_decir} />
              ${cultivo.variedad ? html`<${Fila} etiqueta=${a.variedad} valor=${cultivo.variedad} />` : null}
              <${Fila} etiqueta=${a.desde_cuando} valor=${cultivo.fecha || a.sin_decir} />
            </div>
          `
        : html`<div className="aviso">${frase(a.sin_cultivo_declarado)}</div>`
    }
    ${
      // El apero después de la siembra: se dice que no borra lo sembrado, porque es lo primero que se
      // pregunta al ver un rodillo justo detrás de una siembra.
      estado && estado.apero_no_cambia
        ? html`<p className="pista-campo">${frase(estado.apero_no_cambia)}</p>`
        : null
    }

    ${
      estado && estado.ultima_labor
        ? html`
            <h2>${frase(a.ultima_labor)}</h2>
            <p>${frase(estado.ultima_labor_titulo)}</p>
            <p className="pista-campo">${frase(estado.ultima_labor_cuando)}</p>
          `
        : null
    }

    <h2>${frase(a.historial_titulo)}</h2>
    <p className="pista-campo">${frase(a.historial_explica)}</p>
    ${
      historial.length === 0
        ? html`<div className="aviso">${frase(a.historial_vacio)}</div>`
        : html`<ul className="lista">
            ${historial.map(
              (linea, indice) => html`
                <li key=${"l" + indice}>
                  <strong>${frase(linea.titulo)}</strong>
                  <p className="pista-campo">${frase(linea.cuando)}</p>
                  ${(linea.filas || []).map(
                    (fila, numero) =>
                      html`<${Fila} key=${"lf" + numero} etiqueta=${fila.etiqueta} valor=${fila.valor} />`,
                  )}
                  ${
                    linea.anulado
                      ? html`
                          <div className="aviso">
                            <p><strong>${frase(linea.no_cuenta)}</strong></p>
                            <p>${frase(linea.motivo_anulacion || "")}</p>
                          </div>
                        `
                      : null
                  }
                  ${linea.revisado ? html`<p className="pista-campo">${frase(a.revisado)}</p>` : null}
                  ${linea.firmado ? html`<p className="pista-campo">${frase(a.firmado)}</p>` : null}
                </li>
              `,
            )}
          </ul>`
    }

    ${
      // Lo que queda previsto, aparte de lo hecho: nunca en la misma lista. **Y cada uno con su botón de
      // «ya lo he hecho»** (07/10/2026): lo previsto se podía leer aquí pero no marcar, así que para
      // apuntar que un trabajo previsto se hizo había que ir a la agenda, buscarlo y marcarlo allí —y la
      // tierra que se estaba mirando se perdía por el camino—. Es el eslabón que le faltaba al recorrido
      // (lo señaló la revisión: E3). El botón es el mismo de la agenda, con la misma acción y su id.
      estado && (estado.previstos || []).length
        ? html`
            <h2>${frase(a.previstos_titulo)}</h2>
            <ul className="lista">
              ${estado.previstos.map(
                (linea, indice) => html`
                  <li key=${"qp" + indice}>
                    <strong>${frase(linea.titulo)}</strong>
                    <p className="pista-campo">${frase(linea.cuando)}</p>
                    ${
                      linea.id
                        ? html`<${Botones}
                            botones=${[
                              {
                                etiqueta: a.ya_lo_he_hecho,
                                accion: "trabajo-hecho",
                                datos: { id: linea.id },
                                clase: "boton-principal",
                                sencillo: true,
                              },
                            ]}
                            barra=${false}
                          />`
                        : null
                    }
                  </li>
                `,
              )}
            </ul>
          `
        : null
    }

    ${
      // **Lo que ha costado esta tierra** (T15 + T13, 05/10/2026): la mitad que le faltaba al recorrido
      // de abrir una tierra —«qué cultivo tiene, qué trabajos se han hecho, qué queda previsto y **qué
      // costes conocidos tiene**»—. Las dos cifras van **separadas** y no sumadas en una: lo que pone el
      // papel (directos) y lo que se repartió (una estimación que acordó el agricultor) son dos cosas de
      // fiabilidad distinta. Y los gastos que **no dicen lo que costaron** se cuentan y se dicen, en vez
      // de sumar un cero que diría que salieron gratis.
      //
      // **Cada línea lleva su enlace al registro**: el botón abre la ficha de ese gasto (`gasto-abrir`,
      // que ya existe), que es donde están sus repartos, sus pagos y su cuadre. Un número del que no se
      // puede llegar a sus apuntes no sirve para comprobarlo.
      costes
        ? html`
            <h2>${frase(a.costes_titulo)}</h2>
            <p className="pista-campo">${frase(a.costes_explica)}</p>
            <div className="aviso">
              <${Fila} etiqueta=${a.costes_directos} valor=${costes.texto_directos || costes.directos} />
              <${Fila} etiqueta=${a.costes_repartidos} valor=${costes.texto_repartidos || costes.repartidos} />
              <${Fila} etiqueta=${a.costes_total} valor=${costes.texto_total || costes.total_conocido} />
            </div>
            ${
              // Un total que calla que le faltan datos miente: se dice cuántos no dicen el importe.
              costes.sin_importe
                ? html`<p className="pista-campo">${frase(rellena(a.costes_sin_importe, { cuantos: String(costes.sin_importe) }))}</p>`
                : null
            }
            ${
              (costes.filas || []).length === 0
                ? html`<div className="aviso">${frase(a.costes_vacio)}</div>`
                : html`<ul className="lista">
                    ${costes.filas.map(
                      (linea, indice) => html`
                        <li key=${"c" + indice}>
                          <strong>${frase(linea.que_es || a.sin_decir)}</strong>
                          <p className="pista-campo">${frase(linea.fecha || a.sin_decir)}</p>
                          <p>${frase(linea.texto_importe || a.sin_decir)}</p>
                          ${
                            // **Y se dice de dónde sale la cifra**: un gasto que dice la tierra y un
                            // trozo repartido no se leen igual.
                            html`<p className="pista-campo">${frase(linea.de_donde === "repartido" ? a.costes_repartido_es : a.costes_directo_es)}</p>`
                          }
                          ${
                            linea.gasto_id
                              ? html`<${Botones}
                                  botones=${[
                                    {
                                      etiqueta: a.ver_el_gasto,
                                      accion: "gasto-abrir",
                                      datos: { id: linea.gasto_id },
                                      clase: "boton-claro",
                                      sencillo: true,
                                    },
                                  ]}
                                  barra=${false}
                                />`
                              : null
                          }
                        </li>
                      `,
                    )}
                  </ul>`
            }
          `
        : null
    }

    <${LoQueNoConsta} textos=${textos} avisos=${no_consta} />

    ${
      estado && (estado.observaciones || []).length
        ? html`
            <h2>${frase(a.observaciones_de_campo)}</h2>
            <ul className="lista">
              ${estado.observaciones.map(
                (observacion, indice) => html`
                  <li key=${"o" + indice}>
                    <p>${frase(observacion.texto || a.sin_decir)}</p>
                    <p className="pista-campo">${frase(observacion.cuando || a.sin_decir)}</p>
                  </li>
                `,
              )}
            </ul>
          `
        : null
    }

    <div className="barra-acciones">
      <${Boton} etiqueta=${a.planificar} accion="trabajo-planificar" clase="boton-principal" />
      ${
        // **Y la vuelta a la lista de tierras** (07/10/2026, E4). El único botón que tenía esta pantalla
        // era «VOLVER A LOS TRABAJOS», y desde la agenda **no hay camino de vuelta a la tierra**: el
        // agricultor que entraba a mirar una tierra y apuntaba algo acababa en la agenda, sin forma de
        // volver a la lista de donde salió (lo midió la revisión del recorrido). Se dice con el nombre de
        // la pantalla a la que lleva —«Mis parcelas, productos y máquinas»—, que es como se llama esa
        // pantalla en el menú: aquí no se inventa ninguna palabra.
        a.mis_tierras
          ? html`<${BotonSencillo} etiqueta=${a.mis_tierras} accion="mis-cosas" clase="" />`
          : null
      }
      <${BotonSencillo} etiqueta=${a.volver_a_los_trabajos} accion="trabajos-ver" clase="" />
    </div>
  `;
}

/** El elemento de React de la agenda. */
export function pantallaDeLosTrabajos(propiedades) {
  return html`
    <${PantallaDeLosTrabajos}
      textos=${propiedades.textos}
      previstos=${propiedades.previstos}
      hechos=${propiedades.hechos}
      resumen=${propiedades.resumen}
      sin_decir=${propiedades.sin_decir}
      aviso=${propiedades.aviso}
      avisos=${propiedades.avisos}
      lo_que_no_se_sabe=${propiedades.lo_que_no_se_sabe}
      error=${propiedades.error}
      cargando=${propiedades.cargando}
      puedePlanificar=${propiedades.puedePlanificar}
    />
  `;
}

/** Y el de un trabajo. */
export function pantallaDeUnTrabajo(propiedades) {
  return html`
    <${PantallaDeUnTrabajo}
      textos=${propiedades.textos}
      modo=${propiedades.modo}
      borrador=${propiedades.borrador}
      tipos=${propiedades.tipos}
      subtipos=${propiedades.subtipos}
      tierras=${propiedades.tierras}
      maquinas=${propiedades.maquinas}
      insumos=${propiedades.insumos}
      unidades=${propiedades.unidades}
      previsto=${propiedades.previsto}
      repaso=${propiedades.repaso}
      guardando=${propiedades.guardando}
      error=${propiedades.error}
    />
  `;
}

/** Y el de la historia de una tierra. */
export function pantallaDeLaTierra(propiedades) {
  return html`
    <${PantallaDeLaTierra}
      textos=${propiedades.textos}
      tierra=${propiedades.tierra}
      historial=${propiedades.historial}
      estado=${propiedades.estado}
      costes=${propiedades.costes}
      no_consta=${propiedades.no_consta}
      error=${propiedades.error}
    />
  `;
}
