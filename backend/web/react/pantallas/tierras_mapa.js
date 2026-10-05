/*
 * tierras_mapa.js — Las tierras de la finca, en la tabla y en el mapa, escritas en React (T06).
 *
 * POR QUÉ ESTA PANTALLA
 *
 * Lo pide el contrato en su apartado 2.1, con estas palabras: «Vista de las 64 tierras: tabla y mapa
 * vinculados, con búsqueda por alias y referencia, filtros por cultivo/municipio/estado/PAC,
 * agrupación y selección múltiple. Una fila sin polígono sigue en la tabla y en un grupo «sin
 * forma». Al seleccionar un polígono se enfoca la fila y viceversa; el mapa no debe saltar a otra
 * provincia ni inventar un centro.»
 *
 * Las cinco cosas que el contrato pide, y dónde está cada una:
 *
 *  1. **La tabla con lo que hace falta para reconocer una tierra**: su número (como la llama el
 *     agricultor), su nombre, su referencia del SIGPAC, sus hectáreas, lo que tiene sembrado, su
 *     pueblo, si se ha revisado y si tiene forma. Y una casilla para marcarla.
 *  2. **Buscador y filtros**: por nombre **y por referencia**, y por lo sembrado, el pueblo, la
 *     revisión y lo que se puede declarar. Las opciones y sus recuentos vienen del servidor
 *     (`/api/parcelas/vista`); aquí solo se elige.
 *  3. **Agrupación**: por lo sembrado, por pueblo o por si se les ha medido la forma. El grupo
 *     **«Sin forma»** es el que pide el contrato: una tierra a la que no le ha llegado el polígono
 *     no desaparece de la lista ni se le dibuja un cuadro.
 *  4. **Selección múltiple**: se marcan las que se quieran, con su recuento y con los dos botones de
 *     marcar todas las que se ven y de quitar la selección.
 *  5. **El mapa de la finca**: los trozos de verdad, dibujados encima de la capa que se elija, con su
 *     leyenda. El mapa **no se abre en un sitio cualquiera**: la caja que se mira sale de las formas
 *     que hay (`/api/parcelas/vista` → `mapa.caja`), y si no hay ninguna se dice en vez de inventar
 *     un centro.
 *
 * LO QUE ESTE COMPONENTE **NO** HACE, Y POR QUÉ
 *
 *  · **No se inventa ninguna cifra**: ni un total, ni una media, ni un porcentaje. El pie dice «ves
 *    10 de 64», que son dos recuentos: el de las filas que se ven y el que da el servidor. **No hay
 *    ningún total de hectáreas**: la mitad de las tierras puede tenerlas en blanco, y sumarlas sería
 *    inventarse una cifra (`docs/T02_VALORES_POR_DEFECTO.md`).
 *  · **No monta ni una frase**: todo lo que se lee llega por propiedades. Las frases que llevan un
 *    número dentro (`{cuantas}`) las rellena `app.js`, que es quien tiene los números ya en
 *    castellano; aquí no se une un texto con otro, que es lo que la prueba de «ni una frase escrita
 *    a mano» persigue (`docs/REACT.md`, apartado 6.3).
 *  · **No calcula coordenadas a mano en cada sitio**: `puntosDelTrozo` es una función pura de este
 *    módulo, con prueba propia, y es la única que sabe de la caja y del tamaño de la imagen.
 *  · **No usa la pieza `tabla.js`**, y está decidido: esa pieza pinta una lista con un pie y un panel
 *    al lado, y aquí hacen falta los grupos con su título, la casilla de marcar de cada fila y un pie
 *    que diga cuántas se ven de cuántas. Se ha preferido una tabla propia con **las mismas clases**
 *    (`.tabla`, `.tabla-numero`, `.tabla-enlace`, `.tabla-acciones`) antes que meterle a la pieza tres
 *    modos que no usa nadie más.
 *  · **Nada de `esc()` y nada de `style`**: React escapa solo y los colores viven en el `:root` de
 *    `estilos.css`.
 *
 * EL TOQUE EN EL MAPA NO SE ENGANCHA AQUÍ
 *
 * Es la misma decisión que en la pantalla del SIGPAC (`pantalla/mapa.js`): el manejador de clics es
 * **uno solo** y vive en `document` (`app.js`), así que cada trozo del mapa lleva su `data-accion` y
 * su `data-id`, y al tocarlo se enfoca **su** fila, que es la mitad del enlace entre las dos vistas.
 * El componente no pone ni un manejador de React para eso (el único que pone es el de la imagen que
 * no llega, y es una propiedad que le pasa `app.js`, no una decisión suya).
 */

import { AvisoDeError, Boton, BotonSencillo, OpcionesParaElegir, frase, html } from "../componentes.js";
// **El quitador de tildes es el de siempre** (`nucleo.js`, el mismo que usa el buscador de «mis
// cosas»): copiar aquí un `normalize` propio sería tener dos formas de buscar y una de las dos se
// quedaría atrás. `hecho.js` ya importa de `nucleo.js`, así que no es un camino nuevo.
import { sinTildes } from "../../nucleo.js";

