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
/**
 * **Un lado del saldo**: su cifra y, debajo, los documentos que la explican.
 *
 * POR QUÉ ASÍ. El encargo pide que *«cada cifra abra los documentos que la explican, con fecha, importe, cobrado
 * o pagado y pendiente»*. Se enseñan debajo y no en otra pantalla porque un total sin sus papeles no se puede
 * comprobar, y aquí se comprueba de un vistazo. Cada documento lleva su enlace **solo si tiene dirección**: para
 * un gasto es `#/cuentas/<id>` y para una compra `#/facturas/<id>`; las entregas y las facturas emitidas van a la
 * lista de ventas, porque **no se inventa una dirección que no existe**.
 */
/**
 * **Lo que el saldo trae, con el hueco por defecto** (13/10/2026).
 *
 * POR QUÉ. La primera versión leía `saldo.sin_asignar.cobros` directamente, y **con un saldo incompleto la ficha
 * entera reventaba**: `TypeError: Cannot read properties of undefined (reading 'cobros')`. Lo encontró la prueba
 * del 409 de las notas —que responde al saldo con una carga que no es la esperada— en cuanto el envoltorio empezó
 * a reenviar el saldo. Es la regla de la casa aplicada a la pantalla: lo que no viene **es un hueco, no un
 * reventón**, y un agregado de dinero no puede impedir ver los datos del contacto. Se lee una vez aquí y ya no hay
 * ningún acceso sin comprobar.
 */
function loQueTraeElSaldo(saldo) {
  return {
    sinAsignar: (saldo && saldo.sin_asignar) || { cobros: [], pagos: [] },
    paraRevisar: (saldo && saldo.para_revisar) || [],
  };
}

function unLadoDelSaldo(titulo, lado, c, verbo) {
  const suyos = (lado && lado.documentos) || [];
  return html`
    <h3>${frase(titulo)}: ${frase(lado && lado.total_texto ? lado.total_texto : c.saldo_nada)}</h3>
    ${
      suyos.length === 0
        ? html`<p className="pista">${frase(c.saldo_sin_documentos)}</p>`
        : html`<ul className="lista lista-del-saldo">
            ${suyos.map((uno) => {
              const suDireccion = uno.clase === "gasto" ? `#/cuentas/${uno.id}` : "#/ventas";
              return html`
                <li key=${uno.clase + uno.id}>
                  <a href=${suDireccion}>
                    ${frase(uno.fecha)} · ${frase(uno.referencia)} · ${frase(uno.importe_texto)}
                  </a>
                  <span className="pista-campo">
                    ${frase(verbo)}: ${frase(uno.cobrado_texto || uno.pagado_texto || "")} ·
                    ${frase(c.saldo_pendiente)}: ${frase(uno.pendiente_texto)}
                  </span>
                </li>
              `;
            })}
          </ul>`
    }
    ${lado && lado.sin_importe ? html`<p className="pista">${frase(c.saldo_sin_importe)}: ${lado.sin_importe}</p>` : null}
  `;
}


