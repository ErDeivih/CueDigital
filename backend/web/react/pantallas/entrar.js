/*
 * entrar.js — La pantalla de entrar, escrita en React.
 *
 * POR QUÉ ESTA PANTALLA
 *
 * Es la decimoctava que se pasa a React y es **la primera que ve cualquiera**: la puerta. Hasta
 * ahora era de la interfaz vieja, así que lo primero que se encontraba el agricultor (y quien
 * evalúe el programa) era la mitad antigua. Ahora la puerta y la pantalla de inicio —las dos que se
 * ven siempre— son de React.
 *
 * DOS MODOS, UNA PANTALLA
 *
 * `modo` es `"entrar"` o `"registro"`. Al registrarse se preguntan cuatro cosas más (nombre, NIF,
 * pueblo y provincia) porque hay que crear la finca; al entrar, solo correo y clave. Los campos del
 * registro **solo existen en ese modo**: no se pintan escondidos.
 *
 * LO QUE SE CONSERVA A PROPÓSITO
 *
 *  1. **Los `id` de los seis campos** (`nombre`, `nif`, `municipio`, `provincia`, `correo`, `clave`):
 *     los lee `entrar()` en `app.js`, que es donde vive el manejador de clics. Si uno cambia, el
 *     agricultor escribe su correo y su clave y no entra, sin saber por qué.
 *  2. **Siempre hay una forma de entrar que no depende del certificado.** El botón del certificado
 *     solo sale si la instalación está preparada, y no tapa el de correo y clave: si el certificado
 *     falla, el agricultor tiene que poder entrar igual.
 *  3. **El botón del certificado no se enseña si no se puede usar.** Un botón que lleva a un error es
 *     peor que no tenerlo.
 *  4. Nada de `esc()` y ninguna frase escrita aquí: los textos llegan por propiedades.
 *
 * El componente es PURO: no llama a `fetch`, no lee `localStorage` y no toca el DOM.
 */

import { AvisoDeError, Boton, Marca, frase, html } from "../componentes.js";

/**
 * La ayuda de un campo, tal y como la pinta la pantalla vieja: un bloque con cuatro explicaciones.
 *
 * Llega **ya preparada** por `app.js` (título y las cuatro frases), con sus rótulos del servidor:
 * aquí no se escribe ni una palabra. Si no hay ayuda para ese campo, no se dibuja nada.
 */
function AyudaDeUnCampo({ ayuda }) {
  if (!ayuda) return null;
  return html`
    <div className="ayuda-campo">
      <h3>${frase(ayuda.titulo)}</h3>
      <p>
        <span className="etiqueta-dato">${frase(ayuda.rotulos.que_es)}</span>
        ${frase(ayuda.que_es)}
      </p>
      <p>
        <span className="etiqueta-dato">${frase(ayuda.rotulos.por_que)}</span>
        ${frase(ayuda.por_que)}
      </p>
      <p>
        <span className="etiqueta-dato">${frase(ayuda.rotulos.ejemplo)}</span>
        ${frase(ayuda.ejemplo)}
      </p>
      <p>
        <span className="etiqueta-dato">${frase(ayuda.rotulos.si_falta)}</span>
        ${frase(ayuda.si_falta)}
      </p>
    </div>
  `;
}

/**
 * La pantalla entera.
 *
 * Propiedades:
 *
 *  - `textos`: `{ pantalla_entrar, ayuda, certificado, acciones }`, tal y como los sirve
 *    `/api/interfaz`.
 *  - `modo`: `"entrar"` o `"registro"`.
 *  - `provincias`: la lista del servidor, para no tener que escribir la provincia a mano.
 *  - `certificado`: `{ configurado }`, o nada. Si no está configurado, el botón no se enseña.
 *  - `ayudaDelNif`: la ayuda del campo del NIF, ya preparada (o nada).
 *  - `errorEntrar` y `errorCertificado`: lo que ha dicho el servidor.
 */
