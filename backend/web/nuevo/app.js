/**
 * app.js — La pantalla nueva (`/nuevo/`).
 *
 * QUÉ ES ESTO
 *
 * El armazón (barra superior con la finca, la campaña, la cobertura y la cuenta; barra
 * lateral en el ordenador; barra de cinco destinos en el móvil) y las dos primeras
 * pantallas: «Hoy» y «Mis tierras».
 *
 * REGLAS QUE SE CUMPLEN AQUÍ
 *
 *  1. Los textos que lee el agricultor **no se escriben aquí**: viven en `modelo.js`
 *     (`textos`), en un solo sitio, y hay una prueba que los revisa contra la lista de
 *     palabras prohibidas del proyecto.
 *  2. Un fallo de la red **no es «no hay nada»**: son estados distintos y se dicen
 *     distintos. Sin cuenta se ofrece entrar; si no llega, se ofrece volver a intentarlo.
 *  3. Las tierras pueden estar en municipios distintos y no caben en una imagen: por eso
 *     hay **selector de municipio**, zoom y la caja se calcula del municipio elegido.
 *     Una tierra sin forma se enseña como punto en su centro; sin centro ni forma, se
 *     dice «sin mapa» y no se dibuja un cuadro inventado.
 *  4. La lógica que se puede probar sin navegador está en `modelo.js`, no aquí.
 *
 * Sin compilación: React 18 UMD y `htm` vienen de `/vendor/` (los ficheros oficiales,
 * con su licencia). Donde corre esto no hay Node ni paso de compilación.
 */

import {
  ALTO_MAPA,
  ANCHO_MAPA,
  CLAVE_TOKEN,
  agruparPorMunicipio,
  ajustarBbox,
  bboxDeMunicipio,
  bboxDelConjunto,
  calcularTotales,
  datosDelPanel,
  decidirEstado,
  etiquetaCampana,
  filtrarTierras,
  formateaNumero,
  municipioDeTierra,
  proyeccionDePunto,
  rutaDeAnillo,
  sinMapa,
  textos,
  textoRelleno,
  urlDelMapa,
} from "./modelo.js";

const html = htm.bind(React.createElement);
const { useEffect, useMemo, useState } = React;

const RUTA_HOY = "/api/nuevo/hoy";
const RUTA_TIERRAS = "/api/nuevo/tierras";

/** Los límites del servidor para una zona del mapa (grados). El servidor los vuelve a mirar. */
const LADO_MINIMO = 0.0008;
const LADO_MAXIMO = 0.5;
const PASO_DE_ZOOM = 0.6;

// ---------------------------------------------------------------- iconos

function Icono({ nombre, tamano = 24 }) {
  const comun = {
    width: tamano,
    height: tamano,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 2,
    strokeLinecap: "round",
    strokeLinejoin: "round",
    "aria-hidden": "true",
    focusable: "false",
  };

  switch (nombre) {
    case "hoy":
      return html`<svg ...${comun}><path d="M3 10.5 12 3l9 7.5" /><path d="M5.5 9.5V21h13V9.5" /><path d="M10 21v-6h4v6" /></svg>`;
    case "tierras":
      return html`<svg ...${comun}><path d="M9 4 3 6v14l6-2 6 2 6-2V4l-6 2-6-2Z" /><path d="M9 4v14" /><path d="M15 6v14" /></svg>`;
    case "apuntar":
      return html`<svg ...${comun}><path d="M4 20l4-1 10-10a2.5 2.5 0 0 0-3.5-3.5L4.5 15.5 4 20Z" /></svg>`;
    case "cuaderno":
      return html`<svg ...${comun}><path d="M12 6c-2-1.5-4.5-2-7-2v14c2.5 0 5 .5 7 2 2-1.5 4.5-2 7-2V4c-2.5 0-5 .5-7 2Z" /><path d="M12 6v14" /></svg>`;
    case "puntos":
      return html`<svg ...${comun}><circle cx="5" cy="12" r="1.5" /><circle cx="12" cy="12" r="1.5" /><circle cx="19" cy="12" r="1.5" /></svg>`;
    case "campana":
      return html`<svg ...${comun}><rect x="3" y="5" width="18" height="16" rx="2" /><path d="M8 3v4M16 3v4M3 10h18" /></svg>`;
    case "pac":
      return html`<svg ...${comun}><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8Z" /><path d="M14 3v5h5" /><path d="m9 14 2 2 4-4" /></svg>`;
    case "documentos":
      return html`<svg ...${comun}><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7Z" /></svg>`;
    case "persona":
      return html`<svg ...${comun}><path d="M16 20v-1.5a3.5 3.5 0 0 0-3.5-3.5h-5A3.5 3.5 0 0 0 4 18.5V20" /><circle cx="10" cy="8" r="3.5" /><path d="M20 20v-1.5a3.5 3.5 0 0 0-2.5-3.35" /><path d="M15.5 4.6a3.5 3.5 0 0 1 0 6.8" /></svg>`;
    case "mas":
      return html`<svg ...${comun}><path d="M12 5v14M5 12h14" /></svg>`;
    case "menos":
      return html`<svg ...${comun}><path d="M5 12h14" /></svg>`;
    case "centrar":
      return html`<svg ...${comun}><circle cx="12" cy="12" r="6.5" /><path d="M12 2.5v3M12 18.5v3M2.5 12h3M18.5 12h3" /></svg>`;
    case "aviso":
      return html`<svg ...${comun}><path d="M12 4 3 20h18L12 4Z" /><path d="M12 10v3" /><path d="M12 16.5h.01" /></svg>`;
    case "cerrar":
      return html`<svg ...${comun}><path d="m6 6 12 12M18 6 6 18" /></svg>`;
    default:
      return null;
  }
}

