/*
 * componentes.js — Las piezas que se repiten en todas las pantallas.
 *
 * POR QUÉ EXISTE ESTE FICHERO
 *
 * En la interfaz vieja había una función `boton()` en `app.js` que montaba el HTML de un botón, y la
 * usaban casi todas las pantallas. Al pasar las pantallas a React, lo primero que aparece es que
 * **cada una necesita el mismo botón**: el icono, el texto, la pista, la clase y los `data-*`. Si
 * cada pantalla se lo escribiera a mano, tendríamos veinte botones parecidos y ninguno igual, y el
 * día que cambie una clase habría que tocar veinte sitios.
 *
 * Así que aquí está **el mismo botón de siempre**, escrito una vez:
 *
 *  - `Boton`: el botón de las listas y de las pantallas. Se le pasa `datos` (un diccionario) y cada
 *    clave se convierte en un `data-` igual que hacía `boton()`: `{tipo: "parcela"}` →
 *    `data-tipo="parcela"`. Eso es lo que lee el manejador de clics delegado de `document`, así que
 *    el atributo tiene que salir **exactamente** igual que antes.
 *  - `boton` (la plantilla `html`): se exporta para las pantallas que necesitan un botón con una
 *    forma que no es la de nadie más. Mejor eso que copiar el de al lado.
 *
 * Y las reglas de siempre, que valen para todos los componentes:
 *
 *  1. **Nada de `esc()`**: React escapa solo.
 *  2. **Nada de `style`**: los colores viven en el `:root` de `estilos.css`.
 *  3. **Ninguna frase escrita aquí**: los textos llegan por propiedades, del servidor.
 */

/** React, tal y como lo ha dejado el fichero de `vendor`. */
function react() {
  const React = globalThis.React;
  if (!React) throw new Error("faltan los ficheros de React de web/vendor");
  return React;
}

/**
 * La plantilla `html` de htm, atada a React.
 *
 * Se arma la primera vez que hace falta y no al cargar el fichero: si los ficheros de `vendor/` no
 * llegaran (un móvil sin cobertura con la caché a medias después de un despliegue), armar esto al
 * importar reventaría, `app.js` no arrancaría y el agricultor se quedaría con una pantalla en
 * blanco. Así, el módulo se puede importar igual y `montar.js` puede enseñar el aviso de emergencia.
 */
let plantilla = null;

export function html(cadenas, ...valores) {
  if (!plantilla) {
    if (typeof globalThis.htm !== "function") {
      throw new Error("faltan los ficheros de React de web/vendor");
    }
    plantilla = globalThis.htm.bind(react().createElement);
  }
  return plantilla(cadenas, ...valores);
}

/** Un texto del servidor, en texto. Lo que no viene, no se escribe. */
export function frase(valor) {
  return valor === null || valor === undefined ? "" : String(valor);
}

/** Las clases de un botón, sin dejar huecos: `.boton` siempre, y luego la suya si la tiene. */
export function clasesDeBoton(clase) {
  return ["boton", clase].filter(Boolean).join(" ");
}

/**
 * Los `data-*` de un botón, tal y como los montaba `boton()` en `app.js`.
 *
 * Un valor vacío o nulo **no se escribe**: así un botón que no lleva `data-tipo` no manda
 * `data-tipo=""`, que el manejador podría leer como un tipo de verdad.
 */
export function datosDelBoton(datos = {}) {
  const salida = {};
  for (const [clave, valor] of Object.entries(datos || {})) {
    if (valor === null || valor === undefined || valor === "") continue;
    salida[`data-${clave}`] = String(valor);
  }
  return salida;
}