// ---------------------------------------------------------------------------
// Lo que se filtra, lo que se agrupa y cómo se dibuja (funciones puras, con prueba propia)
// ---------------------------------------------------------------------------

/**
 * Un texto, en la forma en la que se busca: sin mayúsculas y sin tildes.
 *
 * **Por qué sin tildes.** El agricultor escribe «penaranda» en el teclado del móvil, y su pueblo se
 * llama «Peñaranda de Bracamonte». Si la búsqueda distinguiera la «ñ» de la «n», escribir su propio
 * pueblo no encontraría nada, y eso es exactamente lo que hace que un buscador no se use.
 */
export function paraBuscar(texto) {
  return sinTildes(texto);
}

/**
 * Un texto del servidor con su hueco relleno (`{cuantas}`, `{total}`).
 *
 * **Por qué se rellena aquí y no en `app.js`.** Porque el número que va dentro **depende del filtro**
 * (cuántas tierras se están viendo), y el filtro lo aplica este componente: si lo rellenara `app.js`
 * tendría que aplicar el mismo filtro otra vez, y el día que uno de los dos cambiara, el pie diría un
 * número y la tabla enseñaría otro. Es el mismo `rellena` de `nucleo.js` y **solo rellena huecos de
 * una plantilla del servidor**: aquí no se une un texto con otro (eso se hace en `app.js`, y hay una
 * prueba que lo persigue).
 */
function rellena(plantilla, datos = {}) {
  return String(plantilla || "").replace(/\{(\w+)\}/g, (todo, nombre) =>
    Object.prototype.hasOwnProperty.call(datos, nombre) ? String(datos[nombre]) : todo,
  );
}

/** ¿Esta tierra cumple el filtro de lo que se puede declarar? Son cuatro hechos, no cuatro opiniones. */
function pasaElFiltroDeLoDeclarable(tierra, pac) {
  if (!pac) return true;
  if (pac === "con_referencia") return Boolean(tierra.tiene_referencia_completa);
  if (pac === "sin_referencia") return !tierra.tiene_referencia_completa;
  if (pac === "con_hectareas") return Boolean(tierra.tiene_hectareas_dichas);
  if (pac === "sin_hectareas") return !tierra.tiene_hectareas_dichas;
  // **Un filtro que no se conoce no filtra.** Es la misma decisión que en `rutas.js` con los
  // parámetros de una dirección: un valor que quizá venga de una pantalla más nueva no puede
  // vaciarle la lista al agricultor.
  return true;
}

/**
 * Los estados de revisión que esta pantalla conoce, que son los del servidor
 * (`versiones_de_recinto.ESTADOS_DE_REVISION`) más el «sin ninguna versión de este año».
 */
const REVISIONES_CONOCIDAS = ["sin_revisar", "revisado", "con_dudas", "sin_version"];

/**
 * Las tierras que se ven, con los filtros puestos.
 *
 * `filtro` es `{q, cultivo, municipio, revision, pac}`, y **vacío quiere decir «no filtrar»**: un
 * filtro en blanco es no tener filtro, igual que en una dirección (`rutas.js`).
 *
 * Y hay una diferencia que importa entre los cinco, dicha aquí para que nadie la «arregle»:
 *
 *  · `q`, `cultivo` y `municipio` filtran por **lo que hay escrito en la tierra** (su nombre, su
 *    referencia, el cultivo, el pueblo). Pedir un cultivo que no tiene nadie devuelve **cero tierras**,
 *    y eso es correcto: el valor es un dato.
 *  · `revision` y `pac` filtran por **un código de una lista cerrada**. Un valor que esta pantalla no
 *    conoce **no filtra**: puede venir de una versión más nueva del programa o de una dirección
 *    guardada hace meses, y vaciarle la lista al agricultor por eso sería peor que no filtrar. Es la
 *    misma decisión que toma `rutas.js` con los parámetros que no entiende.
 */
