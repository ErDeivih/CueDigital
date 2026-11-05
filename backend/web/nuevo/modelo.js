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
    gastos: "Gastos",
    ventas: "Ventas",
    cuaderno: "Cuaderno",
    facturas: "Facturas",
    faltaCuaderno: "Falta para el cuaderno",
    queFalta: "Qué falta",
    queFaltaVacio: "No falta nada para el cuaderno.",
    verQueFalta: "Ver qué falta",
    abrirAppVieja: "Abrir la app de siempre",
    apunte: "apunte",
    apuntes: "apuntes",
    factura: "factura",
    facturasCuenta: "facturas",
    sinCerrar: "sin cerrar",
    porPagar: "quedan {importe} por pagar",
    cobrado: "cobrado {importe}",
    faltan: "faltan {n} cosas",
    faltaUna: "falta 1 cosa",
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
    sinUso: "Sin uso",
    sinCultivo: "Sin cultivo",
    colorPor: "Colorear por",
    colorPorUso: "Uso",
    colorPorCultivo: "Cultivo",
    leyenda: "Leyenda",
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
      editar: "Editar",
      alias: "Nombre",
      superficieEditable: "Superficie (ha)",
      guardar: "Guardar cambios",
      guardando: "Guardando…",
      guardado: "Guardado",
      noSeGuardo: "No se ha podido guardar. Prueba otra vez.",
      soloEsto: "El resto de los datos del SIGPAC se enseñan, no se cambian.",
    },
  },
  alta: {
    titulo: "Añadir tierras",
    accion: "Añadir tierras",
    intro: "Se pueden traer del SIGPAC o de un cuaderno de la Junta.",
    porCodigo: "Por su código del SIGPAC",
    porCodigoAyuda: "Los números del papel de la parcela. Con eso sale la lista de recintos.",
    provincia: "Provincia",
    municipio: "Municipio",
    agregado: "Agregado",
    zona: "Zona",
    poligono: "Polígono",
    parcela: "Parcela",
    recintoFiltro: "Recinto (opcional)",
    buscar: "Buscar",
    buscando: "Buscando en el SIGPAC…",
    sinRecintos: "No salen recintos con esos datos. Repasa los números del papel.",
    noSePudoBuscar: "No se ha podido preguntar al SIGPAC. Prueba otra vez.",
    recintos: "Recintos encontrados",
    recintosCuenta: "{n} recintos",
    recinto: "Recinto",
    superficie: "Superficie",
    uso: "Uso",
    pendiente: "Pendiente",
    sinDibujo: "sin dibujo",
    anadirMarcados: "Añadir los marcados",
    marcados: "{n} marcados",
    anadiendo: "Añadiendo…",
    anadidas: "{n} tierras añadidas",
    conFallos: "{n} sin añadir",
    referenciasPegadas: "O pega las referencias",
    referenciasPista: "Una por línea, como las tengas",
    traerPegadas: "Traer las pegadas",
    ventana: "Ventana del SIGPAC",
    ventanaAyuda: "Toca en el mapa para coger el recinto que es tuyo.",
    ventanaSinMapa: "Todavía no hay una zona con la que abrir el mapa. Busca por código y añade la primera tierra.",
    sinForma: "Este recinto no trae forma en el SIGPAC: se lista, pero no se dibuja.",
    sinPuntos: "Esta búsqueda no trae el dibujo de los recintos. Se pueden añadir desde la lista, marcándolos.",
    recintosEnElMapa: "{n} recintos en el mapa",
    fichaRecinto: "Datos del recinto",
    anadirEsta: "Añadir esta tierra",
    importar: "Traer un cuaderno",
    importarAyuda: "El cuaderno de la Junta de un cliente. Se leen sus tierras y se dan de alta sin escribirlas a mano.",
    elegirFichero: "Elegir el cuaderno",
    importando: "Trayendo el cuaderno…",
    importado: "Cuaderno traído",
    titular: "Titular",
    anio: "Año",
    tierrasEnElCuaderno: "Tierras en el cuaderno",
    creadas: "Tierras nuevas",
    yaEstaban: "Ya estaban",
    sinApuntar: "Sin poder apuntar",
    noSeImporto: "No se ha podido traer el cuaderno. Prueba otra vez o ábrelo en la app de siempre.",
    otroFichero: "Elegir otro cuaderno",
    sinDatos: "Todavía no hay nada que enseñar aquí.",
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

// ---------------------------------------------------------------------------
// El mapa de colores: cada uso (o cultivo) con su color y su palabra
// ---------------------------------------------------------------------------

/*
 * Los colores salen de los tokens del sistema, no de aquí a mano: en el mapa se usan como
 * `var(--token)` y así el día y la noche los cambian solos. Siete y no más: más colores en
 * una foto aérea no se distinguen, y la leyenda lleva la palabra al lado para no depender
 * del color.
 */
const PALETA = [
  "var(--brand-bright)",
  "var(--accent)",
  "var(--info)",
  "var(--danger)",
  "var(--warning)",
  "var(--surface-sunk)",
  "var(--ink)",
];

const COLOR_SIN_DATO = "var(--ink-muted)";

/** Los colores disponibles para pintar las tierras. */
export function paletaDeUso() {
  return PALETA.slice();
}

/** El color que le toca a un valor por su puesto en la leyenda. */
export function colorDeUso(valor, indice = 0) {
  if (valor === null || valor === undefined || String(valor).trim() === "") return COLOR_SIN_DATO;
  return PALETA[Math.abs(Number(indice) || 0) % PALETA.length];
}

/** El valor por el que se colorea una tierra: su uso del SIGPAC o el cultivo del año. */
export function valorDeColor(tierra, campo = "uso") {
  const t = tierra || {};
  if (campo === "cultivo") {
    const cultivo = t.cultivo || null;
    return cultivo && cultivo.nombre ? cultivo.nombre : null;
  }
  return t.uso_sigpac || null;
}

/**
 * La leyenda: qué valores hay, cuántas tierras tiene cada uno y de qué color se pinta.
 * Ordenada de más tierras a menos y, a igualdad, por nombre, para que no baile entre
 * repintados. Lo que no tiene dato va al final y con su palabra («Sin uso»).
 */
export function leyendaDe(tierras, campo = "uso") {
  const cuenta = new Map();
  for (const tierra of Array.isArray(tierras) ? tierras : []) {
    if (!tierra) continue;
    const valor = valorDeColor(tierra, campo);
    cuenta.set(valor, (cuenta.get(valor) || 0) + 1);
  }
  const sinDato = campo === "cultivo" ? textos.tierras.sinCultivo : textos.tierras.sinUso;
  const filas = [...cuenta.entries()]
    .map(([valor, n]) => ({
      valor,
      n,
      etiqueta: valor === null ? sinDato : String(valor),
    }))
    .sort((a, b) => {
      if (a.valor === null) return 1;
      if (b.valor === null) return -1;
      if (b.n !== a.n) return b.n - a.n;
      return a.etiqueta.localeCompare(b.etiqueta, "es");
    });

  let indice = 0;
  return filas.map((fila) => {
    const color = fila.valor === null ? COLOR_SIN_DATO : PALETA[indice % PALETA.length];
    if (fila.valor !== null) indice += 1;
    return { ...fila, color };
  });
}

/** El color de una tierra, buscándolo en la leyenda de su valor. */
export function colorDeTierra(tierra, leyenda, campo = "uso") {
  const valor = valorDeColor(tierra, campo);
  const fila = (Array.isArray(leyenda) ? leyenda : []).find((una) => una.valor === valor);
  return fila ? fila.color : COLOR_SIN_DATO;
}

// ---------------------------------------------------------------------------
// El alta: referencias pegadas y lo que llega de las puertas del servidor
// ---------------------------------------------------------------------------

/** Las referencias que se han pegado, una por línea o separadas por comas o puntos y coma. */
export function referenciasDeTexto(texto) {
  const vistos = new Set();
  const referencias = [];
  for (const trozo of String(texto ?? "").split(/[\n\r,;]+/)) {
    const limpia = trozo.trim();
    if (!limpia || vistos.has(limpia)) continue;
    vistos.add(limpia);
    referencias.push(limpia);
  }
  return referencias;
}

/** Un importe en castellano, o `null` si no hay dato (que no es lo mismo que cero). */
export function importeEnTexto(valor) {
  if (valor === null || valor === undefined || valor === "") return null;
  if (typeof valor === "number") {
    return Number.isFinite(valor) ? `${formateaNumero(valor)} €` : null;
  }
  if (typeof valor === "string") {
    const limpio = valor.trim();
    return limpio === "" ? null : limpio;
  }
  if (typeof valor === "object") {
    for (const clave of ["total", "importe", "euros", "total_eur", "valor"]) {
      if (clave in valor) return importeEnTexto(valor[clave]);
    }
  }
  return null;
}

function cuentaEnTexto(cantidad, singular, plural) {
  if (cantidad === null || cantidad === undefined || Number.isNaN(Number(cantidad))) return null;
  const n = Number(cantidad);
  return n === 1 ? `${n} ${singular}` : `${n} ${plural}`;
}

/** Las tarjetas de «Hoy»: gastos, ventas, cuaderno y facturas, cada una con su cifra. */
export function normalizaResumen(datos) {
  const resumen = datos || {};
  const gastos = resumen.gastos || {};
  const ventas = resumen.ventas || {};
  const cuaderno = resumen.cuaderno || {};
  const facturas = resumen.facturas || {};

  const porPagar = (pendiente) => {
    if (pendiente === null || pendiente === undefined || Number(pendiente) === 0) return null;
    const importe = importeEnTexto(pendiente);
    return importe ? textoRelleno(textos.hoy.porPagar, { importe }) : null;
  };
  const loCobrado = (cobrado) => {
    if (cobrado === null || cobrado === undefined || Number(cobrado) === 0) return null;
    const importe = importeEnTexto(cobrado);
    return importe ? textoRelleno(textos.hoy.cobrado, { importe }) : null;
  };
  const loQueFalta = () => {
    const faltan = cuaderno.faltan;
    if (faltan === null || faltan === undefined || Number.isNaN(Number(faltan))) return null;
    return Number(faltan) === 1 ? textos.hoy.faltaUna : textoRelleno(textos.hoy.faltan, { n: faltan });
  };

  return {
    gastos: {
      importe: importeEnTexto(gastos.total ?? gastos.importe ?? gastos),
      nota:
        cuentaEnTexto(gastos.n ?? gastos.apuntes, textos.hoy.apunte, textos.hoy.apuntes) ??
        porPagar(gastos.pendiente),
    },
    ventas: {
      importe: importeEnTexto(ventas.total ?? ventas.importe ?? ventas),
      nota:
        cuentaEnTexto(ventas.n ?? ventas.ventas, textos.hoy.apunte, textos.hoy.apuntes) ??
        loCobrado(ventas.cobrado) ??
        porPagar(ventas.pendiente),
    },
    cuaderno: {
      importe: null,
      nota:
        loQueFalta() ??
        cuentaEnTexto(cuaderno.sin_cerrar, textos.hoy.sinCerrar, textos.hoy.sinCerrar),
    },
    facturas: {
      importe: importeEnTexto(facturas.total),
      nota: cuentaEnTexto(facturas.n ?? facturas.cuantas, textos.hoy.factura, textos.hoy.facturasCuenta),
    },
  };
}

/** «Qué falta»: una lista de qué falta y dónde se arregla, sin inventarse ninguna fila. */
export function normalizaQueFalta(datos) {
  let filas = [];
  if (Array.isArray(datos)) filas = datos;
  else if (datos && typeof datos === "object") {
    for (const clave of ["items", "lista", "faltan", "que_falta", "ejemplos"]) {
      if (Array.isArray(datos[clave])) {
        filas = datos[clave];
        break;
      }
    }
  }

  const limpias = [];
  for (const fila of filas) {
    if (typeof fila === "string") {
      const que = fila.trim();
      if (que) limpias.push({ que, donde: null, enlace: null });
      continue;
    }
    if (!fila || typeof fila !== "object") continue;
    const que = fila.que ?? fila.texto ?? fila.titulo ?? fila.descripcion ?? null;
    if (!que || !String(que).trim()) continue;
    limpias.push({
      que: String(que).trim(),
      donde: fila.donde ?? fila.pantalla ?? null,
      enlace: fila.enlace ?? fila.url ?? null,
    });
  }
  return limpias;
}

/**
 * Lo que se ha traído de un cuaderno: el titular, el año y las cuentas de lo que se ha
 * creado, de lo que ya estaba y de lo que no se ha podido apuntar. Sirve para las dos
 * formas (la de un paso y la de leer y luego importar).
 */
export function normalizaImportacion(datos) {
  const todo = datos || {};
  const leido = todo.leido || {};
  const importado = todo.importado || todo.importacion || {};

  const lineas = Array.isArray(leido.lineas) ? leido.lineas.length : null;
  const tierras = Array.isArray(todo.tierras) ? todo.tierras.length : null;
  const numero = (valor) => (valor === null || valor === undefined || Number.isNaN(Number(valor)) ? null : Number(valor));

  return {
    titular: leido.titular || null,
    anio: numero(leido.anio ?? importado.anio),
    tierrasEnElCuaderno: numero(importado.tierras_en_el_cuaderno ?? lineas ?? tierras),
    creadas: numero(importado.creadas),
    yaEstaban: numero(importado.ya_estaban),
    sinApuntar: numero(importado.sin_apuntar),
    hectareas: numero(importado.hectareas_declaradas),
    falta: normalizaQueFalta(todo.que_falta),
    avisos: Array.isArray(importado.avisos) ? importado.avisos : [],
  };
}

/** Un toque en el mapa, en coordenadas de verdad. El sur abajo, como se mira un mapa. */
export function puntoDelMapa(x, y, caja, ancho = ANCHO_MAPA, alto = ALTO_MAPA) {
  if (!esBboxValida(caja)) return null;
  const [oeste, sur, este, norte] = caja;
  const lon = oeste + (Number(x) / ancho) * (este - oeste);
  const lat = norte - (Number(y) / alto) * (norte - sur);
  if (!Number.isFinite(lon) || !Number.isFinite(lat)) return null;
  return [lon, lat];
}

/**
 * Los recintos de una búsqueda que **traen su dibujo**, cada uno con su color. Los que vienen
 * sin puntos (o con puntos que no son coordenadas) se quedan fuera del mapa: se listan, pero no
 * se dibuja un cuadro que nadie ha medido.
 */
export function recintosConPuntos(recintos) {
  const conDibujo = [];
  for (const recinto of Array.isArray(recintos) ? recintos : []) {
    if (!recinto) continue;
    const puntos = [];
    if (Array.isArray(recinto.puntos)) {
      for (const punto of recinto.puntos) {
        if (!Array.isArray(punto) || punto.length < 2) continue;
        const lon = Number(punto[0]);
        const lat = Number(punto[1]);
        if (!Number.isFinite(lon) || !Number.isFinite(lat)) continue;
        puntos.push([lon, lat]);
      }
    }
    if (puntos.length < 3) continue;
    conDibujo.push({
      recinto: recinto.recinto,
      referencia: recinto.referencia ?? null,
      uso: recinto.uso || recinto.uso_sigpac || null,
      superficie_ha: recinto.superficie_ha ?? null,
      pendiente_pct: recinto.pendiente_pct ?? null,
      puntos,
    });
  }
  return conDibujo.map((uno, indice) => ({
    ...uno,
    color: colorDeUso(uno.referencia || String(uno.recinto), indice),
  }));
}

/**
 * La caja que abarca los dibujos de esos recintos, para abrir el mapa donde están ellos y no
 * donde estaba la finca. Si ninguno trae puntos, `null`: no se abre en un sitio inventado.
 */
export function cajaDeLosRecintos(recintos) {
  const longitudes = [];
  const latitudes = [];
  for (const recinto of Array.isArray(recintos) ? recintos : []) {
    const puntos = recinto && recinto.puntos;
    if (!Array.isArray(puntos)) continue;
    for (const punto of puntos) {
      if (!Array.isArray(punto) || punto.length < 2) continue;
      const lon = Number(punto[0]);
      const lat = Number(punto[1]);
      if (!Number.isFinite(lon) || !Number.isFinite(lat)) continue;
      longitudes.push(lon);
      latitudes.push(lat);
    }
  }
  if (!longitudes.length) return null;

  let oeste = Math.min(...longitudes);
  let este = Math.max(...longitudes);
  let sur = Math.min(...latitudes);
  let norte = Math.max(...latitudes);

  // Un recinto diminuto puede dar una caja de lado cero; el servidor no pinta una zona así.
  const relleno = 0.001;
  if (este - oeste < relleno) {
    const medio = (oeste + este) / 2;
    oeste = medio - relleno / 2;
    este = medio + relleno / 2;
  }
  if (norte - sur < relleno) {
    const medio = (sur + norte) / 2;
    sur = medio - relleno / 2;
    norte = medio + relleno / 2;
  }

  const caja = [oeste, sur, este, norte];
  return esBboxValida(caja) ? caja : null;
}
