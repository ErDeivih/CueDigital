/*
 * marco.js — El armazón de la aplicación en el ordenador: el menú de la izquierda y la barra de arriba.
 *
 * POR QUÉ EXISTE (30/09/2026)
 *
 * Hasta hoy la aplicación era **una columna de móvil** también en el ordenador: sin menú, sin barra con la
 * finca y el año, y para llegar a las 64 tierras había que saber que estaban detrás de un botón de la
 * pantalla de inicio. David lo dijo con estas palabras: *«debe ser responsive para usarse en pc y móvil, no
 * solo móvil… no es una app usable de gestión»*. Esto es el armazón que resuelve eso: **el mismo programa**
 * con un menú lateral que lleva a cada módulo y una barra que dice siempre en qué finca y en qué año se
 * está apuntando.
 *
 * LO QUE HACE Y LO QUE NO
 *
 *  1. **No es una pantalla**: es el marco donde se montan las pantallas. Va fuera del contenedor de las
 *     pantallas (`#marco`), y las pruebas de cableado siguen mirando lo que se monta en `#pantalla` como
 *     siempre.
 *  2. **No se enseña en el móvil.** En una pantalla estrecha el menú no se pinta (lo hace el CSS): ahí se
 *     sigue entrando por la pantalla de inicio, que es lo que el agricultor ya conoce. Un menú escondido
 *     detrás de un botón sería una cosa más que aprender en el sitio donde peor se aprende.
 *  3. **Todo lo que se lee viene del servidor**: los nombres de los módulos son los títulos de sus propias
 *     pantallas (`textos.py`), y las palabras de la barra («Finca», «Campaña», «Tu cuenta») están en
 *     `MENU`. Aquí no se escribe ni una frase para el agricultor.
 *  4. **Cada módulo lleva su `data-accion`** (y sus `data-*`), que es lo que lee el manejador de clics de
 *     siempre: el mismo botón del menú y el de dentro de una pantalla hacen lo mismo.
 *  5. **El módulo en el que se está va marcado**, con su clase y con `aria-current`: el color solo no
 *     informa (regla de la casa).
 *
 * CAMBIO DEL 02/10/2026 (T04): la barra también dice LA FINCA y deja cambiarla (y cambiar de campaña)
 *
 * Lo pidió el ticket de T04 con estas palabras: «la barra enseña la finca y deja cambiar de campaña y de
 * finca». Hasta hoy la finca no estaba en la barra y **eso fue una decisión, no un olvido**: la finca se
 * identifica por el nombre del titular (`Explotacion.nombre`), así que poner «Finca: David Pérez Velasco»
 * sería decir una cosa que no es (está escrito en `textos.MENU`). Lo que cambia ahora no es el olvido,
 * es el dato: una cuenta ya puede entrar en **varias fincas** (ronda 89), y ahí la barra tiene que decir
 * en cuál se está trabajando y dejar cambiarla, porque apuntar en la finca que no es mete un dato falso
 * en el cuaderno.
 *
 * Se añade con un prop **opcional** (`contexto`) y **sin tocar nada de lo que ya hacía**:
 *
 *  - **Sin `contexto`, la barra se pinta exactamente igual que antes de este cambio.** No es una
 *    promesa: hay pruebas que comparan lo que se ve hoy (`tests_js/react.test.js`, «la barra dice el
 *    año y la cuenta, y lleva el botón de apuntar» y «sin año y sin cuenta no se queda un hueco»), y
 *    siguen pasando sin tocarlas. Por eso el dato de la campaña no se sustituye: cuando no hay nada que
 *    elegir, la línea del año es la misma de siempre.
 *  - **Con `contexto`, se añade lo que falta**: la finca, y los botones para cambiar de finca y de
 *    campaña. Los botones llevan `data-accion` y `data-valor`, que es el convenio de toda la
 *    aplicación (un solo manejador de clics lee `data-accion` y decide), así que el armazón no tiene
 *    ninguna lógica propia de navegación.
 *  - **Las palabras siguen viniendo del servidor** (`textos.menu` y, si se sirven aparte, `textos.marco`).
 *    Aquí no se escribe ni una frase: lo único que se pinta son los nombres de las fincas y los años,
 *    que son datos.
 *
 * El componente es PURO: no llama a `fetch`, no lee `localStorage` y no toca el DOM.
 */

import { datosDelBoton, frase, html } from "../componentes.js";

/** Una lista de lo que llegue, sin reventar si no es una lista: el armazón no puede tumbar la pantalla. */
function lista(valor) {
  return Array.isArray(valor) ? valor : [];
}

/** Un dato del servidor, en texto, sin dejar huecos (`null`, `undefined` y `""` son lo mismo: nada). */
function texto(valor) {
  return valor === null || valor === undefined ? "" : String(valor);
}

