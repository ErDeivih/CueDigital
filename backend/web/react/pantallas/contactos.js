/*
 * contactos.js — Las personas y las empresas (T11, 03/10/2026), en React.
 *
 * POR QUÉ ESTAS PANTALLAS
 *
 * En el cuaderno, el nombre de quien te vende, de quien te compra o de quien te asesora está escrito
 * **a mano** en siete sitios: el proveedor de una factura, el de un albarán, el comprador de una venta,
 * el laboratorio de un análisis, el proveedor de un producto del catálogo, y el nombre de un aplicador
 * y de un asesor. Cada vez que llega un papel hay que volver a teclearlo, y dos formas de escribirlo
 * conviven sin que nadie sepa que son la misma persona.
 *
 * Estas pantallas son la respuesta: **una ficha** (la persona o la empresa, con los papeles que hace) y
 * **un enlace** desde el nombre que ya está escrito. Son tres:
 *
 *  · **La lista** (`PantallaDeLosContactos`): todas las fichas, con lo que hace cada una y cuántos
 *    nombres suyos hay escritos.
 *  · **La ficha** (`PantallaDeUnContacto`): sus datos, sus papeles y **dónde está escrito su nombre**.
 *  · **Los nombres escritos** (`PantallaDeLosNombresEscritos`): lo que hay escrito y todavía no tiene
 *    dueño, para enlazarlo sin teclear una letra.
 *
 * LAS TRES COSAS QUE NO SE PUEDEN ROMPER
 *
 *  1. **El nombre que escribió el agricultor no se toca nunca.** No hay ni un campo que lo cambie: lo
 *     que se enseña del papel es lo que dice el papel, y quitarlo de la ficha solo quita el enlace.
 *  2. **El programa no junta a dos que no puede asegurar que son el mismo.** Por eso una propuesta
 *     puede venir con `segura: false`: **se enseña y no lleva botón de apuntar**. Un «ESTE ES» donde no
 *     se puede asegurar sería la forma de fusionar dos hermanos con un toque.
 *  3. **Nada se calcula aquí.** Cuántos nombres hay escritos, cuántos enlaces tiene una ficha y si dos
 *     nombres se parecen lo dice el servidor. La pantalla solo prepara las filas.
 *
 * Los `id` de los campos (`contacto-nombre`, `contacto-nif`…) son los que lee `app.js` y **no se pueden
 * cambiar**: si cambian, el formulario se rellena y se guarda vacío sin que salte nada. Hay pruebas que
 * miran la lista entera de `id`.
 */

import { AvisoDeError, Boton, BotonSencillo, frase, html } from "../componentes.js";
import { Tarjeta } from "../piezas/tarjeta.js";
import { Tabla } from "../piezas/tabla.js";

/** Un campo de escribir con su etiqueta y su pista. Descontrolado: lo lee `app.js` por su `id`. */
function Campo({ id, etiqueta, pista, valor = "", area = false }) {
  return html`
    <div className="campo">
      <label htmlFor=${id}>${frase(etiqueta)}</label>
      ${pista ? html`<p className="pista-campo">${frase(pista)}</p>` : null}
      ${
        area
          ? html`<textarea id=${id} rows="2" defaultValue=${frase(valor)}></textarea>`
          : html`<input id=${id} type="text" defaultValue=${frase(valor)} />`
      }
    </div>
  `;
}

/**
 * Los rótulos del buscador, que son los mismos en las dos pantallas que buscan.
 *
 * `etiquetaBoton` va aparte de `etiqueta` a propósito: la pregunta del campo («Buscar por el nombre») y
 * la palabra del botón («BUSCAR») no son lo mismo, y poner la pregunta entera dentro del botón lo deja
 * largo y repetido. Lo vio una captura de la pantalla a 390 px.
 */
