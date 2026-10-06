/*
 * bandeja.js — La bandeja de los papeles (T08, S10, 06/10/2026).
 *
 * QUÉ ES ESTA PANTALLA, Y QUÉ ES LO QUE NO HACE NUNCA
 *
 * El recorrido entero, en el orden en que se hace: **subir un papel** (una foto o un PDF) diciendo de qué
 * es → **comprobar que ese mismo papel no estaba ya** (y decirlo antes de apuntarlo) → **mirar el original
 * con la propuesta al lado** → **decir qué queda de él** → **confirmarlo**, con quién y cuándo → y
 * **decir con qué va** (una compra, un gasto, una venta, una máquina, un trabajo o una inspección) y a qué
 * papel corrige, si es una rectificativa. Son **dos pantallas en un fichero**, como en la maquinaria, los
 * trabajos y el banco: la lista (`#/papeles/bandeja`) y la ficha de un papel
 * (`#/papeles/bandeja/<id>`). Las dos se reconstruyen enteras al abrir su dirección —piden sus datos al
 * servidor— y **los formularios no tienen dirección**: uno que al recargar saliera vacío es peor que no
 * tenerla.
 *
 * Y las cinco cosas que esta pantalla NO hace, cada una con su motivo:
 *
 *  1. **No dice que la lectura sea buena.** Ni «leído correctamente», ni un porcentaje, ni una confianza.
 *     El corpus para medirlo (T07) no existe, así que la pantalla **dice que no se puede medir** y enseña
 *     lo único que sí es un hecho: si la cuenta de cada línea cuadra (cantidad × precio = importe). Hay
 *     una prueba que lo muerde: se pinta una propuesta entera y no puede salir ni un `%` ni la palabra
 *     «confianza».
 *  2. **No deja confirmar lo que nadie ha mirado.** El botón de confirmar **solo se pinta cuando el
 *     servidor dice que se puede** (`se_puede_confirmar`), y el servidor no lo dice hasta que hay algo
 *     aceptado. La pantalla no decide eso por su cuenta: lo obedece.
 *  3. **No toca el original.** El fichero no se puede reescribir desde aquí: no hay ningún campo para su
 *     nombre, su ruta ni su huella, y **lo único que se puede hacer es verlo**. La huella se enseña para
 *     que se vea que está y que no cambia (una prueba comprueba que no hay dónde editarla).
 *  4. **No crea nada al enlazar.** Conciliar un pago no crea un segundo gasto, y esto es lo mismo: enlazar
 *     escribe un vínculo con algo que ya existe. Por eso esta pantalla **no ofrece** «crear un gasto» ni
 *     «crear una factura»: eso se hace en su pantalla, con sus campos y sus comprobaciones.
 *  5. **No suma ni formatea dinero.** Todos los importes llegan del servidor en texto decimal **y ya
 *     escritos** para leerlos («980,10 €»), y un importe que no consta llega **vacío**: la pantalla enseña
 *     su palabra («No consta»), nunca un `0,00 €` que diría que el papel pone cero euros.
 *
 * LOS `data-accion` VAN ESCRITOS EN CADA RAMA, Y NO EN UNA VARIABLE
 *
 * El manejador de clics es **uno solo** y vive en `app.js`. Hay un guardián
 * (`tests/test_los_botones_hacen_algo.py`) que lee las acciones del código y exige que todas tengan quien
 * las atienda; una acción puesta por variable **no se puede leer**, así que un botón que no hiciera nada
 * pasaría desapercibido. Por eso aquí todas van escritas literales en su rama, y la lista está una por una
 * en el informe del ticket (`docs/T08_BANDEJA.md`), con lo que tiene que hacer cada una.
 *
 * Y ojo con el guardián al escribir este fichero: **no quita los comentarios** antes de mirar, así que
 * escribir aquí la forma prohibida (con su dólar y su llave) hace que cuente este fichero como uno de los
 * que pintan acciones por variable. Se dice porque le pasó al del banco.
 *
 * Y LO MISMO CON LAS FRASES: NINGUNA ESCRITA AQUÍ
 *
 * Todo lo que se lee viene del servidor: de cada papel se enseña **lo que dice el servidor** (su título,
 * su estado ya en palabras, su tipo, el nombre de lo que tiene enlazado) y los rótulos son claves de
 * `textos.BANDEJA`, que llegan por la propiedad `textos`. Las claves compuestas (`estado_<estado>` y
 * `clase_<clase>`) **las resuelve el servidor** y llegan ya escritas (`etiqueta_estado`, `etiqueta_clase`),
 * que es la regla de este programa: el vocabulario vive en el servidor y la pantalla no traduce.
 *
 * El componente es PURO: no llama a `fetch`, no lee `localStorage` y no toca el DOM.
 */

import { AvisoDeError, Boton, Botones, BotonSencillo, frase, html } from "../componentes.js";
import { Campo } from "../piezas/campo.js";

// ==========================================================================
// Las piezas pequeñas de esta pantalla
// ==========================================================================

/**
 * Un renglón de «nombre y valor».
 *
 * Va en su propia pieza porque aquí se repite en casi todos los bloques (el papel, su fichero, la
 * propuesta, lo aceptado, lo enlazado). `aviso` es lo que hay que decir **además** del dato («esto no
 * cuenta», «lo escribiste tú»).
 */
function Datos({ filas = [] }) {
  const conDatos = (filas || []).filter(Boolean);
  if (!conDatos.length) return null;
  return html`
    <dl>
      ${conDatos.map(
        (fila, indice) => html`
          <div className="resumen-dato" key=${indice}>
            <dt>${frase(fila.etiqueta)}</dt>
            <dd>
              ${frase(fila.valor)}
              ${fila.aviso ? html`<span className="pista-campo"> ${frase(fila.aviso)}</span>` : null}
            </dd>
          </div>
        `,
      )}
    </dl>
  `;
}