// ---------------------------------------------------------------- datos

function leerToken() {
  try {
    return window.localStorage.getItem(CLAVE_TOKEN) || "";
  } catch (fallo) {
    return "";
  }
}

function borrarToken() {
  try {
    window.localStorage.removeItem(CLAVE_TOKEN);
  } catch (fallo) {
    /* Si el navegador no deja tocar el almacén, se sigue: solo se pedirá entrar otra vez. */
  }
}

/**
 * Trae una pantalla y dice en qué estado está. El estado no se queda en «cargando» para
 * siempre: cada intento empieza de cero, y un 401 o un fallo de red se dicen distinto.
 */
function usarPantalla(ruta, activa) {
  const [conToken, setConToken] = useState(Boolean(leerToken()));
  const [estado, setEstado] = useState("cargando");
  const [datos, setDatos] = useState(null);
  const [intento, setIntento] = useState(0);

  useEffect(() => {
    if (!activa) return undefined;

    const token = leerToken();
    setConToken(Boolean(token));
    if (!token) {
      setEstado("sin-permiso");
      setDatos(null);
      return undefined;
    }

    let vivo = true;
    const control = new AbortController();
    setEstado("cargando");

    fetch(ruta, {
      headers: { Authorization: `Bearer ${token}` },
      signal: control.signal,
    })
      .then(async (respuesta) => {
        if (!vivo) return;
        // 401: no hay vale o ha caducado. 403: la cuenta no puede ver esta finca. Los dos
        // acaban donde el agricultor puede arreglarlo: volver a entrar.
        if (respuesta.status === 401 || respuesta.status === 403) {
          borrarToken();
          setConToken(false);
          setEstado("sin-permiso");
          setDatos(null);
          return;
        }
        if (!respuesta.ok) {
          setEstado("error");
          return;
        }
        const cuerpo = await respuesta.json();
        if (!vivo) return;
        setDatos(cuerpo);
        setEstado("listo");
      })
      .catch((fallo) => {
        if (!vivo || fallo.name === "AbortError") return;
        setEstado("error");
      });

    return () => {
      vivo = false;
      control.abort();
    };
  }, [ruta, activa, intento]);

  return { estado, datos, conToken, reintentar: () => setIntento((n) => n + 1) };
}

function inicialesDe(nombre) {
  const palabras = String(nombre || "")
    .trim()
    .split(/\s+/)
    .filter(Boolean);
  if (!palabras.length) return "";
  const primera = palabras[0].charAt(0);
  const segunda = palabras.length > 1 ? palabras[palabras.length - 1].charAt(0) : "";
  return (primera + segunda).toUpperCase();
}

function fechaDe(valor) {
  if (!valor) return "";
  const partes = String(valor).slice(0, 10).split("-");
  if (partes.length === 3) return `${partes[2]}/${partes[1]}/${partes[0]}`;
  return String(valor);
}

/** Acercar o alejar sin pasarse de lo que el servidor puede dibujar. */
function zoomSobre(caja, factor) {
  const nueva = ajustarBbox(caja, factor);
  if (!nueva) return caja;
  const lado = Math.max(nueva[2] - nueva[0], nueva[3] - nueva[1]);
  if (lado < LADO_MINIMO || lado > LADO_MAXIMO) return caja;
  return nueva;
}