export function PantallaDeUnContacto({
  saldo,

  textos = {},
  borrador = {},
  papeles = [],
  vivos = [],
  corrigiendo = false,
  // Lo que se estaba apuntando en el alta rápida, para no perderlo si el servidor dice que no.
  canal_a_medias = null,
  // Lo que se estaba apuntando en el alta de una tarea, para no perderlo si el servidor dice que no.
  tarea_a_medias = null,
  // **Lo que esta cuenta puede hacer** (Entrega 4). Por defecto, **sí**: la pantalla no parpadea, y
  // esconder de más dejaría al agricultor sin botones que sí puede usar. La autorización, en todo
  // caso, la da la puerta.
  puede_modificar = true,
  puede_ver_lo_economico = true,
  borrando = false,
  guardando = false,
  error = "",
}) {
  // **Lo que el saldo trae, leído una vez y con el hueco por defecto**: si viene incompleto, se enseña lo
  // que hay y lo que falta es un hueco, no un reventón (ver `loQueTraeElSaldo`).
  const { sinAsignar, paraRevisar } = loQueTraeElSaldo(saldo);

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

    ${
      // **Las notas, con su autor y su fecha** (CRM-03, criterio (f), 11/10/2026). Solo en una ficha que ya
      // existe: una nota necesita una ficha de la que colgar.
      //
      // **Y no hay botón de corregir ni de borrar, a propósito**: las notas no se corrigen, se apuntan. Si algo
      // cambió, se apunta otra nota diciéndolo —y así queda lo de antes, que es lo que hace que un diario sirva
      // para acordarse de lo que pasó—. El servidor tampoco tiene puerta para tocarlas, y hay una prueba que lo
      // impide.
      corrigiendo
        ? html`
            <h2>${frase(c.notas_titulo)}</h2>
            <p className="pista">${frase(c.notas_pista)}</p>
            ${
              (borrador.notas_con_autor || []).length === 0
                ? html`<p className="aviso">${frase(c.sin_notas)}</p>`
                : html`<ul className="lista lista-de-notas">
                    ${borrador.notas_con_autor.map(
                      (nota) => html`
                        <li key=${String(nota.id)}>
                          <p className="nota-texto">${frase(nota.texto)}</p>
                          <p className="pista-campo">
                            ${
                              // **Los tres estados del autor, y no dos** (13/10/2026, revisión). Antes, cualquier
                              // nota sin nombre decía «Lo apuntó el programa», y eso es afirmar algo que no se
                              // sabe: una nota escrita por una persona cuyo nombre ya no está **no** es una nota
                              // del programa. Se dice lo que se sabe en cada caso.
                              nota.autor_estado === "el_programa"
                                ? frase(c.nota_lo_escribio_el_programa)
                                : nota.autor_estado === "sin_nombre"
                                  ? `${frase(c.nota_la_escribio)}: ${frase(c.nota_autor_sin_nombre)}`
                                  : `${frase(c.nota_la_escribio)}: ${frase(nota.autor)}`
                            }
                            ${nota.creado_en ? html`· ${frase(String(nota.creado_en).slice(0, 10))}` : null}
                          </p>
                        </li>
                      `,
                    )}
                  </ul>`
            }
            <${Campo}
              id="contacto-nota-texto"
              etiqueta=${c.nota_nueva}
              pista=${c.nota_nueva_pista}
              valor=${borrador.nota_a_medias || ""}
            />
            <div className="barra-acciones">
              <button
                type="button"
                className="boton"
                data-accion="contacto-nota"
                data-id=${String(valor("id") || "")}
                disabled=${guardando}
              >
                ${frase(c.apuntar_la_nota)}
              </button>
            </div>
          `
        : null
    }

    ${
      // **El saldo** (Entrega 1, 13/10/2026). Solo en una ficha que ya existe, y **los dos sentidos por
      // separado**: lo que nos debe y lo que le debemos no se restan, porque que a la misma persona se le venda
      // y se le compre es lo normal y juntarlo escondería las dos.
      //
      // El dinero llega **ya escrito** del servidor (`total_texto`, `importe_texto`…), y con la palabra cuando no
      // se sabe («No se sabe cuánto»): **nunca un `0,00 €`** que afirmaría que el papel pone cero. La pantalla no
      // decide cómo se escribe el dinero; eso se decide en un solo sitio.
      corrigiendo && saldo && puede_ver_lo_economico
        ? html`
            <h2>${frase(c.saldo_titulo)}</h2>
            <p className="pista">${frase(c.saldo_explica)}</p>
            ${unLadoDelSaldo(c.saldo_nos_debe, saldo.nos_debe, c, c.saldo_cobrado)}
            ${unLadoDelSaldo(c.saldo_le_debemos, saldo.le_debemos, c, c.saldo_pagado)}
            ${
              (sinAsignar.cobros || []).length || (sinAsignar.pagos || []).length
                ? html`
                    <h3>${frase(c.saldo_sin_asignar)}</h3>
                    <p className="pista">${frase(c.saldo_sin_asignar_pista)}</p>
                    <ul className="lista">
                      ${(sinAsignar.cobros || []).map(
                        (uno) => html`<li key=${"c" + uno.id}>
                          ${frase(uno.fecha)} · ${frase(String(uno.importe))}
                        </li>`,
                      )}
                      ${(sinAsignar.pagos || []).map(
                        (uno) => html`<li key=${"p" + uno.id}>
                          ${frase(uno.fecha)} · ${frase(String(uno.importe))}
                        </li>`,
                      )}
                    </ul>
                  `
                : null
            }
            ${
              paraRevisar.length
                ? html`
                    <h3>${frase(c.saldo_para_revisar)}</h3>
                    <p className="pista">${frase(c.saldo_para_revisar_pista)}</p>
                    <ul className="lista">
                      ${paraRevisar.map(
                        (uno) => html`<li key=${"r" + uno.clase + uno.id}>${frase(uno.referencia)}</li>`,
                      )}
                    </ul>
                  `
                : null
            }
            <p className="pista">
              ${frase(c.saldo_cobertura)}: ${frase(c.saldo_en_euros)}. ${frase(c.saldo_cobertura_pista)}
            </p>
          `
        : null
    }

    ${
      // **Sus canales** (Entrega 2, 13/10/2026): los teléfonos, correos y direcciones, con su etiqueta y su
      // principal. Se enseña **cuál es el principal** y no una lista pelada, porque cuando hay dos teléfonos hay que
      // saber cuál se marca —y eso es justo lo que el agricultor quiere saber de un vistazo—.
      //
      // La clase se dice con su palabra (un teléfono es «Teléfono») y un canal sin etiqueta lo dice: **no se deja un
      // hueco en blanco**, que parecería un descuido de la pantalla en vez de un dato que nadie apuntó.
      corrigiendo && (borrador.canales || []).length
        ? html`
            <h2>${frase(c.canales_titulo)}</h2>
            <p className="pista">${frase(c.canales_pista)}</p>
            <ul className="lista lista-de-canales">
              ${borrador.canales.map(
                (canal) => html`
                  <li key=${String(canal.id)}>
                    <strong>${frase(c[canal.clase] || canal.clase)}</strong>
                    ${canal.etiqueta ? html` · ${frase(canal.etiqueta)}` : html` · ${frase(c.canales_sin_etiqueta)}`}
                    ${
                      // El valor, del campo que le toca a su clase. La dirección lleva su pueblo detrás.
                      canal.clase === "telefono"
                        ? html` · ${frase(canal.telefono)}`
                        : canal.clase === "correo"
                          ? html` · ${frase(canal.correo)}`
                          : html` · ${frase(canal.direccion)}${canal.localidad ? html` (${frase(canal.localidad)})` : null}`
                    }
                    ${canal.principal ? html` · <strong>${frase(c.canales_principal)}</strong>` : null}
                    ${" "}
                    ${
                      // **Qué se puede hacer con él** (Entrega 2): usarlo como principal o quitarlo. El que ya es
                      // principal no lleva el botón de usarlo: un botón que no hace nada es peor que no tenerlo.
                      //
                      // **Y si esta cuenta no puede modificar, no se ofrece ninguno** (Entrega 4). Las dos cosas son
                      // escribir. Y si alguien llega a mano por la URL o por un identificador, **la puerta contesta
                      // 403 igual**: esto es no ofrecer, no autorizar.
                      puede_modificar
                        ? html`
                            ${
                              canal.principal
                                ? null
                                : html`<${BotonSencillo}
                                    etiqueta=${c.canales_hacer_principal}
                                    accion="canal-principal"
                                    datos=${{ id: borrador.id, canal: canal.id }}
                                  />`
                            }
                            <${BotonSencillo}
                              etiqueta=${c.canales_quitar}
                              accion="canal-quitar"
                              datos=${{ id: borrador.id, canal: canal.id }}
                            />
                          `
                        : null
                    }
                  </li>
                `,
              )}
            </ul>
            ${
              // **El alta rápida** (Entrega 2). Tres controles y un botón: qué es, cómo lo llamas tú y el dato. La
              // clase va en una lista porque son tres y no hay más; la etiqueta no, porque la escribe el agricultor
              // con sus palabras («el del almacén») y una lista cerrada le obligaría a mentir.
              puede_modificar
                ? html`
                <div className="alta-rapida-de-canal">
                  <label>
                    ${frase(c.canales_cual)}
                    <select id="canal-clase" defaultValue="telefono">
                      <option value="telefono">${frase(c.telefono)}</option>
                      <option value="correo">${frase(c.correo)}</option>
                      <option value="direccion">${frase(c.direccion)}</option>
                    </select>
                  </label>
                  <label>
                    ${frase(c.canales_el_dato)}
                    <input id="canal-valor" type="text" defaultValue=${(canal_a_medias || {}).valor || ""} />
                  </label>
                  <label>
                    ${frase(c.canales_como_se_llama)}
                    <input id="canal-etiqueta" type="text" defaultValue=${(canal_a_medias || {}).etiqueta || ""} />
                  </label>
                  <${BotonSencillo}
                    etiqueta=${c.canales_apuntar}
                    accion="canal-nuevo"
                    datos=${{ id: borrador.id }}
                  />
                </div>
              `
                : null
            }
          `
        : null
    }

    ${
      // **Lo que hay que hacer con este contacto** (Entrega 3, 13/10/2026). Cada tarea con su día **dicho con
      // palabras** (lo manda el servidor ya escrito, para que la pantalla no tenga que formatear fechas) y **marcada
      // como vencida** cuando se ha pasado: lo vencido se dice, **no se cancela solo**, que es lo que pide el
      // encargo con estas palabras —«la fecha vencida no transforma automáticamente una tarea en cancelada»—.
      //
      // Y una tarea cerrada **no lleva botones**: enseña **quién** la hizo o la canceló, y ya está. Un botón para
      // volver a hacer lo que ya está hecho no es una opción, es una trampa.
      corrigiendo
        ? html`
            <h2>${frase(c.tareas_titulo)}</h2>
            <p className="pista">${frase(c.tareas_pista)}</p>
            ${
              (borrador.tareas || []).length
                ? html`
                    <ul className="lista lista-de-tareas">
                      ${borrador.tareas.map(
                        (tarea) => html`
                          <li key=${String(tarea.id)} className=${tarea.vencida ? "tarea-vencida" : ""}>
                            <strong>${frase(tarea.titulo)}</strong>
                            ${" · "}${frase(tarea.fecha_texto)}
                            ${tarea.vencida ? html` · <strong>${frase(c.tareas_vencida)}</strong>` : null}
                            ${tarea.responsable ? html` · ${frase(tarea.responsable)}` : null}
                            ${
                              tarea.estado === "pendiente"
                                ? html`
                                    ${
                                      // **Cerrar una tarea es escribir** (Entrega 4): si esta cuenta no puede modificar,
                                      // no se ofrecen. Y si alguien llega a mano, la puerta contesta 403 igual.
                                      puede_modificar
                                        ? html`<${BotonSencillo}
                                            etiqueta=${c.tareas_completar}
                                            accion="tarea-completar"
                                            datos=${{ id: borrador.id, tarea: tarea.id }}
                                          />
                                          <${BotonSencillo}
                                            etiqueta=${c.tareas_cancelar}
                                            accion="tarea-cancelar"
                                            datos=${{ id: borrador.id, tarea: tarea.id }}
                                          />`
                                        : null
                                    }
                                  `
                                : html` · ${frase(
                                    tarea.estado === "hecha" ? c.tareas_hecha_por : c.tareas_cancelada_por,
                                  )} ${frase(tarea.completada_por || tarea.cancelada_por || "")}`
                            }
                          </li>
                        `,
                      )}
                    </ul>
                  `
                : html`<p className="pista">${frase(c.tareas_sin_nada)}</p>`
            }
            ${
              // **El alta rápida**: qué hay que hacer, para cuándo y quién. El día es un `date` de verdad (un día, no
              // una hora, como el campo del servidor) y **se puede dejar en blanco**: una tarea sin fecha es una
              // tarea, y obligarla a tener fecha sería inventarla.
              puede_modificar
                ? html`
                <div className="alta-rapida-de-tarea">
                  <label>
                    ${frase(c.tareas_que_hacer)}
                    <input id="tarea-titulo" type="text" defaultValue=${(tarea_a_medias || {}).titulo || ""} />
                  </label>
                  <label>
                    ${frase(c.tareas_cuando)}
                    <input id="tarea-fecha" type="date" defaultValue=${(tarea_a_medias || {}).fecha || ""} />
                  </label>
                  <label>
                    ${frase(c.tareas_quien)}
                    <input id="tarea-responsable" type="text" defaultValue=${(tarea_a_medias || {}).responsable || ""} />
                  </label>
                  <${BotonSencillo}
                    etiqueta=${c.tareas_apuntar}
                    accion="tarea-nueva"
                    datos=${{ id: borrador.id }}
                  />
                </div>
              `
                : null
            }
          `
        : null
    }

    ${
      // **Y los botones que CAMBIAN la ficha, solo si esta cuenta puede cambiarla** (Entrega 4). Todo lo que
      // hay en esta barra escribe: guardar, enlazar, dar de baja o volver a usar, y borrar. Si no se puede
      // modificar, no se ofrecen — y si alguien llega por la URL o por un identificador, **la puerta contesta
      // 403 igual**: esto es no ofrecer, no autorizar.
      puede_modificar
        ? html`
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
          `
        : null
    }
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
/**
 * **El envoltorio de la ficha del contacto, y por qué importa** (13/10/2026).
 *
 * Lo que usa la aplicación es **esta** función, no el componente: `app.js` monta `pantallaDeUnContacto(props)`. Por
 * eso una propiedad que no se reenvíe aquí **no llega nunca a la pantalla**, aunque el componente sepa pintarla y
 * aunque `app.js` la mande.
 *
 * Pasó con el saldo: `app.js` lo mandaba, el componente lo pintaba… y **el bloque no aparecía**, porque faltaba
 * esta línea. Lo encontró la verificación en navegador (13 fallos de 34) y **no** las pruebas, porque montaban el
 * componente directamente. Es el mismo error que tuvo `tabla` antes. De ahí la prueba que monta **por aquí**.
 */
export function pantallaDeUnContacto(propiedades) {
  // ***AQUI VAN LOS COMENTARIOS, FUERA DEL `html`, Y NO DENTRO*** (17/10/2026). *Dentro de una plantilla
  // `html\`…\`` un `//` **no es un comentario de JavaScript: htm la lee como HTML y eso es TEXTO**, asi que
  // se mete **entre los atributos** y **los que van detras dejan de pasar**. Paso aqui mismo: se documento
  // un typo con un comentario dentro, y se cayeron **cuatro props** -`canal_a_medias`, `tarea_a_medias`,
  // `puede_modificar` y `puede_ver_lo_economico`- sin un solo error. **Lo cazo la prueba que mira el
  // envoltorio**, que es justo para lo que esta.*
  //
  // ***Y las dos de los permisos, con su nombre de verdad***: *estaban escritas como*
  // `propiedades.puedo_modificar` *-con «puedo» y no «puede»-, y `app.js` manda `puede_modificar`: llegaba
  // `undefined`, y como el componente tiene `puede_modificar = true` por defecto, **la pantalla ofrecia los
  // botones igual**. `undefined` y `true` se comportan igual, y por eso el typo no lo cazaba nadie. Estaban
  // repetidas dos veces, que es de donde venia.*
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
      saldo=${propiedades.saldo}
      canal_a_medias=${propiedades.canal_a_medias || null}
      tarea_a_medias=${propiedades.tarea_a_medias || null}
      puede_modificar=${propiedades.puede_modificar}
      puede_ver_lo_economico=${propiedades.puede_ver_lo_economico}
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