/**
 * Las opciones de un desplegable, con la forma que quiere esta pieza.
 *
 * El servidor manda las listas de vocabulario como `[{valor, etiqueta}]` (`tipos`, `estados`, `clases` de
 * `GET /api/bandeja`) y las que prepara `app.js` van como `[{valor, texto}]`. En vez de obligar a las dos
 * mitades a escribirlo igual —que es como se acaba teniendo dos formas que se separan—, aquí se acepta
 * cualquiera de las dos y se elige el rótulo que venga. Sin esto, un desplegable salía **con las opciones
 * en blanco**: el `etiqueta` del servidor no lo leía nadie y el `texto` no existía.
 */
function lasOpciones(opciones = []) {
  return (opciones || []).map((opcion) => ({
    valor: opcion.valor,
    texto: opcion.texto || opcion.etiqueta || "",
    pista: opcion.pista,
  }));
}

/**
 * Un desplegable con su etiqueta.
 *
 * `opciones` es `[{valor, texto}]` (o `[{valor, etiqueta}]`, que es como lo manda el servidor) y **lo
 * prepara el servidor**: la pantalla no tiene ninguna lista de palabras propia. `vacio` es la opción «no lo
 * sé» / «elige uno», y si no se pasa, no se pinta.
 */
function Elegir({ id, etiqueta, pista, opciones = [], elegido = "", vacio = "" }) {
  return html`
    <div className="campo">
      <label htmlFor=${id}>${frase(etiqueta)}</label>
      ${pista ? html`<p className="pista-campo">${frase(pista)}</p>` : null}
      <select id=${id} defaultValue=${frase(elegido)}>
        ${vacio ? html`<option value="">${frase(vacio)}</option>` : null}
        ${lasOpciones(opciones).map(
          (opcion) => html`
            <option value=${String(opcion.valor)} key=${String(opcion.valor)}>${frase(opcion.texto)}</option>
          `,
        )}
      </select>
    </div>
  `;
}

/**
 * Un formulario, tal y como lo prepara `app.js`: un título, sus campos y sus dos botones.
 *
 * Es **la misma forma** que la del banco y la de las cuentas, y a propósito: un bloque es de escribir
 * (`{tipo, id, etiqueta, valor, pista}`) y un bloque con un `tipo` que no se conoce se pinta como texto.
 * Entre un campo de más —que el agricultor puede rellenar y se guarda en su sitio— y un campo que
 * desaparece sin decir nada, el de más.
 *
 * `datos.clase` dice **qué** se está guardando (la revisión de un papel, el tipo de un papel): el manejador
 * de clics lee ese dato y manda el formulario a su puerta. Sin él, «GUARDAR» sería un botón que no se sabe
 * qué guarda.
 */
function Formulario({ formulario, guardando = false }) {
  if (!formulario) return null;
  return html`
    <h2>${frase(formulario.titulo)}</h2>
    ${formulario.pista ? html`<p className="pista">${frase(formulario.pista)}</p>` : null}
    ${(formulario.bloques || []).map((bloque, indice) =>
      html`
        <${Campo}
          key=${indice}
          id=${bloque.id}
          etiqueta=${bloque.etiqueta}
          tipo=${bloque.tipo}
          valor=${bloque.valor}
          sufijo=${bloque.pista}
          unidad=${bloque.unidad}
          placeholder=${bloque.placeholder}
          filas=${bloque.filas}
        />
      `,
    )}
    ${formulario.error ? html`<${AvisoDeError} texto=${formulario.error} />` : null}
    <div className="barra-acciones">
      <${Boton} etiqueta=${formulario.guardar} accion="bandeja-guardar" datos=${formulario.datos} clase="" />
      <${BotonSencillo} etiqueta=${formulario.cancelar} accion="bandeja-cancelar" />
    </div>
    ${guardando ? html`<p className="pista-campo">${frase(formulario.guardando)}</p>` : null}
  `;
}

/**
 * Un dato de una cabecera (lo leído o lo aceptado): **lo que dice el dato**, y no lo que dice su texto.
 *
 * POR QUÉ NO SE ENSEÑA EL TEXTO SIN MIRAR EL DATO. El servidor manda las dos cosas: el campo con su valor
 * (`campos.total`, en texto decimal) y su versión escrita (`textos.total`, «980,10 €»). Enseñar el texto
 * sin mirar el dato es lo que hace que un papel del que **no consta el importe** acabe enseñando un
 * `0,00 €`: diría que el papel pone cero euros, que es lo contrario de lo que dice. Aquí manda el dato, y
 * cuando no consta se dice con la palabra del servidor. Hay una prueba que lo muerde: se le pasa un
 * `textos.total` de `0,00 €` **con el dato a nulo**, y la pantalla no puede enseñar el cero.
 */
function unDato({ escritos = {}, campos = {}, campo, noConsta = "" }) {
  const valor = (campos || {})[campo];
  if (valor === null || valor === undefined || valor === "") return frase(noConsta);
  return frase(escritos[campo]) || frase(noConsta);
}

// ==========================================================================
// Subir un papel: el original entra tal y como llega
// ==========================================================================

/**
 * La subida: elegir el fichero, decir de qué es, **comprobar** y subir.
 *
 * Y una decisión que se ve en los botones: **subir solo se ofrece después de comprobar y solo si el papel
 * no estaba ya**. Es la regla del ticket («si el mismo fichero ya está, se dice antes de apuntarlo y no se
 * crea otra ficha») llevada a la pantalla: no es un aviso que se pueda saltar, es un botón que no está.
 *
 * El campo del fichero lleva su `id` (`bandeja-fichero`) y **no es controlado a propósito**: `app.js` lee de
 * ahí el fichero que el agricultor ha elegido y lo **guarda en su estado**, porque repintar la pantalla
 * borra la casilla y hay que volver a mandar el mismo fichero al subirlo. Eso ya pasó una vez en este
 * programa, con el cuaderno de la Junta, y está contado en `AGENTS.md`.
 */
