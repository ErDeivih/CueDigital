/*
 * lista_para_elegir.js — La lista de botones con la que el asistente pregunta «¿cuál?».
 *
 * POR QUÉ EXISTE ESTE FICHERO
 *
 * La mitad de los pasos del asistente son la misma pantalla: una lista de botones donde el agricultor
 * toca el que quiere (la tierra, el producto, la nave, la máquina, el trabajo que ha hecho). Estaban
 * escritos **siete veces** en `app.js` con la misma forma, y cada copia se acordaba de cosas distintas:
 * unas ponían el título, otras la pista, otras el aviso con su botón para arreglarlo.
 *
 * Al pasar esos pasos a React se ha escrito **una vez**: aquí. Lo que cambia de un paso a otro —qué
 * botones salen, con qué texto y con qué pista— lo prepara `app.js`, que es quien conoce los datos.
 * Este fichero **no mira el estado de la aplicación**: recibe la lista hecha.
 *
 * LO QUE SE CONSERVA A PROPÓSITO
 *
 *  1. **El aviso va con el botón que lo arregla.** Cuando no hay ninguna tierra dada de alta, un aviso
 *     solo deja al agricultor sin salida: dice que añada una parcela y no hay dónde. Por eso el aviso
 *     y su botón viajan juntos, en la misma propiedad.
 *  2. **Cada bloque con su título y su pista**, en el orden en que se le pasan: las tierras primero y
 *     las salidas («no es una parcela») después, que es lo que decidió la guía de interfaz.
 *  3. **El botón es el de siempre** (`Boton`, de `componentes.js`): los mismos `data-*`, que son lo
 *     que lee el manejador de clics de `app.js`. Si aquí se escribiera un botón a mano, el agricultor
 *     tocaría y no pasaría nada.
 *  4. **Ninguna frase escrita aquí**: los textos llegan por propiedades, del servidor.
 *
 * El componente es PURO: no llama a `fetch`, no lee `localStorage` y no toca el DOM.
 */

import { Boton, BotonSencillo, frase, html } from "../componentes.js";
import { AyudaDeUnCampo } from "./ayuda_de_un_campo.js";
import { Tarjeta } from "./tarjeta.js";

/**
 * Un bloque de la lista: un título, una pista y sus botones. Cualquiera de los tres puede faltar.
 *
 * El título y la pista se ponen **solo si vienen**: un `<h2>` vacío deja un hueco raro en medio de la
 * pantalla, y en el asistente eso se nota mucho porque cada paso es una pregunta sola.
 *
 * **Dos formas de botón, y la diferencia importa**: el botón normal (lo que se pregunta casi siempre:
 * un producto, una máquina, un trabajo) y la **tarjeta** (ver `tarjeta.js`), que lleva el dibujo de la
 * forma de la tierra porque con cincuenta y una tierras una fila de texto no se distingue de la de al
 * lado. Cuál es cuál lo dice `tarjeta: true`, que prepara `app.js`: aquí no se adivina por los datos
 * que traiga.
 */
function Bloque({ titulo, pista, botones = [] }) {
  return html`
    ${titulo ? html`<h2>${frase(titulo)}</h2>` : null}
    ${pista ? html`<p className="pista-campo">${frase(pista)}</p>` : null}
    ${botones.map((boton, indice) =>
      boton.tarjeta
        ? html`
            <${Tarjeta}
              key=${indice}
              etiqueta=${boton.etiqueta}
              lineas=${boton.lineas}
              dibujo=${boton.dibujo}
              avisos=${boton.avisos}
              elegida=${boton.elegida}
              accion=${boton.accion}
              datos=${boton.datos}
              textos=${boton.textos}
            />
          `
        : html`
            <${Boton}
              key=${indice}
              etiqueta=${boton.etiqueta}
              pista=${boton.pista}
              icono=${boton.icono}
              accion=${boton.accion}
              datos=${boton.datos}
              clase=${boton.clase}
            />
          `,
    )}
  `;
}

/**
 * La lista entera: el aviso (si lo hay), sus bloques y su ayuda.
 *
 * Propiedades:
 *
 *  - `aviso`: `{ texto, boton, pista }` o nada. `texto` es lo que se le dice al agricultor y `boton` es
 *    el botón que lo arregla (con la misma forma que los demás: `etiqueta`, `icono`, `accion`, `datos`,
 *    `clase`). Si el botón lleva `sencillo: true` se pinta **sin icono y sin flecha**, que es como
 *    estaba en la interfaz vieja en algunos avisos (el de «no hay análisis de esta parcela»): es un
 *    botón que abre una cosa concreta, no un camino que saca de la pantalla. `pista` es la explicación
 *    que va **debajo del aviso**: sirve para decir qué se puede hacer igualmente («el trabajo se apunta
 *    sin máquina»), que es lo que evita que el agricultor crea que no puede seguir. Si el aviso viene,
 *    **los bloques de botones no se enseñan**: cuando no hay nada que elegir, la lista está vacía y lo
 *    único que hace falta es el camino para arreglarlo.
 *  - `bloques`: los bloques de botones, ya preparados y en su orden.
 *  - `ayuda`: `{ datos, rotulos }` o nada. Es la explicación que va **debajo de toda la lista**, para
 *    las preguntas que la necesitan (el motivo por el que se echó el producto, con qué máquina se
 *    aplicó). Va después de los bloques y no dentro: es lo que explica la pregunta entera, no uno de
 *    sus botones.
 */
export function ListaParaElegir({ aviso = null, bloques = [], ayuda = null }) {
  if (aviso && aviso.texto) {
    return html`
      <div className="aviso">${frase(aviso.texto)}</div>
      ${aviso.pista ? html`<p className="pista-campo">${frase(aviso.pista)}</p>` : null}
      ${
        aviso.boton
          ? aviso.boton.sencillo
            ? html`
                <${BotonSencillo}
                  etiqueta=${aviso.boton.etiqueta}
                  accion=${aviso.boton.accion}
                  datos=${aviso.boton.datos}
                  clase=${aviso.boton.clase}
                />
              `
            : html`
                <${Boton}
                  etiqueta=${aviso.boton.etiqueta}
                  icono=${aviso.boton.icono}
                  accion=${aviso.boton.accion}
                  datos=${aviso.boton.datos}
                  clase=${aviso.boton.clase}
                />
              `
          : null
      }
    `;
  }
  return html`
    ${bloques.map(
      (bloque, indice) => html`
        <${Bloque}
          key=${indice}
          titulo=${bloque.titulo}
          pista=${bloque.pista}
          botones=${bloque.botones}
        />
      `,
    )}
    <${AyudaDeUnCampo} datos=${ayuda ? ayuda.datos : null} rotulos=${ayuda ? ayuda.rotulos : null} />
  `;
}

/** El elemento de React de esta lista, ya con sus propiedades puestas. */
export function listaParaElegir(propiedades) {
  return html`
    <${ListaParaElegir}
      aviso=${propiedades.aviso}
      bloques=${propiedades.bloques}
      ayuda=${propiedades.ayuda}
    />
  `;
}