export function filtrarLasTierras(tierras, filtro = {}) {
  const buscado = paraBuscar(filtro.q || "").trim();
  const revision = REVISIONES_CONOCIDAS.includes(filtro.revision) ? filtro.revision : "";
  // **El pueblo y lo sembrado se cotejan sin distinguir mayúsculas, tildes ni espacios de más**, y el
  // motivo está en los datos de verdad: **el cuaderno del agricultor escribe `MACHACON`** (como lo
  // escribe la Junta) **y la lista oficial dice `Machacón`** (con tilde, `data/municipios_cyl.csv`,
  // municipio 37175): el mismo pueblo escrito de dos maneras según quién lo escriba. Y hay tierras con
  // dos espacios de más dentro del nombre, de teclearlo a mano. Con el cotejo literal, elegir el pueblo
  // en el filtro dejaría fuera las tierras escritas de la otra manera, y el agricultor no entendería
  // por qué.
  //
  // **Dato que se corrigió aquí y no se puede volver a contar mal** (03/10/2026): una medición anterior
  // dio por bueno que el mismo pueblo estaba escrito de dos formas en esta finca (`CALVARRASA DE
  // ARRIBA` en 54 tierras y `Calvarrasa de Arriba` en 1) y **era falso**: se contaron los 65 registros
  // de toda la base sin separar por explotación, y la tierra escrita de la otra manera es de **otra
  // finca**. **En su finca hay 7 municipios y ninguno repetido con otra ortografía** (en toda la base
  // son 8, por esa tierra de la otra explotación: por eso se dice cuál es cuál); el que falta en la
  // lista es `CALVARRASA DE ABAJO`, que es **otro pueblo**. El cotejo sin tildes sigue haciendo falta,
  // pero por el caso de `MACHACON`/`Machacón` y por los espacios, no por aquel.
  //
  // **Y lo que NO se hace: cambiarle el nombre al dato.** La tierra sigue enseñando y guardando su
  // pueblo tal y como está escrito en su cuaderno; lo único que hace el programa es dejar de tratar
  // dos formas de escribirlo como si fueran dos pueblos.
  const pueblo = paraBuscar(filtro.municipio || "");
  const sembrado = paraBuscar(filtro.cultivo || "");
  return (tierras || []).filter((tierra) => {
    if (buscado) {
      const enElNombre = paraBuscar(tierra.alias).includes(buscado);
      const enLaReferencia = paraBuscar(tierra.referencia).includes(buscado);
      // La búsqueda es por nombre **y por referencia del SIGPAC**, que es lo que pide el contrato:
      // son las dos formas que tiene el agricultor de nombrar una tierra.
      if (!enElNombre && !enLaReferencia) return false;
    }
    if (filtro.cultivo === "sin_cultivo") {
      if (tierra.cultivo_clave) return false;
    } else if (sembrado && paraBuscar(tierra.cultivo_clave) !== sembrado) {
      return false;
    }
    if (filtro.municipio === "sin_pueblo") {
      if (tierra.municipio) return false;
    } else if (pueblo && paraBuscar(tierra.municipio) !== pueblo) {
      return false;
    }
    if (revision === "sin_version") {
      if (tierra.estado_revision) return false;
    } else if (revision && tierra.estado_revision !== revision) {
      return false;
    }
    return pasaElFiltroDeLoDeclarable(tierra, filtro.pac);
  });
}

/**
 * Las tierras repartidas en grupos, cada uno con su título.
 *
 * Tres formas de agrupar, y las tres salen de un dato que ya está en la fila:
 *
 *  · **por forma** — dos grupos: «Con su forma medida» y **«Sin forma»**. Es el grupo que pide el
 *    contrato, y es el único sitio donde una tierra sin polígono se ve junta con las que están igual;
 *  · **por lo sembrado** y **por pueblo** — un grupo por valor, y **el grupo de las que no lo tienen
 *    siempre el último** («Sin decir qué tiene»), que es donde el agricultor va a mirar qué le falta.
 *
 * Sin agrupar devuelve **un solo grupo sin título**: así el pintor tiene un camino solo y no dos.
 */
export function agruparLasTierras(tierras, grupo, textos = {}) {
  const t = textos || {};
  const lista = tierras || [];
  if (grupo === "forma") {
    return [
      {
        clave: "con_forma",
        titulo: t.grupo_con_forma || "",
        tierras: lista.filter((una) => una.tiene_forma),
      },
      {
        clave: "sin_forma",
        titulo: t.grupo_sin_forma || "",
        tierras: lista.filter((una) => !una.tiene_forma),
      },
    ].filter((bloque) => bloque.tierras.length);
  }
  if (grupo === "cultivo" || grupo === "municipio") {
    const esCultivo = grupo === "cultivo";
    const clave = (tierra) => (esCultivo ? tierra.cultivo_clave : tierra.municipio);
    const sinNada = esCultivo ? t.sin_cultivo || "" : t.sin_pueblo || "";
    // **Se agrupa por la forma normalizada y se titula con la forma escrita de verdad.** Con los
    // datos reales esto no es un detalle: el mismo pueblo puede estar escrito `MACHACON` (como lo
    // escribe la Junta) y `Machacón` (como lo escribe la lista oficial), y agrupando por el texto tal
    // cual saldrían **dos grupos del mismo pueblo** —el agricultor pensaría que tiene tierras en otro
    // sitio—. El título es la forma que más veces está escrita (y si empatan, la primera por orden
    // alfabético), **nunca una inventada**: el nombre del pueblo de sus tierras es suyo.
    const porClave = new Map();
    for (const tierra of lista) {
      const escrito = (clave(tierra) || "").trim();
      if (!escrito) continue;
      const normal = paraBuscar(escrito);
      if (!porClave.has(normal)) porClave.set(normal, new Map());
      const formas = porClave.get(normal);
      formas.set(escrito, (formas.get(escrito) || 0) + 1);
    }
    const bloques = [...porClave.entries()]
      .map(([normal, formas]) => {
        const masUsada = Math.max(...formas.values());
        const titulo = [...formas.entries()]
          .filter(([, cuantas]) => cuantas === masUsada)
          .map(([escrito]) => escrito)
          .sort((una, otra) => una.localeCompare(otra, "es"))[0];
        return {
          clave: normal,
          titulo,
          tierras: lista.filter((tierra) => paraBuscar(clave(tierra)) === normal),
        };
      })
      .sort((una, otra) => una.titulo.localeCompare(otra.titulo, "es"));
    const huerfanas = lista.filter((tierra) => !(clave(tierra) || "").trim());
    if (huerfanas.length) bloques.push({ clave: "sin_nada", titulo: sinNada, tierras: huerfanas });
    return bloques;
  }
  return [{ clave: "", titulo: "", tierras: lista }];
}

