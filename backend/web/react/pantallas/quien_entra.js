/*
 * quien_entra.js — «Quién entra en mi finca», escrita en React.
 *
 * POR QUÉ ESTA PANTALLA
 *
 * David lo pidió con estas palabras: «también quiero que una explotación puedan acceder varias cuentas,
 * no solo 1». El servidor ya lo sabía hacer desde la ronda 89 (`/api/fincas`, la tabla `accesos_a_fincas`
 * y sus cuatro caminos), pero **no había forma de hacerlo desde el móvil**: los endpoints estaban, los
 * textos estaban, y ninguna pantalla los pedía. Es el fallo de siempre en este proyecto —un dato que
 * existe y no tiene puerta—, y esta es la puerta.
 *
 * LAS DOS COSAS QUE HACE, Y POR QUÉ VAN JUNTAS
 *
 *  1. **Decir quién entra** en la finca en la que se está trabajando, y (si eres el titular) añadir y
 *     quitar cuentas por su correo. Es lo que se viene a hacer aquí.
 *  2. **Cambiar de finca**, cuando la cuenta puede entrar en más de una. Es la otra mitad del mismo
 *     asunto: quien ayuda en dos fincas tiene que poder decir en cuál está apuntando, o apuntaría en la
 *     que no es. Va después, porque solo sale cuando hay más de una: con una sola finca, un bloque que
 *     enseña una lista de uno es ruido.
 *
 * QUÉ NO HACE, QUE ES LO IMPORTANTE
 *
 *  - **No decide nada por su cuenta.** Quién entra, con qué papel y qué finca está activa viene ya
 *    resuelto del servidor (`/api/fincas` y `/api/fincas/quien-entra`). Aquí no se compara correos ni se
 *    supone un papel: lo que llega, se pinta. Cambiar de finca devuelve además **un vale nuevo**, y eso
 *    lo hace `app.js`, que es quien guarda el vale.
 *  - **No escribe la clave de nadie.** Se pide el correo de una cuenta **que ya existe**; la clave la
 *    elige cada uno. Por eso, cuando el correo no está, el servidor dice que esa persona se dé de alta
 *    primero, y esta pantalla lo enseña tal cual.
 *  - **Ni un texto escrito aquí.** Todo (los títulos, los papeles, los botones y hasta los avisos del
 *    servidor) sale de `textos.FINCAS`, por `/api/interfaz`.
 *
 * LO QUE SE CONSERVA A PROPÓSITO
 *
 *  1. **El campo del correo lleva su `id`** (`persona-correo`) y lo lee `app.js` al pulsar AÑADIR UNA
 *     CUENTA, igual que los campos de «mis datos»: en esta aplicación el manejador de clics es **uno
 *     solo** y vive allí. Es un formulario no controlado, a propósito (ver `docs/REACT.md`).
 *  2. **Los `data-accion` de siempre** (`quien-entra-abrir`, `finca-anadir`, `finca-quitar`,
 *     `finca-entrar`) y los `data-*` que dicen a qué finca o a qué cuenta se refiere cada botón.
 *  3. **Las mismas clases que ya existen** en `estilos.css` (`.lista`, `.pista`, `.pista-campo`,
 *     `.apunte-detalle`, `.campo`, `.barra-acciones`). Ni un `style` aquí: los colores viven en el
 *     `:root`.
 *  4. **El aviso de error** es el de toda la aplicación (`AvisoDeError`), con su `role="alert"`.
 */

import { AvisoDeError, Boton, BotonSencillo, frase, html } from "../componentes.js";

/**
 * Una finca de la lista, con su papel y el botón para ponerse en ella.
 *
 * El botón **no sale en la finca en la que ya se está**: un botón que no cambia nada es una promesa que
 * no se cumple, y aquí, además, el agricultor acabaría pulsándolo para «confirmar» sin saber qué pasa.
 * Que estás en esa se ve porque es la única sin botón y porque arriba se dice en cuál estás.
 */
function Finca({ finca, textos }) {
  const d = textos.fincas || {};
  // El papel de la finca, no el de la persona: «Tuya» o «Te ayuda».
  const papel = finca.papel === "titular" ? d.la_tuya : d.papel_ayudante;
  return html`
    <li>
      <div className="apunte-cabecera">
        <strong>${frase(finca.nombre)}</strong>
        ${finca.hectareas ? html`<span className="cuantas">${frase(finca.hectareas)}</span>` : null}
      </div>
      ${finca.municipio ? html`<div className="apunte-detalle">${frase(finca.municipio)}</div>` : null}
      <p className="pista-campo">${frase(papel)}</p>
      ${
        // En la que ya se está no hay botón —no cambiaría nada— y se dice con palabras (diseño de Stitch de
        // esta pantalla, ronda 90): una finca sin botón y sin explicación parece un fallo del programa.
        finca.activa
          ? html`<p className="tarjeta-aviso">
              <span className="tarjeta-aviso-icono" aria-hidden="true">✓</span>
              ${frase(d.estas_aqui)}
            </p>`
          : html`
              <${Boton}
                etiqueta=${d.entrar_en}
                accion="finca-entrar"
                datos=${{ id: finca.id }}
                clase="boton-claro"
              />
            `
      }
    </li>
  `;
}