// ---------------------------------------------------------------- estados

function EstadoCargando({ mensaje }) {
  return html`<div className="estado" role="status" aria-live="polite">
    <p className="estado__texto">${mensaje}</p>
  </div>`;
}

function EstadoFallo({ mensaje, alReintentar }) {
  return html`<div className="estado estado--fallo" role="alert">
    <p className="estado__texto">${mensaje}</p>
    <button type="button" className="boton" data-reintentar onClick=${alReintentar}>${textos.comun.reintentar}</button>
  </div>`;
}

function EstadoSinPermiso({ mensaje }) {
  return html`<div className="estado">
    <p className="estado__texto">${mensaje}</p>
    <a className="boton boton--principal" data-entrar href="/">${textos.comun.entrar}</a>
  </div>`;
}

function EstadoVacio({ mensaje, textoBoton }) {
  return html`<div className="estado">
    <p className="estado__texto">${mensaje}</p>
    <a className="boton boton--principal" data-traer-tierras href="/">${textoBoton}</a>
  </div>`;
}

// ---------------------------------------------------------------- armazón

function BarraSuperior({ finca, campana, cuenta, sinCobertura }) {
  const nombreFinca = (finca && finca.nombre) || textos.app.nombre;
  const partesCampana = [etiquetaCampana(campana), finca && finca.municipio].filter(Boolean);
  const claseConexion = sinCobertura ? "aviso-conexion aviso-conexion--sin" : "aviso-conexion";
  const textoConexion = sinCobertura ? textos.app.sinCobertura : textos.app.conCobertura;
  const iniciales = inicialesDe(cuenta && cuenta.nombre);
  const contenidoCuenta = iniciales || html`<${Icono} nombre="persona" tamano=${20} />`;

  return html`<header className="barra-superior">
    <div className="barra-superior__finca">
      <span className="barra-superior__nombre">${nombreFinca}</span>
      <span className="barra-superior__campana">${partesCampana.join(" · ")}</span>
    </div>
    <div className="barra-superior__derecha">
      <span className=${claseConexion}>
        <span className="punto" aria-hidden="true"></span>
        ${textoConexion}
      </span>
      <a className="cuenta" href="/" aria-label=${textos.nav.cuenta}>${contenidoCuenta}</a>
    </div>
  </header>`;
}

function claseNav(activa) {
  return activa ? "nav__enlace nav__enlace--activo" : "nav__enlace";
}

function BarraLateral({ vista, ir }) {
  const claseHoy = claseNav(vista === "hoy");
  const claseTierras = claseNav(vista === "tierras");

  return html`<nav className="barra-lateral" data-nav-lateral aria-label="Secciones">
    <p className="barra-lateral__titulo">${textos.app.nombre}</p>
    <div className="nav">
      <button type="button" className=${claseHoy} data-destino="hoy" onClick=${() => ir("hoy")} aria-current=${vista === "hoy" ? "page" : undefined}>
        <span className="nav__icono"><${Icono} nombre="hoy" /></span>
        ${textos.nav.hoy}
      </button>
      <button type="button" className=${claseTierras} data-destino="tierras" onClick=${() => ir("tierras")} aria-current=${vista === "tierras" ? "page" : undefined}>
        <span className="nav__icono"><${Icono} nombre="tierras" /></span>
        ${textos.nav.tierras}
      </button>
      <a className="nav__enlace" href="/" data-destino="cuaderno">
        <span className="nav__icono"><${Icono} nombre="cuaderno" /></span>
        ${textos.nav.cuaderno}
      </a>
      <a className="nav__enlace" href="/">
        <span className="nav__icono"><${Icono} nombre="campana" /></span>
        ${textos.nav.campana}
      </a>
      <a className="nav__enlace" href="/">
        <span className="nav__icono"><${Icono} nombre="pac" /></span>
        ${textos.nav.pac}
      </a>
      <a className="nav__enlace" href="/">
        <span className="nav__icono"><${Icono} nombre="documentos" /></span>
        ${textos.nav.documentos}
      </a>
    </div>
  </nav>`;
}

function claseDestino(activa, base) {
  return activa ? `${base} ${base}--activo` : base;
}