/**
 * Los puntos de un trozo, ya convertidos a píxeles de la imagen del mapa.
 *
 * **La cuenta, y por qué es esta.** La caja que se está mirando son dos coordenadas (oeste, sur,
 * este, norte) y la imagen mide unos píxeles. Un punto cae en:
 *
 *     x = (longitud − oeste) / (este − oeste) × ancho
 *     y = (norte − latitud) / (norte − sur) × alto
 *
 * El **norte va arriba**, que es lo que hace que la foto y las rayas coincidan: si se invirtiera, el
 * dibujo saldría del revés sobre la ortofoto y el agricultor creería que su tierra está en otro
 * sitio. Y se devuelve **un texto por anillo** (no una lista de puntos) porque un trozo partido en
 * dos son dos polígonos, y unirlos dibujaría una raya entre ellos que nadie ha medido.
 */
export function puntosDelTrozo(anillos, caja, ancho, alto) {
  if (!caja || !anillos || !anillos.length) return [];
  const largo = Math.max(Number(ancho) || 1, 1);
  const altoDeLaImagen = Math.max(Number(alto) || 1, 1);
  const anchoDeLaCaja = caja.este - caja.oeste;
  const altoDeLaCaja = caja.norte - caja.sur;
  if (!(anchoDeLaCaja > 0) || !(altoDeLaCaja > 0)) return [];
  return anillos
    .filter((anillo) => anillo && anillo.length >= 3)
    .map((anillo) =>
      anillo
        .map(([longitud, latitud]) => {
          const x = ((longitud - caja.oeste) / anchoDeLaCaja) * largo;
          const y = ((caja.norte - latitud) / altoDeLaCaja) * altoDeLaImagen;
          return `${x.toFixed(1)},${y.toFixed(1)}`;
        })
        .join(" "),
    );
}

// ---------------------------------------------------------------------------
// Las piezas de la pantalla
// ---------------------------------------------------------------------------

/**
 * El buscador y los filtros.
 *
 * El buscador es **descontrolado** (`defaultValue`, no `value`) y lo lee `app.js` por su `id`, que es
 * el patrón de toda la aplicación: React lo pinta y `app.js` lo lee. El `id` no se puede cambiar.
 */
function Filtros({ textos, filtros, filtro }) {
  return html`
    <section className="t06-filtros" aria-label=${frase(textos.filtros_titulo)}>
      <h2 className="t06-titulo-seccion">${frase(textos.filtros_titulo)}</h2>
      <div className="campo">
        <label htmlFor="t06_buscar">${frase(textos.buscar)}</label>
        <div className="t06-buscar">
          <input id="t06_buscar" type="search" defaultValue=${frase(filtro.q || "")} />
          <${BotonSencillo} etiqueta=${textos.buscar_boton} accion="t06-buscar" clase="boton-claro" />
        </div>
      </div>
      <${OpcionesParaElegir}
        rotulo=${textos.filtro_cultivo}
        opciones=${filtros.cultivos}
        accion="t06-filtrar"
        campo="cultivo"
        elegido=${filtro.cultivo || ""}
        todas=${textos.filtro_todas}
      />
      <${OpcionesParaElegir}
        rotulo=${textos.filtro_municipio}
        opciones=${filtros.municipios}
        accion="t06-filtrar"
        campo="municipio"
        elegido=${filtro.municipio || ""}
        todas=${textos.filtro_todas}
      />
      <${OpcionesParaElegir}
        rotulo=${textos.filtro_revision}
        opciones=${filtros.revisiones}
        accion="t06-filtrar"
        campo="revision"
        elegido=${filtro.revision || ""}
        todas=${textos.filtro_todas}
      />
      <${OpcionesParaElegir}
        rotulo=${textos.filtro_pac}
        opciones=${filtros.pac}
        accion="t06-filtrar"
        campo="pac"
        elegido=${filtro.pac || ""}
        todas=${textos.filtro_todas}
      />
      <div className="barra-acciones">
        <${Boton} etiqueta=${textos.quitar_filtros} accion="t06-quitar-filtros" clase="boton-claro" />
      </div>
    </section>
  `;
}