function LaSubida({
  textos = {},
  tipos = [],
  ficheroElegido = "",
  tipoElegido = "",
  comprobado = null,
  comprobando = false,
  subiendo = false,
}) {
  const b = textos.bandeja || {};
  const yaEstaba = Boolean(comprobado && comprobado.ya_estaba);
  return html`
    <h2>${frase(b.subir_titulo)}</h2>
    <p className="pista">${frase(b.subir_explica)}</p>
    <p className="pista-campo">${frase(b.nada_se_apunta)}</p>

    <div className="campo">
      <label htmlFor="bandeja-fichero">${frase(b.fichero)}</label>
      <p className="pista-campo">${frase(b.fichero_pista)}</p>
      <input
        id="bandeja-fichero"
        type="file"
        accept=".pdf,.jpg,.jpeg,.png,.webp,.heic,.heif,.doc,.docx,.odt,.xls,.xlsx,.ods,.ppt,.pptx,.txt,.csv,.zip"
      />
      ${
        ficheroElegido
          ? html`<p className="pista-campo">
              <span>${frase(b.fichero_elegido)}</span>
              <strong>${frase(ficheroElegido)}</strong>
            </p>`
          : null
      }
    </div>

    <${Elegir}
      id="bandeja-tipo-nuevo"
      etiqueta=${b.de_que_es}
      pista=${b.de_que_es_pista}
      opciones=${tipos}
      elegido=${tipoElegido}
      vacio=${b.no_lo_se_todavia}
    />

    <div className="barra-acciones">
      <${Boton}
        etiqueta=${comprobando ? b.comprobando : b.comprobar_el_fichero}
        accion="bandeja-comprobar"
        clase="boton-claro"
      />
    </div>

    ${
      comprobado
        ? html`
            <h3>${frase(b.lo_que_se_ha_comprobado)}</h3>
            <${Datos}
              filas=${[
                { etiqueta: b.el_fichero, valor: comprobado.nombre_del_fichero || b.no_consta },
                { etiqueta: b.tamano, valor: comprobado.texto_tamano || b.no_consta },
                { etiqueta: b.la_huella, valor: comprobado.huella || b.no_consta, aviso: b.la_huella_pista },
              ]}
            />
            ${
              yaEstaba
                ? html`
                    <div className="aviso">
                      <p><strong>${frase(b.ya_estaba)}</strong></p>
                      <p>${frase(b.ya_estaba_explica)}</p>
                      <${Datos}
                        filas=${[
                          {
                            etiqueta: b.lo_que_es,
                            valor:
                              (comprobado.el_que_ya_estaba && comprobado.el_que_ya_estaba.id
                                ? comprobado.el_que_ya_estaba.titulo
                                : "") || b.no_consta,
                          },
                          {
                            etiqueta: b.del_que_ya_estaba_subido,
                            valor:
                              (comprobado.el_que_ya_estaba &&
                                comprobado.el_que_ya_estaba.texto_subido) ||
                              b.no_consta,
                          },
                        ]}
                      />
                      <p>${frase(comprobado.que_hacer)}</p>
                      <div className="barra-acciones">
                        <${Boton}
                          etiqueta=${b.abrir_el_que_ya_estaba}
                          accion="bandeja-abrir"
                          datos=${{ id: comprobado.el_que_ya_estaba && comprobado.el_que_ya_estaba.id }}
                          clase="boton-claro"
                        />
                        <${BotonSencillo} etiqueta=${b.olvidar_el_fichero} accion="bandeja-olvidar-fichero" />
                      </div>
                    </div>
                  `
                : html`
                    <p className="aviso">${frase(b.no_estaba)}</p>
                    <div className="barra-acciones">
                      <${Boton}
                        etiqueta=${subiendo ? b.subiendo : b.subir_el_papel}
                        accion="bandeja-subir"
                        clase=""
                      />
                      <${BotonSencillo} etiqueta=${b.olvidar_el_fichero} accion="bandeja-olvidar-fichero" />
                    </div>
                  `
            }
          `
        : null
    }
  `;
}

// ==========================================================================
// La lista: lo que hay que revisar
// ==========================================================================

/**
 * Un papel en la lista: qué es, cómo está, **qué le falta** y con qué va.
 *
 * Cuatro cosas que se dicen siempre, y las cuatro son la mitad del ticket:
 *
 *  · **cómo está**, con la palabra del servidor: mientras no esté confirmado, se ve que está sin revisar;
 *  · **qué hay que hacer con él**, según su estado (`que_hacer_<estado>`), porque una lista de papeles sin
 *    decir qué hacer con ellos es un montón de papeles;
 *  · **si tiene lectura y si ya se ha mirado**, que no es lo mismo;
 *  · **con qué va y a quién corrige**, cuando lo tiene.
 */
