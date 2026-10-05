/*
 * venta_ajuste.js — Apuntar una devolución o un ajuste de peso, humedad o calidad (T12).
 *
 * POR QUÉ NO ES UN NÚMERO SUELTO, QUE ES LO QUE ESTA PANTALLA VIENE A IMPEDIR
 *
 * Lo pide el contrato con estas palabras (§4, S12): «Registrar devoluciones y ajustes de
 * peso/humedad/calidad **con evidencia y origen**». Un número que cambia el importe de una entrega sin
 * decir de dónde sale es exactamente lo que este programa no puede tener: dentro de un año, con una
 * inspección delante —o con el comprador discutiendo la cuenta—, nadie sabría si esos 3.000 kg de menos
 * son una devolución, una báscula distinta o un error de tecleo.
 *
 * Por eso las cuatro preguntas obligatorias, en el orden en que se contestan de verdad:
 *
 *  1. **Qué ha pasado** (el tipo): una devolución, el peso, la humedad o la calidad. Cuatro cosas
 *     distintas que se cuentan de cuatro maneras.
 *  2. **Cuánto cambia**: los kilos y los euros, **con signo** (lo que devuelven resta). Cualquiera de los
 *     dos puede quedarse en blanco —un ajuste de calidad acordado en euros no mueve ni un kilo—, pero no
 *     los dos: un apunte que no ajusta nada no se apunta, y se dice por qué.
 *  3. **Quién lo dice** (el origen): el cliente, la báscula, un análisis o un acuerdo. Es la pregunta que
 *     contesta «¿y esto quién lo dice?».
 *  4. **Por qué**, con las palabras del agricultor.
 *
 * Y EL PAPEL, QUE PUEDE FALTAR
 *
 * La descripción de la evidencia (el número del boletín, lo que dijo el básculero) se escribe aquí; el
 * fichero en sí se sube después. **Un ajuste sin papel se puede apuntar** —en el campo hay veces que el
 * papel llega más tarde—, y entonces la pantalla lo dice («sin papel adjunto») en vez de dar por bueno
 * que lo hay. Lo que no se puede es que un número entre en el importe sin que nadie sepa de dónde sale.
 *
 * Lo que no hace: ni una cuenta (los deltas los suma el servidor con `Decimal`, y el importe de la entrega
 * con ellos) y ni una frase escrita a mano.
 */

import { Boton, Botones, frase, html } from "../componentes.js";
import { Campo, Elegir } from "../piezas/campo_de_un_importe.js";

/** Un ajuste que ya está apuntado, con lo que trae dicho y si trae papel. */
function AjusteApuntado({ ajuste, entrega, textos }) {
  const v = textos.venta || {};
  return html`
    <li>
      <strong>${frase(ajuste.etiqueta_tipo)}</strong>
      <dl>
        <div className="resumen-dato">
          <dt>${frase(v.tabla_importe)}</dt>
          <dd>${frase(ajuste.texto_importe)}</dd>
        </div>
        <div className="resumen-dato">
          <dt>${frase(v.ajuste_cantidad)}</dt>
          <dd>${frase(ajuste.cantidad === null || ajuste.cantidad === undefined ? "" : String(ajuste.cantidad))}</dd>
        </div>
        <div className="resumen-dato">
          <dt>${frase(v.ajuste_origen)}</dt>
          <dd>${frase(ajuste.etiqueta_origen)}</dd>
        </div>
        <div className="resumen-dato">
          <dt>${frase(v.ajuste_motivo)}</dt>
          <dd>${frase(ajuste.motivo)}</dd>
        </div>
        <div className="resumen-dato">
          <dt>${frase(v.ajuste_evidencia)}</dt>
          <dd>${frase(ajuste.tiene_papel ? ajuste.nombre_del_papel || "" : v.ajuste_sin_papel)}</dd>
        </div>
      </dl>
      <${Botones}
        botones=${[
          {
            etiqueta: v.ajuste_anular,
            accion: "ajuste-anular",
            datos: { id: ajuste.id, venta: entrega.id },
            clase: "boton-claro",
            sencillo: true,
          },
        ]}
        barra=${false}
      />
    </li>
  `;
}