/** El mapa: la capa elegida, los trozos de la finca encima, y la leyenda con la fecha. */
function ElMapa({ textos, mapa, tierras, marcadas, elegida, mismoRecinto }) {
  const t = textos.tierras || {};
  const capas = mapa.capas || {};
  const laQueSeVe = capas[mapa.capa] || {};
  const trozos = (tierras || []).filter((tierra) => (tierra.anillos || []).length);
  // **Varias tierras pueden ser el mismo trozo de tierra.** En los datos de verdad un mismo recinto
  // del cuaderno de la Junta aparece partido en varias líneas de cultivo, así que hay más tierras que
  // referencias distintas. Cuando eso pasa, el trozo se enciende igual para todas —no se elige una
  // fila al azar— y debajo va la frase que dice cuántas son.
  //
  // **Los números, medidos sobre su finca (explotación 1) y dichos con lo que son**: 64 tierras y
  // **51 referencias distintas**; una sola referencia, `37-70-0-0-507-24-1`, la comparten **9 tierras**
  // y otra 6. (En toda la base son 65 tierras y 52 referencias: hay una tierra más en otra explotación,
  // y por eso se dice cuál es cuál — quien vuelva a medir y le salga 52 sabrá que no se ha equivocado,
  // sino que ha medido otra cosa.)
  const delRecinto = (id) =>
    (mismoRecinto || []).some((una) => Number(una) === Number(id)) && (mismoRecinto || []).length > 1;
  return html`
    <section className="t06-mapa" aria-label=${frase(t.mapa_titulo)}>
      <h2 className="t06-titulo-seccion">${frase(t.mapa_titulo)}</h2>
      <p className="pista">${frase(t.mapa_explica)}</p>
      <${OpcionesParaElegir}
        rotulo=${t.cambiar_capa}
        opciones=${Object.keys(capas).map((clave) => ({
          valor: clave,
          texto: capas[clave].titulo || "",
        }))}
        accion="t06-capa"
        campo="capa"
        elegido=${mapa.capa}
        todas=""
      />
      <div className="barra-acciones">
        <${Boton} etiqueta=${t.encajar} accion="t06-encajar" clase="boton-claro" />
        <${Boton} etiqueta=${t.acercar} accion="t06-acercar" clase="boton-claro" />
        <${Boton} etiqueta=${t.alejar} accion="t06-alejar" clase="boton-claro" />
        <${Boton}
          etiqueta=${mapa.ver_mis_tierras ? t.ver_mis_tierras : t.ocultar_mis_tierras}
          accion="t06-ver-mis-tierras"
          clase="boton-claro"
        />
      </div>
      ${
        // **Cuando una capa no llega, no se borra nada y se dice.** El aviso llega desde `app.js`
        // (que es quien sabe que la imagen falló, por la propiedad `alNoLlegarLaImagen`) y sustituye
        // a la imagen: dejar la foto vieja sin fecha sería enseñar una foto que no es la de esta
        // caja, y borrar los trozos dejaría al agricultor sin nada que mirar. Ninguna de las dos
        // cosas: se avisa, los linderos se quedan y la tabla sigue funcionando.
        //
        // **Y sin dirección de imagen no se pinta ninguna imagen**, que es el caso de la finca de
        // verdad (ninguna tierra con su forma medida, así que no hay caja que pedir). Se descubrió
        // con los datos reales: sin esto se pintaba un `<img src="">`, el navegador pedía la propia
        // página como si fuera una foto, esa petición fallaba y la pantalla acababa diciendo que **no
        // se había podido traer la imagen del mapa** cuando lo que pasa es que no hay nada que
        // enseñar. Un aviso que habla de un fallo que no ha ocurrido es peor que no decir nada.
        mapa.fallo
          ? html`<div className="aviso aviso-mirar" role="status">${frase(mapa.fallo)}</div>`
          : mapa.url
            ? html`<img
                className="t06-imagen"
                src=${mapa.url}
                alt=${frase(laQueSeVe.titulo || "")}
                onError=${mapa.alNoLlegarLaImagen}
              />`
            : null
      }
      <div className="t06-mapa-vista">
        <svg
          className="t06-svg"
          viewBox=${`0 0 ${mapa.ancho} ${mapa.alto}`}
          role="img"
          aria-label=${frase(t.mapa_titulo)}
        >
          ${mapa.ver_mis_tierras
            ? trozos.map((tierra) =>
                puntosDelTrozo(tierra.anillos, mapa.caja, mapa.ancho, mapa.alto).map(
                  (puntos, indice) => html`
                    <polygon
                      key=${`${tierra.id}-${indice}`}
                      className=${[
                        "t06-tierra",
                        Number(tierra.id) === Number(elegida) || delRecinto(tierra.id)
                          ? "t06-tierra-elegida"
                          : "",
                        (marcadas || []).some((una) => Number(una) === Number(tierra.id))
                          ? "t06-tierra-marcada"
                          : "",
                      ]
                        .filter(Boolean)
                        .join(" ")}
                      points=${puntos}
                      data-accion="t06-elegir-fila"
                      data-id=${String(tierra.id)}
                    >
                      <title>${frase(tierra.alias)}</title>
                    </polygon>
                  `,
                ),
              )
            : null}
        </svg>
      </div>
      ${
        // Sin ninguna forma que enseñar no se dibuja un cuadro en medio de Castilla y León: se dice.
        mapa.tiene_forma ? null : html`<p className="pista-campo">${frase(t.sin_forma_que_ensenar)}</p>`
      }
      ${
        // Y cuando el trozo que se está mirando lo comparten varias tierras, se dice cuántas: **no se
        // elige una fila al azar**. El texto lo prepara `app.js` (el número lo cuenta él de la misma
        // lista que la tabla, para que no puedan decir cosas distintas).
        mapa.recinto_compartido_texto
          ? html`<div className="aviso aviso-mirar" role="status">${frase(mapa.recinto_compartido_texto)}</div>`
          : null
      }
      ${
        // **Cuando la finca no cabe en una imagen del mapa**, se dice: se está viendo una parte, y
        // tocar una tierra de la lista pone el mapa en ella. Sin esto, el agricultor leería el aviso
        // de la imagen que no llega («puede ser la cobertura») delante de un problema que no tiene
        // nada que ver con la cobertura.
        mapa.no_caben_todas_texto
          ? html`<p className="pista-campo">${frase(mapa.no_caben_todas_texto)}</p>`
          : null
      }
      <div className="t06-leyenda">
        <h3 className="t06-subtitulo">${frase(t.leyenda)}</h3>
        <ul>
          ${(mapa.leyenda || []).map(
            (linea, indice) => html`<li key=${indice}>${frase(linea)}</li>`,
          )}
        </ul>
        <p className="pista-campo">${frase(mapa.capa_avisos_no_esta || "")}</p>
      </div>
    </section>
  `;
}