function UnPapel({ papel = {}, textos = {} }) {
  const b = textos.bandeja || {};
  const vinculos = papel.vinculos || [];
  const corregidoPor = papel.rectificada_por || [];
  return html`
    <li>
      <strong>${frase(papel.titulo)}</strong>
      <span className="pista-campo"> ${frase(papel.etiqueta_estado)}</span>
      <${Datos}
        filas=${[
          { etiqueta: b.lo_que_es, valor: papel.etiqueta_tipo || b.no_consta },
          { etiqueta: b.el_dia_del_papel, valor: papel.texto_fecha || b.no_consta },
          { etiqueta: b.de_quien, valor: papel.quien || b.no_consta },
          {
            // El fichero: su nombre, y lo que ocupa **como pista** (no pegado al nombre, que sería una
            // frase compuesta aquí dentro, y las frases las escribe el servidor).
            etiqueta: b.el_fichero,
            valor: papel.tiene_fichero ? papel.nombre_del_fichero || b.no_consta : b.sin_fichero,
            aviso: papel.tiene_fichero ? papel.texto_tamano : "",
          },
          {
            etiqueta: b.su_lectura,
            valor: papel.la_propuesta ? b.tiene_propuesta : b.sin_propuesta,
          },
        ]}
      />
      ${
        // Con qué va, cada cosa en su renglón: unirlas con un separador sería una frase compuesta en la
        // pantalla, y aquí las frases las escribe el servidor.
        vinculos.length
          ? html`<p className="pista-campo">
              <span>${frase(b.enlazado_con)}</span>
              ${vinculos.map((vinculo) => html`<span key=${vinculo.id}>${frase(vinculo.que_es)}</span>`)}
            </p>`
          : html`<p className="pista-campo">${frase(b.sin_enlazar)}</p>`
      }
      ${
        corregidoPor.length
          ? html`<p className="pista-campo">
              <span>${frase(b.rectificada_por)}</span>
              ${corregidoPor.map((otro) => html`<span key=${otro.id}>${frase(otro.titulo)}</span>`)}
            </p>`
          : null
      }
      ${
        // Y qué hacer con él, según cómo esté. Sin esto, la bandeja es una lista de nombres.
        papel.estado === "confirmado" || !b[`que_hacer_${papel.estado}`]
          ? null
          : html`<p className="pista-campo">${frase(b[`que_hacer_${papel.estado}`])}</p>`
      }
      <${Botones}
        botones=${[{ etiqueta: b.abrir, accion: "bandeja-abrir", datos: { id: papel.id }, clase: "boton-claro" }]}
        barra=${false}
      />
    </li>
  `;
}

/**
 * La pantalla de la bandeja (S10, `#/papeles/bandeja`).
 *
 * Propiedades (todas preparadas por `app.js`, que es quien tiene los datos y el vocabulario):
 *
 *  - `textos`: `{bandeja, acciones}` del servidor. Aquí no hay ni una frase escrita.
 *  - `papeles`: `items` de `GET /api/bandeja`, cada uno con su estado y lo que le falta.
 *  - `tipos`, `estados`, `clases`: `[{valor, etiqueta}]` del servidor, para los tres desplegables.
 *  - `resumen`, `cuantos`, `sinDecirDeQueEs`: el pie ya compuesto («Tienes 7 papeles…») y las dos cuentas.
 *  - `estadoElegido`, `tipoElegido`, `filtro`: lo que está puesto en el buscador y en los dos desplegables.
 *  - `ficheroElegido`, `tipoNuevoElegido`: lo que se está subiendo ahora mismo.
 *  - `comprobado`: lo que contestó `POST /api/bandeja/comprobar` — **no ha guardado nada**.
 *  - `comprobando`, `subiendo`, `guardando`: lo que está en marcha, y se dice en pantalla.
 *  - `formulario`: el formulario abierto (la revisión de un papel), o `null`.
 *  - `error`, `aviso`: lo que ha dicho el servidor cuando ha ido mal, y lo bueno.
 */
export function PantallaDeLaBandeja({
  textos = {},
  papeles = [],
  tipos = [],
  estados = [],
  clases = [],
  resumen = "",
  cuantos = 0,
  sinDecirDeQueEs = 0,
  estadoElegido = "sin_revisar",
  tipoElegido = "",
  filtro = "",
  ficheroElegido = "",
  tipoNuevoElegido = "",
  comprobado = null,
  comprobando = false,
  subiendo = false,
  formulario = null,
  guardando = false,
  error = "",
  aviso = "",
}) {
  const b = textos.bandeja || {};
  const acciones = textos.acciones || {};
  const filtrando = Boolean(filtro || (estadoElegido && estadoElegido !== "sin_revisar") || tipoElegido);
  return html`
    <h1>${frase(b.titulo)}</h1>
    <p className="pista">${frase(b.explica)}</p>
    ${error ? html`<${AvisoDeError} texto=${error} />` : null}
    ${aviso ? html`<div className="aviso">${frase(aviso)}</div>` : null}

    ${formulario ? html`<${Formulario} formulario=${formulario} guardando=${guardando} />` : null}

    <${LaSubida}
      textos=${textos}
      tipos=${tipos}
      ficheroElegido=${ficheroElegido}
      tipoElegido=${tipoNuevoElegido}
      comprobado=${comprobado}
      comprobando=${comprobando}
      subiendo=${subiendo}
    />

    <h2>${frase(b.lista_titulo)}</h2>
    <p className="pista-campo">${frase(b.lista_explica)}</p>

    <div className="campo">
      <label htmlFor="bandeja-buscar">${frase(b.buscar)}</label>
      <p className="pista-campo">${frase(b.buscar_pista)}</p>
      <input id="bandeja-buscar" type="text" defaultValue=${frase(filtro)} />
    </div>
    <${Elegir} id="bandeja-estado" etiqueta=${b.cuales_ver} opciones=${estados} elegido=${estadoElegido} />
    <${Elegir}
      id="bandeja-tipo"
      etiqueta=${b.de_que_es}
      opciones=${tipos}
      elegido=${tipoElegido}
      vacio=${b.todos_los_tipos}
    />
    <div className="barra-acciones">
      <${BotonSencillo} etiqueta=${b.buscar_boton} accion="bandeja-filtrar" clase="boton-claro" />
      <${BotonSencillo} etiqueta=${b.ver_todo} accion="bandeja-ver-todas" clase="boton-claro" />
    </div>

    ${resumen ? html`<p className="cuantas">${frase(resumen)}</p>` : null}
    ${
      sinDecirDeQueEs
        ? html`<div className="aviso">${frase(b.faltan_por_decir_de_que_son)}</div>`
        : null
    }

    ${
      papeles.length
        ? html`<ul className="lista">
            ${papeles.map((papel) => html`<${UnPapel} key=${papel.id} papel=${papel} textos=${textos} />`)}
          </ul>`
        : html`<div className="aviso">${frase(filtrando ? b.sin_resultados : b.sin_papeles)}</div>`
    }

    <div className="barra-acciones">
      <${Boton} etiqueta=${b.los_papeles} accion="papel-ver-todos" clase="boton-claro" />
      <${BotonSencillo} etiqueta=${acciones.volver || ""} accion="ir-inicio" clase="" />
    </div>
  `;
}