/**
 * La pantalla entera.
 *
 * Propiedades:
 *
 *  - `textos`: `{ venta, acciones }` del servidor.
 *  - `entrega`: `{ id, producto, texto_cantidad }`, ya preparado por `app.js`.
 *  - `borrador`: lo que se lleva escrito (el tipo y el origen se eligen con botones).
 *  - `tipos` y `origenes`: las dos listas cerradas del servidor, **con su orden y con su nombre**.
 *  - `ajustes`: lo que ya tiene apuntado esta entrega.
 *  - `error`: lo que ha dicho el servidor, o nada.
 */
export function PantallaAjuste({
  textos = {},
  entrega = {},
  borrador = {},
  tipos = [],
  origenes = [],
  ajustes = [],
  error = "",
}) {
  const v = textos.venta || {};
  const acciones = textos.acciones || {};
  return html`
    <h1>${frase(v.ajuste_titulo)}</h1>
    <p className="pista">${frase(v.ajuste_explica)}</p>
    ${error ? html`<p className="aviso-error" role="alert">${frase(error)}</p>` : null}
    <dl>
      <div className="resumen-dato">
        <dt>${frase(v.tabla_producto)}</dt>
        <dd>${frase(entrega.producto || "")}</dd>
      </div>
      <div className="resumen-dato">
        <dt>${frase(v.tabla_cantidad)}</dt>
        <dd>${frase(entrega.texto_cantidad || "")}</dd>
      </div>
      <div className="resumen-dato">
        <dt>${frase(v.tabla_importe)}</dt>
        <dd>${frase(entrega.texto_importe_total || "")}</dd>
      </div>
    </dl>

    <${Elegir}
      rotulo=${v.ajuste_tipo}
      opciones=${tipos}
      accion="ajuste-elegir-tipo"
      campo="tipo"
      elegido=${borrador.tipo}
    />
    <${Campo}
      id="ajuste-cantidad"
      etiqueta=${v.ajuste_cantidad}
      pista=${v.ajuste_cantidad_pista}
      tipo="numero"
      valor=${borrador.cantidad}
    />
    <${Campo}
      id="ajuste-importe"
      etiqueta=${v.ajuste_importe}
      pista=${v.ajuste_importe_pista}
      tipo="numero"
      valor=${borrador.importe}
    />
    <${Elegir}
      rotulo=${v.ajuste_origen}
      pista=${v.ajuste_origen_pista}
      opciones=${origenes}
      accion="ajuste-elegir-origen"
      campo="origen"
      elegido=${borrador.origen}
    />
    <${Campo}
      id="ajuste-motivo"
      etiqueta=${v.ajuste_motivo}
      pista=${v.ajuste_motivo_pista}
      valor=${borrador.motivo}
    />
    <${Campo}
      id="ajuste-evidencia"
      etiqueta=${v.ajuste_evidencia}
      pista=${v.ajuste_evidencia_pista}
      valor=${borrador.evidencia_descripcion}
    />

    ${
      // Lo que ya tiene apuntado esta entrega, con **si trae papel o no**: un ajuste sin papel se dice, no
      // se da por bueno. Y se puede quitar, con su motivo, sin que se borre el papel que traía.
      ajustes.length
        ? html`
            <h2>${frase(v.ajustes_de_esta_entrega)}</h2>
            <ul className="lista">
              ${ajustes.map(
                (ajuste, indice) => html`<${AjusteApuntado}
                  key=${indice}
                  ajuste=${ajuste}
                  entrega=${entrega}
                  textos=${textos}
                />`,
              )}
            </ul>
          `
        : null
    }

    <div className="barra-acciones">
      <button type="button" className="boton" data-accion="ajuste-guardar">${frase(acciones.guardar)}</button>
      <${Boton} etiqueta=${acciones.volver} accion="ventas-ver" clase="boton-claro" />
    </div>
  `;
}

/** El elemento de React de esta pantalla, ya con sus propiedades puestas. */
export function pantallaDeAjuste(propiedades) {
  return html`<${PantallaAjuste}
    textos=${propiedades.textos}
    entrega=${propiedades.entrega}
    borrador=${propiedades.borrador}
    tipos=${propiedades.tipos}
    origenes=${propiedades.origenes}
    ajustes=${propiedades.ajustes}
    error=${propiedades.error}
  />`;
}