/** Una fila de la tabla. */
function FilaDeLaTabla({ tierra, textos, marcada, elegida, delMismoRecinto }) {
  const t = textos.tierras || {};
  const encendida = Boolean(delMismoRecinto) || Number(tierra.id) === Number(elegida);
  return html`
    <tr className=${[encendida ? "tabla-fila-elegida" : "", delMismoRecinto ? "t06-mismo-recinto" : ""]
      .filter(Boolean)
      .join(" ")}>
      <td className="t06-casilla">
        <label>
          <input
            type="checkbox"
            checked=${Boolean(marcada)}
            data-accion="t06-marcar"
            data-id=${String(tierra.id)}
            aria-label=${frase(t.marcar_esta)}
          />
        </label>
      </td>
      <td className="tabla-numero">${frase(String(tierra.numero))}</td>
      <td>
        <button
          type="button"
          className="tabla-enlace"
          data-accion="t06-elegir-fila"
          data-id=${String(tierra.id)}
        >
          ${frase(tierra.alias)}
        </button>
        ${
          // **El nombre repetido se dice.** Con los datos de verdad hay tierras que se llaman igual
          // —hasta con la misma superficie—, y en una tabla con selección el agricultor no puede
          // distinguirlas para elegir una. El programa **no le cambia el nombre a sus tierras**: le
          // dice que está repetido, que es lo que le hace mirar el número y la referencia. El texto y
          // el número de veces los prepara `app.js` (el recuento lo da el servidor).
          tierra.nombre_repetido_texto
            ? html`<span className="tabla-pista t06-nombre-repetido">${frase(tierra.nombre_repetido_texto)}</span>`
            : null
        }
      </td>
      <td>
        ${tierra.referencia ? html`<span className="tabla-dato">${frase(tierra.referencia)}</span>` : null}
      </td>
      <td className="tabla-numero">
        ${tierra.superficie_texto
          ? html`<span className="tabla-dato">${frase(tierra.superficie_texto)}</span>`
          : html`<span className="etiqueta-estado etiqueta-estado-mirar">${frase(t.sin_hectareas)}</span>`}
        ${
          // **Y debajo, lo que el agricultor declara este año**, cuando la superficie de la tierra no
          // se sabe. La casilla sigue siendo la superficie de la tierra (la misma regla que el pie y
          // el filtro), y lo declarado va con su nombre para no mezclar dos magnitudes distintas: la
          // que se cultiva y la que se declara. Sin esto, la columna enseñaba un hueco mientras la
          // versión del año sí traía hectáreas (revisión de T06, D1).
          !tierra.superficie_texto &&
          tierra.area_declarada_ha !== null &&
          tierra.area_declarada_ha !== undefined &&
          tierra.hectareas_declaradas_texto
            ? html`<span className="tabla-pista t06-hectareas-declaradas"
                >${frase(tierra.hectareas_declaradas_texto)}</span
              >`
            : null
        }
      </td>
      <td>
        ${tierra.cultivo
          ? html`<span className="tabla-dato">${frase(tierra.cultivo)}</span>`
          : html`<span className="etiqueta-estado etiqueta-estado-mirar">${frase(t.sin_cultivo)}</span>`}
      </td>
      <td>
        ${tierra.municipio ? html`<span className="tabla-dato">${frase(tierra.municipio)}</span>` : null}
      </td>
      <td>
        ${
          // La forma: se dice con palabras, y el color solo no informa (regla de la casa).
          tierra.tiene_forma
            ? html`<span className="tabla-dato">${frase(tierra.forma_texto || "")}</span>`
            : html`<span className="etiqueta-estado etiqueta-estado-mirar">${frase(t.sin_forma)}</span>`
        }
      </td>
      <td>
        ${tierra.revision_texto
          ? html`<span className="tabla-dato">${frase(tierra.revision_texto)}</span>`
          : null}
      </td>
      <td className="tabla-acciones">
        <${BotonSencillo}
          etiqueta=${t.ver_versiones}
          accion="t06-versiones"
          datos=${{ id: tierra.id }}
          clase="boton-claro"
        />
      </td>
    </tr>
  `;
}