/**
 * El año de una campaña, se la pase como se la pase.
 *
 * Hace falta porque el mismo dato llega de dos formas según de dónde salga: la pantalla de los años
 * trabaja con fichas del servidor (`{id, anio, fecha_inicio…}`) y el renglón de la barra, con el año a
 * secas («2026»). Traducirlo aquí, y no en `app.js`, es lo que evita que la barra enseñe un hueco el día
 * que se le pase la lista del servidor tal cual.
 */
function elAnioDe(campana) {
  if (campana && typeof campana === "object") return texto(campana.anio);
  return texto(campana);
}

/** Un módulo del menú: se toca y lleva a su pantalla. */
function Modulo({ modulo }) {
  return html`
    <li>
      <button
        type="button"
        id=${`menu-${modulo.clave}`}
        className=${`menu-enlace${modulo.activo ? " menu-activo" : ""}`}
        data-accion=${modulo.accion}
        ...${datosDelBoton(modulo.datos)}
        aria-current=${modulo.activo ? "page" : undefined}
      >
        ${frase(modulo.etiqueta)}
      </button>
    </li>
  `;
}

/**
 * Los botones para elegir, dentro de un dato de la barra: uno por finca y uno por año.
 *
 * POR QUÉ BOTONES Y NO UN DESPLEGABLE. Porque un desplegable, en un móvil, abre la rueda del sistema y
 * tapa la pantalla; y en un ordenador con 64 tierras hay dos o tres fincas y cinco años, que caben de
 * sobra. Además así cada opción es lo que el resto de la aplicación ya usa para todo: un botón con su
 * `data-accion` y su `data-valor`, que es lo que lee el manejador de clics de siempre. El año elegido va
 * marcado con su clase **y** con `aria-current`: el color solo no informa (regla de la casa).
 *
 * Los nombres de las fincas y los años **son datos**, no textos: lo único que viene del servidor son las
 * palabras de alrededor (`textos.menu`), como en todo el armazón.
 */
function BotonesDeElegir({ accion, opciones }) {
  return opciones.map(
    (opcion, indice) => html`
      <button
        key=${`${accion}-${indice}`}
        type="button"
        className=${`boton-letra${opcion.elegida ? " boton-elegido" : ""}`}
        data-accion=${accion}
        ...${datosDelBoton({ valor: opcion.valor })}
        aria-current=${opcion.elegida ? "true" : undefined}
      >
        ${frase(opcion.texto)}
      </button>
    `,
  );
}

/**
 * El contexto ya preparado para pintarlo: las fincas, los años y en cuál se está.
 *
 * Se prepara aquí y no en `app.js` porque es una traducción de forma, no una decisión: la lista de
 * fincas llega del servidor tal cual (`/api/fincas`: `{id, nombre, activa…}`) y la de años puede llegar
 * como años a secas o como fichas (`{id, anio…}`, de `/api/campanas`). Se aceptan las dos, y **lo que no
 * se sabe se queda en blanco**: una finca sin nombre o sin identificador no se pinta como botón (un
 * botón que no dice a qué finca cambia es peor que no tenerlo), y si no hay ningún nombre se dice con la
 * palabra del servidor (`sin_finca`), nunca con un guion.
 */
function preparaElContexto(contexto, campana) {
  const suyo = contexto && typeof contexto === "object" ? contexto : {};
  const campanaElegida = elAnioDe(suyo.campana) || texto(campana);
  const campanas = lista(suyo.campanas)
    .map((una) => elAnioDe(una))
    .filter((anio) => anio !== "")
    .map((anio) => ({ valor: anio, texto: anio, elegida: anio === campanaElegida }));
  const fincas = lista(suyo.fincas)
    .filter((finca) => finca && typeof finca === "object")
    .map((finca) => ({
      valor: texto(finca.id),
      texto: frase(finca.nombre),
      activa: Boolean(finca.activa),
    }))
    .filter((finca) => finca.valor !== "" && finca.texto !== "");
  // El nombre de la finca se lee de dos sitios y en este orden: el que mande `app.js` (que es el que
  // sabe en cuál se está trabajando) y, si no lo manda, la que el servidor marca como activa.
  const nombreDeLaFinca =
    texto(suyo.finca) || (fincas.find((una) => una.activa) || {}).texto || "";
  return {
    campanas,
    nombreDeLaFinca,
    fincas: fincas.map((finca) => ({
      valor: finca.valor,
      texto: finca.texto,
      elegida: finca.activa || finca.texto === nombreDeLaFinca,
    })),
  };
}