/**
 * Los dibujos de los botones, en SVG.
 *
 * POR QUÉ ESTÁN AQUÍ Y NO EN UN FICHERO APARTE
 *
 * Estaban en `iconos.js`, y ese fichero tenía que importar `html` de este —y este, a los iconos—: una
 * **importación circular**. Funciona hasta que un día no (depende de en qué orden se carguen los
 * módulos), así que los iconos viven aquí, que es donde están las demás piezas compartidas. Los usa
 * `Boton` para todos los botones de la aplicación.
 *
 * DE DÓNDE SALEN LOS TRAZOS
 *
 * De los que dibujó Stitch en el rediseño (ronda 76, `docs/stitch/rediseno/`), que son del estilo de
 * [Feather Icons](https://feathericons.com), **licencia MIT**: se pueden usar y copiar. Los tres
 * últimos (`parcela`, `plan`, `firma`) están dibujados con las mismas reglas: rejilla de 24×24, trazo
 * de 2 px, esquinas redondeadas y sin relleno.
 *
 * CÓMO SE ELIGE EL DIBUJO
 *
 * La clave es **el emoji que trae el texto del servidor** (`textos.py`): así cambiar un icono no obliga
 * a tocar los textos, y los emoji siguen siendo la lista de iconos que hay. Si un emoji no tiene
 * dibujo, **se enseña el emoji tal cual** en vez de dejar un hueco: el día que se añada un botón nuevo
 * sale algo, aunque sea el emoji de siempre.
 */
const DIBUJOS = {
  "💧": {
    trazos: ["M12 2v6m0 0L8 5m4 3l4-3M7 11h10l-1 11H8L7 11z"],
    circulos: [[12, 16, 2]],
  },
  "🟤": {
    trazos: ["M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z", "M12 8v8m-4-4h8"],
  },
  "🚜": {
    trazos: ["M7 14h6l4-5h-4l-2-4H7v9zM13 14l2 3"],
    circulos: [
      [7, 17, 3],
      [17, 17, 2],
    ],
  },
  "📖": {
    trazos: [
      "M4 19.5A2.5 2.5 0 0 1 6.5 17H20",
      "M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z",
      "M8 7h8M8 11h8",
    ],
  },
  "🖨️": {
    trazos: [
      "M6 9V2h12v7M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2",
      "M6 14h12v8H6z",
    ],
  },
  "❓": {
    trazos: ["M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3m0 3.5h.01"],
    circulos: [[12, 12, 10]],
  },
  "🔁": {
    trazos: ["M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8", "M3 3v5h5M12 7v5l4 2"],
  },
  "🎤": {
    trazos: [
      "M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z",
      "M19 10v2a7 7 0 0 1-14 0v-2M12 19v4m-4 0h8",
    ],
  },
  "📋": {
    trazos: ["M3 21h18M5 21V7l8-4v18M13 11h8v10M9 9v.01M9 13v.01M9 17v.01M17 15v.01M17 19v.01"],
  },
  "📍": {
    trazos: ["M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0z"],
    circulos: [[12, 10, 3]],
  },
  "🧪": {
    trazos: [
      "M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2",
      "M9 2h6v4H9zM8 12h8M8 16h5",
    ],
  },
  "✍️": {
    trazos: ["M12 20h9", "M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"],
  },
  "✅": { trazos: ["M20 6L9 17l-5-5"] },
  "⬜": { trazos: ["M5 5h14v14H5z"] },
};

/** ¿Hay dibujo para esta clave? */
export function hayDibujo(clave) {
  return Object.prototype.hasOwnProperty.call(DIBUJOS, clave);
}

/** Las claves que tienen dibujo, en orden. Lo usan las pruebas. */
export function clavesConDibujo() {
  return Object.keys(DIBUJOS);
}

/** El dibujo de una clave: el `<svg>` si lo hay, y si no el propio texto (el emoji). */
export function Icono({ clave }) {
  const dibujo = DIBUJOS[clave];
  if (!dibujo) return html`${clave || ""}`;
  return html`
    <svg
      className="dibujo-icono"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      ${(dibujo.trazos || []).map((trazo, indice) => html`<path key=${indice} d=${trazo}></path>`)}
      ${(dibujo.circulos || []).map(
        ([cx, cy, r], indice) => html`<circle key=${"c" + indice} cx=${cx} cy=${cy} r=${r}></circle>`,
      )}
    </svg>
  `;
}

/**
 * El cuadro del icono: el dibujo (o el emoji) con su marco.
 *
 * El `data-icono` lleva la clave con la que se dibujó. No es decoración: **es lo que deja comprobar en
 * las pruebas que el icono de cada botón es el que le toca**, y en el navegador se ve de un vistazo qué
 * dibujo es. Va con `aria-hidden` porque quien usa un lector de pantalla ya oye que es un botón.
 */
