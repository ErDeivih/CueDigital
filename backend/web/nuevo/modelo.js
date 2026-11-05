/**
 * modelo.js — Lo que la pantalla nueva calcula sin pintar nada.
 *
 * Aquí vive todo lo que se puede probar sin navegador: cómo se agrupan las tierras por
 * municipio, cuánto suman, dónde cae un anillo dentro de la imagen del mapa y qué se le
 * enseña al agricultor en cada momento (cargando, sin permiso, sin nada, o la lista).
 *
 * Y aquí viven **todos los textos** que lee el agricultor en esta pantalla, en un solo
 * sitio: ni repartidos por el código ni escritos a mano en el marcado. La lista de
 * palabras prohibidas del proyecto (`app/textos.py`) se comprueba contra este objeto.
 *
 * Regla de la casa: un dato que no se sabe se enseña como «no consta». Nunca un cero, ni
 * un «no», ni un cuadro inventado.
 */

/** La misma clave que usa la aplicación de siempre: la cuenta se comparte. */
export const CLAVE_TOKEN = "cuedigital.token";

/** La imagen del mapa se pide con este tamaño y se estira al hueco que haya. */
export const ANCHO_MAPA = 800;
export const ALTO_MAPA = 600;

export const textos = {
  app: {
    nombre: "CUE Digital",
    conCobertura: "Con cobertura",
    sinCobertura: "Sin cobertura",
  },
  nav: {
    hoy: "Hoy",
    tierras: "Tierras",
    apuntar: "Apuntar",
    cuaderno: "Cuaderno",
    mas: "Más",
    campana: "Campaña",
    pac: "PAC y subvenciones",
    documentos: "Documentos",
    cuenta: "Tu cuenta",
  },
  comun: {
    cargando: "Trayendo tus datos…",
    fallo: "No se ha podido cargar. Revisa la cobertura y vuelve a intentarlo.",
    reintentar: "Volver a intentar",
    sinPermiso: "Entra con tu cuenta para ver lo tuyo.",
    entrar: "Entrar",
    vacio: "Aquí todavía no hay nada.",
    reintentarCorto: "Volver a intentar",
  },
  hoy: {
    titulo: "Hoy",
    accion: "Apunta lo que has hecho",
    ultimos: "Lo último",
    contador: "{n} tierras · {ha} ha",
    contadorSinHa: "{n} tierras",
    sinUltimos: "Cuando apuntes un trabajo o un tratamiento, saldrá aquí.",
    sinTierras: "Todavía no tienes tierras. Trae las tierras para poder apuntar.",
    cargando: "Trayendo lo de hoy…",
    fallo: "No se ha podido cargar lo de hoy. Revisa la cobertura y vuelve a intentarlo.",
    sinPermiso: "Entra con tu cuenta para ver lo de hoy.",
    vacio: "Todavía no has apuntado nada hoy.",
    vacioBoton: "Apunta lo que has hecho",
  },
  tierras: {
    titulo: "Mis tierras",
    buscador: "Buscar tierra",
    buscadorPista: "Nombre o municipio",
    totales: "{n} tierras · {ha} ha · {m} municipios",
    totalesUno: "{n} tierra · {ha} ha · {m} municipio",
    totalesSinHa: "{n} tierras · {m} municipios",
    totalesUnoSinHa: "{n} tierra · {m} municipio",
    cargando: "Trayendo tus tierras…",
    fallo: "No se han podido cargar las tierras. Revisa la cobertura y vuelve a intentarlo.",
    sinPermiso: "Entra con tu cuenta para ver tus tierras.",
    vacio: "Todavía no tienes tierras.",
    traerTierras: "Traer tierras",
    sinMunicipio: "Sin municipio",
    sinResultados: "Ninguna tierra se llama así.",
    quitarBusqueda: "Ver todas",
    mapa: "Mapa",
    municipio: "Municipio",
    ayudaDelMapa: "Elige una tierra de la lista para ver su forma.",
    mapaNoLlega: "No se ha podido traer la foto del mapa.",
    sinMapa: "Sin mapa",
    zoomMas: "Acercar el mapa",
    zoomMenos: "Alejar el mapa",
    zoomTodo: "Ver todo el municipio",
    elegida: "Elegida",
    panel: {
      titulo: "Datos de la tierra",
      superficie: "Superficie",
      sigpac: "Superficie del SIGPAC",
      uso: "Uso",
      coeficiente: "Coeficiente",
      region: "Región",
      admisibilidad: "Admisible",
      cultivo: "Cultivo",
      variedad: "Variedad",
      otrosAnios: "Otros años",
      sinOtrosAnios: "No hay años anteriores guardados.",
      anio: "Campaña",
      hectareas: "ha",
      noConsta: "no consta",
      cerrar: "Cerrar la tierra",
    },
  },
};