/**
 * La pantalla entera (que es el marco).
 *
 * Propiedades:
 *
 *  - `textos`: `{ menu, acciones }`, tal y como los sirve `/api/interfaz`. Las palabras que trae el
 *    contexto (la finca, «cambiar de finca», «cambiar de campaña») se leen de `textos.marco` y, si no
 *    están ahí, de `textos.menu`, que es el bloque que ya se manda hoy: las dos formas valen.
 *  - `finca`: el nombre de la finca en la que se está trabajando (o vacío).
 *  - `campana`: el año que se está llevando, ya escrito («2026»), o vacío.
 *  - `usuario`: el nombre de quien está apuntando (o vacío).
 *  - `modulos`: la lista de módulos, ya preparada por `app.js`
 *    (`[{clave, etiqueta, accion, datos, activo}]`).
 *  - `contexto` (opcional): `{finca, campanas, fincas}` — el nombre de la finca en la que se trabaja, los
 *    años que se pueden elegir y las fincas en las que puede entrar esta cuenta. **Sin este prop la barra
 *    se pinta exactamente igual que antes** de que existiera; con él, se le añaden la finca y los botones
 *    para cambiar de finca y de campaña.
 */
export function Marco({
  textos = {},
  cuenta = "",
  campana = "",
  modulos = [],
  contexto = null,
}) {
  // El armazón no tiene palabras propias: las que ya había vienen de `menu` y las del contexto, del
  // bloque que les toque. Se juntan en un solo sitio para que el resto de la función pida `m.loquesea`.
  const m = { ...(textos.menu || {}), ...(textos.marco || {}) };
  const suyo = preparaElContexto(contexto, campana);
  const hayContexto = Boolean(contexto) && typeof contexto === "object";

  return html`
    <nav className="menu" aria-label=${frase(m.etiqueta)}>
      <p className="menu-marca">${frase(m.titulo)}</p>
      ${
        // Quién está apuntando, arriba del menú: una cuenta puede entrar en varias fincas y esto es lo que
        // deja claro en cuál se está (es el mismo dato que el de la barra, dicho una vez en cada sitio).
        html`<p className="menu-cuenta">${frase(cuenta || m.sin_cuenta)}</p>`
      }
      <ul className="menu-lista">
        ${modulos.map((modulo) => html`<${Modulo} key=${modulo.clave} modulo=${modulo} />`)}
      </ul>
    </nav>
    <div className="barra">
      <div className="barra-datos">
        ${
          // La finca, que es lo primero que hay que saber para no apuntar en la que no es. Solo se añade
          // cuando hay contexto: sin él, la barra es la de siempre, y eso está comprobado con pruebas.
          hayContexto
            ? html`
                <p
                  className="barra-dato"
                  role=${suyo.fincas.length ? "group" : undefined}
                  aria-label=${suyo.fincas.length ? frase(m.cambiar_finca) : undefined}
                >
                  <span className="barra-rotulo">${frase(m.finca)}</span>
                  ${
                    suyo.fincas.length
                      ? html`<${BotonesDeElegir} accion="cambiar-finca" opciones=${suyo.fincas} />`
                      : html`<span className="barra-valor">${frase(suyo.nombreDeLaFinca || m.sin_finca)}</span>`
                  }
                </p>
              `
            : null
        }
        <p
          className="barra-dato"
          role=${suyo.campanas.length ? "group" : undefined}
          aria-label=${suyo.campanas.length ? frase(m.cambiar_campana) : undefined}
        >
          <span className="barra-rotulo">${frase(m.campana)}</span>
          ${
            // Con años que elegir, la línea del año se convierte en los botones para cambiarlo; sin ellos
            // (que es el caso de siempre), es el mismo renglón de texto que había.
            suyo.campanas.length
              ? html`<${BotonesDeElegir} accion="cambiar-campana" opciones=${suyo.campanas} />`
              : html`<span className="barra-valor">${frase(campana || m.sin_campana)}</span>`
          }
        </p>
        <p className="barra-dato">
          <span className="barra-rotulo">${frase(m.cuenta)}</span>
          <span className="barra-valor">${frase(cuenta)}</span>
        </p>
      </div>
      <div className="barra-acciones">
        <button type="button" className="boton boton-principal" data-accion="ir-inicio">
          ${frase(m.apuntar)}
        </button>
        <button
          type="button"
          className="boton-letra"
          data-accion="cambiar-letra"
          aria-label=${frase(m.letra_etiqueta)}
        >
          ${frase(m.letra)}
        </button>
        <button
          type="button"
          className="boton-letra"
          data-accion="salir"
          aria-label=${frase(m.salir_etiqueta)}
        >
          ${frase(m.salir)}
        </button>
      </div>
    </div>
  `;
}

/** El elemento de React de este armazón, ya con sus propiedades puestas. */
export function marcoDeLaAplicacion(propiedades) {
  return html`<${Marco}
    textos=${propiedades.textos}
    cuenta=${propiedades.cuenta}
    campana=${propiedades.campana}
    modulos=${propiedades.modulos}
    contexto=${propiedades.contexto}
  />`;
}