// ==========================================================================
// La ficha de un papel: el original, la propuesta y con qué va
// ==========================================================================

/**
 * **El original, siempre a la vista**: su nombre, cuánto ocupa y su huella.
 *
 * Es el bloque que sostiene la primera regla del ticket. Y por eso **no hay aquí ningún campo**: el nombre
 * del fichero, su tamaño y su huella **se enseñan**, no se editan. La huella se explica, porque un número
 * largo sin decir para qué sirve no le dice nada a nadie.
 */
function ElOriginal({ papel = {}, textos = {} }) {
  const b = textos.bandeja || {};
  return html`
    <h2>${frase(b.el_original)}</h2>
    <p className="pista-campo">${frase(b.el_original_explica)}</p>
    ${
      papel.tiene_fichero
        ? html`
            <${Datos}
              filas=${[
                { etiqueta: b.el_fichero, valor: papel.nombre_del_fichero || b.no_consta },
                { etiqueta: b.tamano, valor: papel.texto_tamano || b.no_consta },
                {
                  etiqueta: b.la_huella,
                  valor: papel.huella || b.no_consta,
                  aviso: b.la_huella_pista,
                },
              ]}
            />
            <div className="barra-acciones">
              <${Boton}
                etiqueta=${b.ver_el_original}
                accion="bandeja-original"
                datos=${{ id: papel.id }}
                clase="boton-claro"
              />
            </div>
          `
        : html`<div className="aviso">${frase(b.sin_fichero_aviso)}</div>`
    }
    ${
      // A qué papel corrige este, si es una rectificativa: se dice aquí arriba, porque es lo primero que
      // hay que saber de una factura corregida.
      papel.rectifica_a
        ? html`<p className="aviso">
            <strong>${frase(b.rectifica_a)}</strong> ${frase((papel.rectifica_a || {}).titulo || "")}
          </p>`
        : null
    }
    ${
      papel.rectificada_por && papel.rectificada_por.length
        ? html`<p className="aviso">
            <strong>${frase(b.rectificada_por)}</strong>
            ${frase((papel.rectificada_por || []).map((otro) => otro.titulo).join(" · "))}
          </p>`
        : null
    }
  `;
}

/** Una línea leída: lo que dice, y **si su cuenta cuadra**, que es lo único que se puede afirmar. */
function UnaLinea({ linea = {}, textos = {} }) {
  const b = textos.bandeja || {};
  return html`
    <li>
      <strong>${frase(linea.descripcion)}</strong>
      <${Datos}
        filas=${[
          {
            etiqueta: b.cantidad,
            valor: unDato({
              escritos: { cantidad: linea.texto_cantidad },
              campos: { cantidad: linea.cantidad },
              campo: "cantidad",
              noConsta: b.no_consta,
            }),
            // La unidad va como pista, en su trocito de texto: pegarla a la cantidad sería una frase
            // compuesta aquí dentro.
            aviso: linea.unidad || "",
          },
          {
            etiqueta: b.precio,
            valor: unDato({
              escritos: { precio: linea.texto_precio_unitario },
              campos: { precio: linea.precio_unitario },
              campo: "precio",
              noConsta: b.no_consta,
            }),
          },
          {
            etiqueta: b.importe,
            valor: unDato({
              escritos: { importe: linea.texto_importe },
              campos: { importe: linea.importe },
              campo: "importe",
              noConsta: b.no_consta,
            }),
          },
        ]}
      />
      <p className="pista-campo">
        ${frase(linea.la_cuenta_cuadra ? b.la_cuenta_cuadra : b.la_cuenta_no_cuadra)}
      </p>
    </li>
  `;
}

/** Los avisos de la lectura, que son los del lector y vienen ya escritos del servidor. */
function LosAvisos({ avisos = [], textos = {} }) {
  const b = textos.bandeja || {};
  if (!avisos.length) return null;
  return html`
    <h3>${frase(b.avisos_titulo)}</h3>
    <ul className="lista">
      ${avisos.map((aviso, indice) => html`<li key=${indice}><p>${frase(aviso)}</p></li>`)}
    </ul>
  `;
}

/**
 * **La propuesta**: lo que el programa ha leído, al lado del original y **sin entrar en el cuaderno**.
 *
 * Tres cosas se dicen siempre, y en este orden:
 *
 *  1. que esto **es una propuesta** y no un dato;
 *  2. que **no se puede decir si está bien**, con su motivo (no hay corpus para medirlo) — y eso se dice
 *     aunque no haya ninguna lectura, porque es una regla que el agricultor tiene que poder leer;
 *  3. lo que sí es un hecho: las líneas leídas, cuántas cuadran, y si las cuentas del papel cuadran.
 */