export function PantallaEntrar({
  textos = {},
  modo = "entrar",
  provincias = [],
  certificado = null,
  ayudaDelNif = null,
  errorEntrar = "",
  errorCertificado = "",
}) {
  const ent = textos.pantalla_entrar || {};
  const ayuda = textos.ayuda || {};
  const cert = textos.certificado || {};
  const primeraVez = modo === "registro";

  return html`
    <section className="entrada-cuenta">
    <${Marca} textos=${textos.marca} />
    ${textos.marca?.lema ? html`<p className="marca-lema">${frase(textos.marca.lema)}</p>` : null}
    <h1>${frase(ent.titulo)}</h1>
    <p className="pista">${frase((ayuda.porques || {}).papel_o_digital)}</p>
    <${AvisoDeError} texto=${errorEntrar} />
    <div id="formulario">
      ${
        primeraVez
          ? html`
              <div className="campo">
                <label htmlFor="nombre">${frase(ent.como_te_llamas)}</label>
                <input id="nombre" type="text" autoComplete="name" />
              </div>
              <div className="campo">
                <label htmlFor="nif">${frase(ent.tu_nif)}</label>
                <input id="nif" type="text" inputMode="text" />
                <${AyudaDeUnCampo} ayuda=${ayudaDelNif} />
              </div>
              <div className="campo">
                <label htmlFor="municipio">${frase(ent.tu_pueblo)}</label>
                <input id="municipio" type="text" />
              </div>
              <div className="campo">
                <label htmlFor="provincia">${frase(ent.tu_provincia)}</label>
                <select id="provincia">
                  ${provincias.map(
                    (provincia) => html`<option key=${provincia}>${frase(provincia)}</option>`,
                  )}
                </select>
              </div>
            `
          : null
      }
      <div className="campo">
        <label htmlFor="correo">${frase(ent.tu_correo)}</label>
        <input id="correo" type="email" autoComplete="email" />
      </div>
      <div className="campo">
        <label htmlFor="clave">${frase(ent.tu_clave)}</label>
        <input
          id="clave"
          type="password"
          autoComplete=${primeraVez ? "new-password" : "current-password"}
        />
      </div>
    </div>
    <div className="barra-acciones">
      <${Boton}
        etiqueta=${primeraVez ? ent.crear : ent.entrar}
        accion="entrar"
        datos=${{ modo: primeraVez ? "registro" : "entrar" }}
      />
    </div>
    ${
      // El botón del certificado solo sale si la instalación está preparada, y **después** del de
      // correo y clave: siempre tiene que haber una forma de entrar que no dependa del certificado.
      certificado && certificado.configurado
        ? html`<button
            type="button"
            className="boton boton-secundario"
            data-accion="entrar-certificado"
          >
            <span className="icono" aria-hidden="true">🪪</span>
            <span className="texto">
              <span>${frase(cert.boton)}</span>
              <span className="pista-boton">${frase(cert.pista)}</span>
            </span>
          </button>`
        : null
    }
    <${AvisoDeError} texto=${errorCertificado} />
    <${Boton}
      etiqueta=${primeraVez ? ent.ya_tengo_cuenta : ent.primera_vez}
      accion="cambiar-modo-entrar"
      datos=${{ modo: primeraVez ? "entrar" : "registro" }}
      clase="boton-claro"
    />
    </section>
  `;
}

/** El elemento de React de esta pantalla, ya con sus propiedades puestas. */
export function pantallaDeEntrar(propiedades) {
  return html`<${PantallaEntrar}
    textos=${propiedades.textos}
    modo=${propiedades.modo}
    provincias=${propiedades.provincias}
    certificado=${propiedades.certificado}
    ayudaDelNif=${propiedades.ayudaDelNif}
    errorEntrar=${propiedades.errorEntrar}
    errorCertificado=${propiedades.errorCertificado}
  />`;
}