function BarraInferior({ vista, ir }) {
  const claseHoy = claseDestino(vista === "hoy", "barra-inferior__destino");
  const claseTierras = claseDestino(vista === "tierras", "barra-inferior__destino");

  return html`<nav className="barra-inferior" data-nav-inferior aria-label="Los cinco destinos">
    <button type="button" className=${claseHoy} data-destino="hoy" onClick=${() => ir("hoy")} aria-current=${vista === "hoy" ? "page" : undefined}>
      <${Icono} nombre="hoy" />
      ${textos.nav.hoy}
    </button>
    <button type="button" className=${claseTierras} data-destino="tierras" onClick=${() => ir("tierras")} aria-current=${vista === "tierras" ? "page" : undefined}>
      <${Icono} nombre="tierras" />
      ${textos.nav.tierras}
    </button>
    <a className="barra-inferior__apuntar" href="/" data-destino="apuntar" aria-label=${textos.nav.apuntar}>
      <${Icono} nombre="apuntar" tamano=${20} />
      ${textos.nav.apuntar}
    </a>
    <a className="barra-inferior__destino" href="/" data-destino="cuaderno">
      <${Icono} nombre="cuaderno" />
      ${textos.nav.cuaderno}
    </a>
    <a className="barra-inferior__destino" href="/" data-destino="mas">
      <${Icono} nombre="puntos" />
      ${textos.nav.mas}
    </a>
  </nav>`;
}

// ---------------------------------------------------------------- Hoy

function PantallaHoy({ estadoVista, datos, alReintentar }) {
  if (estadoVista === "cargando") return html`<${EstadoCargando} mensaje=${textos.hoy.cargando} />`;
  if (estadoVista === "error") return html`<${EstadoFallo} mensaje=${textos.hoy.fallo} alReintentar=${alReintentar} />`;
  if (estadoVista === "sin-permiso") return html`<${EstadoSinPermiso} mensaje=${textos.hoy.sinPermiso} />`;

  const tierras = (datos && datos.tierras) || { n: 0, ha: 0 };
  const ultimos = ((datos && datos.ultimos) || []).slice(0, 5);
  const nTierras = tierras.n === null || tierras.n === undefined ? 0 : tierras.n;
  const haDeLaFinca = tierras.ha === null || tierras.ha === undefined ? null : tierras.ha;
  const plantillaDelContador = haDeLaFinca === null ? textos.hoy.contadorSinHa : textos.hoy.contador;
  const contador = textoRelleno(plantillaDelContador, {
    n: nTierras,
    ha: haDeLaFinca === null ? "" : formateaNumero(haDeLaFinca),
  });

  const filas = ultimos.map((fila, indice) => {
    const tierra = fila.tierra || "";
    const detalle = fila.tipo ? `${tierra} · ${fila.tipo}` : tierra;
    return html`<li className="lista-ultimos__fila" key=${`ultimo-${indice}`}>
      <span className="lista-ultimos__fecha">${fechaDe(fila.fecha)}</span>
      <span>
        <span className="lista-ultimos__titulo">${fila.titulo || ""}</span>
        <span className="lista-ultimos__tierra">${detalle}</span>
      </span>
    </li>`;
  });

  const vacio = html`<div data-ultimos>
    <p className="estado__texto">${textos.hoy.vacio}</p>
    <p><a className="boton" href="/" data-traer-tierras>${textos.hoy.vacioBoton}</a></p>
  </div>`;

  const lista = html`<ul className="lista-ultimos" data-ultimos=${ultimos.length}>${filas}</ul>`;

  return html`<div>
    <header className="pagina__cabecera" data-titulo=${textos.hoy.titulo}>
      <h1 className="pagina__titulo">${textos.hoy.titulo}</h1>
      <p className="pagina__dato" data-contador-tierras=${contador}>${contador}</p>
    </header>
    <a className="boton boton--principal boton--grande" href="/">
      <${Icono} nombre="apuntar" />
      ${textos.hoy.accion}
    </a>
    <section className="tarjeta" aria-labelledby="ultimos-titulo">
      <h2 className="tarjeta__titulo" id="ultimos-titulo">${textos.hoy.ultimos}</h2>
      ${ultimos.length ? lista : vacio}
    </section>
  </div>`;
}

// ---------------------------------------------------------------- mapa

