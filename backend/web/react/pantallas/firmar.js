/*
 * firmar.js — «Firmar el cuaderno», escrita en React.
 *
 * POR QUÉ ESTA PANTALLA
 *
 * Es la decimosexta que se pasa a React y es de las que tienen peso legal: **firmar es lo que hace que
 * el cuaderno valga delante de la administración**. La pantalla son tres pasos —descargar el fichero,
 * firmarlo con AutoFirma, subir la firma— y el programa **no firma nada**: prepara el fichero, lo
 * entrega y recibe la firma. Así la firma es del agricultor de verdad y no un «firmado por el
 * sistema» que no valdría para nada.
 *
 * LO QUE SE CONSERVA A PROPÓSITO
 *
 *  1. **El campo del fichero conserva su `id`** (`firma-fichero`) y lo lee `app.js` al subir la
 *     firma: los campos son descontrolados y el manejador de clics es uno solo, que vive allí.
 *  2. Los `data-accion` (`firmar-descargar`, `firmar-subir`, `inicio` con `data-ir`) y las clases.
 *  3. **El aviso de «ya está firmado» solo sale si de verdad se acaba de firmar**, y el error va en su
 *     bloque: un hueco vacío asusta sin motivo.
 *  4. Nada de `esc()` y ninguna frase escrita aquí: los textos llegan del servidor.
 *
 * El componente es PURO: no llama a `fetch`, no descarga nada y no toca el DOM. Descargar el fichero,
 * abrirlo con AutoFirma y subir la firma lo hace `app.js`.
 */

import { AvisoDeError, Boton, frase, html } from "../componentes.js";

/**
 * La pantalla entera.
 *
 * Propiedades:
 *
 *  - `textos`: `{ firma, acciones }`, tal y como los sirve `/api/interfaz`.
 *  - `nombreDelFichero`: cómo se llama el fichero que hay que descargar y firmar. Va con su nombre
 *    porque el agricultor tiene que reconocerlo en su carpeta de descargas.
 *  - `firmado`: la frase que se enseña cuando la firma se acaba de subir (o nada, si no es el caso).
 *  - `error`: lo que ha dicho el servidor o la comprobación de la firma.
 */
export function PantallaFirmar({
  textos = {},
  nombreDelFichero = "",
  firmado = "",
  error = "",
  estado = "",
  avisos = [],
}) {
  const f = textos.firma || {};
  const acciones = textos.acciones || {};

  return html`
    <h1>${frase(f.titulo)}</h1>
    <p className="pista">${frase(f.explica)}</p>
    <${AvisoDeError} texto=${error} />
    ${
      // **El estado de la firma, con su etiqueta** (diseño de Stitch de esta pantalla, ronda 90): la pantalla
      // solo enseñaba los tres pasos y el estado no se veía en ninguna parte. Es lo primero que se pregunta
      // quien entra aquí: «¿ya está firmado o no?».
      estado
        ? html`
            <span className="etiqueta-estado etiqueta-estado-voluntario">${frase(estado)}</span>
          `
        : null
    }
    ${
      // Y el aviso de que aquí no se puede firmar (porque hace falta el certificado): sin él, los tres pasos
      // parecen poder terminarse, y el último no funciona.
      avisos.map(
        (aviso, indice) => html`
          <p className="tarjeta-aviso" key=${indice}>
            <span className="tarjeta-aviso-icono" aria-hidden="true">!</span>
            ${frase(aviso)}
          </p>
        `,
      )
    }
    ${firmado ? html`<div className="aviso">${frase(firmado)}</div>` : null}

    <h2>${frase(f.paso_1)}</h2>
    <p className="pista-campo">${frase(nombreDelFichero)}</p>
    <button type="button" className="boton boton-claro" data-accion="firmar-descargar">
      <span className="icono" aria-hidden="true">⬇️</span>
      <span className="texto"><span>${frase(f.descargar)}</span></span>
    </button>

    <h2>${frase(f.paso_2)}</h2>
    <p className="pista-campo">${frase(f.instrucciones)}</p>

    <h2>${frase(f.paso_3)}</h2>
    <div className="campo">
      <label htmlFor="firma-fichero">${frase(f.subir)}</label>
      <input id="firma-fichero" type="file" />
    </div>
    <div className="barra-acciones">
      <${Boton} etiqueta=${f.subir} accion="firmar-subir" />
      <${Boton}
        etiqueta=${acciones.volver}
        accion="inicio"
        datos=${{ ir: "mi_cuaderno" }}
        clase="boton-claro"
      />
    </div>
  `;
}

/** El elemento de React de esta pantalla, ya con sus propiedades puestas. */
export function pantallaDeFirmar(propiedades) {
  return html`<${PantallaFirmar}
    textos=${propiedades.textos}
    nombreDelFichero=${propiedades.nombreDelFichero}
    firmado=${propiedades.firmado}
    error=${propiedades.error}
    estado=${propiedades.estado}
    avisos=${propiedades.avisos}
  />`;
}