function CuadroDelIcono({ icono }) {
  if (!icono) return null;
  return html`
    <span className="icono" aria-hidden="true" data-icono=${icono}>
      <${Icono} clave=${icono} />
    </span>
  `;
}

/**
 * El botón de toda la vida.
 *
 * Propiedades: `etiqueta`, `pista`, `icono`, `accion` (lo que se pone en `data-accion`) y,
 * opcionalmente, `datos` (los demás `data-*`), `clase` y `flecha`.
 *
 * `flecha: false` es para los botones que **no llevan a ninguna parte**: los de las medidas preventivas
 * marcan y desmarcan una cosa en la misma pantalla, y la flecha —que en esta aplicación significa «esto
 * te lleva a otro sitio» (ver `Flecha`)— ahí mentía (ronda 85). El cuadro del icono (✅ / ⬜) ya dice que
 * eso se marca.
 */

// ---------------------------------------------------------------------------
// ***Lo que este usuario PUEDE escribir*** (permisos en servidor **y pantalla**, 18/10/2026)
// ---------------------------------------------------------------------------
//
// ***Y el clasificador ya NO es por sufijos***: *la revision independiente demostro que se quedaba corto con
// **siete** acciones -`contacto-borrar-si` borra, `fusion-hacer` fusiona, `contacto-nota` apunta...-, y «una
// confirmacion puede ser precisamente la operacion destructiva».*
//
// *Ahora se consulta **el inventario**, que esta en `acciones.js` y se hizo mirando **lo que cada accion hace**.
// Aqui solo queda la regla de la pantalla.*
import { escribeEstaAccion, LAS_DE_SESION, LAS_QUE_ESCRIBEN } from "./acciones.js";

export { escribeEstaAccion, LAS_DE_SESION, LAS_QUE_ESCRIBEN };

let puedeEscribir = true;

/** **Dice si este usuario puede escribir.** *Lo pone `app.js` al montar cada pantalla.* */
export function ponerSiSePuedeEscribir(puede) {
  puedeEscribir = puede !== false;
}

/** ***Si hay que esconder ese boton***: *escribe y este usuario no puede escribir.* */
function seEscondeElBoton(accion) {
  return !puedeEscribir && escribeEstaAccion(accion);
}

export function Boton({ etiqueta, pista, icono, accion, datos, clase = "", flecha = true }) {
  // ***Lo que no se puede hacer no se ofrece***: *el boton no sale, en vez de salir y contestar 403.*
  if (seEscondeElBoton(accion)) return null;
  return html`
    <button
      type="button"
      className=${clasesDeBoton(clase)}
      data-accion=${accion}
      ...${datosDelBoton(datos)}
    >
      <${CuadroDelIcono} icono=${icono} />
      <span className="texto">
        <span>${frase(etiqueta)}</span>
        ${pista ? html`<span className="pista-boton">${frase(pista)}</span>` : null}
      </span>
      ${flecha ? html`<${Flecha} />` : null}
    </button>
  `;
}

/**
 * El botón **sencillo**: el texto, su acción y sus datos, sin icono y sin flecha.
 *
 * Existe porque en la aplicación hay dos clases de botón y las dos son de verdad:
 *
 *  - el de casa (`Boton`), con su icono y su flecha, para **los caminos** (lo que lleva a otra
 *    pantalla o a otra pregunta);
 *  - este, para **los atajos**: los de «HOY» y «AYER» que van debajo de una fecha, y los que salen
 *    dentro de un aviso («AÑADIR UN ANÁLISIS»). Un botón con flecha invita a salir de la pantalla, y
 *    estos solo rellenan lo que hay justo encima o abren una cosa concreta.
 *
 * Se conserva **exactamente** la misma forma que tenían en la interfaz vieja (`.boton` más su clase),
 * porque el diseño ya estaba decidido y comprobado.
 *
 * `deshabilitado` es para el botón que **no se puede pulsar todavía, y se ve que no se puede** (ronda 93):
 * el BORRAR de un año del cuaderno que tiene cosas dentro. Un botón apagado sin decir por qué es un botón
 * roto; por eso la pantalla que lo apaga pone al lado la frase que lo explica, y en el mismo sitio.
 */
