/*
 * documentos.js — «Los papeles», escrita en React.
 *
 * POR QUÉ ESTA PANTALLA
 *
 * Es la cuarta que se pasa a React y la segunda que enseña listas agrupadas. Los papeles son lo que
 * demuestra lo que dice el cuaderno cuando llega una inspección (contratos, facturas, resguardos de
 * Sigfito, boletines…), así que esta pantalla se usa de verdad.
 *
 * **Lo que NO hace este componente:** no sabe nada de `estado` ni de la API. Recibe los papeles **ya
 * agrupados por carpeta** —quien los agrupa es `app.js`, que es quien tiene los datos— y los pinta.
 *
 * DOS COSAS QUE SE CONSERVAN A PROPÓSITO, y que no son un detalle:
 *
 *  1. El `<input type="file">` oculto de cada papel **lleva el mismo `id`** (`papel-<id>`) y la misma
 *     clase `oculto` que antes. No es capricho: quien sube el fichero (`subirFicheroDeDocumento` en
 *     `app.js`) lo busca por ese `id` para leer lo que el agricultor ha elegido. Si el `id` cambia,
 *     el botón de subir deja de encontrar el fichero y no pasa nada al pulsarlo.
 *  2. Los `data-accion` y los `data-id` de los botones, porque los despacha el manejador delegado de
 *     `document`, igual que en el resto de la aplicación.
 *
 * Y una decisión que se ve en pantalla: **un papel sin fichero no enseña el mismo botón que uno con
 * fichero**, porque no son la misma cosa. Uno se descarga; al otro hay que subirle el fichero, y se
 * dice que todavía no lo tiene en vez de dejar un botón que no haría nada.
 */

import { AvisoDeError, Boton, frase, html } from "../componentes.js";
import { AccionesDeUnaFicha } from "../piezas/acciones_de_una_ficha.js";

/**
 * Un papel: su título, su detalle y lo que se puede hacer con él.
 *
 * Del diseño de Stitch de esta pantalla (ronda 90, `docs/stitch/rediseno/documentos.png`): al papel al
 * que le falta el fichero se le dice **en su franja de aviso** y su botón de subirlo es **el de color de
 * acción**, porque es lo único que le falta. Uno con fichero se descarga con un botón claro.
 */
function Papel({ papel, textos }) {
  const d = textos.documentos || {};
  return html`
    <li>
      <strong>${frase(papel.titulo)}</strong>
      <div className="apunte-detalle">${frase(papel.detalle)}</div>
      ${
        papel.tiene_fichero
          ? html`
              <${Boton}
                etiqueta=${d.descargar}
                accion="papel-ver"
                datos=${{ id: papel.id }}
                clase="boton-claro"
              />
            `
          : html`
              <p className="tarjeta-aviso">
                <span className="tarjeta-aviso-icono" aria-hidden="true">!</span>
                ${frase(d.sin_fichero)}
              </p>
              <input type="file" id=${`papel-${papel.id}`} className="oculto" />
              <${Boton}
                etiqueta=${d.subir_fichero}
                accion="papel-subir"
                datos=${{ id: papel.id }}
                clase="boton-principal"
              />
            `
      }
      ${
        // **CORREGIR y BORRAR el papel** (ronda 93), al final de su ficha y con la misma pieza que en las
        // demás listas. Corregir abre **la misma pantalla con la que se guarda un papel**, con sus seis
        // campos puestos; borrar pregunta antes y, si el papel tenía fichero, **el fichero también se
        // borra** (dejarlo ahí sería basura del agricultor que nadie va a limpiar nunca).
        html`<${AccionesDeUnaFicha} acciones=${papel.acciones} />`
      }
    </li>
  `;
}

/** Un grupo de papeles: el nombre de la carpeta y lo que hay dentro. */
function Carpeta({ carpeta, textos }) {
  return html`
    <h2>${frase(carpeta.nombre)}</h2>
    <ul className="lista">
      ${carpeta.papeles.map((papel) => html`<${Papel} key=${papel.id} papel=${papel} textos=${textos} />`)}
    </ul>
  `;
}

/**
 * La pantalla entera.
 *
 * Propiedades:
 *
 *  - `textos`: `{ documentos, maestros, acciones }`, tal y como los sirve `/api/interfaz`.
 *  - `carpetas`: los grupos con sus papeles, ya preparados por `app.js`.
 *  - `sinCarpeta`: los papeles que no caen en ninguna carpeta conocida (una carpeta que el agricultor
 *    escribió a mano, por ejemplo). **No se esconden**: si están, se enseñan.
 *  - `total`: cuántos papeles hay en total. Sirve para el aviso de «todavía no hay ninguno».
 *  - `error`: lo que ha dicho el servidor cuando algo ha fallado, o nada.
 */
export function PantallaDocumentos({
  textos = {},
  carpetas = [],
  sinCarpeta = [],
  total = 0,
  error = "",
}) {
  const d = textos.documentos || {};
  const maestros = textos.maestros || {};
  const acciones = textos.acciones || {};

  return html`
    <h1>${frase(d.titulo)}</h1>
    <p className="pista">${frase(d.explica)}</p>
    <${AvisoDeError} texto=${error} />
    ${
      // El botón de guardar un papel, **también arriba** (diseño de Stitch de esta pantalla, ronda 90):
      // con diez papeles guardados, el de abajo queda a dos pantallas de scroll, y guardar es a lo que se
      // entra aquí. Son el mismo botón y la misma acción, que las atiende el manejador de `document`.
      total
        ? html`<div className="barra-acciones">
            <${Boton} etiqueta=${d.nuevo} accion="papel-nuevo" clase="boton-principal" />
          </div>`
        : null
    }
    ${total === 0 ? html`<div className="aviso">${frase(d.sin_papeles)}</div>` : null}
    ${carpetas.map((carpeta) => html`<${Carpeta} key=${carpeta.nombre} carpeta=${carpeta} textos=${textos} />`)}
    ${
      sinCarpeta.length
        ? html`
            <h2>${frase(d.sin_carpeta)}</h2>
            <ul className="lista">
              ${sinCarpeta.map((papel) => html`<${Papel} key=${papel.id} papel=${papel} textos=${textos} />`)}
            </ul>
          `
        : null
    }
    <div className="ayuda-campo">
      <p><strong>${frase(d.para_que)}</strong></p>
    </div>
    <div className="barra-acciones">
      <${Boton} etiqueta=${d.nuevo} accion="papel-nuevo" clase="boton-principal" />
      <${Boton} etiqueta=${d.listado} accion="papel-listado" clase="boton-claro" />
      <!-- **La puerta de la bandeja** (T08, 06/10/2026): lo que llega y hay que revisar. Va antes del
           atajo a las tierras, que es lo que se mira de vez en cuando. -->
      <${Boton} etiqueta=${d.bandeja} accion="bandeja-ver" clase="boton-claro" />
      <${Boton} etiqueta=${maestros.titulo} accion="mis-cosas" clase="boton-claro" />
      <${Boton} etiqueta=${acciones.volver} accion="ir-inicio" clase="boton-claro" />
    </div>
  `;
}

/** El elemento de React de esta pantalla, ya con sus propiedades puestas. */
export function pantallaDeDocumentos(propiedades) {
  return html`
    <${PantallaDocumentos}
      textos=${propiedades.textos}
      carpetas=${propiedades.carpetas}
      sinCarpeta=${propiedades.sinCarpeta}
      total=${propiedades.total}
      error=${propiedades.error}
    />
  `;
}