function Buscador({ id, etiqueta, pista, accion, accionLimpiar, etiquetaLimpiar, etiquetaBoton = "", valor = "" }) {
  return html`
    <div className="campo">
      <label htmlFor=${id}>${frase(etiqueta)}</label>
      ${pista ? html`<p className="pista-campo">${frase(pista)}</p>` : null}
      <input id=${id} type="text" defaultValue=${frase(valor)} />
    </div>
    <div className="barra-acciones">
      <${BotonSencillo} etiqueta=${etiquetaLimpiar} accion=${accionLimpiar} clase="" />
      <button type="button" className="boton boton-principal" data-accion=${accion}>
        ${frase(etiquetaBoton)}
      </button>
    </div>
  `;
}

/**
 * La tabla montada **con lo que la pantalla sí recibe**: las tarjetas.
 *
 * POR QUÉ ASÍ (11/10/2026). La primera versión montaba la tabla en `app.js` y se la pasaba como propiedad, y
 * **no llegaba**: medido con dos sondas en el navegador, `app.js` construía las **6 columnas y las 20 filas** y
 * **el componente recibía `tabla: null`**, porque esta pantalla se repinta con los datos de la caché del campo
 * y las propiedades montadas allí no viajan. Montarla aquí con las tarjetas lo resuelve de raíz: **no depende
 * de por dónde venga el repintado**.
 *
 * Y los datos están: cada tarjeta trae el nombre (`etiqueta`), los papeles en palabras (`rotulo`) y sus
 * **pares etiqueta/valor** (`filas`), con las etiquetas que sirve el servidor. El valor se busca **por la
 * etiqueta**, para que las columnas queden alineadas aunque a un contacto le falte un dato.
 */
function tablaDeLasTarjetas(tarjetas, c) {
  const sinDato = c.tabla_sin_dato || "—";
  const elValorDe = (tarjeta, etiqueta) => {
    const fila = (tarjeta.filas || []).find((suya) => suya.etiqueta === etiqueta);
    return fila && fila.valor ? fila.valor : sinDato;
  };
  return {
    columnas: [
      { texto: c.tabla_nombre, campo: "nombre", clase: "" },
      { texto: c.tabla_que_es, clase: "" },
      { texto: c.nif, clase: "" },
      { texto: c.telefono, clase: "tabla-numero" },
      { texto: c.correo, clase: "" },
      { texto: c.tabla_acciones, clase: "tabla-acciones" },
    ],
    filas: tarjetas.map((tarjeta) => ({
      celdas: [
        { texto: tarjeta.etiqueta, accion: "contacto-abrir", datos: { id: tarjeta.id } },
        { texto: tarjeta.rotulo || sinDato },
        { texto: elValorDe(tarjeta, c.nif) },
        { texto: elValorDe(tarjeta, c.telefono), clase: "tabla-numero" },
        { texto: elValorDe(tarjeta, c.correo) },
      ],
      acciones: [{ accion: "contacto-abrir", texto: c.tabla_abrir, datos: { id: tarjeta.id } }],
    })),
  };
}

/**
 * La lista de las personas y las empresas de la finca.
 *
 * Propiedades:
 *
 *  - `textos`: `{ contactos }` del servidor.
 *  - `tarjetas`: las fichas ya preparadas por `app.js` (nombre, papeles, cuántos nombres escritos).
 *  - `resumen`: cuántas hay, ya en singular o en plural.
 *  - `buscado`: lo que hay escrito en el buscador, para no perderlo al repintar.
 */