/**
 * Una persona que entra en la finca: su nombre, su correo, su papel y —si se puede— el botón de quitarla.
 *
 * El papel se escribe con **una de las cuatro frases** del servidor, según quién sea y quién esté
 * mirando: «Tú (titular)», «El titular de la finca», «Tu cuenta» y «Ayuda en la finca». No se compone
 * ninguna: se elige la que toca. Si el papel llegara con un valor que no se conoce, sale el de ayuda,
 * que es el que no promete nada.
 */
function Persona({ persona, textos }) {
  const d = textos.fincas || {};
  const esTitular = persona.papel === "titular";
  let papel = esTitular ? d.papel_titular : d.ayudante;
  if (esTitular && persona.eres_tu) papel = d.titular;
  if (!esTitular && persona.eres_tu) papel = d.tu_cuenta;
  return html`
    <li>
      <strong>${frase(persona.nombre)}</strong>
      <div className="apunte-detalle">${frase(persona.correo)}</div>
      <p className="pista-campo">${frase(papel)}</p>
      ${
        // Lo que puede hacer quien ayuda (diseño de Stitch de esta pantalla, ronda 90): sin decirlo, el
        // titular no sabe qué le está dando a la otra persona. Es lo que hace de verdad el servidor.
        !esTitular && d.que_puede_ayudante
          ? html`<p className="apunte-detalle">${frase(d.que_puede_ayudante)}</p>`
          : null
      }
      ${persona.se_puede_quitar
        ? html`
            <${BotonSencillo}
              etiqueta=${d.quitar}
              accion="finca-quitar"
              datos=${{ persona: persona.usuario_id }}
              clase="boton-peligro"
            />
          `
        : null}
    </li>
  `;
}

/**
 * La pantalla entera.
 *
 * Propiedades:
 *
 *  - `textos`: `{ fincas, acciones }`, tal y como los sirve `/api/interfaz`.
 *  - `finca`: el nombre de la finca en la que se está trabajando, o nada.
 *  - `fincas`: las fincas en las que puede entrar esta cuenta, ya preparadas por `app.js`, con cuál es
 *    la activa. **Solo se enseña la lista si hay más de una.**
 *  - `personas`: quién entra en la finca, con su papel y si se puede quitar.
 *  - `soyTitular`: si quien mira es el titular. Decide tres cosas: qué frase se lee, si sale el campo
 *    del correo y si sale el formulario entero.
 *  - `aviso`: lo que se dice cuando la lista acaba de cambiar («Ya puede entrar en tu finca»), o nada.
 *  - `error`: lo que ha dicho el servidor cuando no se ha podido hacer algo, o nada.
 */
export function PantallaQuienEntra({
  textos = {},
  finca = "",
  fincas = [],
  personas = [],
  soyTitular = false,
  aviso = "",
  error = "",
}) {
  const d = textos.fincas || {};
  const acciones = textos.acciones || {};

  return html`
    <h1>${frase(d.titulo)}</h1>
    <p className="pista">${frase(d.explica)}</p>
    <${AvisoDeError} texto=${error} />
    ${aviso ? html`<p className="aviso">${frase(aviso)}</p>` : null}
    ${finca ? html`<p className="pista">${frase(d.estas_en)} <strong>${frase(finca)}</strong></p>` : null}

    <p className="pista-campo">${frase(soyTitular ? d.eres_el_titular : d.no_eres_el_titular)}</p>
    ${personas.length === 1 ? html`<p className="pista-campo">${frase(d.solo_una)}</p>` : null}
    ${
      personas.length
        ? html`
            <ul className="lista">
              ${personas.map(
                (persona) => html`<${Persona} key=${persona.usuario_id} persona=${persona} textos=${textos} />`,
              )}
            </ul>
          `
        : null
    }
    ${
      soyTitular
        ? html`
            <div className="campo">
              <label htmlFor="persona-correo">${frase(d.que_correo)}</label>
              <input id="persona-correo" type="email" />
              <p className="pista-campo">${frase(d.que_correo_pista)}</p>
            </div>
            <p className="pista-campo">${frase(d.anadir_pista)}</p>
            <div className="barra-acciones">
              <${Boton} etiqueta=${d.anadir} accion="finca-anadir" clase="boton-principal" />
            </div>
          `
        : null
    }
    ${
      fincas.length > 1
        ? html`
            <h2>${frase(d.cambiar_titulo)}</h2>
            <p className="pista-campo">${frase(d.cambiar_explica)}</p>
            <ul className="lista">
              ${fincas.map((una) => html`<${Finca} key=${una.id} finca=${una} textos=${textos} />`)}
            </ul>
          `
        : null
    }
    <div className="barra-acciones">
      <${Boton} etiqueta=${acciones.volver} accion="inicio" datos=${{ ir: "mi_cuaderno" }} clase="boton-claro" />
    </div>
  `;
}

/** El elemento de React de esta pantalla, ya con sus propiedades puestas. */
export function pantallaDeQuienEntra(propiedades) {
  return html`
    <${PantallaQuienEntra}
      textos=${propiedades.textos}
      finca=${propiedades.finca}
      fincas=${propiedades.fincas}
      personas=${propiedades.personas}
      soyTitular=${propiedades.soyTitular}
      aviso=${propiedades.aviso}
      error=${propiedades.error}
    />
  `;
}