/**
 * La tabla entera, con sus grupos.
 *
 * Los grupos son `<tbody>` con su fila de título, que es lo que un lector de pantalla anuncia como
 * el nombre del grupo de filas. Una tierra sin forma cae en el grupo «Sin forma» cuando se agrupa
 * por forma, y **siempre lleva su etiqueta** en la columna de la forma aunque no se agrupe: que una
 * tierra no tenga polígono no puede depender de cómo esté la lista ordenada.
 */
function TablaDeTierras({ textos, bloques, marcadas, elegida, mismoRecinto }) {
  const t = textos.tierras || {};
  const delRecinto = (id) =>
    (mismoRecinto || []).some((una) => Number(una) === Number(id)) && (mismoRecinto || []).length > 1;
  return html`
    <table className="tabla t06-tabla" aria-label=${frase(t.tabla_etiqueta)}>
      <thead>
        <tr>
          <th scope="col" className="t06-casilla">${frase(t.col_marcar)}</th>
          <th scope="col" className="tabla-numero">${frase(t.col_numero)}</th>
          <th scope="col">${frase(t.col_nombre)}</th>
          <th scope="col">${frase(t.col_referencia)}</th>
          <th scope="col" className="tabla-numero">${frase(t.col_hectareas)}</th>
          <th scope="col">${frase(t.col_cultivo)}</th>
          <th scope="col">${frase(t.col_pueblo)}</th>
          <th scope="col">${frase(t.col_forma)}</th>
          <th scope="col">${frase(t.col_revision)}</th>
          <th scope="col">${frase(t.col_acciones)}</th>
        </tr>
      </thead>
      ${(bloques || []).map(
        (bloque) => html`
          <tbody key=${`g-${bloque.clave}`}>
            ${
              bloque.titulo
                ? html`<tr className="t06-grupo">
                    <th scope="colgroup" colSpan=${10}>${frase(bloque.titulo)}</th>
                  </tr>`
                : null
            }
            ${bloque.tierras.map(
              (tierra) => html`
                <${FilaDeLaTabla}
                  key=${tierra.id}
                  tierra=${tierra}
                  textos=${textos}
                  marcada=${(marcadas || []).some((una) => Number(una) === Number(tierra.id))}
                  elegida=${elegida}
                  delMismoRecinto=${delRecinto(tierra.id)}
                />
              `,
            )}
          </tbody>
        `,
      )}
    </table>
  `;
}

// ---------------------------------------------------------------------------
// La pantalla
// ---------------------------------------------------------------------------

/**
 * La pantalla entera.
 *
 * Propiedades (todo lo prepara `app.js`, y todo viene del servidor):
 *
 *  - `textos`: `{ tierras, mapa, acciones }`.
 *  - `vista`: lo que devuelve `/api/parcelas/vista` (`tierras`, `totales`, `mapa`, `filtros`).
 *  - `filtro`: `{q, cultivo, municipio, revision, pac}`. Vacío es «no filtrar».
 *  - `grupo`: `""`, `"cultivo"`, `"municipio"` o `"forma"`.
 *  - `marcadas`: los identificadores marcados, para la selección múltiple.
 *  - `elegida`: el identificador de la tierra enfocada (la fila que se está mirando y su trozo).
 *  - `mapa`: lo del mapa, ya preparado: `{capa, ver_mis_tierras, url, caja, ancho, alto, capas,
 *    tiene_forma, leyenda (las líneas ya escritas), capa_avisos_no_esta, fallo, alNoLlegarLaImagen}`.
 *    La caja sale de las formas que hay; si no hay ninguna, `tiene_forma` va en falso y **no se
 *    dibuja ni una raya**.
 *  - `aviso`: lo que ha dicho el servidor cuando una petición no ha salido bien.
 *
 * El pie y el recuento de lo marcado **los monta este componente**, y es a propósito: los dos
 * dependen del filtro, y el filtro se aplica aquí. Los números son los que da el servidor en
 * `vista.totales` (los de la finca entera) y el de las filas que se ven; las frases son del servidor
 * y el hueco lo rellena `rellena`.
 */