export function BotonSencillo({ etiqueta, accion, datos, clase = "boton-claro", deshabilitado = false, pista = "" }) {
  // **El mismo criterio que `Boton`**: *este tambien puede llevar una accion que escribe.*
  if (seEscondeElBoton(accion)) return null;
  return html`
    <button
      type="button"
      className=${clasesDeBoton(clase)}
      data-accion=${accion}
      disabled=${deshabilitado ? true : undefined}
      ...${datosDelBoton(datos)}
    >
      ${frase(etiqueta)}
      ${
        // **La pista también cabe en un botón sencillo** (06/10/2026). `Boton` la llevaba desde siempre y
        // este no, así que los botones que van en una lista (`Botones`) no podían decir **qué hacen**:
        // el de «GUARDAR LOS DATOS EN UN FICHERO», por ejemplo, se llevaba el cuaderno entero del año y
        // no lo decía en ninguna parte (el texto existía en el servidor y **no lo pintaba nadie**). Se
        // pinta igual que en `Boton`, para que los dos se lean igual.
        pista ? html`<span className="pista-boton">${frase(pista)}</span>` : null
      }
    </button>
  `;
}

/**
 * La flecha del final del botón.
 *
 * Sale del diseño que generó Stitch (ver `docs/stitch/`): sirve para que se vea de un vistazo que
 * **ese botón lleva a algún sitio**. Va marcada con `aria-hidden` porque quien use un lector de
 * pantalla ya oye que es un botón y leerle «flecha» solo estorba.
 *
 * Se exporta para que las pantallas que montan un botón a mano (las que no usan `Boton`, porque su
 * forma no es la de nadie más) puedan poner **la misma flecha** en vez de copiarla.
 */
export function Flecha() {
  return html`<span className="flecha" aria-hidden="true">→</span>`;
}

/**
 * Un botón de una lista de botones: `sencillo` es «sin icono y sin flecha» y `principal` es la clase.
 *
 * - `sencillo` lo usan los atajos y los botones que ya llevan su emoji dentro del texto (los tres de
 *   abajo de «mi cuaderno», el VOLVER de un aviso de error, las teclas del asistente).
 * - `principal` es la clase: los principales llevan solo `.boton` y los demás `.boton boton-claro`. Se
 *   escribe así —y no como una `clase` suelta— porque una `clase` vacía se confunde con «no me han
 *   dicho nada» y acabaría pintando un botón claro donde iba uno principal.
 */
function UnBotonDeLaLista({ boton }) {
  const clase = boton.principal ? "" : "boton-claro";
  if (boton.sencillo) {
    return html`<${BotonSencillo}
      etiqueta=${boton.etiqueta}
      accion=${boton.accion}
      datos=${boton.datos}
      clase=${clase}
      pista=${boton.pista}
    />`;
  }
  return html`<${Boton}
    etiqueta=${boton.etiqueta}
    icono=${boton.icono}
    accion=${boton.accion}
    datos=${boton.datos}
    clase=${clase}
    pista=${boton.pista}
  />`;
}

/**
 * Una lista de botones: los pinta todos, dentro de una `.barra-acciones` o sueltos.
 *
 * Vive aquí, y no en cada pantalla, porque **la necesitan dos**: «mi cuaderno» (que tiene nueve bloques
 * y cada uno con sus botones) y el asistente (los suyos: VOLVER, DEJARLO y SEGUIR/APUNTARLO). Antes
 * estaba escrita dentro de `mi_cuaderno.js`; al migrar el asistente se subió aquí, que es donde el
 * proyecto tiene las piezas que se repiten (ver `docs/REACT.md`).
 *
 * `barra` importa: `.barra-acciones` es una fila con su separación, y **un botón dentro de ella no se ve
 * igual que un botón suelto** debajo de un párrafo. En «mi cuaderno» el de firmar y el de hacer el plan
 * van sueltos, como estaban; en los avisos de error, también.
 */
export function Botones({ botones = [], barra = true }) {
  if (!botones.length) return null;
  if (!barra) return botones.map((boton, indice) => html`<${UnBotonDeLaLista} key=${indice} boton=${boton} />`);
  return html`
    <div className="barra-acciones">
      ${botones.map((boton, indice) => html`<${UnBotonDeLaLista} key=${indice} boton=${boton} />`)}
    </div>
  `;
}

