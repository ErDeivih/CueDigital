/*
 * bancos.js — El extracto del banco y la conciliación (S14, T20 / E11, 06/10/2026).
 *
 * QUÉ ES ESTA PANTALLA, Y QUÉ ES LO QUE NO HACE NUNCA
 *
 * El recorrido entero, en el orden en que se hace: **subir el fichero** que el agricultor ha descargado
 * de su banca → **mirar lo que ha entendido** (incluidas las líneas que no, y por qué) → **apuntar los
 * movimientos** → **cuadrar cada uno contra sus papeles** (una factura, un cobro, una factura de compra)
 * → **deshacer** sin borrar nada → **mirar lo que queda por cuadrar** → y **sacar el extracto en un
 * fichero**. Son **dos pantallas en un fichero**, como en la maquinaria y en los trabajos: la lista
 * (`#/cuentas/bancos`) y la ficha de un movimiento (`#/cuentas/bancos/<id>`). Las dos se reconstruyen
 * enteras al abrir su dirección —piden sus datos al servidor—, y **los formularios no tienen dirección**:
 * uno que al recargar saliera vacío es peor que no tenerla.
 *
 * Y las cinco cosas que esta pantalla NO hace, cada una con su motivo:
 *
 *  1. **No se conecta a ningún banco.** Aquí solo se lee **un fichero que el agricultor ha subido**. No
 *     hay claves, ni direcciones de banco, ni un sitio donde poner una credencial. Lo prohíbe el encargo
 *     del T20 y lo comprueba una prueba del servidor (`TestNoHayNingunaConexionBancaria`).
 *  2. **No crea ningún documento al conciliar.** Conciliar escribe un vínculo entre un movimiento y un
 *     papel que **ya existe**, así que esta pantalla no ofrece por ningún lado «crear un gasto» ni «crear
 *     una factura». Es la regla «un pago conciliado no crea un segundo gasto», y se ve en la lista de
 *     acciones del informe, que no tiene ninguna de esas.
 *  3. **No suma ni resta nada.** En el navegador todo número es de coma flotante, así que los importes,
 *     los totales de la lectura y lo que le queda por cuadrar a cada movimiento llegan **calculados del
 *     servidor** con `Decimal`, y aquí solo se colocan. Lo único que se hace con un importe es enseñarlo,
 *     y para eso llega ya escrito por `app.js` (`texto_importe`, `texto_por_conciliar`…), que es quien
 *     tiene el formateador del programa (`enEuros`).
 *  4. **No adivina un importe.** Un movimiento sin importe es «no lo sé» y se enseña **como hueco, con su
 *     palabra**, nunca como `0,00 €`: un cero diría que el banco movió cero euros. Se ve en tres sitios:
 *     en la vista previa, en la lista de movimientos y en su ficha.
 *  5. **No apunta nada hasta que el agricultor lo dice.** Leer el fichero es una puerta que **no guarda**
 *     (`/extractos/vista-previa`): lo que se enseña es una propuesta, y hasta que no se pulsa APUNTAR
 *     ESTOS MOVIMIENTOS no se manda nada. Y subir dos veces el mismo fichero no duplica nada: lo dice el
 *     servidor, con su número, en la propuesta.
 *
 * LOS `data-accion` VAN ESCRITOS EN CADA RAMA, Y NO EN UNA VARIABLE
 *
 * El manejador de clics es **uno solo** y vive en `app.js`. Hay un guardián
 * (`tests/test_los_botones_hacen_algo.py`) que lee las acciones del código y exige que todas tengan quien
 * las atienda; una acción puesta por variable **no se puede leer**, así que un botón que no hiciera nada
 * pasaría desapercibido. Por eso aquí **todas las acciones van escritas literales en su rama**, y la lista
 * está una por una en el informe del ticket (`docs/T20_PANTALLA.md`), con lo que tiene que hacer cada una.
 *
 * Y ojo con el guardián al escribir este fichero: **no quita los comentarios** antes de mirar, así que
 * escribir aquí la forma prohibida (con su dólar y su llave) hace que cuente este fichero como uno de los
 * que pintan acciones por variable. Se dice porque pasó: este párrafo, escrito con el ejemplo dentro, puso
 * roja esa prueba.
 *
 * Y LO MISMO CON LAS FRASES: NINGUNA ESCRITA AQUÍ
 *
 * Todo lo que se lee viene del servidor: de cada movimiento, de cada papel y de cada propuesta se enseña
 * **lo que dice el servidor**, y los rótulos son claves de `textos.BANCOS` que llegan por la propiedad
 * `textos`. Hay cuatro familias de claves que se leen **compuestas**, y se dicen aquí para que nadie las
 * busque en balde:
 *
 *  · `estado_<estado>` — cómo está un movimiento (`sin_conciliar`, `conciliado_en_parte`, `conciliado`,
 *    `no_se_puede_conciliar`);
 *  · `falta_<lo_que_falta>` — qué no consta de una línea (`importe_no_consta`, `saldo_no_consta`,
 *    `referencia_no_consta`, `concepto_no_consta`, `importe_ilegible_en_la_fila`, `saldo_ilegible`);
 *  · `por_que_no_<clave>` — por qué no se puede cuadrar (`no_consta_el_importe`,
 *    `es_un_traspaso_entre_cuentas_tuyas`);
 *  · `propuesta_<tipo>` — cómo cuadra una propuesta (`exacta`, `agrupada`, `parcial`).
 *
 * Son las claves que el servidor manda **como claves** (no como frases) en `estado`, `lo_que_falta` y
 * `por_que_no`, y por eso la pantalla las traduce. Falta una, y esa frase sale en blanco sin que salte
 * nada: hay una prueba que recorre las cuatro familias enteras y avisa.
 *
 * El componente es PURO: no llama a `fetch`, no lee `localStorage` y no toca el DOM.
 */

import { AvisoDeError, Boton, Botones, BotonSencillo, frase, html } from "../componentes.js";
import { Campo } from "../piezas/campo.js";
import { Tabla } from "../piezas/tabla.js";

// ==========================================================================
// Las piezas pequeñas de esta pantalla
// ==========================================================================

