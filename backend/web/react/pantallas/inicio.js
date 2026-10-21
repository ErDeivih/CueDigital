/*
 * inicio.js — La pantalla de inicio, escrita en React.
 *
 * POR QUÉ ESTA PANTALLA ESTÁ EN REACT
 *
 * Es el paso piloto de la migración (la guía está en `docs/REACT.md`). Se empieza por la
 * pantalla de inicio porque es la que más se ve —es la primera que abre el agricultor todos
 * los días— y porque es la única que no tiene campos de formulario que leer del DOM. Si el
 * piloto sale caro, se para aquí.
 *
 * Y React entra **SIN COMPILAR**: los ficheros de `web/vendor` dejan `React` y `htm` en los
 * globales del navegador, y `htm` permite escribir las plantillas sin JSX. No hay `npm`, ni
 * un paso de compilación, ni una dependencia de red: donde corre esto no hay Node, y el
 * agricultor tiene que poder abrir la aplicación en el campo, sin cobertura.
 *
 * QUÉ SE CONSERVA A PROPÓSITO (esto es lo que hace que la pantalla siga funcionando igual)
 *
 *  1. Los `data-accion` y los demás `data-*` salen **exactamente iguales** que los de la
 *     interfaz vieja (`boton()` en `app.js`). Los clics no se enganchan botón a botón: hay un
 *     solo manejador delegado en `document` que lee `elemento.dataset.accion`. Si un
 *     `data-accion` cambia, el botón deja de hacer nada.
 *  2. Las mismas `className` que ya existen en `estilos.css` (`.boton`, `.boton-principal`,
 *     `.boton-claro`, `.boton-secundario`, `.texto`, `.icono`, `.pista-boton`, `.aviso`,
 *     `.pista`, `.pista-campo`). Aquí no hay ni un `style={{…}}`: los colores viven solo en
 *     el `:root` de `estilos.css`.
 *  3. Los textos NO se escriben aquí. Llegan por propiedades, y vienen de `textos.py` a
 *     través de `GET /api/interfaz`. Lo único escrito a mano en este fichero son los iconos
 *     (los emoji), que ya estaban en el JavaScript antes y no son una frase para nadie.
 *  4. **Nada de `esc()`.** React escapa solo: si se escapara aquí, el agricultor leería
 *     `&amp;` en pantalla.
 *  5. El orden de los seis botones es el que traiga el servidor, y no se toca. Hay una prueba
 *     que lo blinda (`backend/tests/test_interfaz.py`).
 *
 * El componente es PURO: no llama a `fetch`, no lee `localStorage` y no toca el DOM. Todo lo
 * que necesita le llega por propiedades, y por eso se puede probar sin navegador (ver
 * `backend/tests_js/react.test.js`).
 */

/**
 * De dónde salen las piezas que usa esta pantalla.
 *
 * Al principio este fichero traía **su propia copia** de la plantilla `html`, del `frase()` y del botón
 * (fue el paso piloto de la migración, cuando todavía no había nada compartido). Ya no: el botón, la
 * flecha, el cuadro del icono y su dibujo son **el mismo de toda la aplicación** (`componentes.js`), y
 * así la pantalla de inicio no puede quedar distinta de las demás. El `html` de `componentes.js` ya trae
 * el respaldo para cuando los ficheros de React de `vendor/` no han llegado, que era el motivo por el que
 * aquí había una copia con su propio `try`.
 */
import { Boton, frase, html } from "../componentes.js";
// *`rellena` vive en el nucleo, que es donde esta escrita **una sola vez**.* 
import { rellena } from "../../nucleo.js";
import { PanelDeMando } from "../piezas/panel_de_mando.js";

/**
 * Un botón de la pantalla, con la forma de la casa.
 *
 * Se conserva el nombre y las propiedades (`ir` y `tipo` son los dos `data-*` de esta pantalla) porque
 * lo usan las pruebas del componente; por dentro es el `Boton` de siempre, con su flecha y su cuadro de
 * icono. **Los `data-*` que no tocan no se escriben**: `datosDelBoton()` quita los vacíos.
 */
export function BotonDeInicio({ etiqueta, pista, icono, accion, ir, tipo, clase }) {
  return html`
    <${Boton}
      etiqueta=${etiqueta}
      pista=${pista}
      icono=${icono}
      accion=${accion}
      datos=${{ ir, tipo }}
      clase=${clase || ""}
    />
  `;
}

