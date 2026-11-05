/**
 * app.js — La pantalla nueva (`/nuevo/`).
 *
 * QUÉ HAY AQUÍ
 *
 * El armazón (barra superior, barra lateral en el ordenador, barra de cinco destinos en el
 * móvil) y las pantallas: «Hoy», «Mis tierras» y «Añadir tierras» (por código del SIGPAC, con
 * ventana del SIGPAC para coger el recinto en el mapa, y trayendo el cuaderno de la Junta).
 *
 * REGLAS QUE SE CUMPLEN AQUÍ
 *
 *  1. Los textos que lee el agricultor **no se escriben aquí**: viven en `modelo.js`
 *     (`textos`), en un solo sitio, y hay una prueba que los revisa contra la lista de
 *     palabras prohibidas del proyecto.
 *  2. Un fallo de la red **no es «no hay nada»**: son estados distintos y se dicen distintos.
 *     Sin cuenta se ofrece entrar; si no llega, volver a intentarlo.
 *  3. Las tierras pueden estar en municipios distintos y no caben en una imagen: por eso hay
 *     selector de municipio, zoom y colores con leyenda. Una tierra sin forma se enseña como
 *     punto en su centro; sin centro ni forma, se dice «sin mapa».
 *  4. Solo se añaden tierras con datos que vienen del SIGPAC o del cuaderno: no se inventa
 *     ninguna forma ni ninguna superficie.
 *  5. La lógica que se puede probar sin navegador está en `modelo.js`, no aquí.
 *
 * Sin compilación: React 18 UMD y `htm` vienen de `/vendor/` (los ficheros oficiales, con su
 * licencia). Donde corre esto no hay Node ni paso de compilación.
 */

import {
  ALTO_MAPA,
  ANCHO_MAPA,
  CLAVE_TOKEN,
  agruparPorMunicipio,
  ajustarBbox,
  bboxDeMunicipio,
  bboxDelConjunto,
  cajaDeLosRecintos,
  calcularTotales,
  colorDeTierra,
  colorDeUso,
  datosDelPanel,
  decidirEstado,
  etiquetaCampana,
  filtrarTierras,
  formateaNumero,
  importeEnTexto,
  leyendaDe,
  municipioDeTierra,
  normalizaImportacion,
  normalizaQueFalta,
  normalizaResumen,
  proyeccionDeAnillo,
  proyeccionDePunto,
  puntoDelMapa,
  recintosConPuntos,
  referenciasDeTexto,
  rutaDeAnillo,
  sinMapa,
  textos,
  textoRelleno,
  urlDelMapa,
} from "./modelo.js";

const html = htm.bind(React.createElement);
const { useEffect, useMemo, useRef, useState } = React;

const RUTA_HOY = "/api/nuevo/hoy";
const RUTA_TIERRAS = "/api/nuevo/tierras";
const RUTA_RESUMEN = "/api/nuevo/resumen";
const RUTA_QUE_FALTA = "/api/nuevo/que-falta";
const RUTA_BUSCAR = "/api/sigpac/buscar";
const RUTA_PARCELA_UNA = "/api/parcelas/desde-sigpac";
const RUTA_PARCELAS_VARIAS = "/api/parcelas/desde-sigpac/varias";
const RUTA_MAPA_PUNTO = "/api/mapa/punto";
const RUTA_IMPORTAR = "/api/nuevo/importar-cuaderno";
const RUTA_CUADERNO_LEER = "/api/cuaderno-cyl/leer";
const RUTA_CUADERNO_IMPORTAR = "/api/cuaderno-cyl/importar";

/** Los límites del servidor para una zona del mapa (grados). Él los vuelve a mirar. */
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
    case "buscar":
      return html`<svg ...${comun}><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></svg>`;
    case "subir":
      return html`<svg ...${comun}><path d="M12 19V5" /><path d="m6 11 6-6 6 6" /></svg>`;
    case "anadir":
      return html`<svg ...${comun}><path d="M12 5v14M5 12h14" /></svg>`;
    case "comprobar":
      return html`<svg ...${comun}><path d="m5 12.5 4.5 4.5L19 7" /></svg>`;
    default:
      return null;
  }
}

// ---------------------------------------------------------------- puertas

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
    /* Si el navegador no deja tocar el almacén, se sigue: se pedirá entrar otra vez. */
  }
}

/**
 * Una llamada al servidor con el vale. Devuelve el estado, no lanza: la pantalla decide qué
 * enseñar, y un fallo de red nunca se disfraza de «no hay nada».
 */
async function pedir(ruta, opciones = {}) {
  const token = leerToken();
  if (!token) return { estado: "sin-permiso" };
  const cabeceras = { ...(opciones.headers || {}), Authorization: `Bearer ${token}` };
  let respuesta;
  try {
    respuesta = await fetch(ruta, { ...opciones, headers: cabeceras });
  } catch (fallo) {
    return { estado: "error" };
  }
  if (respuesta.status === 401 || respuesta.status === 403) {
    borrarToken();
    return { estado: "sin-permiso" };
  }
  if (respuesta.status === 404 || respuesta.status === 405) return { estado: "no-disponible" };
  if (!respuesta.ok) return { estado: "error", codigo: respuesta.status };
  try {
    return { estado: "ok", datos: await respuesta.json() };
  } catch (fallo) {
    return { estado: "error" };
  }
}

function conCuerpoJson(cuerpo) {
  return {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(cuerpo),
  };
}

function cuerpoDeLaTierra(actual, cambios) {
  return {
    alias: cambios.alias ?? actual.alias,
    ref_sigpac: actual.ref_sigpac,
    provincia: actual.provincia ?? "",
    municipio: actual.municipio ?? "",
    codigo_ine: actual.codigo_ine,
    poligono: actual.poligono,
    numero_parcela: actual.numero_parcela,
    numero_recinto: actual.numero_recinto,
    agregado: actual.agregado ?? 0,
    zona: actual.zona ?? 0,
    referencia_catastral: actual.referencia_catastral,
    superficie_ha: cambios.superficie_ha,
    superficie_oficial: actual.superficie_oficial,
    uso_sigpac: actual.uso_sigpac,
    sistema: actual.sistema,
    pendiente_pct: actual.pendiente_pct,
    masa_agua_cerca: actual.masa_agua_cerca,
    captacion_consumo_humano: actual.captacion_consumo_humano,
    zona_vulnerable_nitratos: actual.zona_vulnerable_nitratos,
  };
}

/**
 * Corregir el nombre y la superficie de una tierra. Se lee la tierra entera primero porque el
 * servidor guarda lo que le llega: mandar solo el nombre borraría el resto. La forma del trozo
 * no se manda y el servidor no la deja tocar.
 */
async function guardarTierra(id, cambios) {
  const leida = await pedir(`/api/parcelas/${id}`);
  if (leida.estado !== "ok") return leida;
  return pedir(`/api/parcelas/${id}`, {
    ...conCuerpoJson(cuerpoDeLaTierra(leida.datos, cambios)),
    method: "PUT",
  });
}