export function PantallaTierrasDeLaExplotacion({
  textos = {},
  vista = {},
  filtro = {},
  grupo = "",
  marcadas = [],
  elegida = null,
  mismoRecinto = [],
  mapa = {},
  aviso = "",
}) {
  const t = textos.tierras || {};
  const acciones = textos.acciones || {};
  const tierras = vista.tierras || [];
  const totales = vista.totales || {};
  const seVen = filtrarLasTierras(tierras, filtro);
  const bloques = agruparLasTierras(seVen, grupo, t);
  // **El pie: dos recuentos y ni una cifra más.** «Ves N de M» cuando hay filtro, y el total del
  // servidor cuando no. Y los tres «sin» de la finca entera, que son los que dicen qué queda por
  // hacer: un dato que falta no es un cero, es trabajo pendiente.
  const pies = (
    seVen.length === tierras.length
      ? [
          rellena(t.pie_todas, { cuantas: totales.tierras }),
          rellena(t.pie_sin_forma, { cuantas: totales.sin_forma }),
          rellena(t.pie_sin_cultivo, { cuantas: totales.sin_cultivo }),
          rellena(t.pie_sin_hectareas, { cuantas: totales.sin_hectareas }),
        ]
      : [
          rellena(t.pie_filtrado, { cuantas: seVen.length, total: totales.tierras }),
          rellena(t.pie_sin_forma, { cuantas: totales.sin_forma }),
        ]
  ).filter(Boolean);
  // El recuento de lo marcado, en singular y en plural: «1 tierras» es lo primero que hace desconfiar
  // de un programa.
  const marcadasTexto = marcadas.length
    ? rellena(marcadas.length === 1 ? t.marcadas_uno : t.marcadas_varios, { cuantas: marcadas.length })
    : t.ninguna_marcada || "";
  return html`
    <h1>${frase(t.titulo)}</h1>
    <p className="pista">${frase(t.explica)}</p>
    <${AvisoDeError} texto=${aviso} />
    <${Filtros} textos=${t} filtros=${vista.filtros || {}} filtro=${filtro} />
    <${OpcionesParaElegir}
      rotulo=${t.agrupar_titulo}
      opciones=${[
        { valor: "cultivo", texto: t.agrupar_cultivo },
        { valor: "municipio", texto: t.agrupar_municipio },
        { valor: "forma", texto: t.agrupar_forma },
      ]}
      accion="t06-agrupar"
      campo="grupo"
      elegido=${grupo}
      todas=${t.agrupar_no}
    />
    <div className="barra-acciones">
      <${Boton} etiqueta=${t.marcar_todas} accion="t06-marcar-todas" clase="boton-claro" />
      <${Boton} etiqueta=${t.desmarcar_todas} accion="t06-desmarcar-todas" clase="boton-claro" />
    </div>
    <p className="pista-campo">${frase(marcadasTexto)}</p>
    ${
      seVen.length
        ? html`<div className="tabla-scroll t06-tabla-scroll">
            <${TablaDeTierras}
              textos=${textos}
              bloques=${bloques}
              marcadas=${marcadas}
              elegida=${elegida}
              mismoRecinto=${mismoRecinto}
            />
          </div>`
        : html`
            <h2>${frase(t.sin_filtros_titulo)}</h2>
            <p className="pista">${frase(t.sin_filtros_pista)}</p>
            <div className="barra-acciones">
              <${Boton} etiqueta=${t.quitar_filtros} accion="t06-quitar-filtros" clase="boton-principal" />
            </div>
          `
    }
    <p className="pista-campo">${(pies || []).filter(Boolean).join(" · ")}</p>
    ${
      // **El mapa dibuja las tierras que pasan el filtro**, no las 64 siempre: es lo que pide el
      // contrato («el mapa respeta la selección declarada») y lo que hace útil filtrar por lo
      // sembrado —se ven en el mapa solo esos trozos—. El pie sigue diciendo el total de la finca,
      // así que el agricultor nunca pierde de vista cuántas se está dejando fuera.
      html`<${ElMapa}
        textos=${textos}
        mapa=${mapa}
        tierras=${seVen}
        marcadas=${marcadas}
        elegida=${elegida}
        mismoRecinto=${mismoRecinto}
      />`
    }
    <div className="barra-acciones">
      <${Boton} etiqueta=${acciones.volver} accion="t06-volver" clase="boton-claro" />
    </div>
  `;
}

/** El elemento de React de esta pantalla, ya con sus propiedades puestas. */
export function pantallaDeLasTierrasDeLaExplotacion(propiedades) {
  return html`<${PantallaTierrasDeLaExplotacion}
    textos=${propiedades.textos}
    vista=${propiedades.vista}
    filtro=${propiedades.filtro}
    grupo=${propiedades.grupo}
    marcadas=${propiedades.marcadas}
    elegida=${propiedades.elegida}
    mismoRecinto=${propiedades.mismoRecinto}
    mapa=${propiedades.mapa}
    aviso=${propiedades.aviso}
  />`;
}