/**
 * El aviso que desbloquea al agricultor nuevo.
 *
 * Sin esto, quien acaba de darse de alta ve seis botones que no llevan a ninguna parte: todos
 * necesitan una parcela, y no hay ninguna. Es mejor decirlo antes de que los pulse y darle el
 * botón que lo arregla. Va antes de la pregunta a propósito: es lo primero que tiene que leer.
 */
export function BloqueAntesDeEmpezar({ maestros = {} }) {
  // El aviso y el botón se devuelven **seguidos**, sin envolverlos en nada: es una lista de elementos y
  // React los pinta uno detrás de otro. (Antes iban dentro de un `React.Fragment`, que ya no hace falta:
  // la plantilla `html` de `componentes.js` no sabe hacer fragmentos —ver `docs/REACT.md` §4 bis— y esta
  // es la forma que usa toda la aplicación.)
  return html`
    <div className="aviso">
      <strong>${frase(maestros.antes_de_empezar)}</strong>
      <p>${frase(maestros.falta_parcela)}</p>
    </div>
    <${BotonDeInicio}
      etiqueta=${maestros.anadir_primera_parcela}
      icono="📍"
      accion="anadir-maestro"
      tipo="parcela"
      clase="boton-principal"
    />
  `;
}

/**
 * La pantalla de inicio.
 *
 * Propiedades (todas obligatorias salvo las que tienen valor por defecto):
 *
 *  - `textos`: `{ inicio, maestros, dictado }`, tal y como los sirve `/api/interfaz`. Es la
 *    única fuente de frases: aquí no hay ni una escrita a mano.
 *  - `nombre`: el del titular, o vacío. Sale al lado del saludo.
 *  - `campana`: la campaña en curso (`{ anio }`) o nada. El año sale al lado del saludo.
 *  - `hayParcelas`: si no hay ninguna, se enseña el aviso que desbloquea al agricultor nuevo.
 *  - `hayUltimo`: si hay un último apunte, se ofrece repetirlo. Si no, se dice que no hay nada.
 *  - `sinUltimo`: la frase que se enseña cuando no hay nada que repetir. La elige quien llama,
 *    porque hay dos casos muy distintos —una finca sin ningún apunte y una finca con apuntes
 *    pero sin tratamientos— y decirle «todavía no has apuntado nada» a quien tiene el cuaderno
 *    lleno es mentirle. Si no llega, se usa la frase de «no hay nada apuntado».
 *  - `mando`: lo que necesita el **panel de mando del ordenador** (fase 4), ya preparado por `app.js`, o
 *    `null`. Cuando llega, en pantalla ancha se enseña el panel de mando y **los botones grandes del móvil
 *    se esconden** (`.solo-movil`); en el móvil no cambia nada. Es la misma idea que la tabla y las
 *    tarjetas de una lista: **la misma pantalla, dos formas, en el mismo HTML**, y el CSS decide.
 */
/**
 * **Las metricas de la finca, con lo que hace falta para creerselas** (CRM-11, 17/10/2026).
 *
 * *Un panel no es una pantalla con numeros: es **un numero que se puede defender**.* Cada tarjeta dice:
 *
 *   · **que mide** (su titulo y su pregunta),
 *   · **en que se mide** (su unidad, que es lo que decide si dos se pueden sumar),
 *   · **de donde sale** (su fuente),
 *   · y **cuanto ha mirado** (su cobertura).
 *
 * ***Y lo que no se sabe se dice con su palabra, nunca con un cero***: *`valor` en `null` es «no se sabe»
 * -un cero diria «no hay», que es una afirmacion distinta-.*
 *
 * ***Y el aviso de que no se suman***: *dos cifras en hectareas pueden contestar a preguntas distintas -lo
 * que hay plantado y lo que se trato-, y juntarlas da un numero que no contesta a nada.*
 */