/**
 * Un renglón de «nombre y valor».
 *
 * Va en su propia pieza porque aquí se repite en casi todos los bloques (el movimiento, el papel, la
 * propuesta, el traspaso, lo que se ha apuntado) y escribirlo cinco veces es la forma más segura de que
 * dentro de un mes cuatro digan lo mismo y uno no. `aviso` es lo que hay que decir **además** del dato
 * («lo escribiste tú», «esto no cuenta en los totales»).
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
 * Un desplegable con su etiqueta.
 *
 * Igual que el de los trabajos: lo que se elige aquí —la cuenta, el perfil, el papel, la otra pata del
 * traspaso— es una lista que puede ser larga, y no una pregunta de dos respuestas. Las opciones **las
 * prepara `app.js`** (`[{valor, texto}]`), que es quien tiene los textos del servidor.
 *
 * `vacio` es la opción sin elegir («Elige la cuenta»). Si no se pasa, no se pinta: cuando ya hay un valor
 * elegido de antes, una primera opción en blanco deja al agricultor sin saber si eligió algo.
 */
function Elegir({ id, etiqueta, pista, opciones = [], elegido = "", vacio = "", soloLectura = false }) {
  return html`
    <div className="campo">
      <label htmlFor=${id}>${frase(etiqueta)}</label>
      ${pista ? html`<p className="pista-campo">${frase(pista)}</p>` : null}
      <select id=${id} defaultValue=${frase(elegido)} disabled=${soloLectura}>
        ${vacio ? html`<option value="">${frase(vacio)}</option>` : null}
        ${(opciones || []).map(
          (opcion) => html`
            <option value=${String(opcion.valor)} key=${String(opcion.valor)}>${frase(opcion.texto)}</option>
          `,
        )}
      </select>
    </div>
  `;
}

/**
 * Un formulario, tal y como lo prepara `app.js`: un título, sus bloques y sus dos botones.
 *
 * Es **la misma forma** que la de la pantalla de las cuentas (T13), y a propósito: un bloque es de
 * escribir (`{tipo, id, etiqueta, valor, pista}`) o de elegir (`{tipo: "opciones", campo, etiqueta,
 * opciones, elegido}`), y un bloque con un `tipo` que no se conoce se pinta como texto. Entre un campo de
 * más —que el agricultor puede rellenar y se guarda en su sitio— y un campo que desaparece sin decir
 * nada, el de más.
 *
 * `datos.clase` dice **qué** se está guardando (una cuenta, la forma de escribir del banco o la
 * corrección de un movimiento): el manejador de clics lee ese dato y manda el formulario a su puerta. Sin
 * él, «GUARDAR» sería un botón que no se sabe qué guarda.
 */