function LaPropuesta({ papel = {}, textos = {}, leyendo = false }) {
  const b = textos.bandeja || {};
  const propuesta = papel.la_propuesta;
  return html`
    <h2>${frase(b.la_propuesta)}</h2>
    <p className="pista-campo">${frase(b.la_propuesta_explica)}</p>
    <div className="aviso"><p>${frase(b.no_se_mide_la_lectura)}</p></div>

    ${
      papel.se_puede_leer
        ? html`<div className="barra-acciones">
            <${Boton}
              etiqueta=${leyendo ? b.leyendo : b.leer_el_papel}
              accion="bandeja-leer"
              datos=${{ id: papel.id }}
              clase=""
            />
          </div>`
        : html`<p className="pista-campo">${frase(b.este_papel_no_lo_se_leer)}</p>`
    }

    ${
      propuesta
        ? html`
            ${papel.propuesta_descartada
              ? html`<p className="aviso">${frase(b.descartada)}</p>`
              : null}
            <${Datos}
              filas=${[
                {
                  etiqueta: b.proveedor,
                  valor: unDato({ escritos: propuesta.textos, campos: propuesta.campos, campo: "proveedor", noConsta: b.no_consta }),
                },
                {
                  etiqueta: b.nif_del_proveedor,
                  valor: unDato({ escritos: propuesta.textos, campos: propuesta.campos, campo: "proveedor_nif", noConsta: b.no_consta }),
                },
                {
                  etiqueta: b.numero_de_factura,
                  valor: unDato({ escritos: propuesta.textos, campos: propuesta.campos, campo: "numero_factura", noConsta: b.no_consta }),
                },
                {
                  etiqueta: b.fecha,
                  valor: unDato({ escritos: propuesta.textos, campos: propuesta.campos, campo: "fecha", noConsta: b.no_consta }),
                },
                {
                  etiqueta: b.base_imponible,
                  valor: unDato({ escritos: propuesta.textos, campos: propuesta.campos, campo: "base_imponible", noConsta: b.no_consta }),
                },
                {
                  etiqueta: b.cuota_de_iva,
                  valor: unDato({ escritos: propuesta.textos, campos: propuesta.campos, campo: "cuota_iva", noConsta: b.no_consta }),
                },
                {
                  etiqueta: b.tipo_de_iva,
                  valor: unDato({ escritos: propuesta.textos, campos: propuesta.campos, campo: "tipo_iva_pct", noConsta: b.no_consta }),
                },
                {
                  etiqueta: b.total,
                  valor: unDato({ escritos: propuesta.textos, campos: propuesta.campos, campo: "total", noConsta: b.no_consta }),
                },
                { etiqueta: b.lineas_leidas, valor: propuesta.lineas_leidas },
                { etiqueta: b.lineas_que_cuadran, valor: propuesta.lineas_que_cuadran },
                {
                  etiqueta: b.cuadra_el_total,
                  valor: propuesta.cuadra_el_total ? b.si : b.no,
                },
                {
                  etiqueta: b.suman_las_lineas,
                  valor: propuesta.suman_las_lineas ? b.si : b.no,
                },
              ]}
            />
            <${LosAvisos} avisos=${propuesta.avisos || []} textos=${textos} />
            <h3>${frase(b.las_lineas)}</h3>
            ${
              (propuesta.lineas || []).length
                ? html`<ul className="lista">
                    ${(propuesta.lineas || []).map(
                      (linea, indice) =>
                        html`<${UnaLinea} key=${indice} linea=${linea} textos=${textos} />`,
                    )}
                  </ul>`
                : html`<p className="pista-campo">${frase(b.sin_lineas)}</p>`
            }
          `
        : html`<p className="pista-campo">${frase(b.no_hay_propuesta)}</p>`
    }
  `;
}

/** **Lo que el agricultor ha aceptado**, que todavía no está confirmado. */
function LoAceptado({ papel = {}, textos = {}, aceptando = false }) {
  const b = textos.bandeja || {};
  const aceptado = papel.lo_aceptado;
  return html`
    <h2>${frase(b.lo_aceptado)}</h2>
    ${aceptado ? html`<p className="pista-campo">${frase(b.lo_aceptado_explica)}</p>` : null}
    ${aceptado
      ? html`<${Datos}
          filas=${[
            {
              etiqueta: b.proveedor,
              valor: unDato({ escritos: aceptado.textos, campos: aceptado.campos, campo: "proveedor", noConsta: b.no_consta }),
            },
            {
              etiqueta: b.numero_de_factura,
              valor: unDato({ escritos: aceptado.textos, campos: aceptado.campos, campo: "numero_factura", noConsta: b.no_consta }),
            },
            {
              etiqueta: b.fecha,
              valor: unDato({ escritos: aceptado.textos, campos: aceptado.campos, campo: "fecha", noConsta: b.no_consta }),
            },
            {
              etiqueta: b.base_imponible,
              valor: unDato({ escritos: aceptado.textos, campos: aceptado.campos, campo: "base_imponible", noConsta: b.no_consta }),
            },
            {
              etiqueta: b.cuota_de_iva,
              valor: unDato({ escritos: aceptado.textos, campos: aceptado.campos, campo: "cuota_iva", noConsta: b.no_consta }),
            },
            {
              etiqueta: b.total,
              valor: unDato({ escritos: aceptado.textos, campos: aceptado.campos, campo: "total", noConsta: b.no_consta }),
            },
          ]}
        />`
      : null}
    ${
      // Y las dos salidas, que son distintas: **revisar** es decir qué queda (y todavía no es un dato del
      // cuaderno), y **confirmar** es dar el papel por bueno, con quién y cuándo. Se dice qué hace cada
      // una, porque son lo que parece lo mismo y no lo es.
      papel.se_puede_confirmar
        ? html`
            <p className="pista-campo">${frase(b.confirmar_explica)}</p>
            <div className="barra-acciones">
              <${Boton}
                etiqueta=${aceptando ? b.confirmando : b.confirmar}
                accion="bandeja-confirmar"
                datos=${{ id: papel.id }}
                clase=""
              />
            </div>
          `
        : html`
            <p className="pista-campo">${frase(b.sin_aceptar_nada)}</p>
            <p className="pista-campo">${frase(b.hay_que_revisar_antes)}</p>
          `
    }
    ${
      papel.estado === "confirmado"
        ? html`
            <div className="aviso">
              <p><strong>${frase(b.ya_esta_en_los_papeles)}</strong></p>
              <${Datos}
                filas=${[
                  { etiqueta: b.confirmado_por, valor: papel.confirmado_por || b.no_consta },
                  { etiqueta: b.confirmado_en, valor: papel.texto_confirmado_en || b.no_consta },
                ]}
              />
            </div>
          `
        : null
    }
  `;
}