function LasMetricas({ panel = {} }) {
  const t = (panel && panel.textos) || {};
  const las = (panel && panel.las_metricas) || [];
  const sinComprobar = new Set(((panel && panel.sin_comprobar) || []).map((una) => una.clave));
  if (!las.length) return null;
  return html`
    <section className="las-metricas">
      <h2>${frase(t.titulo)}</h2>
      <p className="pista">${frase(t.explica)}</p>
      <ul className="lista">
        ${las.map(
          (una) => html`
            <li key=${una.clave} className="fila-dato" data-metrica=${una.clave} data-se-sabe=${una.valor !== null}>
              <span className="tabla-dato">${frase(una.titulo)}</span>
              <span className="tabla-numero"
                >${una.texto_valor || (
                  // ***`null` es «no se sabe», y NUNCA se pinta como un cero.***
                  una.valor === null || una.valor === undefined
                    ? // ***Y LA UNIDAD SE DICE TAMBIEN CUANDO NO SE SABE*** (CRM-11, 17/10/2026): *es lo
                      // que dice **si esa cifra se puede sumar con otra**, y esconderla justo cuando el
                      // numero no esta deja al agricultor sin la mitad de la informacion. Asi lo encontro
                      // el recorrido: la metrica sin valor salia como «No se sabe» y **sin su unidad**.*
                      `${frase(t.no_se_sabe)} · ${una.unidad || ""}`.trim()
                    : `${una.valor} ${una.unidad || ""}`.trim()
                )}</span
              >
              <span className="tabla-pista"
                >${frase(una.pregunta)}${
                  // *Y de donde sale, que es lo que permite discutir el numero y corregirlo.*
                  una.fuente ? ` · ${frase(una.fuente)}` : ""
                }${
                  // **Y cuanto ha mirado**: *sin eso, un total parece completo aunque le falten cuatro.*
                  una.cobertura && una.cobertura.de
                    ? ` · ${rellena(t.cobertura, { contadas: una.cobertura.contadas, de: una.cobertura.de })}`
                    : ""
                }${
                  // ***Y lo que no se puede dar por bueno se dice***: «sin cumplimiento global que tape una
                  // regla critica no comprobada».
                  sinComprobar.has(una.clave) ? ` · ${frase(t.sin_fuente)}` : ""
                }</span
              >
            </li>
          `,
        )}
      </ul>
      <p className="pista-campo">${frase(t.no_se_suman)}</p>
    </section>
  `;
}