function Formulario({ formulario, guardando = false }) {
  if (!formulario) return null;
  return html`
    <h2>${frase(formulario.titulo)}</h2>
    ${formulario.pista ? html`<p className="pista">${frase(formulario.pista)}</p>` : null}
    ${(formulario.bloques || []).map((bloque, indice) =>
      bloque.tipo === "opciones"
        ? html`
            <div className="campo" key=${indice}>
              <p className="etiqueta-campo">${frase(bloque.etiqueta)}</p>
              ${bloque.pista ? html`<p className="pista-campo">${frase(bloque.pista)}</p>` : null}
              <div className="barra-acciones">
                ${(bloque.opciones || []).map((opcion) => {
                  const elegido = String(bloque.elegido) === String(opcion.valor);
                  return html`
                    <button
                      key=${String(opcion.valor)}
                      type="button"
                      className=${`boton ${elegido ? "boton-elegido" : "boton-claro"}`}
                      data-accion="banco-elegir"
                      data-campo=${bloque.campo}
                      data-valor=${String(opcion.valor)}
                      data-elegido=${elegido ? "1" : "0"}
                    >
                      ${frase(opcion.texto)}
                    </button>
                  `;
                })}
              </div>
            </div>
          `
        : html`
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
      <${Boton} etiqueta=${formulario.guardar} accion="banco-guardar" datos=${formulario.datos} clase="" />
      <${BotonSencillo} etiqueta=${formulario.cancelar} accion="banco-cancelar" />
    </div>
    ${guardando ? html`<p className="pista-campo">${frase(formulario.guardando)}</p>` : null}
  `;
}

// ==========================================================================
// Lo que se lee del fichero, sin apuntar nada
// ==========================================================================

/**
 * Las filas del fichero que **no se han podido entender**.
 *
 * Es la mitad del ticket: de cada una se enseña **el número de línea del fichero** (para poder buscarla
 * en el fichero del banco, que es lo que el agricultor tiene delante), **qué le pasa** con las palabras
 * del servidor, y **lo que pone** esa línea, tal cual, para reconocerla. Sin el número y sin el texto, la
 * única salida sería abrir el CSV y contar renglones a mano.
 */
function LasLineasQueNoSeEntienden({ rechazadas = [], textos = {} }) {
  const b = textos.bancos || {};
  if (!rechazadas.length) return null;
  return html`
    <h3>${frase(b.rechazadas_titulo)}</h3>
    <p className="pista-campo">${frase(b.rechazadas_explica)}</p>
    <ul className="lista">
      ${rechazadas.map(
        (fila, indice) => html`
          <li key=${indice}>
            <p>
              <span className="pista-campo">${frase(b.linea_numero)}</span>
              <strong>${frase(fila.numero_de_linea)}</strong>
            </p>
            <p>${frase(fila.que_pasa)}</p>
            ${fila.texto ? html`<p className="pista-campo">${frase(fila.texto)}</p>` : null}
          </li>
        `,
      )}
    </ul>
  `;
}

/** Los avisos de la lectura («las fechas se han leído así porque las líneas 6, 7 y 8 lo demuestran»). */
function LosAvisos({ avisos = [], textos = {} }) {
  const b = textos.bancos || {};
  if (!avisos.length) return null;
  return html`
    <h3>${frase(b.avisos_titulo)}</h3>
    <ul className="lista">
      ${avisos.map((aviso, indice) => html`<li key=${indice}><p>${frase(aviso.que_pasa)}</p></li>`)}
    </ul>
  `;
}

/**
 * Los traspasos que el servidor propone: **el mismo dinero pasado de una cuenta tuya a otra** (A07).
 *
 * Se enseñan y se dice **dónde se marcan**, porque desde aquí no se puede: el servidor los propone por
 * sus claves de duplicado y la puerta que los ata (`POST …/traspaso`) pide el identificador del otro
 * movimiento. Así que el botón está donde se puede pulsar —en la ficha de uno de los dos— y aquí se dice.
 */
function LosTraspasos({ traspasos = [], textos = {} }) {
  const b = textos.bancos || {};
  if (!traspasos.length) return null;
  return html`
    <h3>${frase(b.traspasos_titulo)}</h3>
    <p className="pista-campo">${frase(b.traspasos_explica)}</p>
    <ul className="lista">
      ${traspasos.map(
        (traspaso, indice) => html`
          <li key=${indice}>
            <p>${frase(traspaso.que_pasa)}</p>
            <${Datos}
              filas=${[
                { etiqueta: b.traspaso_sale_de, valor: (traspaso.cuentas || [])[0] || "" },
                { etiqueta: b.traspaso_entra_en, valor: (traspaso.cuentas || [])[1] || "" },
                { etiqueta: b.importe, valor: traspaso.texto_importe || "" },
                { etiqueta: b.traspaso_dias, valor: traspaso.dias_de_diferencia },
              ]}
            />
            <p className="pista-campo">${frase(b.traspaso_donde)}</p>
          </li>
        `,
      )}
    </ul>
  `;
}

/** Un movimiento leído, antes de apuntarlo: lo que se va a apuntar y lo que no consta de él. */
function UnMovimientoLeido({ movimiento = {}, textos = {} }) {
  const b = textos.bancos || {};
  const noConstaElImporte = movimiento.importe === null || movimiento.importe === undefined;
  return html`
    <li>
      <strong>${frase(movimiento.texto_fecha)}</strong>
      <span className="pista-campo"> ${frase(movimiento.concepto)}</span>
      ${movimiento.ya_estaba ? html`<p className="aviso">${frase(b.ya_estaba_esta_linea)}</p>` : null}
      <${Datos}
        filas=${[
          {
            // **Un importe que no consta se enseña en blanco, con la palabra que lo dice.** Un `0,00 €`
            // aquí diría que el banco movió cero euros, que es lo contrario de lo que dice el fichero.
            etiqueta: b.importe,
            valor: noConstaElImporte ? b.no_consta : movimiento.texto_importe,
          },
          { etiqueta: b.saldo, valor: movimiento.texto_saldo || b.no_consta },
          { etiqueta: b.referencia, valor: movimiento.referencia || b.no_consta },
        ]}
      />
      ${(movimiento.lo_que_falta || []).map(
        (falta, indice) => html`<p className="pista-campo" key=${indice}>${frase(b[`falta_${falta}`])}</p>`,
      )}
    </li>
  `;
}

/**
 * **La vista previa entera**: lo que se va a apuntar, lo que no se ha entendido y lo que ya estaba.
 *
 * Es la pantalla que hace que un extracto se pueda revisar, y termina con las dos únicas salidas
 * posibles, las dos explícitas: apuntarlo o no apuntar nada. **Leer no ha guardado nada**, y eso se dice
 * aquí arriba, porque es justo lo que hay que saber antes de pulsar.
 */
function LaVistaPrevia({ vistaPrevia = {}, textos = {}, importando = false }) {
  const b = textos.bancos || {};
  const resumen = vistaPrevia.resumen || {};
  return html`
    <h2>${frase(b.vista_titulo)}</h2>
    <p className="aviso">${frase(b.vista_nada_apuntado)}</p>
    ${vistaPrevia.el_fichero_ya_estaba ? html`<div className="aviso">${frase(b.ya_estaba_el_fichero)}</div>` : null}

    <${Datos}
      filas=${[
        { etiqueta: b.cuenta_detectada, valor: vistaPrevia.cuenta_detectada || b.cuenta_no_detectada },
        { etiqueta: b.lineas_leidas, valor: resumen.lineas_leidas },
        { etiqueta: b.movimientos_leidos, valor: resumen.movimientos },
        { etiqueta: b.se_apuntaran, valor: vistaPrevia.nuevas },
        {
          etiqueta: b.ya_estaban,
          valor: vistaPrevia.ya_estaban,
          aviso: vistaPrevia.ya_estaban ? b.ya_estaban_explica : "",
        },
        { etiqueta: b.rechazadas_cuantas, valor: resumen.rechazadas },
        { etiqueta: b.entradas, valor: resumen.texto_entradas },
        { etiqueta: b.salidas, valor: resumen.texto_salidas },
        {
          // **Y cuántos importes no constan, aparte y con su nombre.** Sin este renglón, los dos totales de
          // arriba parecerían completos sin serlo.
          etiqueta: b.sin_importe,
          valor: resumen.sin_importe,
          aviso: resumen.sin_importe ? b.sin_importe_explica : "",
        },
        { etiqueta: b.formato_de_fecha, valor: vistaPrevia.formato_de_fecha || b.formato_no_dicho },
        { etiqueta: b.saldo_final, valor: vistaPrevia.texto_saldo_final || b.no_consta },
      ]}
    />

    <${LosAvisos} avisos=${vistaPrevia.avisos || []} textos=${textos} />
    <${LasLineasQueNoSeEntienden} rechazadas=${vistaPrevia.rechazadas || []} textos=${textos} />

    <h3>${frase(b.se_van_a_apuntar)}</h3>
    ${
      (vistaPrevia.movimientos || []).length
        ? html`<ul className="lista">
            ${(vistaPrevia.movimientos || []).map(
              (movimiento, indice) =>
                html`<${UnMovimientoLeido} key=${indice} movimiento=${movimiento} textos=${textos} />`,
            )}
          </ul>`
        : html`<div className="aviso">${frase(b.no_hay_ninguno_nuevo)}</div>`
    }

    <${LosTraspasos} traspasos=${vistaPrevia.traspasos || []} textos=${textos} />

    <div className="barra-acciones">
      <${Boton}
        etiqueta=${importando ? b.importando : b.apuntar_los_movimientos}
        accion="banco-importar"
        clase=""
      />
      <${BotonSencillo} etiqueta=${b.descartar} accion="banco-descartar" clase="boton-claro" />
    </div>
  `;
}

/** Lo que el servidor contestó al apuntar el extracto: cuántos entraron, cuántos ya estaban y sus avisos. */
function LoQueSeHaApuntado({ resultado = {}, textos = {} }) {
  const b = textos.bancos || {};
  return html`
    <h2>${frase(b.apuntado_titulo)}</h2>
    <${Datos}
      filas=${[
        { etiqueta: b.apuntados, valor: resultado.creados },
        {
          etiqueta: b.repetidos,
          valor: resultado.repetidos,
          aviso: resultado.repetidos ? b.repetidos_explica : "",
        },
        { etiqueta: b.rechazadas_cuantas, valor: resultado.filas_rechazadas },
        {
          etiqueta: b.sin_importe,
          valor: resultado.sin_importe,
          aviso: resultado.sin_importe ? b.sin_importe_explica : "",
        },
      ]}
    />
    ${(resultado.avisos || []).map(
      (aviso, indice) => html`<div className="aviso" key=${indice}><p>${frase(aviso)}</p></div>`,
    )}
    <${LosTraspasos} traspasos=${resultado.traspasos || []} textos=${textos} />
  `;
}

// ==========================================================================
// La lista: subir el fichero, los movimientos y lo que queda por cuadrar
// ==========================================================================

/**
 * La subida del fichero: **leer no guarda nada**.
 *
 * El campo del fichero lleva su `id` (`banco-fichero`) y **no es controlado a propósito**: `app.js` lee
 * de ahí el fichero que el agricultor ha elegido y lo **guarda en su estado** al leerlo. Hace falta que lo
 * guarde, porque repintar la pantalla borra la casilla del fichero —lo elegido solo vive en el
 * `<input>`— y al apuntar hay que volver a mandar el mismo fichero. Eso ya pasó una vez en este programa,
 * con el cuaderno de la Junta, y está contado en `AGENTS.md`.
 */
function LaSubida({
  textos = {},
  cuentas = [],
  perfiles = [],
  cuentaElegida = "",
  perfilElegido = "",
  leyendo = false,
  ficheroElegido = "",
}) {
  const b = textos.bancos || {};
  return html`
    <h2>${frase(b.subir_titulo)}</h2>
    <p className="pista">${frase(b.subir_explica)}</p>
    <p className="pista-campo">${frase(b.nada_se_apunta)}</p>

    <div className="campo">
      <label htmlFor="banco-fichero">${frase(b.fichero)}</label>
      <p className="pista-campo">${frase(b.fichero_pista)}</p>
      <input id="banco-fichero" type="file" accept=".csv,text/csv" />
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
      id="banco-cuenta"
      etiqueta=${b.cuenta}
      pista=${b.cuenta_pista}
      opciones=${cuentas}
      elegido=${cuentaElegida}
      vacio=${b.elige_la_cuenta}
    />
    <${Elegir}
      id="banco-perfil"
      etiqueta=${b.perfil}
      pista=${b.perfil_pista}
      opciones=${perfiles}
      elegido=${perfilElegido}
      vacio=${b.sin_perfil}
    />

    <div className="barra-acciones">
      <${Boton}
        etiqueta=${leyendo ? b.leyendo : b.leer_el_extracto}
        accion="banco-leer"
        clase=""
      />
      <${BotonSencillo} etiqueta=${b.anadir_una_cuenta} accion="banco-cuenta-nueva" clase="boton-claro" />
      <${BotonSencillo} etiqueta=${b.anadir_un_perfil} accion="banco-perfil-nuevo" clase="boton-claro" />
    </div>
  `;
}

/**
 * Un movimiento ya apuntado, en el móvil: su día, su concepto, su importe y **lo que le queda**.
 *
 * Tres cosas que no se pueden saltar, y las tres a la vista:
 *
 *  · **el importe que no consta se enseña como hueco**, con su palabra y con la frase que dice qué hacer
 *    (escribirlo a mano, que es la puerta que existe para eso);
 *  · **el estado se dice con palabras** (`estado_<estado>`), porque el color nunca informa solo;
 *  · **lo que no consta de la línea se dice**, uno por uno (`falta_<clave>`), para que un hueco no
 *    parezca un descuido del programa.
 */
function UnMovimiento({ movimiento = {}, textos = {} }) {
  const b = textos.bancos || {};
  const noConstaElImporte = movimiento.importe === null || movimiento.importe === undefined;
  const noSeSabeElResto =
    movimiento.por_conciliar === null || movimiento.por_conciliar === undefined;
  return html`
    <li>
      <strong>${frase(movimiento.texto_fecha)}</strong>
      <span className="pista-campo"> ${frase(movimiento.concepto)}</span>
      <${Datos}
        filas=${[
          {
            etiqueta: b.importe,
            valor: noConstaElImporte ? b.no_consta : movimiento.texto_importe,
            aviso: noConstaElImporte ? b.sin_importe_aviso : "",
          },
          { etiqueta: b.saldo, valor: movimiento.texto_saldo || b.no_consta },
          { etiqueta: b.su_cuenta, valor: movimiento.cuenta || b.no_consta },
          { etiqueta: b.como_esta, valor: b[`estado_${movimiento.estado}`] },
          { etiqueta: b.imputado, valor: movimiento.texto_imputado },
          {
            // **Lo que le queda por cuadrar lo dice el servidor.** Si no se sabe, es hueco: un `0,00 €`
            // aquí diría que ya está todo cuadrado.
            etiqueta: b.por_conciliar,
            valor: noSeSabeElResto ? b.no_se_sabe : movimiento.texto_por_conciliar,
          },
        ]}
      />
      ${(movimiento.lo_que_falta || []).map(
        (falta, indice) => html`<p className="pista-campo" key=${indice}>${frase(b[`falta_${falta}`])}</p>`,
      )}
      ${
        // Un traspaso entre cuentas propias **no es un ingreso ni un gasto**: se dice aquí, que es donde el
        // agricultor se pregunta por qué ese dinero no cuenta.
        movimiento.es_traspaso_propio ? html`<p className="aviso">${frase(b.es_traspaso)}</p>` : null
      }
      ${
        // Y por qué un movimiento no se puede cuadrar con nada. Sin esto, una lista vacía de propuestas se
        // leería como «no hay nada que cuadrar», que es otra cosa.
        movimiento.se_puede_conciliar || !movimiento.por_que_no
          ? null
          : html`<p className="pista-campo">${frase(b[`por_que_no_${movimiento.por_que_no}`])}</p>`
      }
      ${movimiento.corregido ? html`<p className="pista-campo">${frase(b.corregido_a_mano)}</p>` : null}
      <${Botones}
        botones=${[
          { etiqueta: b.abrir, accion: "banco-abrir", datos: { id: movimiento.id }, clase: "boton-claro" },
        ]}
        barra=${false}
      />
    </li>
  `;
}

/**
 * **Los dos lados de lo que queda por cuadrar**, que es la pregunta de todo el recorrido.
 *
 * De un lado el **dinero del banco sin papel** —cuántos movimientos están sin cuadrar, cuánto ha entrado
 * y cuánto ha salido, y cuántos no traen importe—, con las cuentas del servidor: los movimientos sin
 * importe **se dicen aparte porque no se suman como cero**. Del otro, los **papeles sin dinero**: las
 * facturas y los cobros a los que les falta algo, con lo que les falta. Y se dice **cómo se cuadra**, que
 * es desde la ficha del movimiento, para que la lista de pendientes no sea un callejón sin salida.
 */
function LoQueQuedaPorCuadrar({ pendientes = [], agregados = {}, textos = {} }) {
  const b = textos.bancos || {};
  return html`
    <h2>${frase(b.pendientes_titulo)}</h2>
    <p className="pista-campo">${frase(b.pendientes_explica)}</p>

    <h3>${frase(b.dinero_sin_papel)}</h3>
    <${Datos}
      filas=${[
        { etiqueta: b.sin_conciliar_cuantos, valor: agregados.sin_conciliar },
        { etiqueta: b.entradas, valor: agregados.texto_entradas },
        { etiqueta: b.salidas, valor: agregados.texto_salidas },
        {
          etiqueta: b.sin_importe,
          valor: agregados.importes_que_no_constan,
          aviso: agregados.importes_que_no_constan ? b.sin_importe_explica : "",
        },
      ]}
    />

    <h3>${frase(b.papeles_sin_dinero)}</h3>
    ${
      pendientes.length
        ? html`<ul className="lista">
            ${pendientes.map(
              (papel, indice) => html`
                <li key=${indice}>
                  <strong>${frase(papel.que_es)}</strong>
                  <${Datos}
                    filas=${[
                      { etiqueta: b.de_quien, valor: papel.contraparte || b.no_consta },
                      { etiqueta: b.referencia, valor: papel.referencia || b.no_consta },
                      { etiqueta: b.fecha, valor: papel.texto_fecha || b.no_consta },
                      {
                        etiqueta: b.importe,
                        valor:
                          papel.importe === null || papel.importe === undefined
                            ? b.no_consta
                            : papel.texto_importe,
                      },
                      {
                        // De un papel cuyo pendiente no se sabe, el servidor **no lo pone en esta lista**:
                        // no se sabe cuánto le falta, y ponerlo con cero sería decir que está pagado.
                        etiqueta: b.le_falta,
                        valor:
                          papel.pendiente === null || papel.pendiente === undefined
                            ? b.no_se_sabe
                            : papel.texto_pendiente,
                      },
                    ]}
                  />
                </li>
              `,
            )}
          </ul>`
        : html`<div className="aviso">${frase(b.sin_pendientes)}</div>`
    }
    <p className="pista-campo">${frase(b.como_se_cuadra)}</p>
  `;
}

/**
 * La pantalla del banco: **el extracto y la conciliación** (S14, `#/cuentas/bancos`).
 *
 * Propiedades (todas preparadas por `app.js`, que es quien tiene los datos y el vocabulario):
 *
 *  - `textos`: `{bancos, acciones, tabla}` del servidor. Aquí no hay ni una frase escrita.
 *  - `cuentas`: `[{valor, texto}]` — las cuentas de la casa, para decir de cuál es el extracto.
 *  - `perfiles`: `[{valor, texto}]` — las formas de escribir que ya se dijeron, una vez.
 *  - `cuentaElegida`, `perfilElegido`: lo que está elegido ahora (el valor de su desplegable).
 *  - `ficheroElegido`: el nombre del fichero que se leyó, para que se vea que sigue ahí.
 *  - `leyendo`, `importando`, `guardando`: lo que está en marcha, y se dice en pantalla.
 *  - `vistaPrevia`: lo que contestó `POST /api/bancos/extractos/vista-previa` — **no ha guardado nada**.
 *  - `resultado`: lo que contestó `POST /api/bancos/extractos/importar`.
 *  - `movimientos`: `items` de `GET /api/bancos/movimientos`, con su estado y lo que les queda.
 *  - `agregados`: sus cuentas (entradas, salidas, sin cuadrar y sin importe), del servidor.
 *  - `resumen`: el pie de la lista ya compuesto («Tienes 7 movimientos»), o vacío.
 *  - `tabla`: la tabla del ordenador, preparada por `app.js`, o `null`.
 *  - `filtro`, `estado`: el buscador y el estado que se está mirando.
 *  - `pendientes`: `GET /api/bancos/pendientes` — los papeles a los que les falta dinero.
 *  - `formulario`: el formulario abierto (una cuenta o la forma de escribir del banco), o `null`.
 *  - `error`, `aviso`: lo que ha dicho el servidor cuando ha ido mal, y lo bueno.
 */
export function PantallaDeLosBancos({
  textos = {},
  cuentas = [],
  perfiles = [],
  cuentaElegida = "",
  perfilElegido = "",
  ficheroElegido = "",
  leyendo = false,
  importando = false,
  guardando = false,
  vistaPrevia = null,
  resultado = null,
  movimientos = [],
  agregados = {},
  resumen = "",
  tabla = null,
  filtro = "",
  estado = "",
  pendientes = [],
  formulario = null,
  error = "",
  aviso = "",
}) {
  const b = textos.bancos || {};
  const acciones = textos.acciones || {};
  const sinCuentas = !(cuentas || []).length;
  // Los cuatro estados que puede mirar el agricultor, con **la palabra del servidor** (no se escribe aquí
  // ninguna). Y `no_se_puede_conciliar` **no es** «sin cuadrar»: uno dice «se puede y no lo has hecho» y
  // el otro «no se puede, y aquí está el porqué».
  const estados = ["sin_conciliar", "conciliado_en_parte", "conciliado", "no_se_puede_conciliar"];
  return html`
    <h1>${frase(b.titulo)}</h1>
    <p className="pista">${frase(b.explica)}</p>
    ${error ? html`<${AvisoDeError} texto=${error} />` : null}
    ${aviso ? html`<div className="aviso">${frase(aviso)}</div>` : null}

    ${formulario ? html`<${Formulario} formulario=${formulario} guardando=${guardando} />` : null}

    ${
      // **Un aviso nunca deja sin salida** (regla de la casa): sin ninguna cuenta dada de alta no se puede
      // subir un extracto, así que el aviso trae el botón que la da de alta.
      sinCuentas
        ? html`
            <div className="aviso">
              <p>${frase(b.sin_cuentas)}</p>
              <div className="barra-acciones">
                <${Boton} etiqueta=${b.anadir_una_cuenta} accion="banco-cuenta-nueva" clase="" />
              </div>
            </div>
          `
        : html`
            <${LaSubida}
              textos=${textos}
              cuentas=${cuentas}
              perfiles=${perfiles}
              cuentaElegida=${cuentaElegida}
              perfilElegido=${perfilElegido}
              leyendo=${leyendo}
              ficheroElegido=${ficheroElegido}
            />
          `
    }

    ${
      vistaPrevia
        ? html`<${LaVistaPrevia} vistaPrevia=${vistaPrevia} textos=${textos} importando=${importando} />`
        : null
    }
    ${resultado ? html`<${LoQueSeHaApuntado} resultado=${resultado} textos=${textos} />` : null}

    <h2>${frase(b.movimientos_titulo)}</h2>
    <p className="pista-campo">${frase(b.movimientos_explica)}</p>

    <div className="campo">
      <label htmlFor="banco-buscar">${frase(b.buscar)}</label>
      <p className="pista-campo">${frase(b.buscar_pista)}</p>
      <input id="banco-buscar" type="text" defaultValue=${frase(filtro)} />
    </div>
    <${Elegir}
      id="banco-estado"
      etiqueta=${b.estado}
      opciones=${estados.map((clave) => ({ valor: clave, texto: b[`estado_${clave}`] }))}
      elegido=${estado}
      vacio=${b.todos_los_estados}
    />
    <div className="barra-acciones">
      <${BotonSencillo} etiqueta=${b.buscar_boton} accion="banco-buscar" clase="boton-claro" />
      <${BotonSencillo} etiqueta=${b.ver_todo} accion="banco-ver-todos" clase="boton-claro" />
      <${Boton} etiqueta=${b.exportar} pista=${b.exportar_pista} accion="banco-exportar" clase="boton-claro" />
    </div>

    ${resumen ? html`<p className="cuantas">${frase(resumen)}</p>` : null}

    ${
      // **La tabla del ordenador y la lista del móvil son la misma lista**, y las dos se pintan: el CSS
      // enseña una u otra según el ancho (`.solo-escritorio` y `.solo-movil`).
      tabla ? html`<div className="solo-escritorio tabla-scroll"><${Tabla} tabla=${tabla} /></div>` : null
    }

    ${
      movimientos.length
        ? html`<ul className="lista solo-movil">
            ${movimientos.map(
              (movimiento, indice) =>
                html`<${UnMovimiento} key=${indice} movimiento=${movimiento} textos=${textos} />`,
            )}
          </ul>`
        : html`<div className="aviso">${frase(filtro || estado ? b.sin_resultados : b.movimientos_vacio)}</div>`
    }

    <${LoQueQuedaPorCuadrar} pendientes=${pendientes} agregados=${agregados} textos=${textos} />

    <div className="barra-acciones">
      <${BotonSencillo} etiqueta=${acciones.volver || ""} accion="ir-inicio" clase="" />
    </div>
  `;
}

// ==========================================================================
// La ficha de un movimiento: contra qué papel va
// ==========================================================================

/**
 * Un papel al que se le va a apuntar dinero, con su nombre y su importe.
 *
 * El servidor manda de una imputación **la clase, el identificador y el importe**, y nada más, porque eso
 * es lo que se guarda. El nombre del papel se busca entre los pendientes que vienen en la misma
 * respuesta: sin eso, el agricultor leería «factura_emitida:3», que es un dato del programa y no el
 * nombre de su factura. Si no se encuentra, **se dice** en vez de enseñar el identificador a secas.
 */
function UnPapelApuntado({ imputacion = {}, pendientes = [], textos = {} }) {
  const b = textos.bancos || {};
  const clave = `${imputacion.clase}:${imputacion.documento_id}`;
  const papel = (pendientes || []).find((uno) => `${uno.clase}:${uno.documento_id}` === clave);
  if (!papel) return html`<p className="pista-campo">${frase(b.papel_desconocido)}</p>`;
  return html`
    <span className="tarjeta-fila">
      <span className="tarjeta-fila-etiqueta">${frase(papel.que_es)}</span>
      <span className="tarjeta-fila-valor">${frase(papel.contraparte || "")}</span>
      <span className="tarjeta-fila-valor">${frase(papel.referencia || "")}</span>
      <span className="tarjeta-fila-valor">${frase(imputacion.texto_importe)}</span>
    </span>
  `;
}

/**
 * Una propuesta de conciliación, **con su porqué y con lo que se apuntaría**.
 *
 * Las tres cosas que la hacen revisable, y las tres vienen del servidor: **cómo cuadra** (exacta,
 * agrupada o parcial), **por qué** («la referencia está en el concepto», «el importe cuadra exacto») y
 * **a qué papeles y cuánto** de cada uno. El botón lleva el **índice** de la propuesta, no los papeles:
 * `app.js` coge esa misma propuesta —la que pidió a `/propuestas`— y manda sus imputaciones tal cual, así
 * que lo que se apunta es **exactamente lo que el agricultor está viendo** en este bloque.
 *
 * El índice es la posición en la lista del servidor, y por eso las propuestas se pintan **en el orden en
 * que llegan**: ordenarlas aquí haría que el botón apuntara a otro papel, que es el peor fallo posible de
 * esta pantalla. Hay una prueba que lo comprueba.
 */
function UnaPropuesta({ propuesta = {}, indice = 0, pendientes = [], textos = {} }) {
  const b = textos.bancos || {};
  return html`
    <li>
      <strong>${frase(b[`propuesta_${propuesta.tipo}`])}</strong>
      <${Datos}
        filas=${[
          { etiqueta: b.se_apuntaria, valor: propuesta.texto_total },
          { etiqueta: b.quedaria_sin_apuntar, valor: propuesta.texto_sobrante },
        ]}
      />
      <p className="pista-campo">${frase(b.porque_titulo)}</p>
      <ul className="lista">
        ${(propuesta.porque || []).map(
          (motivo, numero) => html`<li key=${"m" + numero}><p>${frase(motivo)}</p></li>`,
        )}
      </ul>
      <p className="pista-campo">${frase(b.a_que_papeles)}</p>
      <ul className="lista">
        ${(propuesta.imputaciones || []).map(
          (imputacion, numero) => html`
            <li key=${"i" + numero}>
              <${UnPapelApuntado} imputacion=${imputacion} pendientes=${pendientes} textos=${textos} />
            </li>
          `,
        )}
      </ul>
      <${Botones}
        botones=${[
          {
            etiqueta: b.apuntar_esta,
            accion: "banco-conciliar-propuesta",
            datos: { indice },
            principal: true,
            sencillo: true,
          },
        ]}
        barra=${false}
      />
    </li>
  `;
}

/** Lo que ha quedado apuntado a papeles (o lo que ha vuelto a quedar pendiente al deshacer). */
function LoConciliado({ resultado = null, deshecho = false, pendientes = [], textos = {} }) {
  const b = textos.bancos || {};
  if (!resultado) return null;
  const papeles = resultado.conciliaciones || [];
  return html`
    <h2>${frase(deshecho ? b.lo_devuelto_titulo : b.lo_conciliado_titulo)}</h2>
    ${
      papeles.length
        ? html`<ul className="lista">
            ${papeles.map(
              (papel, indice) => html`
                <li key=${indice}>
                  <${UnPapelApuntado} imputacion=${papel} pendientes=${pendientes} textos=${textos} />
                </li>
              `,
            )}
          </ul>`
        : null
    }
    ${(resultado.avisos || []).map(
      (aviso, indice) => html`<div className="aviso" key=${indice}><p>${frase(aviso)}</p></div>`,
    )}
  `;
}

/**
 * La ficha de un movimiento del banco: **contra qué papel va** (S14, `#/cuentas/bancos/<id>`).
 *
 * Es la pantalla de las cinco cosas que se pueden hacer con un movimiento ya apuntado:
 *
 *  1. **ver qué es** y cómo está, con lo que le queda por cuadrar y lo que no consta de él;
 *  2. **cuadrarlo** con una de las propuestas del servidor, o a mano con un papel de la lista;
 *  3. **deshacerlo**, que **no borra el movimiento**: el banco ya movió ese dinero; lo que se deshace es a
 *     qué papeles estaba apuntado, y queda dicho quién y cuándo;
 *  4. **decir que es un traspaso** entre dos cuentas propias (A07), para que ese dinero no cuente como
 *     ingreso ni como gasto, o **quitar** ese vínculo;
 *  5. **escribir a mano el importe que no consta**, que es la puerta que existe para eso. Con una regla
 *     que se dice en pantalla: si ya hay dinero apuntado a un papel, primero hay que deshacerlo.
 *
 * Y **no ofrece crear nada**: ni un gasto, ni una factura, ni un cobro. Conciliar escribe un vínculo con
 * un papel que ya existe, y ese es el motivo de que la regla «un pago conciliado no crea un segundo
 * gasto» no se pueda romper desde aquí.
 *
 * Propiedades (preparadas por `app.js`):
 *
 *  - `textos`: `{bancos, acciones}` del servidor.
 *  - `movimiento`: el movimiento, con su estado y lo que le queda (y sus `texto_*` ya escritos).
 *  - `propuestas`: lo que contestó `GET /movimientos/<id>/propuestas`, **en su orden**.
 *  - `pendientes`: los papeles a los que se les puede apuntar dinero (para saber cómo se llaman).
 *  - `papeles`: `[{valor, texto}]` — esos mismos, para elegir uno a mano (`banco-papel`).
 *  - `parejas`: `[{valor, texto}]` — los movimientos de **otras cuentas tuyas**, para atar el traspaso.
 *  - `formulario`: la corrección del importe abierta, o `null`.
 *  - `resultado`: lo que contestó la última conciliación o el último deshacer; `deshecho` dice cuál.
 *  - `guardando`, `cargando`, `error`, `aviso`.
 */
export function PantallaDeUnMovimiento({
  textos = {},
  movimiento = {},
  propuestas = [],
  pendientes = [],
  papeles = [],
  parejas = [],
  formulario = null,
  resultado = null,
  deshecho = false,
  guardando = false,
  cargando = false,
  error = "",
  aviso = "",
}) {
  const b = textos.bancos || {};
  const acciones = textos.acciones || {};
  const noConstaElImporte = movimiento.importe === null || movimiento.importe === undefined;
  const noSeSabeElResto =
    movimiento.por_conciliar === null || movimiento.por_conciliar === undefined;
  // Que haya dinero apuntado lo dice **el estado del servidor** (`conciliado` y `conciliado_en_parte` son
  // los dos únicos en los que hay algo imputado): la pantalla no compara importes para averiguarlo.
  const hayAlgoApuntado = movimiento.estado === "conciliado" || movimiento.estado === "conciliado_en_parte";
  return html`
    <h1>${frase(b.ficha_titulo)}</h1>
    <p className="pista">${frase(movimiento.concepto || "")}</p>
    ${error ? html`<${AvisoDeError} texto=${error} />` : null}
    ${aviso ? html`<div className="aviso">${frase(aviso)}</div>` : null}
    ${cargando ? html`<p className="pista">${frase(b.buscando)}</p>` : null}

    <${Datos}
      filas=${[
        { etiqueta: b.fecha, valor: movimiento.texto_fecha || b.no_consta },
        { etiqueta: b.su_cuenta, valor: movimiento.cuenta || b.no_consta },
        { etiqueta: b.referencia, valor: movimiento.referencia || b.no_consta },
        {
          etiqueta: b.importe,
          valor: noConstaElImporte ? b.no_consta : movimiento.texto_importe,
          aviso: noConstaElImporte ? b.sin_importe_aviso : "",
        },
        { etiqueta: b.saldo, valor: movimiento.texto_saldo || b.no_consta },
        { etiqueta: b.como_esta, valor: b[`estado_${movimiento.estado}`] },
        { etiqueta: b.imputado, valor: movimiento.texto_imputado },
        {
          etiqueta: b.por_conciliar,
          valor: noSeSabeElResto ? b.no_se_sabe : movimiento.texto_por_conciliar,
        },
      ]}
    />
    ${(movimiento.lo_que_falta || []).map(
      (falta, indice) => html`<p className="pista-campo" key=${indice}>${frase(b[`falta_${falta}`])}</p>`,
    )}
    ${movimiento.corregido ? html`<p className="pista-campo">${frase(b.corregido_a_mano)}</p>` : null}
    ${movimiento.es_traspaso_propio ? html`<p className="aviso">${frase(b.es_traspaso)}</p>` : null}

    <${LoConciliado}
      resultado=${resultado}
      deshecho=${deshecho}
      pendientes=${pendientes}
      textos=${textos}
    />

    ${
      // **Lo que está apuntado y lo que se puede deshacer.** Y la frase que explica que deshacer no borra
      // nada: es la regla del contrato, y hay que poder leerla **antes** de pulsar.
      hayAlgoApuntado
        ? html`
            <h2>${frase(b.deshacer_titulo)}</h2>
            <p className="pista-campo">${frase(b.deshacer_explica)}</p>
            <${Datos} filas=${[{ etiqueta: b.imputado, valor: movimiento.texto_imputado }]} />
            <div className="barra-acciones">
              <${Boton}
                etiqueta=${b.deshacer}
                accion="banco-deshacer"
                datos=${{ id: movimiento.id }}
                clase="boton-claro"
              />
            </div>
          `
        : html`<p className="pista-campo">${frase(b.nada_que_deshacer)}</p>`
    }

    <h2>${frase(b.propuestas_titulo)}</h2>
    <p className="pista-campo">${frase(b.propuestas_explica)}</p>
    ${
      movimiento.se_puede_conciliar || !movimiento.por_que_no
        ? null
        : html`<div className="aviso"><p>${frase(b[`por_que_no_${movimiento.por_que_no}`])}</p></div>`
    }
    ${
      propuestas.length
        ? html`<ul className="lista">
            ${propuestas.map(
              (propuesta, indice) => html`
                <${UnaPropuesta}
                  key=${indice}
                  propuesta=${propuesta}
                  indice=${indice}
                  pendientes=${pendientes}
                  textos=${textos}
                />
              `,
            )}
          </ul>`
        : html`<div className="aviso">${frase(b.propuestas_vacio)}</div>`
    }

    ${
      // Apuntarlo a mano: el papel lo elige el agricultor de la lista y, si solo le va a apuntar una parte,
      // escribe cuánto. Si lo deja en blanco, el servidor reparte lo que quepa **por orden, del papel más
      // antiguo al más nuevo** —y eso se dice, porque es lo que hace que no haya céntimos perdidos—.
      movimiento.se_puede_conciliar && papeles.length
        ? html`
            <h3>${frase(b.a_mano_titulo)}</h3>
            <p className="pista-campo">${frase(b.a_mano_explica)}</p>
            <${Elegir}
              id="banco-papel"
              etiqueta=${b.papel}
              opciones=${papeles}
              elegido=""
              vacio=${b.elige_el_papel}
            />
            <${Campo}
              id="banco-cantidad"
              etiqueta=${b.cantidad}
              tipo="numero"
              valor=""
              sufijo=${b.cantidad_pista}
            />
            <div className="barra-acciones">
              <${Boton} etiqueta=${b.apuntar} accion="banco-conciliar-a-mano" clase="" />
            </div>
          `
        : null
    }
    ${
      // Y si este dinero no puede ir a ningún papel porque no hay ninguno apuntado, se dice **y se dice qué
      // hacer**, en vez de dejar un desplegable vacío.
      movimiento.se_puede_conciliar && !papeles.length
        ? html`<div className="aviso">${frase(b.sin_papeles)}</div>`
        : null
    }

    <h2>${frase(b.traspaso_titulo)}</h2>
    <p className="pista-campo">${frase(b.traspaso_explica)}</p>
    ${
      movimiento.es_traspaso_propio
        ? html`
            <p className="aviso">${frase(b.traspaso_ya_esta)}</p>
            <div className="barra-acciones">
              <${Boton}
                etiqueta=${b.traspaso_quitar}
                accion="banco-traspaso-quitar"
                datos=${{ id: movimiento.id }}
                clase="boton-claro"
              />
            </div>
          `
        : parejas.length
          ? html`
              <${Elegir}
                id="banco-pareja"
                etiqueta=${b.traspaso_el_otro}
                pista=${b.traspaso_pista}
                opciones=${parejas}
                elegido=""
                vacio=${b.traspaso_elige}
              />
              <div className="barra-acciones">
                <${Boton} etiqueta=${b.traspaso_atar} accion="banco-traspaso-atar" clase="" />
              </div>
            `
          : html`<p className="pista-campo">${frase(b.sin_parejas)}</p>`
    }

    ${
      // **La puerta para escribir el importe que no consta.** Existe porque el programa dice que no consta y
      // tiene que haber dónde ponerlo; y se ofrece siempre, porque un importe mal leído también se
      // corrige. Si ya hay dinero apuntado, el servidor dirá que hay que deshacerlo primero, con su
      // instrucción.
      formulario
        ? html`<${Formulario} formulario=${formulario} guardando=${guardando} />`
        : html`
            <div className="barra-acciones">
              <${Boton}
                etiqueta=${b.corregir}
                accion="banco-corregir"
                datos=${{ id: movimiento.id }}
                clase="boton-claro"
              />
            </div>
          `
    }

    <div className="barra-acciones">
      <${BotonSencillo} etiqueta=${b.volver_a_los_movimientos} accion="banco-ver" clase="" />
      <${BotonSencillo} etiqueta=${acciones.volver || ""} accion="ir-inicio" clase="" />
    </div>
  `;
}

// ==========================================================================
// Los elementos ya montados
// ==========================================================================

/** El elemento de React de la pantalla del banco, ya con sus propiedades puestas. */
export function pantallaDeLosBancos(propiedades) {
  return html`
    <${PantallaDeLosBancos}
      textos=${propiedades.textos}
      cuentas=${propiedades.cuentas}
      perfiles=${propiedades.perfiles}
      cuentaElegida=${propiedades.cuentaElegida}
      perfilElegido=${propiedades.perfilElegido}
      ficheroElegido=${propiedades.ficheroElegido}
      leyendo=${propiedades.leyendo}
      importando=${propiedades.importando}
      guardando=${propiedades.guardando}
      vistaPrevia=${propiedades.vistaPrevia}
      resultado=${propiedades.resultado}
      movimientos=${propiedades.movimientos}
      agregados=${propiedades.agregados}
      resumen=${propiedades.resumen}
      tabla=${propiedades.tabla}
      filtro=${propiedades.filtro}
      estado=${propiedades.estado}
      pendientes=${propiedades.pendientes}
      formulario=${propiedades.formulario}
      error=${propiedades.error}
      aviso=${propiedades.aviso}
    />
  `;
}

/** Y el de la ficha de un movimiento del banco. */
export function pantallaDeUnMovimiento(propiedades) {
  return html`
    <${PantallaDeUnMovimiento}
      textos=${propiedades.textos}
      movimiento=${propiedades.movimiento}
      propuestas=${propiedades.propuestas}
      pendientes=${propiedades.pendientes}
      papeles=${propiedades.papeles}
      parejas=${propiedades.parejas}
      formulario=${propiedades.formulario}
      resultado=${propiedades.resultado}
      deshecho=${propiedades.deshecho}
      guardando=${propiedades.guardando}
      cargando=${propiedades.cargando}
      error=${propiedades.error}
      aviso=${propiedades.aviso}
    />
  `;
}