/** Sube el cuaderno y devuelve lo leído y lo importado, en una llamada o en dos. */
async function subirCuaderno(fichero) {
  const token = leerToken();
  if (!token) return { estado: "sin-permiso" };

  const formulario = new FormData();
  formulario.append("fichero", fichero);

  let respuesta;
  try {
    respuesta = await fetch(RUTA_IMPORTAR, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: formulario,
    });
  } catch (fallo) {
    return { estado: "error" };
  }

  if (respuesta.status === 401 || respuesta.status === 403) return { estado: "sin-permiso" };
  if (respuesta.status !== 404 && respuesta.status !== 405) {
    if (!respuesta.ok) return { estado: "error" };
    const datos = await respuesta.json().catch(() => null);
    return { estado: "ok", datos, deUnaVez: true };
  }

  // La puerta de un paso todavía no está: se lee y se importa, que es lo mismo en dos pasos.
  const leer = new FormData();
  leer.append("fichero", fichero);
  const leidoRespuesta = await fetch(RUTA_CUADERNO_LEER, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: leer,
  }).catch(() => null);
  if (!leidoRespuesta || !leidoRespuesta.ok) {
    return { estado: leidoRespuesta && (leidoRespuesta.status === 401 || leidoRespuesta.status === 403) ? "sin-permiso" : "error" };
  }
  const leido = await leidoRespuesta.json();

  const importar = new FormData();
  importar.append("fichero", fichero);
  const importadoRespuesta = await fetch(RUTA_CUADERNO_IMPORTAR, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: importar,
  }).catch(() => null);
  if (!importadoRespuesta || !importadoRespuesta.ok) {
    return { estado: importadoRespuesta && (importadoRespuesta.status === 401 || importadoRespuesta.status === 403) ? "sin-permiso" : "error" };
  }
  const importado = await importadoRespuesta.json();
  return { estado: "ok", datos: { leido, importado }, deUnaVez: false };
}