/** Lo que tiene enlazado el papel, con su nombre y con el botón de quitarlo de ahí. */function LosVinculos({ papel = {}, textos = {}, guardando = false }) {
  const b = textos.bandeja || {};
  const vinculos = papel.vinculos || [];
  return html`
    <h2>${frase(b.enlazar_titulo)}</h2>
    <p className="pista-campo">${frase(b.enlazar_explica)}</p>
    <p className="pista-campo">${frase(b.no_crea_nada)}</p>
    ${
      vinculos.length
        ? html`
            <h3>${frase(b.enlazado_titulo)}</h3>
            <ul className="lista">
              ${vinculos.map(
                (vinculo) => html`
                  <li key=${vinculo.id}>
                    <p>${frase(vinculo.que_es)}</p>
                    <div className="barra-acciones">
                      <${BotonSencillo}
                        etiqueta=${b.desenlazar}
                        accion="bandeja-desenlazar"
                        datos=${{ clase: vinculo.clase, entidad: vinculo.entidad_id }}
                      />
                    </div>
                  </li>
                `,
              )}
            </ul>
            ${guardando ? html`<p className="pista-campo">${frase(b.enlazando)}</p>` : null}
          `
        : html`<p className="pista-campo">${frase(b.sin_enlazar)}</p>`
    }
  `;
}

/**
 * La ficha de un papel de la bandeja (S10, `#/papeles/bandeja/<id>`).
 *
 * Es la pantalla donde se hace el recorrido entero de un papel ya subido: mirarlo, leerlo, decir qué queda,
 * confirmarlo y decir con qué va. Y las cuatro cosas que **no** se pueden hacer desde aquí, a propósito:
 *
 *  · **cambiar el fichero, su nombre o su huella**: el original está para mirarlo (el fichero se cambia
 *    desde «los papeles», que es donde vive el papel ya archivado);
 *  · **confirmar sin haber revisado**: el botón no se pinta si el servidor no dice que se puede;
 *  · **enlazar con algo que no existe**: la lista de candidatos son cosas que ya están en el cuaderno;
 *  · **borrar al papel que corrijo**: una rectificativa deja las dos, y la corregida sigue consultable.
 *
 * Propiedades (preparadas por `app.js`):
 *
 *  - `textos`: `{bandeja, acciones}` del servidor.
 *  - `papel`: lo que contesta `GET /api/bandeja/<id>`, con su estado ya en palabras y su propuesta.
 *  - `tipos`: `[{valor, texto}]` — los ocho tipos de papel, para decir de qué es el que se está mirando.
 *  - `candidatos`: `[{valor, texto}]` de `GET /api/bandeja/candidatos?clase=…` — cosas que ya existen.
 *  - `papelesParaRectificar`: `[{valor, texto}]` — los otros papeles de la finca.
 *  - `clases`: `[{valor, texto}]` — las seis clases de vínculo, con sus palabras del servidor.
 *  - `claseElegida`, `claseBuscada`, `textoBuscado`: qué se está buscando para enlazar.
 *  - `formulario`: la revisión abierta, o `null`.
 *  - `guardando`, `cargando`, `error`, `aviso`.
 */