export function PantallaDeLosContactos({
  textos = {},
  tarjetas = [],
  tabla = null,
  resumen = "",
  buscado = "",
  aviso = "",
  error = "",
  cargando = false,
}) {
  const c = textos.contactos || {};
  // **La tabla: la de las tarjetas** (11/10/2026). Se monta aquí, con lo que la pantalla **sí recibe**, porque
  // la que se montaba en `app.js` y viajaba como propiedad **no llegaba**: medido con dos sondas, `app.js`
  // construía las 6 columnas y las 20 filas y el componente recibía `tabla: null` —esta pantalla se repinta con
  // los datos de la caché del campo y las propiedades montadas allí no viajan—. Si algún día llega montada y
  // con filas, se usa esa; mientras, la de aquí.
  const laTabla =
    tabla && tabla.filas && tabla.filas.length
      ? tabla
      : tarjetas.length
        ? tablaDeLasTarjetas(tarjetas, c)
        : null;
  return html`
    <h1>${frase(c.titulo)}</h1>
    <p className="pista">${frase(c.explica)}</p>
    <${AvisoDeError} texto=${error} />
    ${aviso ? html`<div className="aviso"><strong>${frase(aviso)}</strong></div>` : null}

    <${Buscador}
      id="contacto-buscar"
      etiqueta=${c.buscar}
      pista=${c.buscar_pista}
      accion="contactos-buscar"
      accionLimpiar="contactos-buscar-limpiar"
      etiquetaLimpiar=${c.buscar_limpiar}
      etiquetaBoton=${c.buscar_boton}
      valor=${buscado}
    />

    ${cargando ? html`<p className="pista">${frase(c.buscando)}</p>` : null}

    ${
      tarjetas.length === 0
        ? html`<p className="aviso">${frase(c.vacia)}</p>`
        : html`<p className="pista">${frase(resumen)}</p>`
    }

    ${
      // **La tabla, en el ordenador** (11/10/2026). Es la pantalla central del CRM y se pintaba como una lista
      // de un renglón por nombre: medido, **20 tarjetas de 92 px**, donde un CRM enseña filas de 45. Va dentro
      // de `.solo-escritorio`, que es lo que la enseña en el ordenador y la esconde en el móvil —el mismo
      // HTML para las dos formas y el CSS decidiendo, que es la regla del proyecto—.
      //
      // **Y las tarjetas NO se envuelven todavía**: en el intento anterior se envolvieron en `.solo-movil` a
      // la vez que se ponía la tabla, y como la tabla no llegó a pintarse, el ordenador se quedó **sin nada**.
      // Aquí va por pasos a propósito: primero la tabla, comprobada; después se callan las tarjetas, con sus
      // pruebas delante. Un cambio de aspecto no puede poder vaciar una pantalla.
      laTabla
        ? html`<div className="solo-escritorio tabla-scroll" data-tabla="contactos"><${Tabla} tabla=${laTabla} /></div>`
        : null
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
          accion="contacto-abrir"
          datos=${{ id: tarjeta.id }}
          textos=${{ elegida: "" }}
        />
      `,
    )}

    <h2>${frase(c.que_se_puede_hacer)}</h2>
    <div className="barra-acciones">
      <${Boton}
        etiqueta=${c.anadir}
        pista=${c.anadir_pista}
        accion="contacto-nuevo"
        clase="boton-principal"
      />
      <${Boton}
        etiqueta=${c.traer_los_nombres}
        pista=${c.traer_los_nombres_pista}
        accion="contactos-revisar-abrir"
        clase=""
      />
      <${BotonSencillo} etiqueta=${c.volver_al_inicio} accion="ir-inicio" clase="" />
    </div>
  `;
}

/**
 * Los botones de los papeles: **se marcan y se desmarcan de uno en uno**.
 *
 * Es un botón por papel y **no se elige uno solo**: los papeles se solapan. Se marca como en las
 * medidas preventivas —el visto del cuadro, su color y su `data-elegido`—, porque **el color solo no
 * informa** (regla de la casa) y así una prueba puede leer cuál está marcado sin mirar el color.
 */
function LosPapeles({ rotulo, pista, papeles = [], marcados = [] }) {
  return html`
    <div className="campo">
      <span className="t06-rotulo">${frase(rotulo)}</span>
      ${pista ? html`<p className="pista-campo">${frase(pista)}</p>` : null}
      <div className="barra-acciones">
        ${papeles.map((papel) => {
          const puesto = marcados.includes(papel.valor);
          return html`
            <${Boton}
              key=${papel.valor}
              etiqueta=${papel.texto}
              icono=${puesto ? "✅" : "⬜"}
              accion="contacto-papel"
              datos=${{ papel: papel.valor, puesto: puesto ? "0" : "1", elegido: puesto ? "1" : "0" }}
              clase=${puesto ? "boton-elegido" : "boton-claro"}
              flecha=${false}
            />
          `;
        })}
      </div>
    </div>
  `;
}

/**
 * La ficha de una persona o de una empresa: sus datos, sus papeles y dónde está escrito su nombre.
 *
 * Propiedades:
 *
 *  - `borrador`: lo que hay que enseñar en los campos. Al dar de alta va casi vacío; al corregir, lo
 *    que ya estaba guardado.
 *  - `papeles`: el catálogo del servidor (`{valor, texto}`), **en su orden**: un cuestionario cuyas
 *    preguntas cambian de sitio se contesta mal.
 *  - `vivos`: los enlaces, uno por uno, con **el texto que dice el papel** y si ha cambiado desde que
 *    se enlazó. Un enlace no se rompe porque el agricultor corrija el papel, pero se dice.
 *  - `corrigiendo`: abre la ficha de una que ya existe (cambia el título y salen BORRAR y ENLAZAR).
 *  - `borrando`: se ha pedido borrar y hay que confirmarlo. **Borrar no se hace de un toque**: lo que
 *    desaparece es la ficha, y el agricultor tiene que poder echarse atrás.
 */
export function PantallaDeUnContacto({
  textos = {},
  borrador = {},
  papeles = [],
  vivos = [],
  corrigiendo = false,
  borrando = false,
  guardando = false,
  error = "",
}) {
  const c = textos.contactos || {};
  const valor = (clave) => (borrador[clave] == null ? "" : borrador[clave]);
  const marcados = borrador.papeles || [];
  return html`
    <h1>${frase(corrigiendo ? c.ficha_titulo_corregir : c.ficha_titulo)}</h1>
    <p className="pista">${frase(c.ficha_explica)}</p>
    <${AvisoDeError} texto=${error} />

    ${
      borrando
        ? html`
            <div className="aviso aviso-error">
              <strong>${frase(c.borrar_confirmar)}</strong>
              <p>${frase(c.borrar_pista)}</p>
              <div className="barra-acciones">
                <button
                  type="button"
                  className="boton"
                  data-accion="contacto-borrar-si"
                  data-id=${String(borrador.id || "")}
                  disabled=${guardando}
                >
                  ${frase(c.borrar_si)}
                </button>
                <${BotonSencillo} etiqueta=${c.borrar_no} accion="contacto-borrar-no" clase="" />
              </div>
            </div>
          `
        : null
    }

    <${Campo} id="contacto-nombre" etiqueta=${c.nombre} pista=${c.nombre_pista} valor=${valor("nombre")} />
    <${Campo} id="contacto-nif" etiqueta=${c.nif} pista=${c.nif_pista} valor=${valor("nif")} />
    <${Campo} id="contacto-telefono" etiqueta=${c.telefono} valor=${valor("telefono")} />
    <${Campo} id="contacto-correo" etiqueta=${c.correo} valor=${valor("correo")} />
    <${Campo} id="contacto-direccion" etiqueta=${c.direccion} valor=${valor("direccion")} />
    <${Campo} id="contacto-localidad" etiqueta=${c.localidad} valor=${valor("localidad")} />
    <${Campo}
      id="contacto-notas"
      etiqueta=${c.notas}
      pista=${c.notas_pista}
      valor=${valor("notas")}
      area=${true}
    />

    <div className="campo">
      <label htmlFor="contacto-es-empresa">${frase(c.es_persona_o_empresa)}</label>
      <select id="contacto-es-empresa" defaultValue=${frase(valor("es_empresa_texto"))}>
        <option value="no_se">${frase(c.es_empresa_no_se)}</option>
        <option value="si">${frase(c.es_empresa_si)}</option>
        <option value="no">${frase(c.es_empresa_no)}</option>
      </select>
    </div>

    <${LosPapeles}
      rotulo=${c.los_papeles}
      pista=${c.los_papeles_pista}
      papeles=${papeles}
      marcados=${marcados}
    />
    ${
      // **Las frases compuestas se montan en `app.js`**, no aquí (`docs/REACT.md`): lo que llega es la
      // frase entera, ya unida con los textos del servidor.
      valor("papeles_segun_lo_escrito_texto")
        ? html`<p className="pista-campo">${frase(valor("papeles_segun_lo_escrito_texto"))}</p>`
        : null
    }
    ${
      // **Una ficha que apuntó el programa desde los papeles se dice**, porque si se corrige se queda
      // como suya y ya no se deshace con las demás. Callarlo sería sorprender al agricultor después.
      valor("origen") === "migracion"
        ? html`<p className="pista-campo">${frase(c.de_la_migracion)}</p>`
        : null
    }

    <h2>${frase(c.donde_aparece)}</h2>
    <p className="pista">${frase(c.donde_aparece_explica)}</p>
    ${
      vivos.length === 0
        ? html`<p className="aviso">${frase(c.sin_enlaces)}</p>`
        : html`
            <ul className="lista">
              ${vivos.map(
                (vivo) => html`
                  <li key=${String(vivo.id)}>
                    <strong>${frase(vivo.escrito.texto)}</strong>
                    <p className="pista-campo">${frase(vivo.rotulo)}</p>
                    ${vivo.aviso ? html`<p className="aviso">${frase(vivo.aviso)}</p>` : null}
                    <button
                      type="button"
                      className="boton boton-claro"
                      data-accion="contacto-desenlazar"
                      data-id=${String(vivo.id)}
                    >
                      ${frase(c.quitar_enlace)}
                    </button>
                  </li>
                `,
              )}
            </ul>
          `
    }

    <div className="barra-acciones">
      <button
        type="button"
        className="boton boton-principal"
        data-accion="contacto-guardar"
        disabled=${guardando}
      >
        ${frase(guardando ? c.guardando : c.guardar)}
      </button>
      ${
        corrigiendo
          ? html`
              <${Boton}
                etiqueta=${c.enlazar}
                accion="contacto-enlazar-abrir"
                datos=${{ id: valor("id") }}
                clase="boton-claro"
              />
              ${
                // **Dejar de usarlo / volver a usarlo** (CRM-03, criterio (e), 11/10/2026). El botón dice el
                // estado en el que se está y lo que va a pasar: con la ficha activa pone «DEJAR DE USARLO» y con
                // la ficha de baja, «VOLVER A USARLO».
                //
                // **No lleva confirmación, y no es un olvido**: no se borra nada y se deshace con el mismo
                // botón, así que preguntar sería estorbar. La confirmación se guarda para BORRAR, que sí se
                // lleva cosas por delante.
                html`<${Boton}
                  etiqueta=${valor("activo") === false ? c.volver_a_usarlo : c.dejarlo_de_usar}
                  accion=${valor("activo") === false ? "contacto-alta" : "contacto-baja"}
                  datos=${{ id: valor("id") }}
                  clase="boton-claro"
                />`
              }
              <button type="button" className="boton boton-claro" data-accion="contacto-borrar">
                ${frase(c.borrar)}
              </button>
            `
          : null
      }
      <${Boton} etiqueta=${c.volver_a_los_contactos} accion="contactos-ver" clase="boton-claro" />
    </div>
  `;
}

/**
 * Los nombres que ya están escritos y todavía no son de nadie.
 *
 * **Lo que se lee es el texto del papel, no el de una ficha**: puede estar escrito de cualquier manera
 * («COOP. AGRICOLA DE PEÑARANDA»), y ese es justo el dato que hay que reconocer. Al tocar uno, queda
 * enlazado con la ficha y **no se cambia ni una letra** del papel.
 */
export function PantallaDeLosNombresEscritos({
  textos = {},
  escritos = [],
  resumen = "",
  buscado = "",
  hayContacto = false,
  aviso = "",
  error = "",
  cargando = false,
}) {
  const c = textos.contactos || {};
  return html`
    <h1>${frase(c.escritos_titulo)}</h1>
    <p className="pista">${frase(c.escritos_explica)}</p>
    <${AvisoDeError} texto=${error} />
    ${aviso ? html`<div className="aviso"><strong>${frase(aviso)}</strong></div>` : null}

    <${Buscador}
      id="escrito-buscar"
      etiqueta=${c.escritos_buscar}
      pista=${c.escritos_buscar_pista}
      accion="contacto-escritos-buscar"
      accionLimpiar="contacto-escritos-buscar-limpiar"
      etiquetaLimpiar=${c.escritos_ver_todos}
      etiquetaBoton=${c.escritos_buscar_boton}
      valor=${buscado}
    />

    ${cargando ? html`<p className="pista">${frase(c.buscando)}</p>` : null}
    ${
      escritos.length === 0
        ? html`<p className="aviso">${frase(c.escritos_vacio)}</p>`
        : html`<p className="pista">${frase(resumen)}</p>`
    }

    ${
      // **Sin ninguna ficha apuntada no hay dónde enlazar**, y un aviso sin la salida deja al agricultor
      // parado: se dice y se le da el botón que lo arregla (regla 8 de la guía).
      !hayContacto
        ? html`
            <div className="aviso">
              <p>${frase(c.vacia)}</p>
              <${BotonSencillo} etiqueta=${c.anadir} accion="contacto-nuevo" clase="" />
            </div>
          `
        : null
    }

    ${escritos.map(
      (escrito) => html`
        <${Tarjeta}
          key=${escrito.claveTarjeta}
          etiqueta=${escrito.texto}
          rotulo=${escrito.rotulo}
          lineas=${escrito.lineas}
          filas=${escrito.filas}
          avisos=${escrito.avisos}
          marca=${false}
          accion=${hayContacto ? "contacto-enlazar" : ""}
          datos=${hayContacto
            ? { tabla: escrito.tabla, campo: escrito.campo, registro: escrito.registro_id }
            : {}}
          textos=${{ elegida: "" }}
        />
      `,
    )}

    <div className="barra-acciones">
      <${Boton} etiqueta=${c.volver_a_los_contactos} accion="contactos-ver" clase="boton-claro" />
    </div>
  `;
}

/** El elemento de React de la lista, ya con sus propiedades puestas. */
export function pantallaDeLosContactos(propiedades) {
  return html`
    <${PantallaDeLosContactos}
      textos=${propiedades.textos}
      tarjetas=${propiedades.tarjetas}
      resumen=${propiedades.resumen}
      buscado=${propiedades.buscado}
      aviso=${propiedades.aviso}
      error=${propiedades.error}
      cargando=${propiedades.cargando}
    />
  `;
}

/** Y el de la ficha. */
export function pantallaDeUnContacto(propiedades) {
  return html`
    <${PantallaDeUnContacto}
      textos=${propiedades.textos}
      borrador=${propiedades.borrador}
      papeles=${propiedades.papeles}
      vivos=${propiedades.vivos}
      corrigiendo=${propiedades.corrigiendo}
      borrando=${propiedades.borrando}
      guardando=${propiedades.guardando}
      error=${propiedades.error}
    />
  `;
}

/** Y el de los nombres escritos. */
export function pantallaDeLosNombresEscritos(propiedades) {
  return html`
    <${PantallaDeLosNombresEscritos}
      textos=${propiedades.textos}
      escritos=${propiedades.escritos}
      resumen=${propiedades.resumen}
      buscado=${propiedades.buscado}
      hayContacto=${propiedades.hayContacto}
      aviso=${propiedades.aviso}
      error=${propiedades.error}
      cargando=${propiedades.cargando}
    />
  `;
}