function Mapa({ municipios, tierras, municipio, caja, elegida, alCambiarMunicipio, alZoom }) {
  const [intento, setIntento] = useState(0);
  const [noLlega, setNoLlega] = useState(false);
  const url = caja ? urlDelMapa(caja, ANCHO_MAPA, ALTO_MAPA) : "";
  const urlConIntento = url ? `${url}&intento=${intento}` : "";

  useEffect(() => {
    setNoLlega(false);
  }, [urlConIntento]);

  const dibujos = [];
  if (caja) {
    for (const tierra of tierras) {
      const esElegida = Boolean(elegida && elegida.id === tierra.id);
      const ruta = rutaDeAnillo(tierra.anillo, caja, ANCHO_MAPA, ALTO_MAPA);
      if (ruta) {
        const clase = esElegida ? "mapa__anillo mapa__anillo--elegido" : "mapa__anillo";
        dibujos.push(html`<path key=${`anillo-${tierra.id}`} className=${clase} d=${ruta} />`);
        continue;
      }
      const punto = proyeccionDePunto(tierra.centro, caja, ANCHO_MAPA, ALTO_MAPA);
      if (punto) {
        const clase = esElegida ? "mapa__punto mapa__punto--elegido" : "mapa__punto";
        dibujos.push(html`<circle key=${`punto-${tierra.id}`} className=${clase} cx=${punto[0]} cy=${punto[1]} r=${esElegida ? 9 : 6} />`);
      }
    }
  }

  const opciones = municipios.map((m) => html`<option key=${m.nombre} value=${m.nombre} data-municipio-opcion=${m.nombre}>${m.nombre}</option>`);

  const fotografía = html`<div className="mapa__lienzo">
    <img className="mapa__foto" data-mapa-imagen src=${urlConIntento} alt=${`${textos.tierras.mapa}: ${municipio}`} onError=${() => setNoLlega(true)} />
    <svg className="mapa__dibujo" viewBox=${`0 0 ${ANCHO_MAPA} ${ALTO_MAPA}`} preserveAspectRatio="none" aria-hidden="true">${dibujos}</svg>
  </div>`;

  const sinCaja = html`<div className="mapa__aviso">
    <p className="estado__texto">${textos.tierras.sinMapa}</p>
  </div>`;

  const falloDeFoto = html`<div className="mapa__aviso" data-mapa-error>
    <p className="estado__texto">${textos.tierras.mapaNoLlega}</p>
    <button type="button" className="boton" onClick=${() => setIntento((n) => n + 1)}>${textos.comun.reintentarCorto}</button>
  </div>`;

  let contenido = sinCaja;
  if (caja) contenido = noLlega ? falloDeFoto : fotografía;

  return html`<section className="mapa" data-mapa aria-labelledby="mapa-titulo">
    <div className="mapa__barra">
      <h2 className="mapa__titulo" id="mapa-titulo">${textos.tierras.mapa}</h2>
      <label className="mapa__selector">
        <span>${textos.tierras.municipio}</span>
        <select className="mapa__campo" data-municipio-selector value=${municipio} onChange=${(evento) => alCambiarMunicipio(evento.target.value)}>
          ${opciones}
        </select>
      </label>
      <div className="mapa__zoom">
        <button type="button" className="boton boton--icono" data-zoom="mas" aria-label=${textos.tierras.zoomMas} onClick=${() => alZoom("mas")}>
          <${Icono} nombre="mas" tamano=${20} />
        </button>
        <button type="button" className="boton boton--icono" data-zoom="menos" aria-label=${textos.tierras.zoomMenos} onClick=${() => alZoom("menos")}>
          <${Icono} nombre="menos" tamano=${20} />
        </button>
        <button type="button" className="boton boton--icono" data-zoom="todo" aria-label=${textos.tierras.zoomTodo} onClick=${() => alZoom("todo")}>
          <${Icono} nombre="centrar" tamano=${20} />
        </button>
      </div>
    </div>
    ${contenido}
    <p className="mapa__pie">${textos.tierras.ayudaDelMapa}</p>
  </section>`;
}

// ---------------------------------------------------------------- panel