// ---------------------------------------------------------------- carga

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

    fetch(ruta, { headers: { Authorization: `Bearer ${token}` }, signal: control.signal })
      .then(async (respuesta) => {
        if (!vivo) return;
        if (respuesta.status === 401 || respuesta.status === 403) {
          borrarToken();
          setConToken(false);
          setEstado("sin-permiso");
          setDatos(null);
          return;
        }
        if (!respuesta.ok) {
          setEstado(respuesta.status === 404 || respuesta.status === 405 ? "no-disponible" : "error");
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

/** Una caja que el servidor del mapa acepte: si la finca es muy grande, se abre por una parte. */
function cajaQueSePuedePedir(caja) {
  if (!caja) return null;
  const lado = Math.max(caja[2] - caja[0], caja[3] - caja[1]);
  if (lado <= LADO_MAXIMO) return caja;
  return ajustarBbox(caja, LADO_MAXIMO / lado);
}

function cajaDeLasTierras(tierras, municipios) {
  const conAnillo = (tierras || []).find((tierra) => Array.isArray(tierra.anillo) && tierra.anillo.length >= 3);
  if (conAnillo) {
    const lons = conAnillo.anillo.map((punto) => punto[0]);
    const lats = conAnillo.anillo.map((punto) => punto[1]);
    return cajaQueSePuedePedir([Math.min(...lons), Math.min(...lats), Math.max(...lons), Math.max(...lats)]);
  }
  return cajaQueSePuedePedir(bboxDelConjunto(municipios || []));
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

function EstadoNoDisponible({ alReintentar }) {
  return html`<div className="estado">
    <p className="estado__texto">${textos.comun.todaviaNo}</p>
    <div className="estado__acciones">
      <button type="button" className="boton" data-reintentar onClick=${alReintentar}>${textos.comun.reintentar}</button>
      <a className="boton boton--principal" href="/">${textos.hoy.abrirAppVieja}</a>
    </div>
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
  const claseTierras = claseNav(vista === "tierras" || vista === "alta");

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
  const claseTierras = claseDestino(vista === "tierras" || vista === "alta", "barra-inferior__destino");

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

function BloqueQueFalta({ estado, lista, alReintentar }) {
  if (estado === "cargando") {
    return html`<section className="tarjeta" aria-labelledby="que-falta-titulo">
      <h2 className="tarjeta__titulo" id="que-falta-titulo">${textos.hoy.faltaCuaderno}</h2>
      <p className="estado__texto">${textos.comun.cargando}</p>
    </section>`;
  }
  if (estado === "error" || estado === "no-disponible") {
    return html`<section className="tarjeta" aria-labelledby="que-falta-titulo">
      <h2 className="tarjeta__titulo" id="que-falta-titulo">${textos.hoy.faltaCuaderno}</h2>
      <p className="estado__texto">${textos.comun.todaviaNo}</p>
      <div className="estado__acciones">
        <button type="button" className="boton" data-reintentar onClick=${alReintentar}>${textos.comun.reintentar}</button>
        <a className="boton boton--principal" href="/">${textos.hoy.abrirAppVieja}</a>
      </div>
    </section>`;
  }
  if (estado === "sin-permiso") {
    return html`<section className="tarjeta" aria-labelledby="que-falta-titulo">
      <h2 className="tarjeta__titulo" id="que-falta-titulo">${textos.hoy.faltaCuaderno}</h2>
      <p className="estado__texto">${textos.comun.sinPermiso}</p>
      <a className="boton boton--principal" data-entrar href="/">${textos.comun.entrar}</a>
    </section>`;
  }

  const filas = lista.map((fila, indice) => html`<li className="que-falta__fila" key=${`falta-${indice}`}>
    <span className="que-falta__que">${fila.que}</span>
    <span className="que-falta__donde">${fila.donde || textos.hoy.abrirAppVieja}</span>
  </li>`);
  const contenido = lista.length
    ? html`<ul className="que-falta" data-que-falta=${lista.length}>${filas}</ul>`
    : html`<div data-que-falta="0"><p className="estado__texto">${textos.hoy.queFaltaVacio}</p></div>`;

  return html`<section className="tarjeta" aria-labelledby="que-falta-titulo">
    <h2 className="tarjeta__titulo" id="que-falta-titulo">${textos.hoy.faltaCuaderno}</h2>
    ${contenido}
    <a className="boton" href="/">${textos.hoy.abrirAppVieja}</a>
  </section>`;
}

function VistaHoy({ estadoVista, datos, alReintentar, resumen, queFalta }) {
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

  const contable = normalizaResumen(resumen.estado === "listo" ? resumen.datos : null);
  const falta = normalizaQueFalta(queFalta.estado === "listo" ? queFalta.datos : null);

  return html`<div className="pantalla-hoy">
    <header className="pagina__cabecera" data-titulo=${textos.hoy.titulo}>
      <h1 className="pagina__titulo">${textos.hoy.titulo}</h1>
      <p className="pagina__dato" data-contador-tierras=${contador}>${contador}</p>
    </header>

    <a className="boton boton--principal boton--grande" href="/">
      <${Icono} nombre="apuntar" />
      ${textos.hoy.accion}
    </a>

    <div className="tarjetas">
      <article className="tarjeta-dato" data-resumen-gastos=${contable.gastos.importe || textos.tierras.panel.noConsta}>
        <h2 className="tarjeta-dato__titulo">${textos.hoy.gastos}</h2>
        <p className="tarjeta-dato__cifra">${contable.gastos.importe || textos.tierras.panel.noConsta}</p>
        <p className="tarjeta-dato__nota">${contable.gastos.nota || textos.tierras.panel.noConsta}</p>
      </article>
      <article className="tarjeta-dato" data-resumen-ventas=${contable.ventas.importe || textos.tierras.panel.noConsta}>
        <h2 className="tarjeta-dato__titulo">${textos.hoy.ventas}</h2>
        <p className="tarjeta-dato__cifra">${contable.ventas.importe || textos.tierras.panel.noConsta}</p>
        <p className="tarjeta-dato__nota">${contable.ventas.nota || textos.tierras.panel.noConsta}</p>
      </article>
      <article className="tarjeta-dato" data-resumen-cuaderno=${contable.cuaderno.nota || textos.tierras.panel.noConsta}>
        <h2 className="tarjeta-dato__titulo">${textos.hoy.cuaderno}</h2>
        <p className="tarjeta-dato__cifra">${contable.cuaderno.nota || textos.tierras.panel.noConsta}</p>
        <p className="tarjeta-dato__nota">${textos.hoy.faltaCuaderno}</p>
      </article>
    </div>

    <section className="tarjeta" aria-labelledby="ultimos-titulo">
      <h2 className="tarjeta__titulo" id="ultimos-titulo">${textos.hoy.ultimos}</h2>
      ${ultimos.length ? lista : vacio}
    </section>

    <${BloqueQueFalta} estado=${queFalta.estado} lista=${falta} alReintentar=${queFalta.reintentar} />
  </div>`;
}

// ---------------------------------------------------------------- mapa

function Leyenda({ leyenda, campo }) {
  const filas = leyenda.map((fila) => html`<li className="leyenda__fila" key=${`leyenda-${fila.etiqueta}`}>
    <span className="leyenda__color" style=${{ background: fila.color }} aria-hidden="true"></span>
    <span className="leyenda__palabra">${fila.etiqueta}</span>
    <span className="leyenda__cuenta">${fila.n}</span>
  </li>`);

  return html`<ul className="leyenda" data-leyenda-uso=${campo} aria-label=${textos.tierras.leyenda}>${filas}</ul>`;
}

function Mapa({ municipios, tierras, municipio, caja, elegida, alCambiarMunicipio, alZoom, alElegir, leyenda, campo }) {
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
      const color = leyenda ? colorDeTierra(tierra, leyenda, campo) : "var(--brand-bright)";
      const estilo = esElegida ? { stroke: color, strokeWidth: 5 } : { stroke: color };
      const ruta = rutaDeAnillo(tierra.anillo, caja, ANCHO_MAPA, ALTO_MAPA);
      if (ruta) {
        dibujos.push(html`<path
          key=${`anillo-${tierra.id}`}
          className="mapa__anillo"
          d=${ruta}
          style=${estilo}
          onClick=${alElegir ? () => alElegir(tierra) : undefined}
        />`);
        continue;
      }
      const punto = proyeccionDePunto(tierra.centro, caja, ANCHO_MAPA, ALTO_MAPA);
      if (punto) {
        dibujos.push(html`<circle
          key=${`punto-${tierra.id}`}
          className="mapa__punto"
          cx=${punto[0]}
          cy=${punto[1]}
          r=${esElegida ? 9 : 6}
          style={estilo}
          onClick=${alElegir ? () => alElegir(tierra) : undefined}
        />`);
      }
    }
  }

  const opciones = municipios.map((m) => html`<option key=${m.nombre} value=${m.nombre} data-municipio-opcion=${m.nombre}>${m.nombre}</option>`);
  const etiquetaDeLaFoto = `${textos.tierras.mapa}: ${municipio}`;

  const fotografía = html`<div className="mapa__lienzo">
    <img className="mapa__foto" data-mapa-imagen src=${urlConIntento} alt=${etiquetaDeLaFoto} onError=${() => setNoLlega(true)} />
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

function Panel({ tierra, alCerrar, alGuardar }) {
  const [alias, setAlias] = useState(tierra.alias || "");
  const [superficie, setSuperficie] = useState(
    tierra.superficie_ha === null || tierra.superficie_ha === undefined ? "" : String(tierra.superficie_ha),
  );
  const [estado, setEstado] = useState("quieto");

  useEffect(() => {
    setAlias(tierra.alias || "");
    setSuperficie(tierra.superficie_ha === null || tierra.superficie_ha === undefined ? "" : String(tierra.superficie_ha));
    setEstado("quieto");
  }, [tierra.id]);

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

  const guardar = async () => {
    setEstado("guardando");
    const numero = superficie.trim() === "" ? null : Number(String(superficie).replace(",", "."));
    const resultado = await guardarTierra(tierra.id, {
      alias: alias.trim(),
      superficie_ha: Number.isNaN(numero) ? null : numero,
    });
    if (resultado.estado === "ok") {
      setEstado("guardado");
      if (alGuardar) alGuardar();
      return;
    }
    setEstado(resultado.estado === "sin-permiso" ? "sin-permiso" : "fallo");
  };

  let editor = null;
  {
    const aviso = estado === "guardado" ? textos.tierras.panel.guardado : estado === "fallo" ? textos.tierras.panel.noSeGuardo : estado === "sin-permiso" ? textos.comun.sinPermiso : null;
    const claseAviso = estado === "guardado" ? "panel__aviso panel__aviso--bien" : "panel__aviso";
    editor = html`<div className="panel__editor">
      <label className="campo">
        <span>${textos.tierras.panel.alias}</span>
        <input className="campo__control" type="text" data-editar-alias value=${alias} onChange=${(evento) => setAlias(evento.target.value)} />
      </label>
      <label className="campo">
        <span>${textos.tierras.panel.superficieEditable}</span>
        <input className="campo__control" type="text" inputMode="decimal" data-editar-superficie value=${superficie} onChange=${(evento) => setSuperficie(evento.target.value)} />
      </label>
      <p className="panel__nota">${textos.tierras.panel.soloEsto}</p>
      <div className="estado__acciones">
        <button type="button" className="boton boton--principal" data-guardar-alias onClick=${guardar} disabled=${estado === "guardando"}>
          ${estado === "guardando" ? textos.tierras.panel.guardando : textos.tierras.panel.guardar}
        </button>
      </div>
      ${aviso ? html`<p className=${claseAviso}>${aviso}</p>` : null}
    </div>`;
  }

  return html`<aside className="panel" data-panel aria-labelledby="panel-alias">
    <div className="panel__cabecera">
      <h2 className="panel__alias" id="panel-alias" data-panel-alias=${tierra.alias}>${tierra.alias}</h2>
      <button type="button" className="boton boton--icono" aria-label=${textos.tierras.panel.cerrar} onClick=${alCerrar}>
        <${Icono} nombre="cerrar" tamano=${20} />
      </button>
    </div>
    ${avisoSinMapa}
    ${editor}
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

function VistaTierras({ estadoVista, datos, alReintentar, alAnadirTierras }) {
  const tierras = (datos && datos.tierras) || [];
  const municipios = (datos && datos.municipios) || [];

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
  const [campoDeColor, setCampoDeColor] = useState("uso");

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
    <div className="pagina__fila">
      <div>
        <h1 className="pagina__titulo">${textos.tierras.titulo}</h1>
        <p className="pagina__dato" data-totales=${textoDeTotales}>${textoDeTotales}</p>
      </div>
      <button type="button" className="boton boton--principal" data-accion="anadir-tierras" onClick=${alAnadirTierras}>
        <${Icono} nombre="anadir" tamano=${20} />
        ${textos.alta.accion}
      </button>
    </div>
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
  const leyenda = leyendaDe(tierras, campoDeColor);

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
      const color = colorDeTierra(tierra, leyenda, campoDeColor);

      return html`<button
        type="button"
        key=${`tierra-${tierra.id}`}
        className=${clase}
        data-tierra-id=${tierra.id}
        data-seleccionada=${esElegida ? "si" : "no"}
        onClick=${() => alElegir(tierra)}
      >
        <span className="tierra__alias"><span className="tierra__color" style=${{ background: color }} aria-hidden="true"></span>${tierra.alias}</span>
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
      alElegir=${alElegir}
      leyenda=${leyenda}
      campo=${campoDeColor}
    />
    <${Leyenda} leyenda=${leyenda} campo=${campoDeColor} />
    ${elegida
      ? html`<${Panel} tierra=${elegida} alCerrar=${() => setElegidaId(null)} alGuardar=${alReintentar} campo=${campoDeColor} />`
      : null}
  </div>`;

  return html`<div>
    ${cabecera}
    <div className="campo-de-color">
      <span>${textos.tierras.colorPor}</span>
      <button type="button" className=${campoDeColor === "uso" ? "pastilla pastilla--activa" : "pastilla"} onClick=${() => setCampoDeColor("uso")} aria-pressed=${campoDeColor === "uso"}>${textos.tierras.colorPorUso}</button>
      <button type="button" className=${campoDeColor === "cultivo" ? "pastilla pastilla--activa" : "pastilla"} onClick=${() => setCampoDeColor("cultivo")} aria-pressed=${campoDeColor === "cultivo"}>${textos.tierras.colorPorCultivo}</button>
    </div>
    <div className="tierras">
      ${visibles.length ? lista : sinResultados}
      ${detalle}
    </div>
  </div>`;
}

// ---------------------------------------------------------------- Añadir tierras

function CampoDeCodigo({ etiqueta, nombre, valor, alCambiar, numerico = true, obligatorio = true, pista }) {
  const tipo = numerico ? "number" : "text";
  return html`<label className="campo">
    <span>${etiqueta}</span>
    <input
      className="campo__control"
      type=${tipo}
      inputMode=${numerico ? "numeric" : undefined}
      min=${numerico ? "0" : undefined}
      required=${obligatorio}
      placeholder=${pista || ""}
      value=${valor}
      onChange=${(evento) => alCambiar(nombre, evento.target.value)}
    />
  </label>`;
}

function ListaDeRecintos({ estado, recintos, marcados, alMarcar, alAnadir, mensaje }) {
  if (estado === "buscando") return html`<p className="estado__texto" role="status">${textos.alta.buscando}</p>`;
  if (estado === "sin-permiso") {
    return html`<div className="estado">
      <p className="estado__texto">${textos.comun.sinPermiso}</p>
      <a className="boton boton--principal" data-entrar href="/">${textos.comun.entrar}</a>
    </div>`;
  }
  if (estado === "error") {
    return html`<div className="estado estado--fallo" role="alert">
      <p className="estado__texto">${textos.alta.noSePudoBuscar}</p>
    </div>`;
  }
  if (estado === "vacio") {
    return html`<div className="estado">
      <p className="estado__texto">${mensaje || textos.alta.sinRecintos}</p>
    </div>`;
  }
  if (estado !== "listo") return null;

  const filas = recintos.map((recinto) => {
    const marcado = marcados.includes(recinto.recinto);
    const clase = marcado ? "recinto recinto--marcado" : "recinto";
    const dibujo = recinto.tiene_dibujo ? null : html`<span className="recinto__sin-dibujo">${textos.alta.sinDibujo}</span>`;
    return html`<li key=${`recinto-${recinto.recinto}`}>
      <label className=${clase} data-recinto-id=${recinto.recinto} data-recinto-marcado=${marcado ? "si" : "no"}>
        <input type="checkbox" checked=${marcado} onChange=${() => alMarcar(recinto.recinto)} />
        <span className="recinto__datos">
          <span className="recinto__titulo">${textos.alta.recinto} ${recinto.recinto} · ${recinto.uso || recinto.uso_sigpac || textos.tierras.panel.noConsta}</span>
          <span className="recinto__detalle">
            ${textos.alta.superficie}: ${recinto.superficie_ha === null || recinto.superficie_ha === undefined ? textos.tierras.panel.noConsta : `${formateaNumero(recinto.superficie_ha)} ${textos.tierras.panel.hectareas}`}
            · ${textos.alta.pendiente}: ${recinto.pendiente_pct === null || recinto.pendiente_pct === undefined ? textos.tierras.panel.noConsta : `${formateaNumero(recinto.pendiente_pct, 1)} %`}
          </span>
          ${dibujo}
        </span>
      </label>
    </li>`;
  });

  const cuenta = textoRelleno(textos.alta.marcados, { n: marcados.length });

  return html`<div>
    <h3 className="panel__subtitulo">${textos.alta.recintos}</h3>
    <p className="pagina__dato">${cuenta}</p>
    <ul className="lista-recintos">${filas}</ul>
    <button type="button" className="boton boton--principal" data-anadir-seleccionados onClick=${alAnadir} disabled=${!marcados.length}>
      ${textos.alta.anadirMarcados}
    </button>
  </div>`;
}

function VentanaSigpac({ cajaInicial, buscados, alAnadir, alRefrescar }) {
  // Los recintos de la búsqueda ya están dibujados en el primer pintado: no se abre el mapa
  // vacío y luego se rellena.
  const [recintos, setRecintos] = useState(() => recintosConPuntos(buscados));
  const [caja, setCaja] = useState(
    () => cajaDeLosRecintos(recintosConPuntos(buscados)) || cajaInicial,
  );
  const [estado, setEstado] = useState("quieto");
  const [ficha, setFicha] = useState(null);
  const [aviso, setAviso] = useState(null);
  const [intento, setIntento] = useState(0);
  const [noLlega, setNoLlega] = useState(false);

  // **Los recintos de la búsqueda, dibujados todos de una vez** cuando el SIGPAC manda sus
  // puntos. El mapa se abre mirando a esos recintos y no a la finca: es donde está lo que se
  // acaba de buscar. Si la búsqueda no trae dibujo, se dice y se queda la lista.
  const deLaBusqueda = useMemo(() => recintosConPuntos(buscados), [buscados]);

  useEffect(() => {
    setRecintos(deLaBusqueda);
    setFicha(null);
    setAviso(null);
    const cajaDeLaBusqueda = cajaDeLosRecintos(deLaBusqueda);
    setCaja(cajaDeLaBusqueda || cajaInicial);
  }, [deLaBusqueda, cajaInicial]);

  const url = caja ? urlDelMapa(caja, ANCHO_MAPA, ALTO_MAPA) : "";
  const urlConIntento = url ? `${url}&intento=${intento}` : "";

  useEffect(() => {
    setNoLlega(false);
  }, [urlConIntento]);

  const alTocar = async (evento) => {
    if (!caja) return;
    // Con el teclado no hay un punto donde tocar: Enter sobre el mapa no elige una parcela al azar.
    if (!evento.detail) return;
    const rect = evento.currentTarget.getBoundingClientRect();
    const x = ((evento.clientX - rect.left) / rect.width) * ANCHO_MAPA;
    const y = ((evento.clientY - rect.top) / rect.height) * ALTO_MAPA;
    const punto = puntoDelMapa(x, y, caja, ANCHO_MAPA, ALTO_MAPA);
    if (!punto) return;

    setEstado("buscando");
    setAviso(null);
    const resultado = await pedir(RUTA_MAPA_PUNTO, conCuerpoJson({ x: punto[0], y: punto[1] }));
    if (resultado.estado === "sin-permiso") {
      setEstado("sin-permiso");
      return;
    }
    if (resultado.estado !== "ok") {
      setEstado("error");
      return;
    }
    if (!resultado.datos.encontrado) {
      setEstado("listo");
      setFicha(null);
      setAviso(resultado.datos.mensaje || textos.alta.sinForma);
      return;
    }
    const encontrado = resultado.datos;
    const conPuntos = Array.isArray(encontrado.puntos) && encontrado.puntos.length >= 3;
    setFicha(encontrado);
    setEstado("listo");
    if (conPuntos) {
      const color = colorDeUso(encontrado.uso_sigpac, recintos.length);
      setRecintos((previos) => {
        const otros = previos.filter((uno) => uno.recinto !== encontrado.recinto);
        return [...otros, { recinto: encontrado.recinto, puntos: encontrado.puntos, uso: encontrado.uso, color }];
      });
      const lons = encontrado.puntos.map((uno) => uno[0]);
      const lats = encontrado.puntos.map((uno) => uno[1]);
      setCaja(cajaQueSePuedePedir([Math.min(...lons), Math.min(...lats), Math.max(...lons), Math.max(...lats)]));
    } else {
      setAviso(textos.alta.sinForma);
    }
  };

  const alZoom = (sentido) => {
    if (sentido === "mas") {
      setCaja(zoomSobre(caja, PASO_DE_ZOOM));
      return;
    }
    if (sentido === "menos") {
      setCaja(zoomSobre(caja, 1 / PASO_DE_ZOOM));
      return;
    }
    setCaja(cajaDeLosRecintos(recintos) || cajaInicial);
  };

  const anadirEste = async () => {
    if (!ficha) return;
    setEstado("anadiendo");
    const resultado = await alAnadir(ficha);
    if (resultado === "ok") {
      setAviso(textoRelleno(textos.alta.anadidas, { n: 1 }));
      if (alRefrescar) alRefrescar();
    } else {
      setAviso(resultado === "sin-permiso" ? textos.comun.sinPermiso : textos.alta.noSePudoBuscar);
    }
    setEstado("listo");
  };

  const dibujos = [];
  if (caja) {
    for (const recinto of recintos) {
      const camino = rutaDeAnillo(recinto.puntos, caja, ANCHO_MAPA, ALTO_MAPA);
      if (!camino) continue;
      dibujos.push(html`<path
        key=${`recinto-${recinto.recinto}`}
        className="mapa__anillo mapa__anillo--recinto"
        d=${camino}
        style=${{ stroke: recinto.color }}
        data-mapa-recinto=${recinto.recinto}
      >
        <title>${`${textos.alta.recinto} ${recinto.recinto} · ${recinto.uso || ""}`}</title>
      </path>`);

      // La etiqueta del recinto, encima de su dibujo y con un borde claro para que se lea
      // sobre la foto sin depender del color.
      const proyectados = proyeccionDeAnillo(recinto.puntos, caja, ANCHO_MAPA, ALTO_MAPA);
      const primerPunto = proyectados && proyectados.length ? proyectados[0] : null;
      if (primerPunto) {
        dibujos.push(html`<text
          key=${`etiqueta-${recinto.recinto}`}
          x=${primerPunto[0] + 6}
          y=${primerPunto[1] - 6}
          style=${{
            fill: "var(--ink)",
            fontSize: "15px",
            fontWeight: "600",
            paintOrder: "stroke",
            stroke: "var(--surface-card)",
            strokeWidth: "3",
          }}
        >${recinto.recinto}</text>`);
      }
    }
  }

  const sinMapa = !caja;
  const etiquetaDeLaFoto = textos.alta.ventana;

  const lienzo = html`<button
    type="button"
    className="mapa__lienzo mapa__lienzo--tocable"
    data-mapa-ventana
    aria-label=${textos.alta.ventanaAyuda}
    onClick=${alTocar}
  >
    <img className="mapa__foto" data-mapa-imagen src=${urlConIntento} alt=${etiquetaDeLaFoto} onError=${() => setNoLlega(true)} />
    <svg className="mapa__dibujo" viewBox=${`0 0 ${ANCHO_MAPA} ${ALTO_MAPA}`} preserveAspectRatio="none" aria-hidden="true">${dibujos}</svg>
  </button>`;

  let contenido = html`<div className="mapa__aviso">
    <p className="estado__texto">${textos.alta.ventanaSinMapa}</p>
  </div>`;
  if (!sinMapa) {
    contenido = noLlega
      ? html`<div className="mapa__aviso" data-mapa-error>
          <p className="estado__texto">${textos.tierras.mapaNoLlega}</p>
          <button type="button" className="boton" onClick=${() => setIntento((n) => n + 1)}>${textos.comun.reintentarCorto}</button>
        </div>`
      : lienzo;
  }

  const fichaDeLaTierra = ficha
    ? html`<div className="ficha-recinto">
        <h4 className="panel__subtitulo">${textos.alta.fichaRecinto}</h4>
        <dl className="panel__datos">
          <div><dt className="panel__dato-etiqueta">${textos.alta.recinto}</dt><dd className="panel__dato-valor">${ficha.recinto ?? textos.tierras.panel.noConsta}</dd></div>
          <div><dt className="panel__dato-etiqueta">${textos.alta.uso}</dt><dd className="panel__dato-valor">${ficha.uso || ficha.uso_sigpac || textos.tierras.panel.noConsta}</dd></div>
          <div><dt className="panel__dato-etiqueta">${textos.alta.superficie}</dt><dd className="panel__dato-valor">${ficha.superficie_ha === null || ficha.superficie_ha === undefined ? textos.tierras.panel.noConsta : `${formateaNumero(ficha.superficie_ha)} ${textos.tierras.panel.hectareas}`}</dd></div>
          <div><dt className="panel__dato-etiqueta">${textos.alta.pendiente}</dt><dd className="panel__dato-valor">${ficha.pendiente_pct === null || ficha.pendiente_pct === undefined ? textos.tierras.panel.noConsta : `${formateaNumero(ficha.pendiente_pct, 1)} %`}</dd></div>
        </dl>
        <button type="button" className="boton boton--principal" data-anadir-recinto onClick=${anadirEste}>
          ${textos.alta.anadirEsta}
        </button>
      </div>`
    : null;

  const estados = [];
  if (estado === "buscando") estados.push(html`<p key="buscando" className="estado__texto" role="status">${textos.comun.cargando}</p>`);
  if (estado === "error") estados.push(html`<p key="error" className="estado__texto">${textos.alta.noSePudoBuscar}</p>`);
  if (estado === "sin-permiso") estados.push(html`<p key="permiso" className="estado__texto">${textos.comun.sinPermiso}</p>`);
  if (aviso) estados.push(html`<p key="aviso" className="panel__aviso">${aviso}</p>`);

  // Lo que se ha buscado y no se puede dibujar se dice: no se pinta un cuadro en su lugar.
  const buscadosSinDibujo = (Array.isArray(buscados) ? buscados : []).filter(
    (recinto) => !(Array.isArray(recinto.puntos) && recinto.puntos.length >= 3),
  );
  if (deLaBusqueda.length && buscadosSinDibujo.length) {
    estados.push(html`<p key="parcial" className="panel__aviso">
      <${Icono} nombre="aviso" tamano=${20} />
      ${textos.alta.sinForma}
    </p>`);
  }
  if (Array.isArray(buscados) && buscados.length && !deLaBusqueda.length) {
    estados.push(html`<p key="sin-puntos" className="panel__aviso" data-sin-puntos>
      <${Icono} nombre="aviso" tamano=${20} />
      ${textos.alta.sinPuntos}
    </p>`);
  }
  const cuentaEnElMapa = deLaBusqueda.length
    ? html`<p className="pagina__dato">${textoRelleno(textos.alta.recintosEnElMapa, { n: deLaBusqueda.length })}</p>`
    : null;

  return html`<section className="tarjeta ventana-sigpac" aria-labelledby="ventana-titulo">
    <div className="pagina__fila">
      <h2 className="tarjeta__titulo" id="ventana-titulo">${textos.alta.ventana}</h2>
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
    <p className="pagina__dato">${textos.alta.ventanaAyuda}</p>
    ${contenido}
    ${cuentaEnElMapa}
    ${estados}
    ${fichaDeLaTierra}
  </section>`;
}

function ResultadoDeImportacion({ estado, resultado, alOtro, alVerTierras }) {
  if (estado === "subiendo") {
    return html`<div className="estado" role="status"><p className="estado__texto">${textos.alta.importando}</p></div>`;
  }
  if (estado === "sin-permiso") {
    return html`<div className="estado">
      <p className="estado__texto">${textos.comun.sinPermiso}</p>
      <a className="boton boton--principal" data-entrar href="/">${textos.comun.entrar}</a>
    </div>`;
  }
  if (estado === "error") {
    return html`<div className="estado estado--fallo" role="alert">
      <p className="estado__texto">${textos.alta.noSeImporto}</p>
      <div className="estado__acciones">
        <button type="button" className="boton" onClick=${alOtro}>${textos.alta.otroFichero}</button>
        <a className="boton boton--principal" href="/">${textos.hoy.abrirAppVieja}</a>
      </div>
    </div>`;
  }
  if (estado !== "traido" || !resultado) return null;

  const filas = [];
  if (resultado.titular) {
    filas.push(html`<div key="titular"><dt className="panel__dato-etiqueta">${textos.alta.titular}</dt><dd className="panel__dato-valor">${resultado.titular}</dd></div>`);
  }
  if (resultado.anio !== null) {
    filas.push(html`<div key="anio"><dt className="panel__dato-etiqueta">${textos.alta.anio}</dt><dd className="panel__dato-valor">${resultado.anio}</dd></div>`);
  }
  if (resultado.tierrasEnElCuaderno !== null) {
    filas.push(html`<div key="tierras"><dt className="panel__dato-etiqueta">${textos.alta.tierrasEnElCuaderno}</dt><dd className="panel__dato-valor">${resultado.tierrasEnElCuaderno}</dd></div>`);
  }
  if (resultado.creadas !== null) {
    filas.push(html`<div key="creadas"><dt className="panel__dato-etiqueta">${textos.alta.creadas}</dt><dd className="panel__dato-valor">${resultado.creadas}</dd></div>`);
  }
  if (resultado.yaEstaban !== null) {
    filas.push(html`<div key="estaban"><dt className="panel__dato-etiqueta">${textos.alta.yaEstaban}</dt><dd className="panel__dato-valor">${resultado.yaEstaban}</dd></div>`);
  }
  if (resultado.sinApuntar !== null) {
    filas.push(html`<div key="sin"><dt className="panel__dato-etiqueta">${textos.alta.sinApuntar}</dt><dd className="panel__dato-valor">${resultado.sinApuntar}</dd></div>`);
  }

  const falta = resultado.falta.map((fila, indice) => html`<li key=${`falta-import-${indice}`}>
    <span className="que-falta__que">${fila.que}</span>
    <span className="que-falta__donde">${fila.donde || textos.hoy.abrirAppVieja}</span>
  </li>`);
  const bloqueFalta = falta.length ? html`<ul className="que-falta">${falta}</ul>` : null;

  return html`<div data-importar-resultado="listo">
    <h4 className="panel__subtitulo">${textos.alta.importado}</h4>
    <dl className="panel__datos">${filas}</dl>
    ${bloqueFalta}
    <div className="estado__acciones">
      <button type="button" className="boton boton--principal" onClick=${alVerTierras}>${textos.nav.tierras}</button>
      <button type="button" className="boton" onClick=${alOtro}>${textos.alta.otroFichero}</button>
    </div>
  </div>`;
}

function VistaAlta({ estadoVista, datos, alReintentar, alAnadirTierras, alIrATierras }) {
  const tierras = (datos && datos.tierras) || [];
  const municipios = (datos && datos.municipios) || [];

  const [campos, setCampos] = useState({ provincia: "", municipio: "", agregado: "0", zona: "0", poligono: "", parcela: "", recinto: "" });
  const [pegadas, setPegadas] = useState("");
  const [busqueda, setBusqueda] = useState({ estado: "quieto", recintos: [], mensaje: null, municipio: null });
  const [marcados, setMarcados] = useState([]);
  const [alta, setAlta] = useState({ estado: "quieto", texto: null });
  const [importacion, setImportacion] = useState({ estado: "inicial", resultado: null });
  const [numeroDeVeces, setNumeroDeVeces] = useState(0);
  const [vecesBuscado, setVecesBuscado] = useState(0);
  const entradaDeFichero = useRef(null);

  const cajaInicial = useMemo(() => cajaDeLasTierras(tierras, municipios), [tierras, municipios, numeroDeVeces]);

  const cambiar = (nombre, valor) => setCampos((previos) => ({ ...previos, [nombre]: valor }));

  const buscar = async () => {
    setBusqueda({ estado: "buscando", recintos: [], mensaje: null, municipio: null });
    setMarcados([]);
    setVecesBuscado((n) => n + 1);
    const referencia = referenciasDeTexto(pegadas);
    if (referencia.length && !campos.poligono && !campos.parcela) {
      // Se han pegado referencias y no hay casillas: se traen por la puerta de varias.
      const creadas = await pedir(RUTA_PARCELAS_VARIAS, conCuerpoJson({ referencias: referencia }));
      if (creadas.estado === "ok") {
        setAlta({ estado: "hecho", texto: textoRelleno(textos.alta.anadidas, { n: creadas.datos.cuantas ?? creadas.datos.creadas?.length ?? 0 }) });
        setNumeroDeVeces((n) => n + 1);
        alReintentar();
        return;
      }
      setBusqueda({ estado: creadas.estado === "sin-permiso" ? "sin-permiso" : "error", recintos: [], mensaje: null, municipio: null });
      return;
    }

    const cuerpo = {
      referencia: referencia.length === 1 ? referencia[0] : null,
      provincia: campos.provincia.trim() || null,
      municipio: campos.municipio.trim() || null,
      agregado: campos.agregado === "" ? null : Number(campos.agregado),
      zona: campos.zona === "" ? null : Number(campos.zona),
      poligono: campos.poligono === "" ? null : Number(campos.poligono),
      parcela: campos.parcela === "" ? null : Number(campos.parcela),
    };

    const resultado = await pedir(RUTA_BUSCAR, conCuerpoJson(cuerpo));
    if (resultado.estado === "ok") {
      const encontrados = resultado.datos.recintos || [];
      // El recinto es opcional: el SIGPAC busca por parcela y devuelve sus trozos; si el agricultor
      // ha escrito el número de uno, se queda con ese.
      const buscado = String(campos.recinto || "").trim();
      const recintos = buscado
        ? encontrados.filter((recinto) => String(recinto.recinto) === buscado)
        : encontrados;
      setBusqueda({
        estado: recintos.length ? "listo" : "vacio",
        recintos,
        mensaje: resultado.datos.mensaje || null,
        municipio: resultado.datos.municipio || null,
      });
      setMarcados(recintos.map((recinto) => recinto.recinto));
      return;
    }
    setBusqueda({
      estado: resultado.estado === "sin-permiso" ? "sin-permiso" : resultado.estado === "ok" ? "listo" : "error",
      recintos: [],
      mensaje: null,
      municipio: null,
    });
  };

  const alMarcar = (recinto) => {
    setMarcados((previos) =>
      previos.includes(recinto) ? previos.filter((uno) => uno !== recinto) : [...previos, recinto],
    );
  };

  const anadirLosMarcados = async () => {
    const elegidos = busqueda.recintos.filter((recinto) => marcados.includes(recinto.recinto));
    if (!elegidos.length) return;
    setAlta({ estado: "anadiendo", texto: null });
    const resultado = await pedir(
      RUTA_PARCELAS_VARIAS,
      conCuerpoJson({
        referencias: elegidos.map((recinto) => recinto.referencia),
        provincia: campos.provincia.trim() || null,
        municipio: busqueda.municipio?.nombre || campos.municipio.trim() || null,
      }),
    );
    if (resultado.estado === "ok") {
      const cuantas = resultado.datos.cuantas ?? (resultado.datos.creadas || []).length;
      const fallos = (resultado.datos.fallos || []).length;
      const texto = fallos
        ? `${textoRelleno(textos.alta.anadidas, { n: cuantas })} · ${textoRelleno(textos.alta.conFallos, { n: fallos })}`
        : textoRelleno(textos.alta.anadidas, { n: cuantas });
      setAlta({ estado: "hecho", texto });
      setNumeroDeVeces((n) => n + 1);
      alReintentar();
      return;
    }
    setAlta({
      estado: resultado.estado === "sin-permiso" ? "sin-permiso" : "fallo",
      texto: resultado.estado === "sin-permiso" ? textos.comun.sinPermiso : textos.alta.noSePudoBuscar,
    });
  };

  const anadirUno = async (ficha) => {
    const resultado = await pedir(
      RUTA_PARCELA_UNA,
      conCuerpoJson({
        ref_sigpac: ficha.referencia,
        provincia: ficha.municipio?.provincia || campos.provincia.trim() || null,
        municipio: ficha.municipio?.nombre || campos.municipio.trim() || null,
      }),
    );
    if (resultado.estado === "ok") {
      setNumeroDeVeces((n) => n + 1);
      alReintentar();
      return "ok";
    }
    return resultado.estado;
  };

  const subir = async (evento) => {
    const fichero = evento.target.files && evento.target.files[0];
    if (!fichero) return;
    setImportacion({ estado: "subiendo", resultado: null });
    const resultado = await subirCuaderno(fichero);
    if (resultado.estado === "ok") {
      setImportacion({ estado: "traido", resultado: normalizaImportacion(resultado.datos) });
      setNumeroDeVeces((n) => n + 1);
      alReintentar();
      return;
    }
    setImportacion({
      estado: resultado.estado === "sin-permiso" ? "sin-permiso" : "error",
      resultado: null,
    });
  };

  const pedirOtroFichero = () => {
    setImportacion({ estado: "inicial", resultado: null });
    if (entradaDeFichero.current) {
      entradaDeFichero.current.value = "";
      entradaDeFichero.current.focus();
    }
  };

  if (estadoVista === "cargando") return html`<${EstadoCargando} mensaje=${textos.comun.cargando} />`;
  if (estadoVista === "error") return html`<${EstadoFallo} mensaje=${textos.comun.fallo} alReintentar=${alReintentar} />`;
  if (estadoVista === "sin-permiso") return html`<${EstadoSinPermiso} mensaje=${textos.comun.sinPermiso} />`;

  const avisoDeAlta = alta.texto
    ? html`<p className=${alta.estado === "fallo" ? "panel__aviso" : "panel__aviso panel__aviso--bien"} data-alta-resultado>
        ${alta.texto}
      </p>`
    : null;

  return html`<div className="pantalla-alta">
    <header className="pagina__cabecera">
      <div className="pagina__fila">
        <div>
          <h1 className="pagina__titulo">${textos.alta.titulo}</h1>
          <p className="pagina__dato">${textos.alta.intro}</p>
        </div>
        <button type="button" className="boton" onClick=${alIrATierras} data-accion="anadir-tierras">
          <${Icono} nombre="tierras" tamano=${20} />
          ${textos.nav.tierras}
        </button>
      </div>
    </header>

    <div className="alta-columnas">
      <section className="tarjeta" aria-labelledby="por-codigo-titulo">
        <h2 className="tarjeta__titulo" id="por-codigo-titulo">${textos.alta.porCodigo}</h2>
        <p className="pagina__dato">${textos.alta.porCodigoAyuda}</p>
        <div className="rejilla-campos">
          <${CampoDeCodigo} etiqueta=${textos.alta.provincia} nombre="provincia" valor=${campos.provincia} alCambiar=${cambiar} numerico=${false} obligatorio=${false} />
          <${CampoDeCodigo} etiqueta=${textos.alta.municipio} nombre="municipio" valor=${campos.municipio} alCambiar=${cambiar} numerico=${false} obligatorio=${false} />
          <${CampoDeCodigo} etiqueta=${textos.alta.agregado} nombre="agregado" valor=${campos.agregado} alCambiar=${cambiar} pista="0" />
          <${CampoDeCodigo} etiqueta=${textos.alta.zona} nombre="zona" valor=${campos.zona} alCambiar=${cambiar} pista="0" />
          <${CampoDeCodigo} etiqueta=${textos.alta.poligono} nombre="poligono" valor=${campos.poligono} alCambiar=${cambiar} obligatorio=${false} />
          <${CampoDeCodigo} etiqueta=${textos.alta.parcela} nombre="parcela" valor=${campos.parcela} alCambiar=${cambiar} obligatorio=${false} />
          <${CampoDeCodigo} etiqueta=${textos.alta.recintoFiltro} nombre="recinto" valor=${campos.recinto} alCambiar=${cambiar} obligatorio=${false} />
        </div>
        <label className="campo">
          <span>${textos.alta.referenciasPegadas}</span>
          <textarea className="campo__control campo__control--alto" rows="3" placeholder=${textos.alta.referenciasPista} value=${pegadas} onChange=${(evento) => setPegadas(evento.target.value)}></textarea>
        </label>
        <div className="estado__acciones">
          <button type="button" className="boton boton--principal" data-buscar-codigos onClick=${buscar}>
            <${Icono} nombre="buscar" tamano=${20} />
            ${textos.alta.buscar}
          </button>
          <button type="button" className="boton" onClick=${buscar} disabled=${!referenciasDeTexto(pegadas).length}>
            ${textos.alta.traerPegadas}
          </button>
        </div>
        ${avisoDeAlta}
        <${ListaDeRecintos}
          estado=${busqueda.estado}
          recintos=${busqueda.recintos}
          marcados=${marcados}
          alMarcar=${alMarcar}
          alAnadir=${anadirLosMarcados}
          mensaje=${busqueda.mensaje}
        />
      </section>

      <${VentanaSigpac}
        key=${`ventana-${vecesBuscado}`}
        cajaInicial=${cajaInicial}
        buscados=${busqueda.recintos}
        alAnadir=${anadirUno}
        alRefrescar=${() => setNumeroDeVeces((n) => n + 1)}
      />

      <section className="tarjeta" aria-labelledby="importar-titulo">
        <h2 className="tarjeta__titulo" id="importar-titulo">${textos.alta.importar}</h2>
        <p className="pagina__dato">${textos.alta.importarAyuda}</p>
        <label className="campo">
          <span>${textos.alta.elegirFichero}</span>
          <input
            className="campo__control"
            type="file"
            accept=".xlsx"
            data-importar-cuaderno
            ref=${entradaDeFichero}
            onChange=${subir}
          />
        </label>
        <${ResultadoDeImportacion}
          estado=${importacion.estado}
          resultado=${importacion.resultado}
          alOtro=${pedirOtroFichero}
          alVerTierras=${alIrATierras}
        />
      </section>
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
  const pantallaTierras = usarPantalla(RUTA_TIERRAS, vista === "tierras" || vista === "alta");
  const pantallaResumen = usarPantalla(RUTA_RESUMEN, vista === "hoy");
  const pantallaQueFalta = usarPantalla(RUTA_QUE_FALTA, vista === "hoy");

  const actual = vista === "hoy" ? pantallaHoy : pantallaTierras;
  const datosDeLaFinca = pantallaHoy.datos || pantallaTierras.datos || null;

  const lista = vista === "hoy"
    ? ((pantallaHoy.datos && pantallaHoy.datos.ultimos) || [])
    : ((pantallaTierras.datos && pantallaTierras.datos.tierras) || []);

  const estadoVista = arrancada
    ? decidirEstado({
        conToken: actual.conToken,
        cargando: actual.estado === "cargando",
        fallo: actual.estado === "error" || actual.estado === "no-disponible",
        sinPermiso: actual.estado === "sin-permiso",
        hayDatos: vista === "alta" ? Boolean(pantallaTierras.datos) : lista.length > 0,
      })
    : "cargando";

  let pantalla = null;
  if (vista === "hoy") {
    pantalla = html`<${VistaHoy}
      estadoVista=${estadoVista}
      datos=${pantallaHoy.datos}
      alReintentar=${pantallaHoy.reintentar}
      resumen=${pantallaResumen}
      queFalta=${pantallaQueFalta}
    />`;
  } else if (vista === "alta") {
    pantalla = html`<${VistaAlta}
      estadoVista=${estadoVista}
      datos=${pantallaTierras.datos}
      alReintentar=${pantallaTierras.reintentar}
      alAnadirTierras=${() => setVista("tierras")}
      alIrATierras=${() => setVista("tierras")}
    />`;
  } else {
    pantalla = html`<${VistaTierras}
      estadoVista=${estadoVista}
      datos=${pantallaTierras.datos}
      alReintentar=${pantallaTierras.reintentar}
      alAnadirTierras=${() => setVista("alta")}
    />`;
  }

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