function redondea(valor, decimales = 2) {
  const factor = 10 ** decimales;
  return Math.round(valor * factor) / factor;
}

/** Un número con coma decimal y punto de millares: 1234,5 → «1.234,5». */
export function formateaNumero(valor, decimales = 2) {
  if (valor === null || valor === undefined || valor === "" || Number.isNaN(Number(valor))) {
    return "";
  }
  const fijo = Number(valor).toFixed(decimales);
  const [entera, decimal] = fijo.split(".");
  const conMillares = entera.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  const decimalLimpia = (decimal || "").replace(/0+$/, "");
  return decimalLimpia ? `${conMillares},${decimalLimpia}` : conMillares;
}

/** Rellena una plantilla con sus huecos: `{n} tierras` con `{n: 3}`. */
export function textoRelleno(plantilla, valores = {}) {
  return String(plantilla ?? "").replace(/\{(\w+)\}/g, (_, clave) =>
    valores[clave] === undefined || valores[clave] === null ? "" : String(valores[clave]),
  );
}

/** Sin tildes y en minúsculas, para buscar sin pelearse con el teclado. */
export function normaliza(texto) {
  return String(texto ?? "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();
}

function esBboxValida(bbox) {
  return (
    Array.isArray(bbox) &&
    bbox.length === 4 &&
    bbox.every((n) => typeof n === "number" && Number.isFinite(n)) &&
    bbox[2] > bbox[0] &&
    bbox[3] > bbox[1]
  );
}

/** El municipio de una tierra, o el grupo de las que no lo tienen. */
export function municipioDeTierra(tierra) {
  const nombre = (tierra && tierra.municipio) || "";
  return nombre.trim() ? nombre.trim() : textos.tierras.sinMunicipio;
}

/** Las tierras que coinciden con lo escrito, por nombre o por municipio. */
export function filtrarTierras(tierras, consulta) {
  const lista = Array.isArray(tierras) ? tierras : [];
  const buscado = normaliza(consulta);
  if (!buscado) return lista.slice();
  return lista.filter(
    (tierra) =>
      normaliza(tierra && tierra.alias).includes(buscado) ||
      normaliza(tierra && tierra.municipio).includes(buscado),
  );
}

/** N tierras, X hectáreas y M municipios. Si a una tierra le falta la superficie, `ha` es `null`:
 *  una suma a la que le falta un sumando no se enseña como si estuviera completa. */
export function calcularTotales(tierras) {
  const grupos = agruparPorMunicipio(tierras);
  const completas = grupos.every((grupo) => grupo.ha !== null);
  const ha = completas ? grupos.reduce((suma, grupo) => suma + grupo.ha, 0) : null;
  return {
    n: Array.isArray(tierras) ? tierras.length : 0,
    ha: ha === null ? null : redondea(ha, 2),
    municipios: grupos.length,
  };
}

/** La lista agrupada por municipio, con la cuenta y la superficie de cada grupo. */
export function agruparPorMunicipio(tierras) {
  const grupos = new Map();
  for (const tierra of Array.isArray(tierras) ? tierras : []) {
    if (!tierra) continue;
    const nombre = municipioDeTierra(tierra);
    if (!grupos.has(nombre)) grupos.set(nombre, { nombre, n: 0, ha: 0, completa: true, tierras: [] });
    const grupo = grupos.get(nombre);
    grupo.n += 1;
    const superficie = tierra.superficie_ha;
    if (superficie === null || superficie === undefined || Number.isNaN(Number(superficie))) {
      grupo.completa = false;
    } else {
      grupo.ha += Number(superficie);
    }
    grupo.tierras.push(tierra);
  }
  return [...grupos.values()]
    .map((grupo) => ({
      nombre: grupo.nombre,
      n: grupo.n,
      ha: grupo.completa ? redondea(grupo.ha, 2) : null,
      tierras: grupo.tierras
        .slice()
        .sort((a, b) => String(a.alias ?? "").localeCompare(String(b.alias ?? ""), "es")),
    }))
    .sort((a, b) => String(a.nombre).localeCompare(String(b.nombre), "es"));
}

/**
 * Dónde cae cada punto del anillo dentro de la imagen: el oeste a la izquierda y el sur
 * abajo, que es como se mira un mapa.
 */
export function proyeccionDeAnillo(puntos, bbox, ancho = ANCHO_MAPA, alto = ALTO_MAPA) {
  if (!Array.isArray(puntos) || !puntos.length || !esBboxValida(bbox)) return null;
  const [oeste, sur, este, norte] = bbox;
  const anchoGrados = este - oeste;
  const altoGrados = norte - sur;
  const proyectados = [];
  for (const punto of puntos) {
    if (!Array.isArray(punto) || punto.length < 2) return null;
    const [lon, lat] = punto;
    if (!Number.isFinite(lon) || !Number.isFinite(lat)) return null;
    proyectados.push([
      ((lon - oeste) / anchoGrados) * ancho,
      ((norte - lat) / altoGrados) * alto,
    ]);
  }
  return proyectados;
}

/** Un solo punto (el centro de una tierra sin forma) dentro de la imagen. */
export function proyeccionDePunto(punto, bbox, ancho = ANCHO_MAPA, alto = ALTO_MAPA) {
  const proyectados = proyeccionDeAnillo([punto], bbox, ancho, alto);
  return proyectados && proyectados.length ? proyectados[0] : null;
}

/** El mismo anillo, como ruta de SVG para pintarlo encima de la foto. */
export function rutaDeAnillo(puntos, bbox, ancho = ANCHO_MAPA, alto = ALTO_MAPA) {
  const proyectados = proyeccionDeAnillo(puntos, bbox, ancho, alto);
  if (!proyectados || !proyectados.length) return null;
  const [primero, ...resto] = proyectados.map(([x, y]) => `${x.toFixed(2)} ${y.toFixed(2)}`);
  return `M${primero} L${resto.join(" L")} Z`;
}

/** ¿Se puede enseñar esta tierra en el mapa? Sin forma ni centro, no. */
export function sinMapa(tierra) {
  const anillo = tierra && tierra.anillo;
  const centro = tierra && tierra.centro;
  const hayAnillo = Array.isArray(anillo) && anillo.length >= 3;
  const hayCentro = Array.isArray(centro) && centro.length >= 2;
  return !hayAnillo && !hayCentro;
}

/** La caja de un municipio, si tiene forma. */
export function bboxDeMunicipio(municipios, nombre) {
  const municipio = (Array.isArray(municipios) ? municipios : []).find(
    (m) => m && m.nombre === nombre,
  );
  return municipio && esBboxValida(municipio.bbox) ? municipio.bbox.slice() : null;
}

/** La caja que abarca todo lo que sí tiene forma: «ver todo». */
export function bboxDelConjunto(municipios) {
  const cajas = (Array.isArray(municipios) ? municipios : [])
    .map((m) => m && m.bbox)
    .filter((bbox) => esBboxValida(bbox));
  if (!cajas.length) return null;
  return [
    Math.min(...cajas.map((c) => c[0])),
    Math.min(...cajas.map((c) => c[1])),
    Math.max(...cajas.map((c) => c[2])),
    Math.max(...cajas.map((c) => c[3])),
  ];
}

/** Acercar (factor < 1) o alejar (factor > 1) sin mover el centro. */
export function ajustarBbox(bbox, factor) {
  if (!esBboxValida(bbox)) return null;
  const [oeste, sur, este, norte] = bbox;
  const centroLon = (oeste + este) / 2;
  const centroLat = (sur + norte) / 2;
  const medioAncho = ((este - oeste) / 2) * factor;
  const medioAlto = ((norte - sur) / 2) * factor;
  return [
    centroLon - medioAncho,
    centroLat - medioAlto,
    centroLon + medioAncho,
    centroLat + medioAlto,
  ];
}

/**
 * La dirección de la ortofoto del IGN. Las coordenadas van con seis decimales: son grados,
 * y con menos se nota el escalón al acercarse.
 */
export function urlDelMapa(bbox, ancho = ANCHO_MAPA, alto = ALTO_MAPA) {
  if (!esBboxValida(bbox)) return "";
  const [oeste, sur, este, norte] = bbox;
  const parametros = [
    "capa=foto",
    `oeste=${oeste.toFixed(6)}`,
    `sur=${sur.toFixed(6)}`,
    `este=${este.toFixed(6)}`,
    `norte=${norte.toFixed(6)}`,
    `ancho=${Math.round(ancho)}`,
    `alto=${Math.round(alto)}`,
  ];
  return `/api/mapa/imagen?${parametros.join("&")}`;
}

/**
 * Qué se enseña: primero quién eres, después si se está trayendo, después si no ha
 * llegado, y solo al final los datos o el vacío. Un fallo de red nunca se disfraza de
 * «no hay nada».
 */
export function decidirEstado({ conToken, cargando, fallo, sinPermiso, hayDatos }) {
  if (!conToken || sinPermiso) return "sin-permiso";
  if (cargando) return "cargando";
  if (fallo) return "error";
  return hayDatos ? "listo" : "vacio";
}

/** La campaña como se escribe en el campo: «2025/2026». */
export function etiquetaCampana(campana) {
  if (!campana) return "";
  const anio = campana.anio ?? campana.id;
  return anio === null || anio === undefined ? "" : String(anio);
}

/** Los datos de la tierra que van al panel, con «no consta» donde no hay dato. */
export function datosDelPanel(tierra) {
  const t = tierra || {};
  const noConsta = textos.tierras.panel.noConsta;
  const conUnidad = (valor, unidad) => (valor === null || valor === undefined ? noConsta : `${formateaNumero(valor)} ${unidad}`);
  const cultivo = t.cultivo || null;
  return [
    { etiqueta: textos.tierras.panel.superficie, valor: conUnidad(t.superficie_ha, textos.tierras.panel.hectareas) },
    { etiqueta: textos.tierras.panel.sigpac, valor: conUnidad(t.superficie_sigpac_ha, textos.tierras.panel.hectareas) },
    { etiqueta: textos.tierras.panel.uso, valor: t.uso_sigpac || noConsta },
    { etiqueta: textos.tierras.panel.coeficiente, valor: t.coef_regadio === null || t.coef_regadio === undefined ? noConsta : formateaNumero(t.coef_regadio) },
    { etiqueta: textos.tierras.panel.region, valor: t.region || noConsta },
    { etiqueta: textos.tierras.panel.admisibilidad, valor: t.admisibilidad === null || t.admisibilidad === undefined ? noConsta : String(t.admisibilidad) },
    { etiqueta: textos.tierras.panel.cultivo, valor: cultivo && cultivo.nombre ? cultivo.nombre : noConsta },
    { etiqueta: textos.tierras.panel.variedad, valor: cultivo && cultivo.variedad ? cultivo.variedad : noConsta },
  ];
}