function Panel({ tierra, alCerrar }) {
  const filas = datosDelPanel(tierra).map((dato) => html`<div key=${dato.etiqueta}>
    <dt className="panel__dato-etiqueta">${dato.etiqueta}</dt>
    <dd className="panel__dato-valor">${dato.valor}</dd>
  </div>`);

  const otros = Array.isArray(tierra.otros_anios) ? tierra.otros_anios : [];
  const filasDeAnios = otros.map((anio) => html`<tr key=${`anio-${anio.anio}`} data-anio=${anio.anio}>
    <td>${anio.anio}</td>
    <td>${anio.cultivo || textos.tierras.panel.noConsta}</td>
    <td>${anio.superficie_ha === null || anio.superficie_ha === undefined ? textos.tierras.panel.noConsta : formateaNumero(anio.superficie_ha)}</td>
    <td>${anio.variedad || textos.tierras.panel.noConsta}</td>
  </tr>`);

  const cuerpoDeAnios = otros.length
    ? filasDeAnios
    : html`<tr><td colSpan=${4}>${textos.tierras.panel.sinOtrosAnios}</td></tr>`;

  const avisoSinMapa = sinMapa(tierra)
    ? html`<p className="panel__aviso"><${Icono} nombre="aviso" tamano=${20} />${textos.tierras.sinMapa}</p>`
    : null;

  return html`<aside className="panel" data-panel aria-labelledby="panel-alias">
    <div className="panel__cabecera">
      <h2 className="panel__alias" id="panel-alias" data-panel-alias=${tierra.alias}>${tierra.alias}</h2>
      <button type="button" className="boton boton--icono" aria-label=${textos.tierras.panel.cerrar} onClick=${alCerrar}>
        <${Icono} nombre="cerrar" tamano=${20} />
      </button>
    </div>
    ${avisoSinMapa}
    <dl className="panel__datos" data-panel-datos>${filas}</dl>
    <div>
      <h3 className="panel__subtitulo">${textos.tierras.panel.otrosAnios}</h3>
      <table className="panel__tabla" data-panel-otros-anios=${otros.length}>
        <thead>
          <tr>
            <th scope="col">${textos.tierras.panel.anio}</th>
            <th scope="col">${textos.tierras.panel.cultivo}</th>
            <th scope="col">${textos.tierras.panel.hectareas}</th>
            <th scope="col">${textos.tierras.panel.variedad}</th>
          </tr>
        </thead>
        <tbody>${cuerpoDeAnios}</tbody>
      </table>
    </div>
  </aside>`;
}

// ---------------------------------------------------------------- Mis tierras