export function PantallaInicio({
  textos = {},
  nombre = "",
  campana = null,
  hayParcelas = false,
  hayUltimo = false,
  sinUltimo = "",
  mando = null,
  // ***Las metricas de la finca*** (CRM-11, 17/10/2026), tal y como las devuelve `GET /api/panel`.
  //
  // ***Y `null` NO es una lista vacia***, que es la distincion de la casa: *`null` es «**todavia no se han
  // pedido**» -la seccion **no se pinta**- y `[]` seria «se pidieron y no hay ninguna». Sin esa distincion,
  // la pantalla diria «no hay nada» antes de haber preguntado.*
  lasMetricas = null,
}) {
  const inicio = textos.inicio || {};
  const maestros = textos.maestros || {};
  const dictado = textos.dictado || {};
  const botones = Array.isArray(inicio.botones) ? inicio.botones : [];
  const repetir = inicio.repetir || {};

  // El año de la campaña solo se escribe si de verdad se sabe cuál es. Antes, si la campaña
  // venía a medias, en la cabecera se leía « · undefined», que es justo lo que no se quiere
  // delante de un agricultor: aquí, lo que no está, no se enseña.
  const anio = campana && campana.anio !== null && campana.anio !== undefined ? campana.anio : "";
  const titulo =
    frase(inicio.saludo) + (nombre ? `, ${nombre}` : "") + (anio === "" ? "" : ` · ${anio}`);
  // **Apuntar un trabajo, arriba** (decisión de David, 07/10/2026). Medido con
  // `scripts/medir_las_acciones.py`: Inicio ofrecía 41 acciones y solo 3 se veían al entrar —el resto son
  // enlaces de lista, uno por tierra—, así que lo que había que decidir era **qué se viene a hacer al abrir
  // el cuaderno**, y la respuesta es **apuntar un trabajo**. Se sube el botón que ya existe en los botones de
  // Inicio —con **su** texto y **su** acción, sin inventar etiquetas ni acciones nuevas—, y en el ordenador
  // se ve además del panel de mando.
  const elTrabajo = (botones || []).find((uno) => uno.id === "trabajo") || null;

  return html`
    <h1>${titulo}</h1>
    ${
      // La acción que se viene a hacer, **nada más entrar** (ver arriba el porqué).
      elTrabajo
        ? html`<div className="barra-acciones">
            <${BotonDeInicio}
              etiqueta=${elTrabajo.texto}
              pista=${elTrabajo.pista}
              icono=${elTrabajo.icono}
              accion=${elTrabajo.accion}
              ir=${elTrabajo.ir}
              tipo=${elTrabajo.tipo}
            />
          </div>`
        : null
    }
    ${hayParcelas ? null : html`<${BloqueAntesDeEmpezar} maestros=${maestros} />`}
    ${
      // **El panel de mando, solo en el ordenador** (fase 4, 30/09/2026): el estado del año de un vistazo.
      mando
        ? html`<div className="solo-escritorio">
            <${PanelDeMando}
              textos=${textos}
              numeros=${mando.numeros}
              faltantes=${mando.faltantes}
              ultimos=${mando.ultimos}
              apuntar=${mando.apuntar}
              cierre=${mando.cierre}
            />
          </div>`
        : null
    }
    <div className=${mando ? "solo-movil" : ""}>
      <p className="pista">${frase(inicio.pregunta)}</p>
      ${botones.map(
        (boton) => html`
          <${BotonDeInicio}
            key=${boton.id}
            etiqueta=${boton.texto}
            pista=${boton.pista}
            icono=${boton.icono}
            accion="inicio"
            ir=${boton.id}
            clase=${boton.principal ? "boton-principal" : ""}
          />
        `,
      )}
      ${hayUltimo
        ? html`
            <${BotonDeInicio}
              etiqueta=${repetir.texto}
              icono="🔁"
              accion="repetir"
              clase="boton-secundario"
            />
          `
        : html`<p className="pista-campo">${frase(sinUltimo || repetir.vacio)}</p>`}
      <${BotonDeInicio}
        etiqueta=${dictado.titulo}
        pista=${dictado.pista_boton}
        icono="🎤"
        accion="dictado"
        clase="boton-secundario"
      />
      <${BotonDeInicio}
        etiqueta=${maestros.mis_cosas}
        icono="📋"
        accion="mis-cosas"
        clase="boton-claro"
      />
    </div>
    ${lasMetricas ? html`<${LasMetricas} panel=${lasMetricas} />` : null}
  `;
}

/**
 * El elemento de React de la pantalla de inicio, ya con sus propiedades puestas.
 *
 * `app.js` no habla con React: pide el elemento aquí y se lo da a `montar.js`, que es el único
 * sitio que habla con ReactDOM. Así, si los ficheros de React no están, la que falla es esta
 * función (y `montar.js` enseña el aviso), en vez de romperse el arranque entero.
 */
/**
 * El envoltorio del inicio: **el unico sitio por el que pasan las pantallas de React**.
 *
 * ***Y una prop que no se reenvie aqui NO LLEGA al componente*** (CRM-11, 17/10/2026). *Las metricas del panel
 * se anadieron al componente y a `app.js`, y **este envoltorio las tiraba**: la seccion salia en la prueba -que
 * montaba el componente directamente- y **no en la pantalla**.*
 *
 * ***Y no lo cazo ninguna prueba de unidad: lo cazo el recorrido***, que es el que monta lo que monta la
 * aplicacion. *La prueba del panel se corrigio despues para montar este envoltorio, y asi habria cazado ella.*
 *
 * **Y el porque de que este comentario este aqui y no dentro de la plantilla**: *una comilla invertida
 * -`` ` ``- dentro de un `` html`…` `` **cierra la plantilla**, y el fichero deja de compilar. Las explicaciones,
 * fuera.*
 */
export function pantallaDeInicio(propiedades) {
  return html`
    <${PantallaInicio}
      textos=${propiedades.textos}
      nombre=${propiedades.nombre}
      campana=${propiedades.campana}
      hayParcelas=${propiedades.hayParcelas}
      hayUltimo=${propiedades.hayUltimo}
      sinUltimo=${propiedades.sinUltimo}
      mando=${propiedades.mando}
      lasMetricas=${propiedades.lasMetricas}
    />
  `;
}