export function PantallaDeUnPapelDeLaBandeja({
  textos = {},
  papel = {},
  tipos = [],
  candidatos = [],
  papelesParaRectificar = [],
  clases = [],
  claseElegida = "",
  claseBuscada = "",
  buscandoCandidatos = false,
  formulario = null,
  guardando = false,
  cargando = false,
  error = "",
  aviso = "",
}) {
  const b = textos.bandeja || {};
  const acciones = textos.acciones || {};
  return html`
    <h1>${frase(b.ficha_titulo)}</h1>
    <p className="pista">${frase(papel.titulo || "")}</p>
    <p className="pista-campo">
      <span>${frase(papel.etiqueta_tipo || "")}</span>
      <span>${frase(papel.etiqueta_estado || "")}</span>
      <span>${frase(b.el_dia_del_papel)}</span>
      <span>${frase(papel.texto_fecha || b.no_consta)}</span>
    </p>
    ${error ? html`<${AvisoDeError} texto=${error} />` : null}
    ${aviso ? html`<div className="aviso">${frase(aviso)}</div>` : null}
    ${cargando ? html`<p className="pista">${frase(b.buscando)}</p>` : null}

    ${
      // Y qué hacer con él, según cómo esté. De un papel ya confirmado no hay nada que hacer, y por eso no
      // hay ninguna frase para ese caso (`que_hacer_confirmado` no existe, y aquí no se busca).
      papel.estado && papel.estado !== "confirmado" && b[`que_hacer_${papel.estado}`]
        ? html`<p className="aviso">${frase(b[`que_hacer_${papel.estado}`])}</p>`
        : null
    }

    ${
      // **Decir de qué es el papel**, que es lo que lo saca de «recién subido». Va aquí arriba y con su
      // botón porque es lo primero que hay que hacer con un papel que acaba de llegar, y sin esto el aviso
      // de «falta decir de qué es» sería una instrucción que no se puede seguir desde ningún sitio.
      html`
        <${Elegir}
          id="bandeja-tipo-del-papel"
          etiqueta=${b.de_que_es}
          pista=${b.de_que_es_pista}
          opciones=${tipos}
          elegido=${papel.tipo || ""}
          vacio=${b.no_lo_se_todavia}
        />
        <div className="barra-acciones">
          <${BotonSencillo}
            etiqueta=${b.decir_de_que_es}
            accion="bandeja-clasificar"
            datos=${{ id: papel.id }}
            clase="boton-claro"
          />
        </div>
      `
    }

    <${ElOriginal} papel=${papel} textos=${textos} />

    <${LaPropuesta} papel=${papel} textos=${textos} leyendo=${guardando && Boolean(papel.se_puede_leer)} />

    ${
      // La puerta para decir qué queda: se abre el formulario (con lo leído ya puesto, para corregirlo) y
      // se guarda. Lo que se guarda es **lo que él acepta**, no lo que el programa propuso.
      formulario
        ? html`<${Formulario} formulario=${formulario} guardando=${guardando} />`
        : html`<div className="barra-acciones">
            <${Boton}
              etiqueta=${b.revisar}
              accion="bandeja-revisar"
              datos=${{ id: papel.id }}
              clase="boton-claro"
            />
          </div>`
    }

    <${LoAceptado} papel=${papel} textos=${textos} aceptando=${guardando} />

    ${
      // **Descartar la lectura** no la borra: se dice por qué y queda apuntado, que es lo que permite
      // entender dentro de un año por qué este papel se escribió a mano.
      papel.se_puede_descartar_la_propuesta
        ? html`
            <div className="campo">
              <label htmlFor="bandeja-motivo-descartar">${frase(b.motivo)}</label>
              <p className="pista-campo">${frase(b.descartar_pista)}</p>
              <input id="bandeja-motivo-descartar" type="text" defaultValue="" />
            </div>
            <div className="barra-acciones">
              <${BotonSencillo}
                etiqueta=${b.descartar_la_propuesta}
                accion="bandeja-descartar"
                datos=${{ id: papel.id }}
              />
            </div>
          `
        : null
    }

    <${LosVinculos} papel=${papel} textos=${textos} guardando=${guardando} />

    ${
      // Y con qué enlazarlo: la clase la elige él, se buscan los candidatos (que ya existen) y se elige uno.
      // El buscador lleva su campo y su botón porque un agricultor puede tener cientos de gastos.
      html`
        <${Elegir}
          id="bandeja-clase"
          etiqueta=${b.de_que_clase}
          opciones=${clases}
          elegido=${claseElegida}
        />
        <div className="campo">
          <label htmlFor="bandeja-candidato-buscar">${frase(b.buscar_candidato)}</label>
          <p className="pista-campo">${frase(b.buscar_candidato_pista)}</p>
          <input id="bandeja-candidato-buscar" type="text" defaultValue=${frase(claseBuscada)} />
        </div>
        <div className="barra-acciones">
          <${BotonSencillo}
            etiqueta=${b.buscar_candidatos}
            accion="bandeja-buscar-candidatos"
            clase="boton-claro"
          />
        </div>
        ${
          candidatos.length
            ? html`
                <${Elegir}
                  id="bandeja-candidato"
                  etiqueta=${b.cual_de_ellos}
                  opciones=${candidatos}
                  elegido=""
                  vacio=${b.elige_uno}
                />
                <div className="barra-acciones">
                  <${Boton}
                    etiqueta=${b.enlazar}
                    accion="bandeja-enlazar"
                    datos=${{ id: papel.id }}
                    clase=""
                  />
                </div>
              `
            : html`<p className="pista-campo">${
                buscandoCandidatos ? frase(b.buscando) : frase(b.sin_candidatos)
              }</p>`
        }
      `
    }

    ${
      // Las rectificativas: las dos quedan, y se dice cuál corrige a cuál.
      html`
        <h2>${frase(b.rectificar_titulo)}</h2>
        <p className="pista-campo">${frase(b.rectificar_explica)}</p>
        ${
          papelesParaRectificar.length
            ? html`
                <${Elegir}
                  id="bandeja-rectifica-a"
                  etiqueta=${b.a_que_papel}
                  opciones=${papelesParaRectificar}
                  elegido=""
                  vacio=${b.elige_el_papel}
                />
                <div className="barra-acciones">
                  <${Boton}
                    etiqueta=${b.rectificar}
                    accion="bandeja-rectificar"
                    datos=${{ id: papel.id }}
                    clase="boton-claro"
                  />
                </div>
              `
            : html`<p className="pista-campo">${frase(b.nadie_lo_ha_corregido)}</p>`
        }
      `
    }

    <div className="barra-acciones">
      <${BotonSencillo} etiqueta=${b.volver_a_la_bandeja} accion="bandeja-ver" clase="" />
      <${BotonSencillo} etiqueta=${b.los_papeles} accion="papel-ver-todos" clase="boton-claro" />
      <${BotonSencillo} etiqueta=${acciones.volver || ""} accion="ir-inicio" clase="" />
    </div>
  `;
}

// ==========================================================================
// Los elementos ya montados
// ==========================================================================

/** El elemento de React de la bandeja, ya con sus propiedades puestas. */
export function pantallaDeLaBandeja(propiedades) {
  return html`
    <${PantallaDeLaBandeja}
      textos=${propiedades.textos}
      papeles=${propiedades.papeles}
      tipos=${propiedades.tipos}
      estados=${propiedades.estados}
      clases=${propiedades.clases}
      resumen=${propiedades.resumen}
      cuantos=${propiedades.cuantos}
      sinDecirDeQueEs=${propiedades.sinDecirDeQueEs}
      estadoElegido=${propiedades.estadoElegido}
      tipoElegido=${propiedades.tipoElegido}
      filtro=${propiedades.filtro}
      ficheroElegido=${propiedades.ficheroElegido}
      tipoNuevoElegido=${propiedades.tipoNuevoElegido}
      comprobado=${propiedades.comprobado}
      comprobando=${propiedades.comprobando}
      subiendo=${propiedades.subiendo}
      formulario=${propiedades.formulario}
      guardando=${propiedades.guardando}
      error=${propiedades.error}
      aviso=${propiedades.aviso}
    />
  `;
}

/** Y el de la ficha de un papel de la bandeja. */
export function pantallaDeUnPapelDeLaBandeja(propiedades) {
  return html`
    <${PantallaDeUnPapelDeLaBandeja}
      textos=${propiedades.textos}
      papel=${propiedades.papel}
      tipos=${propiedades.tipos}
      candidatos=${propiedades.candidatos}
      papelesParaRectificar=${propiedades.papelesParaRectificar}
      clases=${propiedades.clases}
      claseElegida=${propiedades.claseElegida}
      claseBuscada=${propiedades.claseBuscada}
      buscandoCandidatos=${propiedades.buscandoCandidatos}
      formulario=${propiedades.formulario}
      guardando=${propiedades.guardando}
      cargando=${propiedades.cargando}
      error=${propiedades.error}
      aviso=${propiedades.aviso}
    />
  `;
}