function PantallaTierras({ estadoVista, datos, alReintentar }) {
  const tierras = (datos && datos.tierras) || [];
  const municipios = (datos && datos.municipios) || [];

  // El servidor nombra el grupo de las tierras sin municipio con la cadena vacía. Aquí se le
  // pone nombre para que la opción del mapa y la cabecera del grupo digan lo mismo, y para que
  // no salga una opción en blanco en el selector.
  const municipiosDelMapa = useMemo(
    () =>
      municipios.map((delServidor) => ({
        ...delServidor,
        nombre: delServidor.nombre || textos.tierras.sinMunicipio,
      })),
    [municipios],
  );

  const [busqueda, setBusqueda] = useState("");
  const [municipio, setMunicipio] = useState("");
  const [elegidaId, setElegidaId] = useState(null);
  const [caja, setCaja] = useState(null);

  const municipioPorDefecto = useMemo(() => {
    const conForma = municipiosDelMapa.find((m) => Array.isArray(m.bbox) && m.bbox.length === 4);
    if (conForma) return conForma.nombre;
    return municipiosDelMapa.length ? municipiosDelMapa[0].nombre : "";
  }, [municipiosDelMapa]);

  useEffect(() => {
    if (!municipio && municipioPorDefecto) setMunicipio(municipioPorDefecto);
  }, [municipio, municipioPorDefecto]);

  useEffect(() => {
    setCaja(null);
  }, [municipio]);

  const cajaBase = useMemo(
    () => bboxDeMunicipio(municipiosDelMapa, municipio) || bboxDelConjunto(municipiosDelMapa),
    [municipiosDelMapa, municipio],
  );
  const cajaDelMapa = caja || cajaBase;

  const elegida = useMemo(() => tierras.find((tierra) => tierra.id === elegidaId) || null, [tierras, elegidaId]);

  if (estadoVista === "cargando") return html`<${EstadoCargando} mensaje=${textos.tierras.cargando} />`;
  if (estadoVista === "error") return html`<${EstadoFallo} mensaje=${textos.tierras.fallo} alReintentar=${alReintentar} />`;
  if (estadoVista === "sin-permiso") return html`<${EstadoSinPermiso} mensaje=${textos.tierras.sinPermiso} />`;

  // Los totales de cabecera los da el servidor (es él quien sabe qué tierras no tienen
  // superficie); si no vinieran, se calculan en la pantalla con la misma regla: si a una le
  // falta la superficie, no se enseña una suma que parece completa.
  const calculados = calcularTotales(tierras);
  const delServidor = (datos && datos.totales) || {};
  const totales = {
    n: delServidor.n === null || delServidor.n === undefined ? calculados.n : delServidor.n,
    ha: "ha" in delServidor ? delServidor.ha : calculados.ha,
    municipios:
      delServidor.municipios === null || delServidor.municipios === undefined
        ? calculados.municipios
        : delServidor.municipios,
  };
  const conSuperficie = totales.ha !== null && totales.ha !== undefined;
  const plantilla = conSuperficie
    ? totales.n === 1
      ? textos.tierras.totalesUno
      : textos.tierras.totales
    : totales.n === 1
      ? textos.tierras.totalesUnoSinHa
      : textos.tierras.totalesSinHa;
  const textoDeTotales = textoRelleno(plantilla, {
    n: totales.n,
    ha: conSuperficie ? formateaNumero(totales.ha) : "",
    m: totales.municipios,
  });

  const cabecera = html`<header className="pagina__cabecera">
    <h1 className="pagina__titulo">${textos.tierras.titulo}</h1>
    <p className="pagina__dato" data-totales=${textoDeTotales}>${textoDeTotales}</p>
    <label className="buscador">
      <span>${textos.tierras.buscador}</span>
      <input
        className="buscador__campo"
        type="search"
        data-buscador
        value=${busqueda}
        placeholder=${textos.tierras.buscadorPista}
        onChange=${(evento) => setBusqueda(evento.target.value)}
      />
    </label>
  </header>`;

  if (estadoVista === "vacio") {
    return html`<div>
      ${cabecera}
      <${EstadoVacio} mensaje=${textos.tierras.vacio} textoBoton=${textos.tierras.traerTierras} />
    </div>`;
  }

  const visibles = filtrarTierras(tierras, busqueda);
  const grupos = agruparPorMunicipio(visibles);
  const delMunicipio = tierras.filter((tierra) => municipioDeTierra(tierra) === municipio);

  const alElegir = (tierra) => {
    setElegidaId(tierra.id);
    const suMunicipio = municipioDeTierra(tierra);
    if (suMunicipio && suMunicipio !== municipio) setMunicipio(suMunicipio);
  };

  const alCambiarMunicipio = (nombre) => {
    setMunicipio(nombre);
    setElegidaId(null);
  };

  const alZoom = (sentido) => {
    if (sentido === "mas") {
      setCaja(zoomSobre(cajaDelMapa, PASO_DE_ZOOM));
      return;
    }
    if (sentido === "menos") {
      setCaja(zoomSobre(cajaDelMapa, 1 / PASO_DE_ZOOM));
      return;
    }
    setCaja(bboxDelConjunto(municipiosDelMapa) || cajaBase);
  };

  const bloques = grupos.map((grupo) => {
    const unidad = textos.tierras.panel.hectareas;
    const superficie = grupo.ha === null ? textos.tierras.panel.noConsta : `${formateaNumero(grupo.ha)} ${unidad}`;
    const cuenta = `${grupo.n === 1 ? `${grupo.n} tierra` : `${grupo.n} tierras`} · ${superficie}`;
    const filas = grupo.tierras.map((tierra) => {
      const esElegida = Boolean(elegida && elegida.id === tierra.id);
      const clase = esElegida ? "tierra tierra--elegida" : "tierra";
      const hectareas = tierra.superficie_ha === null || tierra.superficie_ha === undefined
        ? textos.tierras.panel.noConsta
        : `${formateaNumero(tierra.superficie_ha)} ${textos.tierras.panel.hectareas}`;
      const detalles = [
        tierra.uso_sigpac,
        tierra.cultivo && tierra.cultivo.nombre,
        sinMapa(tierra) ? textos.tierras.sinMapa : null,
      ].filter(Boolean);
      const detalle = detalles.length
        ? html`<span className="tierra__detalle">${detalles.join(" · ")}</span>`
        : null;

      return html`<button
        type="button"
        key=${`tierra-${tierra.id}`}
        className=${clase}
        data-tierra-id=${tierra.id}
        data-seleccionada=${esElegida ? "si" : "no"}
        onClick=${() => alElegir(tierra)}
      >
        <span className="tierra__alias">${tierra.alias}</span>
        <span className="tierra__hectareas">${hectareas}</span>
        ${detalle}
      </button>`;
    });

    return html`<div key=${`grupo-${grupo.nombre}`}>
      <h3 className="grupo__cabecera" data-municipio=${grupo.nombre}>
        <span className="grupo__nombre">${grupo.nombre}</span>
        <span className="grupo__cuenta">${cuenta}</span>
      </h3>
      ${filas}
    </div>`;
  });

  const sinResultados = html`<div className="estado">
    <p className="estado__texto">${textos.tierras.sinResultados}</p>
    <button type="button" className="boton" onClick=${() => setBusqueda("")}>${textos.tierras.quitarBusqueda}</button>
  </div>`;

  const lista = html`<section className="lista-tierras" aria-label=${textos.tierras.titulo}>${bloques}</section>`;

  const detalle = html`<div>
    <${Mapa}
      municipios=${municipiosDelMapa}
      tierras=${delMunicipio}
      municipio=${municipio}
      caja=${cajaDelMapa}
      elegida=${elegida}
      alCambiarMunicipio=${alCambiarMunicipio}
      alZoom=${alZoom}
    />
    ${elegida ? html`<${Panel} tierra=${elegida} alCerrar=${() => setElegidaId(null)} />` : null}
  </div>`;

  return html`<div>
    ${cabecera}
    <div className="tierras">
      ${visibles.length ? lista : sinResultados}
      ${detalle}
    </div>
  </div>`;
}