/**
 * El dibujo de una parcela: su forma, sacada de la geometría que guardó el programa.
 *
 * Va aquí porque es una pieza que se repite (la lista de parcelas y el mapa la enseñan) y porque en
 * React se dibuja **de verdad**, con sus etiquetas, y no metiendo un texto de HTML dentro de otro
 * (que es lo que se hacía antes con `innerHTML`, y es justo lo que React viene a quitar de encima).
 */
export function DibujoDeLaParcela({ dibujo, etiqueta }) {
  if (!dibujo) return null;
  return html`
    <svg className="dibujo-parcela" viewBox="0 0 100 100" role="img" aria-label=${frase(etiqueta)}>
      <path d=${dibujo}></path>
    </svg>
  `;
}

/**
 * El aviso de error: lo que ha dicho el servidor cuando algo no se ha podido hacer.
 *
 * Es el mismo bloque que montaba `bloqueError()` en `app.js` —`aviso aviso-error` con `role="alert"`—
 * y va aquí porque lo usan casi todas las pantallas. **Si no hay nada que decir, no se dibuja nada**:
 * un hueco vacío con un borde rojo asusta sin motivo.
 *
 * `role="alert"` no es adorno: es lo que hace que un lector de pantalla lo lea en voz alta en cuanto
 * aparece, sin que el agricultor tenga que ir a buscarlo.
 */
export function AvisoDeError({ texto }) {
  if (!texto) return null;
  return html`<div className="aviso aviso-error" role="alert">${frase(texto)}</div>`;
}

/**
 * Una fila de botones de elegir, con su rótulo (T06, 03/10/2026).
 *
 * POR QUÉ ESTÁ AQUÍ Y NO EN UNA PANTALLA. La necesitan **las dos pantallas nuevas de T06** —los
 * filtros y las capas del mapa, y los años que se comparan— y son la misma cosa: un rótulo y una fila
 * de opciones donde **una está elegida**. Escribirla dos veces es exactamente lo que este fichero
 * existe para evitar (`docs/REACT.md`: el día que cambie una clase, se cambia en un sitio).
 *
 * `todas` es la etiqueta de la opción «ninguna» (todas las tierras, sin agrupar) y vale vacío cuando
 * no hay tal opción —las capas del mapa son todas las que hay—: un botón «TODAS» que no dijera nada
 * sería un botón de más.
 *
 * **El elegido lleva su `data-elegido`**, y eso no es decoración: el color solo no informa (regla de
 * la casa), así que el agricultor lo ve marcado **y** una prueba puede comprobar cuál está elegido
 * leyendo el dato en vez de mirando la clase.
 *
 * `datos` lleva los `data-*` de cada opción (el campo que se filtra y su valor). La acción llega por
 * propiedad y por eso este fichero está en la lista de los que pintan acciones por variable
 * (`tests/test_los_botones_hacen_algo.py`): las acciones que se le pasan están todas atendidas.
 */
export function OpcionesParaElegir({ rotulo, opciones = [], accion, campo = "", datos = {}, elegido = "", todas = "" }) {
  return html`
    <div className="campo t06-opciones">
      <span className="t06-rotulo">${frase(rotulo)}</span>
      <div className="barra-acciones">
        ${
          todas
            ? html`<button
                type="button"
                className=${`boton ${!elegido ? "boton-elegido" : "boton-claro"}`}
                data-accion=${accion}
                ...${datosDelBoton({ ...datos, campo, valor: "" })}
                data-elegido=${!elegido ? "1" : "0"}
              >
                ${frase(todas)}
              </button>`
            : null
        }
        ${(opciones || []).map(
          (opcion) => html`
            <button
              key=${String(opcion.valor)}
              type="button"
              className=${`boton ${String(elegido) === String(opcion.valor) ? "boton-elegido" : "boton-claro"}`}
              data-accion=${accion}
              ...${datosDelBoton({ ...datos, campo, valor: opcion.valor })}
              data-elegido=${String(elegido) === String(opcion.valor) ? "1" : "0"}
            >
              ${frase(opcion.texto)}
              ${opcion.pista ? html`<span className="pista-boton">${frase(opcion.pista)}</span>` : null}
            </button>
          `,
        )}
      </div>
    </div>
  `;
}