// ---------------------------------------------------------------- app

function App() {
  const [vista, setVista] = useState("hoy");
  const [arrancada, setArrancada] = useState(false);
  const [sinCobertura, setSinCobertura] = useState(typeof navigator !== "undefined" ? !navigator.onLine : false);

  // El primer pintado es siempre «cargando»: la pantalla acaba de abrirse y todavía no se ha
  // preguntado nada. En el siguiente paso se decide de verdad (sin vale → entrar; si no llega →
  // volver a intentarlo). Así el agricultor no ve un «no hay nada» antes de que nadie haya mirado.
  useEffect(() => {
    setArrancada(true);
  }, []);

  useEffect(() => {
    const alCambiar = () => setSinCobertura(!navigator.onLine);
    window.addEventListener("online", alCambiar);
    window.addEventListener("offline", alCambiar);
    return () => {
      window.removeEventListener("online", alCambiar);
      window.removeEventListener("offline", alCambiar);
    };
  }, []);

  const pantallaHoy = usarPantalla(RUTA_HOY, vista === "hoy");
  const pantallaTierras = usarPantalla(RUTA_TIERRAS, vista === "tierras");

  const actual = vista === "hoy" ? pantallaHoy : pantallaTierras;
  const datosDeLaFinca = pantallaHoy.datos || pantallaTierras.datos || null;

  const lista = vista === "hoy"
    ? ((pantallaHoy.datos && pantallaHoy.datos.ultimos) || [])
    : ((pantallaTierras.datos && pantallaTierras.datos.tierras) || []);

  const estadoVista = arrancada
    ? decidirEstado({
        conToken: actual.conToken,
        cargando: actual.estado === "cargando",
        fallo: actual.estado === "error",
        sinPermiso: actual.estado === "sin-permiso",
        hayDatos: lista.length > 0,
      })
    : "cargando";

  const pantalla = vista === "hoy"
    ? html`<${PantallaHoy} estadoVista=${estadoVista} datos=${pantallaHoy.datos} alReintentar=${pantallaHoy.reintentar} />`
    : html`<${PantallaTierras} estadoVista=${estadoVista} datos=${pantallaTierras.datos} alReintentar=${pantallaTierras.reintentar} />`;

  return html`<div className="app" data-vista=${vista} data-estado=${estadoVista}>
    <${BarraSuperior}
      finca=${datosDeLaFinca && datosDeLaFinca.finca}
      campana=${datosDeLaFinca && datosDeLaFinca.campana}
      cuenta=${datosDeLaFinca && datosDeLaFinca.cuenta}
      sinCobertura=${sinCobertura}
    />
    <div className="cuerpo">
      <${BarraLateral} vista=${vista} ir=${setVista} />
      <main className="contenido" id="contenido">${pantalla}</main>
    </div>
    <${BarraInferior} vista=${vista} ir=${setVista} />
  </div>`;
}

const raiz = document.getElementById("app");
if (raiz) {
  ReactDOM.createRoot(raiz).render(html`<${App} />`);
}
