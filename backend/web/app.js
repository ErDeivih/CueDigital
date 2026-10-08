/*
 * app.js — La interfaz del cuaderno de campo.
 *
 * Reglas que se cumplen en todo este fichero:
 *
 *  1. NUNCA se escribe aquí un texto que lea el agricultor si ese texto tiene que
 *     estar libre de jerga. Los textos vienen de /api/interfaz, o sea de `textos.py`,
 *     que es lo que el test `test_sin_jerga` revisa. Aquí solo hay rótulos internos.
 *  2. Todo lo que se apunta se guarda PRIMERO en el móvil. Si no hay cobertura, se
 *     queda en la cola y se manda solo. Un apunte no se pierde nunca.
 *  3. La lógica que se puede probar sin navegador está en `nucleo.js`, no aquí.
 */

import {
  aNumero,
  avisoDelServidor,
  // Un tratamiento guardado, traducido al borrador del asistente: lo usan «lo mismo que la última
  // vez» y CORREGIR un apunte (ronda 91), para que los dos lean los mismos nombres de campo.
  borradorDeTratamiento,
  crearAlmacenMemoria,
  conCuenta,
  crearCola,
  decideQueHacer,
  diasDeEspera,
  fechaEnPalabras,
  formateaFecha,
  formateaNumero,
  queSePuedeRepetir,
  rellena,
  repetirUltimo,
  sumandoLoQueSeSabe,
  tierrasQueCasen,
  ultimoDeLaFinca,
  validaPaso,
  validaSuperficie,
} from "./nucleo.js";
import { montarEn, montarFueraDeLaPantalla } from "./react/montar.js";
// El enrutador (T04, 02/10/2026): traduce entre la dirección del navegador y la pantalla que se está
// viendo. Aquí solo se usa: dónde vive cada cosa lo decide él (`react/rutas.js`), y este fichero se
// encarga de lo que sí toca el navegador (`history`, `popstate`, la posición de la lista).
import {
  escribir as escribirLaDireccion,
  leer as leerLaDireccion,
  recuerda,
  recupera,
} from "./react/rutas.js";
// `html` se importa para poder **componer** varias piezas en un solo paso: hay tres pantallas del
// asistente que piden dos cosas a la vez (una lista y un campo, una lista y unos números, una fecha y un
// lote). Sin esto habría que hacer una pieza nueva para cada mezcla, y las piezas ya están hechas.
import { html, AvisoDeError, BotonSencillo } from "./react/componentes.js";
import { pantallaDeInicio } from "./react/pantallas/inicio.js";
import { pantallaDeHecho } from "./react/pantallas/hecho.js";
import { pantallaDeMisCosas } from "./react/pantallas/mis_cosas.js";
import { pantallaDeDocumentos } from "./react/pantallas/documentos.js";
import { pantallaDeCesta } from "./react/pantallas/cesta.js";
// El libro del almacén (T09, 03/10/2026): el albarán que llega, los envases y el libro de movimientos.
import { pantallaDelLibroDelAlmacen } from "./react/pantallas/libro_del_almacen.js";
import { pantallaDeNuevoAlbaran } from "./react/pantallas/nuevo_albaran.js";
import { pantallaDeRecepcion } from "./react/pantallas/recepcion.js";
import { pantallaDeMovimientoDeAlmacen } from "./react/pantallas/movimiento_de_almacen.js";
import { pantallaDeSacarDeUnLote } from "./react/pantallas/sacar_de_un_lote.js";
import { pantallaDeEngancharLaFactura } from "./react/pantallas/enganchar_la_factura.js";
import { pantallaDeCultivos } from "./react/pantallas/cultivos.js";
import { pantallaDeAyuda } from "./react/pantallas/ayuda.js";
import { pantallaDeMisDatos } from "./react/pantallas/mis_datos.js";
import { pantallaDeQuienEntra } from "./react/pantallas/quien_entra.js";
import { pantallaDeMedidas } from "./react/pantallas/medidas.js";
import { pantallaDeVentas } from "./react/pantallas/ventas.js";
// **El dinero de lo que se vende** (T12, E6, 03/10/2026): la factura nuestra (la lista, la ficha y el
// paso de juntar entregas) y las cuatro pantallas del cobro y del ajuste. Un fichero por pantalla, como
// todo lo demás aquí, y todos en la caché del campo: la cuenta de la factura se mira también en la nave,
// sin cobertura.
import { pantallaDeFacturasEmitidas } from "./react/pantallas/facturas_emitidas.js";
import { pantallaDeFacturarEntregas } from "./react/pantallas/facturar_entregas.js";
import { pantallaDeUnaFacturaEmitida } from "./react/pantallas/factura_emitida.js";
import { pantallaDeImporte } from "./react/pantallas/venta_importe.js";
import { pantallaDeAjuste } from "./react/pantallas/venta_ajuste.js";
import { pantallaDeCobros } from "./react/pantallas/cobros.js";
import { pantallaDeCobroNuevo } from "./react/pantallas/cobro_nuevo.js";
import { pantallaDeGrupos } from "./react/pantallas/grupos.js";
import { pantallaDeAnaliticas } from "./react/pantallas/analiticas.js";
import { pantallaDeDictado } from "./react/pantallas/dictado.js";
import { pantallaDeBorrador } from "./react/pantallas/borrador.js";
import { pantallaDeNuevoDocumento } from "./react/pantallas/nuevo_documento.js";
import { pantallaDeFirmar } from "./react/pantallas/firmar.js";
import { pantallaDePlanes } from "./react/pantallas/planes.js";
import { pantallaDeEntrar } from "./react/pantallas/entrar.js";
import { pantallaDeFacturas } from "./react/pantallas/facturas.js";
import { pantallaDeNuevaFactura } from "./react/pantallas/nueva_factura.js";
import { pantallaDeInterpretacionDeLaFactura } from "./react/pantallas/interpretacion_factura.js";
import { pantallaDeMapa } from "./react/pantallas/mapa.js";
// Las tierras en el mapa y en la tabla, y lo que ha sido una tierra (T06, 03/10/2026): la vista que
// pide el contrato en su apartado 2.1 —las 64 tierras con buscador, filtros, agrupación, selección
// múltiple y el mapa de la finca enlazado con la tabla— y la ficha que T05 dejó pedida, con sus
// versiones por año y por fuente, la comparación de dos años y el ensayo de una importación.
//
// De los dos módulos se importan también sus **funciones puras** (`filtrarLasTierras`, que es la
// misma que usa la pantalla para contar lo que se ve; `puntosDelTrozo`; `aniosConVersiones` y
// `loteDesdeLasVersiones`): son las que deciden qué se enseña y qué se manda, y viven en un solo
// sitio para que la pantalla y `app.js` no puedan contar cosas distintas.
import {
  filtrarLasTierras,
  pantallaDeLasTierrasDeLaExplotacion,
} from "./react/pantallas/tierras_mapa.js";
import {
  aniosConVersiones,
  loteDesdeLasVersiones,
  pantallaDeLasVersionesDeUnaTierra,
} from "./react/pantallas/tierra_versiones.js";
import { pantallaDeDecirCultivo } from "./react/pantallas/decir_cultivo.js";
// **La búsqueda global** (07/10/2026, del encargo del rediseño): la caja de la cabecera y la pantalla de
// resultados. La puerta del servidor (`GET /api/buscar`, con sus cinco grupos) y la pantalla están hechas
// y probadas; esto es el cable que las une.
import { pantallaDeLaBusqueda } from "./react/pantallas/buscar.js";
// Las semillas, sus etiquetas y las siembras (T10, 03/10/2026): la lista de semillas con lo que queda
// de cada una, la ficha donde se apunta lo que pone la etiqueta —y donde se confirma lo que se ha
// leído de una foto— y la siembra, que es «en esta tierra sembré esta semilla».
import { pantallaDeLasSemillas, pantallaDeUnaSemilla } from "./react/pantallas/semillas.js";
import { pantallaDeLasSiembras, pantallaDeUnaSiembra } from "./react/pantallas/siembras.js";
// Las personas y las empresas (T11, 03/10/2026): la ficha de un contacto —con los papeles que hace con
// la finca—, el enlace desde los nombres que ya están escritos en las facturas, las ventas y los
// análisis, y la revisión de esos nombres, que es donde el programa **propone y no fusiona**.
import {
  pantallaDeLosContactos,
  pantallaDeUnContacto,
  pantallaDeLosNombresEscritos,
} from "./react/pantallas/contactos.js";
import { pantallaDeLaRevisionDeLosNombres } from "./react/pantallas/revision_de_contactos.js";
import { pantallaDeCuadernoDeLaJunta } from "./react/pantallas/cuaderno_de_la_junta.js";
import { pantallaDeCampanas } from "./react/pantallas/campanas.js";
import { marcoDeLaAplicacion } from "./react/piezas/marco.js";
import { pantallaTraerDelSigpac } from "./react/pantallas/traer_del_sigpac.js";
import { pantallaDeMiCuaderno } from "./react/pantallas/mi_cuaderno.js";
import { pantallaDelAsistente } from "./react/pantallas/asistente.js";
import { confirmacion } from "./react/piezas/confirmacion.js";
import { resumenDelApunte } from "./react/piezas/resumen_del_apunte.js";
import { listaParaElegir } from "./react/piezas/lista_para_elegir.js";
// `campo` a secas chocaría con el nombre del parámetro de `pintaFecha`/`montarFecha`, que se llama así
// desde el principio: se le pone `campoDeReact` para que se lea de un vistazo de qué lado está.
import { campo as campoDeReact } from "./react/piezas/campo.js";
import { camposDelMaestro } from "./react/piezas/campos_del_maestro.js";
// **La maquinaria de la finca (T14, E8, 03/10/2026).** Un fichero con las dos pantallas del contrato:
// la lista (`#/maquinaria`) y la ficha de una máquina (`#/maquinaria/<id>`). Es un solo fichero porque
// son la misma cosa mirada de dos maneras —lo mismo que las semillas—, y va aquí, con las demás, para
// que el import diga de un vistazo que esta pantalla ya está en React.
import { pantallaDeLaMaquinaria, pantallaDeUnaMaquina } from "./react/pantallas/maquinaria.js";
// **Las cuentas de la explotación (T13, E7, 05/10/2026).** Un fichero con las dos pantallas del
// contrato: la lista (`#/cuentas`) y la ficha de un gasto (`#/cuentas/<id>`). Es un solo fichero
// porque las dos comparten las mismas piezas —la tarjeta de cifras, el cuadre del reparto y los
// formularios— y separarlas obligaría a copiarlas.
import { pantallaDeLasCuentas, pantallaDeUnGasto } from "./react/pantallas/gastos.js";
// **El extracto del banco y la conciliación (T20, E11, 06/10/2026).** Un fichero con las dos pantallas
// del contrato: los movimientos (`#/cuentas/bancos`) y la ficha de un movimiento
// (`#/cuentas/bancos/<id>`), que es donde se dice contra qué papel va el dinero. Es un solo fichero
// porque las dos comparten las mismas piezas (el renglón de dato, el formulario y el bloque de las
// propuestas) y separarlas obligaría a copiarlas.
import { pantallaDeLosBancos, pantallaDeUnMovimiento } from "./react/pantallas/bancos.js";
// **Los trabajos por tierra (T15, E9, 05/10/2026).** Un fichero con las tres pantallas del contrato: la
// agenda (`#/trabajos`), la ficha de un trabajo (que es un formulario y **no** tiene dirección) y la
// historia de una tierra (`#/tierras/<id>/historial`). Es un solo fichero porque las tres comparten lo
// mismo: el previsto y el hecho, que es lo que este ticket viene a separar.
import {
  pantallaDeLosTrabajos,
  pantallaDeUnTrabajo,
  pantallaDeLaTierra,
} from "./react/pantallas/trabajos.js";
// **La bandeja documental (T08, S10, 06/10/2026).** Un fichero con las dos pantallas del contrato: lo
// que llega y hay que revisar (`#/papeles/bandeja`) y la ficha de un papel (`#/papeles/bandeja/<id>`),
// que es donde se mira **el original con la propuesta al lado**. Es un solo fichero porque las dos
// comparten las mismas piezas (el dato, la línea leída y el bloque de los enlaces).
//
// **Esta línea faltaba, y se encontró en un navegador de verdad**: el bloque del ticket traía el estado,
// las pantallas y las siete líneas de cableado, pero **no el `import`**, así que abrir la bandeja
// enseñaba «esta pantalla no se ha podido abrir… falta un fichero del programa» —el aviso de cuando un
// componente no está— con las 13 puertas del servidor funcionando. Es justo lo que no se ve en las
// pruebas de los componentes (que importan el fichero ellas mismas) ni en las de cableado: hace falta
// abrir la aplicación de verdad.
import { pantallaDeLaBandeja, pantallaDeUnPapelDeLaBandeja } from "./react/pantallas/bandeja.js";

/**
 * Qué pantallas están ya en React y cuáles todavía no.
 *
 * **Esta lista es la fuente de la verdad de la migración**, y no un adorno: hay tres sitios que tienen que
 * decir lo mismo y una prueba de Python (`tests/test_la_migracion_a_react.py`) que lo exige. Son esta
 * lista, la tabla de `docs/REACT.md` y la lista de ficheros que se guardan para abrir **sin cobertura**
 * (`FICHEROS` del `service-worker.js`). Si añades una pantalla aquí y te olvidas de la caché, el
 * agricultor que abra la aplicación en el campo se queda con la pantalla en blanco.
 *
 * **La migración está terminada** (ronda 72): lo que el agricultor ve está entero en React y el único
 * sitio que escribe en la pantalla es `montar()` (ver `docs/REACT.md`). Lo que sigue en la lista son las
 * pantallas que se piden a React, que hoy son todas.
 *
 * Si añades una pantalla a esta lista, tienes que montarla con `montarEn` (o con `montar`) y no con
 * `pintar`: las dos cosas escribirían en el mismo contenedor (`#pantalla`), así que si se pintan las dos,
 * una tapa a la otra.
 */
const PANTALLAS_EN_REACT = new Set([
  "inicio",
  "hecho",
  "mis_cosas",
  "documentos",
  "cesta",
  "cultivos",
  "ayuda",
  "mis_datos",
  "quien_entra",
  "medidas",
  "ventas",
  "grupos",
  "analiticas",
  "dictado",
  "borrador",
  "nuevo_documento",
  "firmar",
  "planes",
  "entrar",
  "facturas",
  "nueva_factura",
  "interpretacion_factura",
  "mapa",
  "decir_cultivo",
  "cuaderno_de_la_junta",
  "traer_del_sigpac",
  "mi_cuaderno",
  "asistente",
  // Ronda 93: los años del cuaderno. Entra con el rediseño de Stitch de esta pantalla y con sus pruebas.
  "campanas",
  "bandeja",
  // El libro del almacén (T09, 03/10/2026): las seis pantallas del albarán, los envases y el libro. Van
  // aquí las seis juntas porque son la misma cosa vista desde sitios distintos: la lista y la ficha de un
  // albarán (que tienen dirección propia) y los cuatro formularios (que no la tienen a propósito).
  "libro_del_almacen",
  "nuevo_albaran",
  "recepcion",
  "movimiento_de_almacen",
  "sacar_de_un_lote",
  "enganchar_la_factura",
  // T06 (03/10/2026): las tierras en el mapa y en la tabla, y lo que ha sido una tierra. Son las dos
  // pantallas nuevas de este ticket, y las dos llevan la pantalla vieja de `mis_cosas` de la mano en
  // vez de sustituirla: `#/tierras` sigue siendo la lista de siempre, con su buscador y su tabla.
  "tierras_mapa",
  "tierra_versiones",
  // La búsqueda global (07/10/2026): su pantalla es de React como las demás, y esta lista es la que lo dice.
  "buscar",
  // T10 (03/10/2026): las semillas con lo que pone su etiqueta y las siembras. Son dos ficheros
  // (`semillas.js` y `siembras.js`) y cuatro pantallas, y los dos van aquí y en la caché del campo:
  // la lista de semillas y la siembra se miran **en la nave y en la parcela**, muchas veces sin
  // cobertura, y una pantalla que no está en la caché es un hueco justo cuando más falta hace.
  "semillas",
  "siembras",
  // T11 (03/10/2026): las personas y las empresas, y la revisión de los nombres que ya están escritos.
  // Son dos ficheros (`contactos.js` y `revision_de_contactos.js`) y cuatro pantallas. Los dos van aquí
  // y en la caché del campo por lo de siempre: una pantalla que no está guardada es un hueco sin
  // cobertura, y la ficha de un proveedor se mira tanto en la nave como en el despacho.
  "contactos",
  "revision_de_contactos",
  // T12 (03/10/2026): el dinero de lo que se vende. Son siete pantallas en tres ficheros
  // (`ventas.js`, `facturas_emitidas.js` y `cobros.js`): la lista con su tabla, la factura nuestra (la
  // lista, la ficha y el paso de juntar entregas), el importe de una entrega, sus ajustes y los
  // cobros. Y van aquí —y en la caché del campo— por lo de siempre: una pantalla que no está guardada
  // es un hueco justo cuando más falta hace.
  "facturas_emitidas",
  "facturar_entregas",
  "factura_emitida",
  "venta_importe",
  "venta_ajuste",
  "cobros",
  "cobro_nuevo",
  // T14 (03/10/2026): la maquinaria de la finca y sus inspecciones. Un solo fichero
  // (`maquinaria.js`) con las dos pantallas: la lista con su tabla y la ficha de una máquina, que es la
  // que separa las cinco obligaciones (ITV, ITEAF, mantenimiento, seguro y ROMA). Va aquí, y en la caché
  // del campo, por lo de siempre: la lista de máquinas se mira en la nave —para saber si se puede contar
  // con el tractor— y ahí es donde peor va la cobertura.
  "maquinaria",
  // T13 (05/10/2026): las cuentas de la explotación. Un solo fichero (`gastos.js`) con las dos
  // pantallas: la lista con su tabla y la ficha de un gasto, que es donde se reparte a las tierras,
  // los cultivos y las máquinas. Va aquí, y en la caché del campo, por lo de siempre: las cuentas se
  // miran en el despacho y también de pie en la nave.
  "gastos",
  // El extracto del banco y la conciliación (T20, E11, 06/10/2026). Un solo fichero (`bancos.js`) con las
  // dos pantallas: los movimientos con su estado y lo que les queda, y la ficha de uno, que es donde se
  // dice contra qué papel va. Va aquí y en la caché del campo por lo de siempre: sin cobertura, una
  // pantalla que no está guardada es un hueco.
  "bancos",
  // T15 (05/10/2026): los trabajos por tierra. La clave de esta lista es **el nombre del fichero**
  // (`trabajos.js`), que trae las tres pantallas: la agenda, la ficha de un trabajo y la historia de
  // una tierra. Va aquí por el mismo motivo que las demás: lo que está pensado y lo que se ha hecho se
  // mira en el campo, y sin este fichero en la caché esa pantalla se queda en blanco.
  "trabajos",
]);

// ---------------------------------------------------------------- almacenamiento

function almacenSeguro() {
  try {
    const prueba = "__cuedigital_prueba__";
    window.localStorage.setItem(prueba, "1");
    window.localStorage.removeItem(prueba);
    return window.localStorage;
  } catch (error) {
    // En modo privado el navegador bloquea el almacenamiento. La aplicación tiene
    // que seguir funcionando, aunque sea sin guardar: es mejor eso que una pantalla
    // en blanco delante de un agricultor.
    return crearAlmacenMemoria();
  }
}

const ALMACEN = almacenSeguro();
const CLAVE_TOKEN = "cuedigital.token";
const CLAVE_NOMBRE = "cuedigital.nombre";
const CLAVE_INTERFAZ = "cuedigital.interfaz";
const CLAVE_ULTIMO = "cuedigital.ultimo";
const CLAVE_RECHAZADOS = "cuedigital.rechazados";
const CLAVE_LETRA = "cuedigital.letra-grande";

const cola = crearCola(ALMACEN);

function guardar(clave, valor) {
  try {
    ALMACEN.setItem(clave, JSON.stringify(valor));
  } catch (error) {
    /* sin almacenamiento: se sigue funcionando en memoria */
  }
}

function leer(clave, porDefecto = null) {
  try {
    const bruto = ALMACEN.getItem(clave);
    return bruto ? JSON.parse(bruto) : porDefecto;
  } catch (error) {
    return porDefecto;
  }
}

// ------------------------------------------------------------------- utilidades

function esc(texto) {
  return String(texto === null || texto === undefined ? "" : texto)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function iso(fecha) {
  return [
    fecha.getFullYear(),
    String(fecha.getMonth() + 1).padStart(2, "0"),
    String(fecha.getDate()).padStart(2, "0"),
  ].join("-");
}

function hoyISO() {
  return iso(new Date());
}

function ayerISO() {
  const fecha = new Date();
  fecha.setDate(fecha.getDate() - 1);
  return iso(fecha);
}

const pantalla = document.getElementById("pantalla");
const avisoPendientes = document.getElementById("aviso-pendientes");
const cabeceraTexto = document.getElementById("cabecera-texto");

// ------------------------------------------------------------------------ estado

const estado = {
  token: ALMACEN.getItem(CLAVE_TOKEN) || null,
  nombre: leer(CLAVE_NOMBRE, ""),
  interfaz: leer(CLAVE_INTERFAZ, null),
  campana: null,
  parcelas: [],
  productos: [],
  abonos: [],
  aplicadores: [],
  asesores: [],
  equipos: [],
  instalaciones: [],
  planes: [],
  analiticas: [],
  medidas: null,
  ventas: [],
  // **El dinero de lo que se vende (T12).** `ventasTabla` es la respuesta de `/api/ventas/tabla`: la
  // tabla con su pie y sus totales, **calculados por el servidor sobre el conjunto filtrado** (el
  // contrato lo pide así y el motivo es que en el navegador el dinero perdería céntimos). El filtro
  // vive aquí porque el filtrado también es del servidor: cambiar el filtro es volver a preguntar.
  ventasTabla: null,
  filtroVentas: { q: "", solo: "", orden: "", sentido: -1 },
  facturasEmitidas: [],
  facturaEmitida: null,
  cobros: [],
  // Los borradores de las tres pantallas que se rellenan: el importe de una entrega, su ajuste y el
  // cobro. Viven aquí y no en el componente por lo de siempre: lo escrito sobrevive al repintado.
  borradorImporte: null,
  borradorAjuste: null,
  borradorCobro: null,
  borradorFactura: null,
  // La entrega entera que se está tocando (la pide al servidor `pantallaImporteDeUnaEntrega`) y la
  // clave de reenvío de la factura que se está haciendo. Las dos son de la pantalla que las usa, pero
  // viven aquí para que un repintado no las pierda.
  entregaDelImporte: null,
  entregaDelAjuste: null,
  claveDeLaFactura: null,
  // Las entregas marcadas para juntarlas en una factura (identificadores) y lo que se acaba de decir
  // al guardar algo del dinero: lo que se enseña en la lista cuando se vuelve a ella.
  entregasAFacturar: [],
  avisoVentas: "",
  errorVentas: "",
  tratamientos: [],
  faltantes: null,
  asistente: null,
  // Lo que el agricultor ha escrito en el buscador de tierras (ronda 82). Vive aquí y no en el paso del
  // asistente porque el paso se vuelve a montar entero cada vez: lo escrito tiene que sobrevivir a eso,
  // y se vacía al abrir un asistente nuevo (ver `abrirAsistente`).
  //
  // Son **dos**: el del asistente (donde se elige una tierra) y el de «mis cosas» (donde se miran). Si
  // fueran uno, buscar «prado» en el asistente dejaría «mis cosas» enseñando dos tierras de las 51 sin que
  // nadie lo hubiera pedido allí —y la cuenta de arriba diría 51—.
  filtroTierras: "",
  filtroTierrasMisCosas: "",
  // El mapa: dónde se está mirando, qué parcela se ha encontrado y con qué nombre se apuntaría.
  mapa: null,
  ultimo: leer(CLAVE_ULTIMO, null),
  confirmacion: null,
  // El dictado: lo que se ha escrito o dicho, y lo que ha entendido el servidor.
  dictadoTexto: "",
  errorDictado: "",
  borradorPendiente: null,
  // Si esta instalación sabe leer el certificado digital, y qué certificado se ve.
  certificadoEstado: null,
  errorCertificado: "",
  // La firma del cuaderno: si está firmado, y si la firma sigue valiendo.
  firmaEstado: null,
  errorFirma: "",
  firmaLista: false,
  // Las medidas preventivas de la finca, y la copia con la que se trabaja en su pantalla
  // mientras el agricultor marca y desmarca.
  medidas: null,
  medidasBorrador: null,
  // Qué hay sembrado en cada parcela este año. Los avisos de esas dos pantallas van aparte de
  // los demás para que un error al guardar un papel no se mezcle con uno al escribir un cultivo.
  errorDocumentos: "",
  errorCesta: "",
  errorCultivos: "",
  errorGrupos: "",
  cultivoParcela: null,
  // Las fincas de la cuenta y quién entra en la que se está usando (ronda 89). Se piden **al abrir la
  // pantalla** y no al arrancar: con una sola finca no hacen falta para nada, y el arranque en el campo
  // (que es cuando peor va la cobertura) no tiene por qué cargar con dos llamadas más.
  fincas: [],
  quienEntra: null,
  errorFincas: "",
  // El aviso de que la lista ha cambiado («Ya puede entrar en tu finca»). Va aparte del error porque los
  // dos pueden salir en la misma pantalla y uno no borra al otro: el aviso dice lo que sí se hizo.
  avisoFincas: "",
  // **La dirección (T04, 02/10/2026).** `pantalla` es la pantalla que se está viendo según el enrutador
  // (`react/rutas.js`), y `vistas` es la memoria de las listas: qué filtros y qué orden tenía cada una y
  // por dónde iba, para que volver de una ficha deje la lista como estaba. Y `completando` dice si la
  // dirección que se está escribiendo viene de una navegación del navegador (atrás/adelante) o del
  // arranque: en esos dos casos se **reemplaza** en vez de añadir una entrada al historial, porque si no
  // «atrás» daría dos pasos para volver a lo mismo.
  pantalla: "",
  vistas: {},
  completando: false,
  // **Las tierras en el mapa y en la tabla (T06, 03/10/2026).** Aquí vive lo que el agricultor tiene
  // puesto en esa pantalla: lo que ha filtrado, cómo ha agrupado, qué ha marcado, qué tierra está
  // mirando y cómo está mirando el mapa. Va en `estado` y no dentro del componente porque **el
  // componente se vuelve a montar entero** cada vez que se toca algo (una raíz de React nueva, ver
  // `docs/REACT.md`), así que lo que el agricultor había elegido tiene que vivir fuera.
  //
  // `vista` es lo que devolvió `/api/parcelas/vista`: las tierras, los recuentos de la finca entera,
  // la caja del mapa y las opciones de los filtros, todo del mismo momento. Se pide al abrir la
  // pantalla y **no** al arrancar: son 64 tierras con sus anillos, y en el campo (que es cuando peor
  // va la cobertura) nadie tiene por qué cargar con eso para apuntar un tratamiento.
  t06: null,
};

/**
 * Busca un texto por su ruta: "mensajes.V10_sin_justificacion",
 * "etiquetas.comun.fecha.pregunta", "ayuda.pantalla.titulo".
 *
 * Las etiquetas de los campos llevan puntos DENTRO del nombre ("comun.fecha" es UNA
 * clave, no dos). Por eso se prueban primero las claves más largas posibles antes de
 * partir la ruta: sin esto, las etiquetas no se encontrarían nunca y las preguntas
 * saldrían en blanco.
 */
function busca(objeto, claves) {
  if (claves.length === 0) return objeto;
  if (objeto === null || typeof objeto !== "object") return undefined;
  for (let largo = claves.length; largo >= 1; largo -= 1) {
    const clave = claves.slice(0, largo).join(".");
    if (Object.prototype.hasOwnProperty.call(objeto, clave)) {
      const resto = busca(objeto[clave], claves.slice(largo));
      if (resto !== undefined) return resto;
    }
  }
  return undefined;
}

/** Coge un texto de la interfaz sin que reviente si todavía no se ha cargado. */
function t(ruta, porDefecto = "") {
  if (!estado.interfaz) return porDefecto;
  const valor = busca(estado.interfaz, String(ruta).split("."));
  return valor === undefined ? porDefecto : valor;
}

function accion(nombre) {
  return (estado.interfaz && estado.interfaz.acciones[nombre]) || nombre;
}

function mensaje(codigo, datos) {
  const plantilla = t(`mensajes.${codigo}`, "");
  return plantilla ? rellena(plantilla, datos) : "";
}

function aviso(clave) {
  return t(`aviso.${clave}`, "");
}

// ------------------------------------------------------------------------- API

async function api(ruta, opciones = {}) {
  const cabeceras = { "Content-Type": "application/json" };
  if (estado.token) cabeceras.Authorization = `Bearer ${estado.token}`;
  const respuesta = await fetch(ruta, { ...opciones, headers: cabeceras });
  if (respuesta.status === 401) {
    salir(false);
    throw new Error("sin permiso");
  }
  return respuesta;
}

/**
 * Una ruta con el año que se está mirando puesto: `?campana_id=3`.
 *
 * **Para qué** (06/10/2026): hay rutas que, sin decirles el año, contestan con **el año en curso** —y
 * algunas con el **más nuevo** de la finca—, y el agricultor puede estar mirando otro. Cuando eso pasa,
 * la pantalla enseña lo de un año y el fichero que se descarga es de otro (aceptación 3 del encargo: el
 * fichero tiene que ser el que se está viendo). Con esto, la ruta y la descarga piden lo mismo.
 *
 * Si todavía no se sabe qué año se está mirando (al arrancar, antes de pedir las campañas), no se añade
 * nada: es lo mismo que hacía antes, y el servidor decide. Se prefiere eso a inventarse un año.
 */
function conLaCampana(ruta) {
  if (!estado.campana || !estado.campana.id) return ruta;
  const union = ruta.includes("?") ? "&" : "?";
  return `${ruta}${union}campana_id=${estado.campana.id}`;
}

async function apiJson(ruta, opciones = {}) {
  const respuesta = await api(ruta, opciones);
  if (!respuesta.ok) {
    let cuerpo = null;
    try {
      cuerpo = await respuesta.json();
    } catch (error) {
      cuerpo = null;
    }
    const texto = avisoDelServidor(cuerpo) || mensaje("no_se_pudo");
    throw new Error(texto || "No se ha podido.");
  }
  return respuesta.status === 204 ? null : respuesta.json();
}

// ------------------------------------------------ mandar, o guardar si no hay red

/**
 * Manda un apunte. Si no hay cobertura, lo guarda en el móvil para mandarlo después.
 *
 * Devuelve `{ok, datos}` si se guardó en el servidor, `{encolado: true}` si quedó
 * pendiente, o `{error}` si el servidor lo rechazó.
 */
/**
 * Manda un apunte. Si no hay cobertura, lo guarda en el móvil para mandarlo después.
 *
 * `guardarComoUltimo` existe porque "LO MISMO QUE LA ÚLTIMA VEZ" solo tiene sentido
 * para lo que se repite: un tratamiento o un abono. Si al dar de alta una parcela se
 * guardase como "último", el atajo ofrecería crear la misma parcela otra vez.
 */
async function enviarOApuntar(ruta, datos, tipo, guardarComoUltimo = true) {
  if (!navigator.onLine) {
    cola.apuntar({ tipo, ruta, datos });
    pintarAvisoPendientes();
    return { encolado: true };
  }
  try {
    const respuesta = await api(ruta, { method: "POST", body: JSON.stringify(datos) });
    if (respuesta.ok) {
      const cuerpo = await respuesta.json();
      if (guardarComoUltimo) {
        guardar(CLAVE_ULTIMO, { tipo, datos });
        estado.ultimo = { tipo, datos };
      }
      return { ok: true, datos: cuerpo };
    }
    const cuerpo = await respuesta.json().catch(() => null);
    // Un 4xx no se arregla mandándolo otra vez: se le dice al agricultor y ya está. **Y se devuelve el
    // estado**, que desde el T09 hace falta: con la misma palabra («no») el servidor avisa de dos cosas
    // distintas que se resuelven distinto —que falta escribir el total, o que lo que sale deja el envase
    // en negativo—, y quien llama tiene que poder distinguirlas.
    if (respuesta.status >= 400 && respuesta.status < 500) {
      return { error: avisoDelServidor(cuerpo) || mensaje("no_se_pudo"), estado: respuesta.status };
    }
    // Un 5xx sí puede ser pasajero: se guarda y se reintenta.
    cola.apuntar({ tipo, ruta, datos });
    pintarAvisoPendientes();
    return { encolado: true };
  } catch (error) {
    // El navegador dice que hay red, pero no llega: es lo normal en el campo.
    cola.apuntar({ tipo, ruta, datos });
    pintarAvisoPendientes();
    return { encolado: true };
  }
}

/**
 * Manda una corrección o un borrado, y **solo se hace con cobertura**.
 *
 * POR QUÉ ESTO NO PASA POR LA COLA DE SIN COBERTURA. La cola guarda apuntes para mandarlos cuando
 * haya red, y todo lo que hay en ella se manda con POST: no sirve para cambiar algo que ya está en
 * el servidor —corregir un apunte que todavía no ha llegado no tiene nada que corregir, y borrarlo
 * sería pedirle al servidor que borre lo que aún no tiene—. Así que corregir y borrar se hacen
 * **en el momento**, y si no hay cobertura se dice con el aviso de siempre. Apuntar en el campo
 * sigue funcionando sin cobertura, que es lo que no puede fallar.
 */
async function mandarCambio(ruta, metodo, datos) {
  try {
    const respuesta = await api(ruta, {
      method: metodo,
      body: datos === undefined ? undefined : JSON.stringify(datos),
    });
    const cuerpo = await respuesta.json().catch(() => null);
    if (!respuesta.ok) {
      // **Y se devuelve el estado**, por el mismo motivo que en `enviarOApuntar`: con la misma palabra
      // («no») el servidor avisa de dos cosas que se resuelven distinto, y quien llama tiene que poder
      // distinguir «falta un dato» de «lo que sale deja el envase en negativo».
      return { error: avisoDelServidor(cuerpo) || mensaje("no_se_pudo"), estado: respuesta.status };
    }
    return { ok: true, datos: cuerpo };
  } catch (error) {
    return { error: mensaje("no_se_pudo") };
  }
}

async function mandarPendientes() {
  const decision = decideQueHacer(cola, navigator.onLine);
  if (decision.accion !== "mandar") {
    pintarAvisoPendientes();
    return;
  }

  const rechazados = leer(CLAVE_RECHAZADOS, []);
  let algoMandado = false;
  for (const apunte of cola.leer()) {
    try {
      const respuesta = await api(apunte.ruta, {
        method: "POST",
        body: JSON.stringify(apunte.datos),
      });
      if (respuesta.ok) {
        cola.quitar(apunte.id_local);
        algoMandado = true;
        continue;
      }
      if (respuesta.status >= 400 && respuesta.status < 500) {
        // Se aparta en vez de borrarlo: perder un apunte del agricultor en silencio
        // es exactamente lo que esta aplicación no puede hacer.
        const cuerpo = await respuesta.json().catch(() => null);
        rechazados.push({
          datos: apunte.datos,
          motivo: avisoDelServidor(cuerpo) || mensaje("no_se_pudo"),
          cuando: apunte.apuntado_en,
        });
        guardar(CLAVE_RECHAZADOS, rechazados);
        cola.quitar(apunte.id_local);
        continue;
      }
      break; // el servidor está de mal humor: se reintenta luego
    } catch (error) {
      break; // se ha ido la red otra vez
    }
  }
  if (algoMandado) {
    // Si lo que se ha mandado era dar de alta una parcela o un producto, las listas
    // de memoria se han quedado viejas. Se recargan sin molestar a nadie.
    await cargarDatos().catch(() => {});
  }
  pintarAvisoPendientes();
}

function pintarAvisoPendientes() {
  const cuantos = cola.tamano();
  const rechazados = leer(CLAVE_RECHAZADOS, []);
  if (cuantos === 0 && rechazados.length === 0) {
    avisoPendientes.classList.add("oculto");
    avisoPendientes.className = "aviso oculto";
    return;
  }

  avisoPendientes.classList.remove("oculto");
  if (rechazados.length > 0) {
    avisoPendientes.className = "aviso aviso-error";
    const ultimo = rechazados[rechazados.length - 1];
    avisoPendientes.innerHTML = `<strong>${esc(ultimo.motivo)}</strong>`;
    return;
  }

  avisoPendientes.className = "aviso";
  // El texto va en singular o en plural según cuántos haya: «1 cosas apuntadas» se lee fatal, y este aviso
  // sale en la cabecera justo cuando el agricultor está en el campo sin cobertura (ronda 84).
  avisoPendientes.textContent = conCuenta(t("aviso", {}) || {}, "pendientes", cuantos);
}

// --------------------------------------------------------------- montar en React

/**
 * Monta una pantalla de React en el contenedor de la pantalla, con la salida de emergencia.
 *
 * **Es el único sitio que escribe en la pantalla.** Hasta la ronda 72 había aquí una función `pintar()`
 * que hacía `pantalla.innerHTML = …`, y con ella se pintaban las pantallas que no estaban migradas —y su
 * último usuario era el asistente, que ya está en React—. Se borró: ya no queda ni un `innerHTML` en la
 * aplicación (fuera del aviso de emergencia de `montar.js`, que lo necesita para cuando React no llega).
 *
 * Si los ficheros de `vendor/` no han llegado, `montarEn` enseña el aviso con su botón de recargar en vez
 * de dejar la pantalla en blanco. El elemento se pide **dentro de un `try`** porque prepararlo también
 * puede fallar (por ejemplo, si falta un texto de los que se piden al servidor): en ese caso se monta nada
 * y sale el aviso.
 */
function montar(elemento) {
  let listo = null;
  try {
    listo = elemento();
  } catch (fallo) {
    listo = null;
  }
  // Antes de cambiar de pantalla se apunta **por dónde iba** en la lista que se deja (T04): es lo que
  // hace que volver de una ficha no devuelva al agricultor al principio de las 64 tierras.
  recordarPorDondeIba();
  // Y se guarda **qué** pantalla está puesta: hace falta para volver a pintar el armazón cuando llegan
  // datos suyos (las fincas de la cuenta) sin dejar el menú sin marcar el módulo.
  estado.ultimoMontado = listo;
  montarEn(pantalla, listo, {
    sin_react: t("react.sin_react", ""),
    recargar: t("react.recargar", ""),
  });
  // **Y el armazón se pone al día** (30/09/2026): el menú lateral y la barra de arriba saben en qué módulo
  // se está (para marcarlo) y en qué finca y año se apunta. Se hace aquí, en el único sitio por el que
  // pasan todas las pantallas, y **fuera** de `montarEn` para no contarse como una pantalla más (ver
  // `montajesDelMarco`).
  pintarMarco(listo);
  // Y la dirección se pone al día **en el mismo sitio por el que pasan todas las pantallas** (T04): si se
  // escribiera en cada `pantalla*()` habría veinte sitios donde olvidarse, y el olvido no se vería hasta
  // que alguien recargara.
  apuntarLaDireccion(listo);
  volverAdondeIba();
}

// ---------------------------------------------------------------------------
// La dirección de lo que se está viendo (T04)
// ---------------------------------------------------------------------------

/**
 * La pantalla del enrutador que corresponde a cada módulo del menú.
 *
 * Solo hay una diferencia de nombre: el menú llama «panel» a la portada y el enrutador la llama
 * «inicio». Los demás módulos se llaman igual en los dos sitios a propósito, porque son la misma cosa
 * vista desde dos lados (el renglón del menú y su dirección).
 */
function pantallaDeLaDireccion(modulo) {
  return modulo === "panel" ? "inicio" : modulo;
}

/** Y al revés: qué módulo del menú hay que marcar cuando se abre una pantalla por su dirección. */
function moduloDeLaPantalla(clave) {
  return clave === "inicio" ? "panel" : clave;
}

/**
 * La tabla de una lista, que es la clave con la que se guardan su orden y su vista.
 *
 * Los nombres no coinciden porque el cuaderno se llama «cuaderno» en el menú y su tabla se llama
 * «apuntes» desde antes de que existiera el enrutador. Se escribe aquí, en un solo sitio, en vez de
 * repartirlo por los `if` que dibujan las pantallas.
 */
const TABLA_DE_LA_PANTALLA = {
  tierras: "tierras",
  cuaderno: "apuntes",
  facturas: "facturas",
  anos: "anos",
  almacen: "cesta",
  cultivos: "cultivos",
  // La maquinaria (T14): una lista con su buscador y su orden, como las demás. Su columna de la próxima
  // revisión se ordena **por la fecha**, no por el texto ya escrito.
  maquinaria: "maquinaria",
};

/**
 * Las pantallas que **tienen dirección propia y no la del módulo**, por el nombre de su componente.
 *
 * POR QUÉ HACE FALTA ESTA TABLA (T04, segunda entrega, 03/10/2026). El módulo del menú (`MODULO_DE_LA_PANTALLA`)
 * dice en qué renglón del menú se está, y eso no siempre es la dirección: el mapa se abre desde las tierras,
 * pero su dirección no es `#/tierras` (volver a la lista no es volver al mapa). Aquí se dice **la dirección de
 * cada pantalla que no coincide con la del módulo del que cuelga**. Lo que no esté en ninguna de las dos
 * tablas no tiene dirección, y no se escribe ninguna.
 */
const DIRECCION_PROPIA = {
  PantallaMapa: "mapa",
  PantallaDecirCultivo: "decir_cultivo",
  PantallaQuienEntra: "quien_entra",
  PantallaFirmar: "firmar",
  PantallaDictado: "dictado",
  PantallaBorrador: "borrador",
  // Esta tiene dirección **solo a veces**: cuando lo que enseña es una factura que ya está guardada
  // (`#/facturas/9`). Si es la lectura de una foto que aún no se ha guardado, no la tiene y no la escribe;
  // lo dice `apuntarLaDireccion`, que es el único sitio donde se decide.
  PantallaInterpretacionDeLaFactura: "interpretacion_factura",
  // Las dos pantallas del libro del almacén que **son un sitio y no un paso** (T09): el libro (lo que ha
  // llegado, lo que queda y lo que ha pasado) y la ficha de un albarán. Las dos se pueden enlazar y
  // recargar sin perder nada, que es lo que exige tener dirección.
  PantallaLibroDelAlmacen: "libro_almacen",
  PantallaRecepcion: "recepcion",
  // Las dos de T06 (03/10/2026): las tierras en el mapa y en la tabla, y lo que ha sido una tierra.
  // Las dos se reconstruyen enteras al abrir su dirección.
  PantallaTierrasDeLaExplotacion: "tierras_mapa",
  PantallaVersionesDeUnaTierra: "tierra_versiones",
  // Lo que se ha sembrado (T10, 03/10/2026): su dirección no es la del renglón del menú del que
  // cuelga (las semillas), porque es otra cosa: la lista de las semillas es la ficha de lo que hay en
  // la nave y esta es lo que se ha hecho con ellas en cada tierra. Se reconstruye entera al abrirla.
  PantallaDeLasSiembras: "siembras",
  // Las personas y las empresas (T11, 03/10/2026): la lista (`#/contactos`) y la revisión de los
  // nombres que ya están escritos (`#/contactos/revisar`). Las dos se reconstruyen enteras al abrir su
  // dirección —piden sus datos al servidor—, así que se pueden enlazar, recargar y mandar a quien
  // ayuda. Y la revisión **tiene** que poder recargarse: es una decisión sobre datos, y volver a
  // mirarla después de pensarlo es lo normal.
  PantallaDeLosContactos: "contactos",
  PantallaDeLaRevisionDeLosNombres: "revisar_contactos",
  // El dinero de lo que se vende (T12, 03/10/2026): la lista de facturas, la ficha de una factura, la
  // lista de cobros, el importe de una entrega y su ajuste. Las cinco se reconstruyen enteras al abrir
  // su dirección —piden sus datos al servidor—, así que se pueden enlazar, recargar y mandar a quien
  // ayuda. La ficha de una factura y las dos de una entrega llevan su identificador en el camino, y lo
  // escribe `apuntarLaDireccion`, que es el único sitio donde se decide.
  PantallaFacturasEmitidas: "facturas_emitidas",
  PantallaUnaFacturaEmitida: "factura_emitida",
  PantallaCobros: "cobros",
  PantallaImporte: "venta_importe",
  PantallaAjuste: "venta_ajuste",
  // La maquinaria (T14, 03/10/2026): la lista coge la dirección de su renglón del menú (`#/maquinaria`),
  // y **la ficha de una máquina tiene la suya** (`#/maquinaria/12`), porque se puede enlazar y recargar:
  // sus datos y sus inspecciones se piden al servidor al abrirla.
  PantallaDeUnaMaquina: "maquina",
  // Las cuentas (T13, 05/10/2026): la lista coge la dirección de su renglón del menú (`#/cuentas`), y
  // **la ficha de un gasto tiene la suya** (`#/cuentas/12`), porque se puede enlazar y recargar: sus
  // repartos y sus pagos se piden al servidor al abrirla.
  PantallaDeUnGasto: "gasto",
  // El extracto del banco y la conciliación (T20, 06/10/2026). La lista vive dentro de la familia de las
  // cuentas (`#/cuentas/bancos`) —de ahí sale, y por eso **hay que escribirla aquí**: sin esta línea,
  // `apuntarLaDireccion` le pondría la dirección del renglón del menú (`#/cuentas`) y las dos pantallas
  // escribirían la misma—, y **la ficha de un movimiento tiene la suya** (`#/cuentas/bancos/12`), porque
  // se puede enlazar y recargar: sus propuestas se piden al servidor al abrirla.
  PantallaDeLosBancos: "bancos",
  PantallaDeUnMovimiento: "banco_movimiento",
  // Los trabajos (T15, 05/10/2026): la agenda coge la dirección de su renglón del menú (`#/trabajos`) y
  // la historia de una tierra tiene la suya (`#/tierras/<id>/historial`), porque se puede enlazar y
  // recargar. **La ficha de un trabajo NO está aquí a propósito**: es un formulario, y uno que al
  // recargar saldría vacío es peor que no tener dirección.
  PantallaDeLaTierra: "trabajo_tierra",
  PantallaDeLaBandeja: "bandeja",
  PantallaDeUnPapelDeLaBandeja: "bandeja_papel",
};

/**
 * Las pantallas que son **un paso de un formulario** y por eso **no escriben ninguna dirección** (T04,
 * segunda entrega).
 *
 * POR QUÉ ESTO EXISTE, Y POR QUÉ ES UNA DECISIÓN Y NO UN OLVIDO. Antes, cualquier pantalla que estuviera en
 * `MODULO_DE_LA_PANTALLA` escribía la dirección de su módulo al montarse. Eso hacía que el asistente de
 * apuntar, en su paso 34, dejara la barra de direcciones en `#/cuaderno`: el agricultor recargaba y se
 * encontraba **el cuaderno**, no el formulario a medias que estaba rellenando, y el botón «atrás» del móvil
 * lo devolvía a la lista en vez de a la pantalla desde la que había empezado.
 *
 * Lo que se decide aquí es que estos pasos **no toquen la dirección**: se queda la de la pantalla de la que
 * salieron, que es la verdad (ahí es donde estaba el agricultor y ahí vuelve). Escribir una dirección para
 * cada paso sería peor que no escribir ninguna: lo que llevan dentro vive en la memoria de la sesión (un
 * formulario a medias, una propuesta que el servidor no guarda, el fichero que se acaba de elegir) y una
 * dirección que al recargar no lleva a lo mismo es una dirección que miente.
 *
 * Las tres primeras son fáciles de justificar (un formulario a medias, una confirmación de lo que se acaba
 * de guardar, y un estado sin sesión); las otras dos son el alta de un papel y la de una factura, que son
 * formularios que el agricultor rellena y que al recargar saldrían vacíos —con el peligro de creer que ya
 * estaban guardados—. El paso del SIGPAC no está en esta lista porque **nunca se monta solo**: vive dentro
 * del asistente (`pasosDeSigpac`), así que lo cubre `PantallaAsistente`.
 */
const PANTALLAS_SIN_DIRECCION = new Set([
  "PantallaAsistente",
  "PantallaHecho",
  "PantallaEntrar",
  "PantallaNuevoDocumento",
  "PantallaNuevaFactura",
  // Los cuatro formularios del almacén (T09): la misma razón que los dos de arriba. Un albarán, una
  // merma, una salida o un enganche **a medias** que al recargar saliera vacío sería peor que no tener
  // dirección: el agricultor creería que ya lo había guardado. La dirección se queda en la pantalla de
  // la que salieron (el libro o el albarán), que es donde estaban y adonde vuelven.
  "PantallaNuevoAlbaran",
  "PantallaMovimientoDeAlmacen",
  "PantallaSacarDeUnLote",
  "PantallaEngancharLaFactura",
  // Y los dos formularios del T10: la ficha de una semilla —con la lectura de la etiqueta, que es una
  // **propuesta** y no se guarda hasta que el agricultor pulsa el botón— y la siembra. Al recargar
  // saldrían vacíos, y un formulario vacío que parece guardado es peor que no tener dirección: la
  // dirección se queda en la pantalla de la que salieron (las semillas o lo que se ha sembrado).
  "PantallaDeUnaSemilla",
  "PantallaDeUnaSiembra",
  // Y los dos del T11: la ficha de una persona o de una empresa —que pide unos datos y se guarda con un
  // botón— y la lista de nombres escritos para enlazarlos. Al recargar saldrían vacías, y una ficha
  // vacía que parece guardada es peor que no tener dirección: la dirección se queda en la pantalla de
  // la que salieron (las fichas o la revisión).
  "PantallaDeUnContacto",
  "PantallaDeLosNombresEscritos",
  // Y las cuatro del dinero de lo que se vende (T12, 03/10/2026): la lista de facturas, el paso de
  // juntar entregas, la lista de cobros y apuntar un cobro. **Al recargar saldrían vacías** —la segunda
  // con las entregas sin marcar, que es peor que vacía: parece que no hay nada que facturar— y un
  // formulario vacío que parece guardado es peor que no tener dirección. La dirección se queda en la
  // pantalla de la que salieron (la lista de lo que se ha vendido).
  "PantallaFacturarEntregas",
  "PantallaCobroNuevo",
  // Y la ficha de un trabajo (T15, 05/10/2026), que es lo que `DIRECCION_PROPIA` ya decía de ella («la
  // ficha de un trabajo NO está aquí a propósito: es un formulario, y uno que al recargar saldría vacío
  // es peor que no tener dirección») pero **faltaba aquí para que fuera verdad**: sin esta línea, al
  // montarse escribía la dirección de su módulo (`#/trabajos`) y perdía la de la pantalla de la que
  // salió —la historia de una tierra, por ejemplo, que es desde donde se corrige un trabajo—.
  "PantallaDeUnTrabajo",
]);

/** La campaña y la finca en las que se está: van en todas las direcciones, porque son el contexto. */
function elContextoDeLaDireccion() {
  const parametros = {};
  if (estado.campana && estado.campana.anio) parametros.campana = estado.campana.anio;
  if (estado.miFinca && estado.miFinca.id) parametros.finca = estado.miFinca.id;
  return parametros;
}

/**
 * Los parámetros que describen lo que se está viendo: la campaña y la finca, y —si es una lista— lo que
 * el agricultor ha buscado, por dónde la ha ordenado y qué fila tiene abierta.
 */
function parametrosDeLaPantalla(clave) {
  const parametros = elContextoDeLaDireccion();
  const tabla = TABLA_DE_LA_PANTALLA[clave];
  if (tabla) {
    const orden = (estado.ordenDeLaTabla || {})[tabla];
    if (orden) {
      parametros.orden = orden.campo;
      parametros.sentido = orden.sentido;
    }
  }
  if (clave === "tierras") {
    if (estado.filtroTierrasMisCosas) parametros.q = estado.filtroTierrasMisCosas;
    const elegida = filaElegida("tierras");
    if (elegida) parametros.id = elegida;
  }
  if (clave === "cuaderno") {
    const elegida = filaElegida("apuntes");
    if (elegida) parametros.id = elegida;
  }
  // **La pantalla de las tierras de T06** (03/10/2026): lo que el agricultor tenga puesto viaja en la
  // dirección, como en cualquier lista de este programa. Es lo que hace que se pueda recargar y
  // mandar a quien le ayuda («mira las tierras sin forma») y que volver de una ficha no pierda nada.
  if (clave === "tierras_mapa") {
    const t06 = estado.t06 || {};
    const filtro = t06.filtro || {};
    for (const campo of ["q", "cultivo", "municipio", "revision", "pac"]) {
      if (filtro[campo]) parametros[campo] = filtro[campo];
    }
    if (t06.grupo) parametros.grupo = t06.grupo;
    if (t06.elegida) parametros.id = t06.elegida;
    if (t06.capa && t06.capa !== "foto") parametros.capa = t06.capa;
    if ((t06.marcadas || []).length) parametros.marcadas = t06.marcadas.join("-");
  }
  // Y la ficha de una tierra con sus versiones: su identificador es lo único que necesita, como la
  // ficha de la tierra. Sin él no hay dirección que escribir (sería la ficha de nada).
  // **La búsqueda global** (07/10/2026): **este bloque no basta, y por eso no está**. Se probó el bloque que
  // escribe el texto en la dirección leyéndolo del estado, y la medición dice que **la dirección no cambia**
  // al buscar desde la pantalla: `montar()` no rehace la dirección — la dirección la escribe el camino de
  // navegación entre pantallas, no el que pinta una pantalla. O sea que el arreglo no es aquí: es que
  // **el manejador de la búsqueda escriba su dirección** (con el escritor de direcciones de la casa) al
  // buscar. Queda medido y apuntado en `docs/ESTADO_DEL_REDISENO.md`, y no se deja un bloque que no hace
  // nada aunque parezca que sí.
  // **La búsqueda global** (07/10/2026): lo que se ha buscado viaja en la dirección, para que recargar
  // deje al agricultor **en su búsqueda** y no en una búsqueda vacía, y para que el enlace se pueda mandar.
  // El texto se lee del estado, donde lo apunta `pantallaBuscar()` al buscar.
  //
  // **Este bloque se probó el 07/10 y entonces no funcionaba** —la dirección se quedaba en la de tierras—,
  // y el motivo era el mismo que el de todo lo demás: sin renglón en el menú no había módulo, y sin módulo
  // esta función no se ejecutaba para esta pantalla. **Con el renglón puesto, el bloque hace lo que dice**,
  // y está medido: `#/buscar?campana=2026&finca=2` es lo que escribía la pantalla antes de esto.
  if (clave === "buscar") {
    const suyo = estado.busqueda || {};
    if (suyo.texto) parametros.texto = suyo.texto;
  }
  if (clave === "tierra_versiones") {
    const suya = (estado.t06 || {}).versionParcela;
    if (!suya) return parametros;
    parametros.id = suya;
  }
  return parametros;
}

/**
 * Escribe en la barra de direcciones lo que se está viendo.
 *
 * **Se escribe desde aquí y no desde cada pantalla** porque `montar()` es el único sitio por el que pasan
 * todas: así no hay veinte sitios donde acordarse, y una pantalla nueva tiene su dirección sin hacer nada.
 * La clave de qué pantalla es sale de `MODULO_DE_LA_PANTALLA` —y, cuando la dirección no es la del módulo
 * del que cuelga, de `DIRECCION_PROPIA`—.
 *
 * **Los pasos de un formulario no escriben ninguna dirección** (`PANTALLAS_SIN_DIRECCION`), y una ficha sin
 * identificador tampoco: `escribirLaDireccion` devuelve vacío y entonces **no se toca la barra**, que es lo
 * único honesto (ponerla en `#/` daría a entender que el agricultor está en su casa).
 */
function apuntarLaDireccion(listo) {
  const nombre = listo && listo.type ? listo.type.name : "";
  if (PANTALLAS_SIN_DIRECCION.has(nombre)) return;
  // **Solo las pantallas del menú y las de `DIRECCION_PROPIA` tienen dirección.** Las que se montan con una
  // pieza suelta (la confirmación, la pantalla de «dirección que no lleva a nada») no están en ninguna de
  // las dos tablas, y entonces **no se toca la dirección**: si se pusiera `#/` por defecto, escribir una
  // dirección equivocada se convertiría sola en la de casa y el agricultor no vería qué pasó.
  const modulo = MODULO_DE_LA_PANTALLA[nombre];
  let clave = DIRECCION_PROPIA[nombre] || (modulo ? pantallaDeLaDireccion(modulo) : "");
  if (!clave) return;
  // Una tierra o un apunte abiertos son su propia dirección: es lo que permite enlazar una ficha.
  if (clave === "tierras" && filaElegida("tierras")) clave = "tierra";
  if (clave === "cuaderno" && filaElegida("apuntes")) clave = "apunte";
  // Los parámetros de la lista de la que cuelga la pantalla (su orden, su buscador) son los de la lista, no
  // los de la ficha: una tierra abierta lleva la campaña, la finca y los filtros con los que se llegó a ella.
  const parametros = parametrosDeLaPantalla(
    clave === "tierra" ? "tierras" : clave === "apunte" ? "cuaderno" : clave,
  );
  if (clave === "tierra") parametros.id = filaElegida("tierras");
  if (clave === "apunte") parametros.id = filaElegida("apuntes");
  if (clave === "decir_cultivo") {
    // De qué tierra se está diciendo el cultivo: sin identificador no hay dirección que escribir (y sin
    // esto se escribiría `#/tierras//cultivo`, que no es la ficha de nada).
    if (!estado.cultivoParcela) return;
    parametros.id = estado.cultivoParcela;
  }
  if (clave === "interpretacion_factura") {
    // **Solo la factura guardada tiene dirección.** La pantalla es la misma para dos cosas: revisar lo que
    // se acaba de leer de una foto (que no está guardado en ningún sitio y no se puede reproducir) y
    // corregir una factura que ya está en el cuaderno (que sí). Sin `corrigiendo` no se escribe nada y la
    // dirección se queda en la lista de facturas, que es de donde se salió.
    const corrigiendo = (estado.facturas || {}).corrigiendo;
    if (!corrigiendo || !corrigiendo.id) return;
    parametros.id = corrigiendo.id;
  }
  if (clave === "recepcion") {
    // De qué albarán es la ficha (T09): sin identificador no hay dirección que escribir, porque
    // `#/almacen/recepcion/` no es la ficha de nada.
    const recepcion = (estadoDelLibro() || {}).recepcion;
    if (!recepcion || !recepcion.id) return;
    parametros.id = recepcion.id;
  }
  // **La ficha de un movimiento del banco (T20)**: su identificador en el camino (`#/cuentas/bancos/12`),
  // como la de un gasto o una máquina. Sale del estado, que es donde está el movimiento que se está
  // mirando.
  if (clave === "banco_movimiento") {
    const movimiento = (estado.bancos || {}).movimiento;
    if (!movimiento || !movimiento.id) return;
    parametros.id = movimiento.id;
  }
  if (clave === "bandeja_papel") {
    const papel = (estado.bandeja || {}).papel;
    if (!papel || !papel.id) return;
    parametros.id = papel.id;
  }
  // **El dinero de lo que se vende** (T12): la factura que se está mirando y la entrega a la que se le
  // está poniendo el importe o el ajuste. Sin identificador no hay dirección que escribir: `#/ventas//importe`
  // no es la pantalla de nada, y escribirla dejaría al agricultor en una dirección que no existe.
  if (clave === "factura_emitida") {
    const factura = estado.facturaEmitida;
    if (!factura || !factura.id) return;
    parametros.id = factura.id;
  }
  if (clave === "venta_importe" || clave === "venta_ajuste") {
    const entrega = clave === "venta_importe" ? estado.entregaDelImporte : estado.entregaDelAjuste;
    if (!entrega || !entrega.id) return;
    parametros.id = entrega.id;
  }
  // **La ficha de una máquina (T14)**: su identificador en el camino (`#/maquinaria/12`), como la de una
  // tierra o una factura. Sin él no hay dirección que escribir: `#/maquinaria/` no es la ficha de nada.
  if (clave === "maquina") {
    const maquina = (estado.maquinaria || {}).maquina;
    if (!maquina || !maquina.id) return;
    parametros.id = maquina.id;
  }
  // **La historia de una tierra (T15)**: su identificador en el camino (`#/tierras/12/historial`). Sale
  // de lo que contestó su puerta, que es lo que está en pantalla. Sin él no hay dirección que escribir:
  // `#/tierras//historial` no es la historia de nada.
  //
  // **Esta rama faltaba, y se notó al añadir el botón que lleva a la historia** (05/10/2026, el mismo
  // día): la pantalla se abría por su dirección, pero **no la escribía**. El agricultor entraba desde su
  // tierra, leía la historia y, al recargar, volvía a la lista de tierras con la historia perdida. Es la
  // mitad que le faltaba a T15 para poder decir que su pantalla «se puede enlazar y recargar».
  if (clave === "trabajo_tierra") {
    const suya = (estado.trabajos || {}).tierra;
    const tierra = suya && suya.tierra ? suya.tierra : null;
    if (!tierra || !tierra.id) return;
    parametros.id = tierra.id;
  }
  const direccion = escribirLaDireccion(clave, parametros);
  if (!direccion) return;
  estado.pantalla = clave;
  if (window.location.hash === direccion) return;
  // `pushState` y no `location.hash = …`: escribir el fragmento a mano dispara `hashchange`, que es lo
  // que se usa para «atrás» y «adelante», y volveríamos a abrir la misma pantalla en un bucle.
  if (estado.completando) window.history.replaceState({ direccion }, "", direccion);
  else window.history.pushState({ direccion }, "", direccion);
}

/** Apunta por dónde iba en la lista que se está dejando, para poder volver a su sitio. */
function recordarPorDondeIba() {
  const clave = estado.pantalla;
  if (!clave || !TABLA_DE_LA_PANTALLA[clave]) return;
  estado.vistas = recuerda(estado.vistas, clave, {
    direccion: window.location.hash,
    scroll: window.scrollY || 0,
  });
}

/** Y si se vuelve **exactamente a la misma lista**, se devuelve al sitio en el que estaba. */
function volverAdondeIba() {
  const clave = estado.pantalla;
  const vista = clave && TABLA_DE_LA_PANTALLA[clave] ? recupera(estado.vistas, clave) : null;
  if (vista && vista.direccion === window.location.hash && vista.scroll) {
    window.scrollTo(0, vista.scroll);
    return;
  }
  window.scrollTo(0, 0);
}

/**
 * Abre la pantalla que dice la dirección: es lo que hace que recargar, un enlace directo y «atrás»
 * funcionen igual.
 *
 * **Lo que la dirección NO puede decidir**: si esa tierra existe o es de este agricultor. Eso lo dice el
 * servidor, y aquí se comprueba contra las tierras que ya están descargadas (que es lo que sabe el mismo
 * «eso no está en tu cuaderno» que contesta la API, y funciona sin cobertura). Si la dirección nombra
 * **otra finca**, se cambia a ella, y si la cuenta no tiene acceso, lo dice el servidor y se enseña.
 */
async function abrirLaDireccion() {
  const leida = leerLaDireccion(window.location.hash);
  // **Sin sesión no se abre ninguna pantalla de dentro** (06/10/2026). Esto solo lo miraba `arrancar()`:
  // escribiendo una dirección de dentro —o volviendo con «atrás»— después de salir, la aplicación
  // pintaba la pantalla igual (vacía y con un error de permiso detrás) en vez de pedir que se entre.
  //
  // Va **antes** de mirar si la dirección es conocida, y eso importa: una dirección que no lleva a ninguna
  // parte, sin sesión, decía «ese enlace no es de tu cuaderno» —y dejaba el menú de la sesión anterior en
  // el tabulador— cuando lo que pasa es que no se ha entrado. La puerta de entrada es su propia dirección
  // (`#/entrar`), así que se puede volver a ella.
  if (!estado.token && leida.pantalla !== "entrar") {
    pantallaEntrar("entrar");
    return;
  }
  if (leida.desconocida) {
    pantallaDeDireccionQueNoLlevaANingunaParte();
    return;
  }
  const finca = leida.parametros.finca;
  if (finca && estado.miFinca && Number(finca) !== Number(estado.miFinca.id)) {
    // Cambiar de finca vuelve a pintar por su cuenta (y pasa por `olvidarLoDeLaFincaAnterior`).
    estado.direccionPendiente = { pantalla: leida.pantalla, parametros: leida.parametros };
    await entrarEnLaFinca(Number(finca));
    return;
  }
  abrirLaPantalla(leida.pantalla, leida.parametros);
}

/** Abre una pantalla por su clave, con lo que venga en la dirección ya puesto en el estado. */
function abrirLaPantalla(clave, parametros = {}) {
  const tabla = TABLA_DE_LA_PANTALLA[clave];
  if (tabla) {
    if (clave === "tierras" && parametros.q !== undefined) {
      estado.filtroTierrasMisCosas = String(parametros.q || "");
    }
    if (parametros.orden) {
      estado.ordenDeLaTabla = estado.ordenDeLaTabla || {};
      estado.ordenDeLaTabla[tabla] = {
        campo: String(parametros.orden),
        sentido: Number(parametros.sentido) === -1 ? -1 : 1,
      };
    }
    // **La dirección manda**: si no trae ficha, no hay ficha abierta. Sin esto, volver con «atrás» de una
    // tierra a la lista dejaría el panel de esa tierra abierto (y la dirección volvería a ser la de la
    // ficha, o sea que «atrás» no habría servido para nada).
    if (clave === "tierras") estado.filaElegida = { ...(estado.filaElegida || {}), tierras: null };
    if (clave === "cuaderno") estado.filaElegida = { ...(estado.filaElegida || {}), apuntes: null };
  }
  if (clave === "tierra" || clave === "apunte") {
    const id = parametros.id;
    const donde = clave === "tierra" ? estado.parcelas : apuntesDeLaCampana();
    const existe = (donde || []).some((uno) => Number(uno.id) === Number(id));
    if (!existe) {
      // **Sin cobertura no se puede saber si esa ficha es suya** (T04). La lista de tierras está vacía
      // porque no se ha podido descargar, no porque la tierra no exista: decir «no está en tu cuaderno»
      // ahí sería mentir, y es justo el aviso que se llevaría el agricultor al abrir un enlace en el
      // campo. Se distingue, y se le ofrece volver a intentarlo.
      if (!navigator.onLine) return pantallaDeUnaDireccionQueNoSePuedeComprobar();
      pantallaDeDireccionQueNoLlevaANingunaParte();
      return;
    }
    estado.filaElegida = { ...(estado.filaElegida || {}) };
    if (clave === "tierra") estado.filaElegida.tierras = id;
    else estado.filaElegida.apuntes = id;
    if (clave === "tierra") return pantallaMisCosas();
    return pantallaCuaderno();
  }
  // **Decir qué hay sembrado en una tierra** (T04, segunda entrega): es de una tierra, y por eso se
  // comprueba igual que la ficha de una tierra —contra lo que hay descargado—, con los mismos tres finales:
  // se abre, «no está en tu cuaderno» o «no lo he podido comprobar» sin cobertura.
  if (clave === "decir_cultivo") {
    const donde = (estado.cultivos || {}).parcelas || [];
    const existe = donde.some((una) => Number(una.parcela_id) === Number(parametros.id));
    if (!existe) {
      if (!navigator.onLine) return pantallaDeUnaDireccionQueNoSePuedeComprobar();
      return pantallaDeDireccionQueNoLlevaANingunaParte();
    }
    return pantallaDecirCultivo(parametros.id);
  }
  // **La revisión de una factura guardada**: se vuelve a armar con lo que hay en el cuaderno, por el mismo
  // camino que el botón CORREGIR de la lista (una sola forma de abrir esta pantalla, no dos que se separen).
  if (clave === "interpretacion_factura") {
    const factura = (estado.facturasLista || []).find(
      (una) => Number(una.id) === Number(parametros.id),
    );
    if (!factura) {
      if (!navigator.onLine) return pantallaDeUnaDireccionQueNoSePuedeComprobar();
      return pantallaDeDireccionQueNoLlevaANingunaParte();
    }
    return corregirAlgo("factura", factura.id);
  }
  // **La ficha de un albarán** (T09): a diferencia de una tierra, sus datos **no están descargados** (el
  // libro se pide al abrirlo), así que se pregunta al servidor y se decide con lo que conteste. Los tres
  // finales de siempre: se abre, «eso no está en tu cuaderno» (404) o «no lo he podido comprobar» (sin
  // cobertura). Y no se adivina: sin cobertura no se puede afirmar que ese albarán no exista.
  if (clave === "recepcion") {
    return abrirLaRecepcion(parametros.id);
  }
  // **Las tierras en el mapa y en la tabla** (T06): lo que venga en la dirección (los filtros, cómo se
  // agrupa, qué capa se mira, qué tierras están marcadas) se pone en el estado **antes** de pedir los
  // datos, que es lo que hace que recargar deje al agricultor donde estaba.
  if (clave === "tierras_mapa") {
    aplicarLaDireccionAT06(parametros);
    return abrirLasTierrasDelMapa();
  }
  // **La búsqueda global**: su dirección está probada el 07/10/2026 y **se quitó el mismo día** porque el
  // recorrido se puso rojo con dos fallos (escribir en el cuadro y pulsar BUSCAR no enseñaba los grupos, y
  // la dirección no acababa donde debía). No se deja a medias: se investiga con el guion en la mano y se
  // vuelve a poner. Mientras tanto, la pantalla sigue medida como **hallazgo** en el recorrido.
  // **La búsqueda global** (07/10/2026): su dirección lleva el texto buscado, así que recargar deja al
  // agricultor donde estaba. **Aquí no hay nada que comprobar contra la finca**, y es distinto de las
  // demás: lo que se busca puede no existir y eso **no** es «una dirección que no lleva a ninguna parte»
  // — la pantalla contesta con su frase de «no hay nada que se llame así», que es la verdad.
  if (clave === "buscar") {
    return pantallaBuscar(parametros.texto || null);
  }
  // **Lo que ha sido una tierra** (T06): se comprueba que la tierra sea suya **antes** de pedir sus
  // versiones, con los mismos tres finales que la ficha de una tierra —se abre, «esa dirección no
  // lleva a ninguna parte» o «no lo he podido comprobar» sin cobertura—: sin cobertura la lista de
  // tierras está vacía porque no se ha podido descargar, no porque la tierra no exista.
  if (clave === "tierra_versiones") {
    const existe = (estado.parcelas || []).some((una) => Number(una.id) === Number(parametros.id));
    if (!existe) {
      if (!navigator.onLine) return pantallaDeUnaDireccionQueNoSePuedeComprobar();
      return pantallaDeDireccionQueNoLlevaANingunaParte();
    }
    return abrirLasVersionesDeUnaTierra(parametros.id);
  }
  // **El dinero de lo que se vende** (T12): la ficha de una factura nuestra y las dos pantallas de una
  // entrega (ponerle el importe y apuntarle una devolución o un ajuste). Se comprueba que el
  // identificador sea de esta finca **contra lo que ya está descargado**, con los tres finales de
  // siempre: se abre, «eso no está en tu cuaderno» o «no lo he podido comprobar» sin cobertura. Sin
  // cobertura la lista está vacía porque no se ha podido descargar, no porque no exista, y decir «no
  // está en tu cuaderno» ahí sería mentirle al agricultor.
  if (clave === "factura_emitida") {
    const existe = (estado.facturasEmitidas || []).some(
      (una) => Number(una.id) === Number(parametros.id),
    );
    if (!existe) {
      if (!navigator.onLine) return pantallaDeUnaDireccionQueNoSePuedeComprobar();
      return pantallaDeDireccionQueNoLlevaANingunaParte();
    }
    return pantallaUnaFacturaEmitida(parametros.id);
  }
  if (clave === "venta_importe" || clave === "venta_ajuste") {
    // La entrega se busca **en la tabla del año**, que es lo que está descargado. Una entrega de otro
    // año no está ahí: se dice que esa dirección no lleva a ninguna parte en vez de enseñar una
    // pantalla a medias.
    const fila = unaEntregaDeLaTabla(parametros.id);
    if (!fila) {
      if (!navigator.onLine) return pantallaDeUnaDireccionQueNoSePuedeComprobar();
      return pantallaDeDireccionQueNoLlevaANingunaParte();
    }
    return clave === "venta_importe"
      ? pantallaImporteDeUnaEntrega(parametros.id)
      : pantallaAjusteDeUnaEntrega(parametros.id);
  }
  // **La ficha de una máquina (T14)**: se pide a su puerta (`GET /api/maquinaria/<id>`), que contesta
  // 404 si no es de esta finca —y 404 y no 403, para no contar si existe en otra—. Los tres finales de
  // siempre: se abre, «eso no está en tu cuaderno» o, sin cobertura, «no lo he podido comprobar» (que no
  // es lo mismo: sin datos la lista está vacía porque no se ha descargado, no porque no exista).
  if (clave === "maquina") {
    return abrirUnaMaquina(parametros.id);
  }
  // **Las cuentas de la explotación (T13, E7, 05/10/2026)**: la lista y la ficha de un gasto. Las dos
  // se piden al servidor al abrirlas, así que se pueden enlazar y recargar.
  if (clave === "gastos") return abrirLasCuentas();
  if (clave === "gasto") return abrirUnGasto(parametros.id);
  // **El extracto del banco y la conciliación (T20, E11, 06/10/2026)**: los movimientos y la ficha de
  // uno. Las dos se piden al servidor al abrirlas, así que se pueden enlazar y recargar.
  if (clave === "bancos") return abrirLosBancos();
  if (clave === "banco_movimiento") return abrirUnMovimientoDelBanco(parametros.id);
  // **La historia de una tierra (T15, E9, 05/10/2026)**: se pide a su puerta, que contesta 404 si esa
  // tierra no es de esta finca. Los tres finales de siempre: se abre, «eso no está en tu cuaderno» o,
  // sin cobertura, «no lo he podido comprobar».
  if (clave === "trabajo_tierra") return abrirLaHistoriaDeUnaTierra(parametros.id);
  if (clave === "bandeja_papel") return abrirUnPapelDeLaBandeja(parametros.id);
  return ABRIR_LA_PANTALLA[clave] ? ABRIR_LA_PANTALLA[clave](parametros) : pantallaInicio();
}

/** Los apuntes del año que se está llevando, que son los que salen en «mi cuaderno». */
function apuntesDeLaCampana() {
  return [
    ...(estado.tratamientos || []),
    ...(estado.fertilizaciones || []),
    ...(estado.labores || []),
  ];
}

/**
 * La pantalla de una dirección que **no se ha podido comprobar** por falta de cobertura (T04).
 *
 * Es distinta de la de arriba a propósito: «no está en tu cuaderno» y «no lo he podido mirar» no son lo
 * mismo, y confundirlos es exactamente lo que este trabajo viene a arreglar (`AGENTS.md`: hay bien, mal y
 * «no lo he podido comprobar»). El botón vuelve a pedir los datos y reintenta abrir la misma dirección.
 */
function pantallaDeUnaDireccionQueNoSePuedeComprobar() {
  const d = (clave) => t(`direccion.${clave}`, "");
  montar(() =>
    confirmacion({
      pregunta: d("sin_cobertura_titulo"),
      pista: mensaje("sin_cobertura"),
      acciones: [
        { etiqueta: d("reintentar"), accion: "reintentar-direccion", clase: "boton-principal" },
        { etiqueta: d("volver"), accion: "ir-inicio", clase: "boton-claro" },
      ],
    }),
  );
}

/**
 * Vuelve a pedir los datos y a abrir la dirección en la que está (T04): es la salida de «no lo he podido
 * comprobar» cuando vuelve la cobertura.
 */
async function reintentarLaDireccion() {
  try {
    await cargarDatos();
  } catch (error) {
    avisarDelError(error.message);
    return;
  }
  estado.completando = true;
  await abrirLaDireccion();
  estado.completando = false;
}

/**
 * Qué función abre cada pantalla del enrutador (las mismas que usa el menú, no unas nuevas).
 *
 * Reciben los parámetros de la dirección, aunque hoy casi ninguna los use (los identificadores van en el
 * camino y los lee `abrirLaPantalla`, que es quien sabe si esa ficha existe): se pasan para que añadir una
 * pantalla que los necesite no obligue a cambiar la forma de llamar.
 */
const ABRIR_LA_PANTALLA = {
  inicio: () => pantallaInicio(),
  tierras: () => pantallaMisCosas(),
  cuaderno: () => pantallaCuaderno(),
  almacen: () => pantallaCesta(),
  facturas: () => pantallaFacturas(),
  anos: () => pantallaCampanas(),
  grupos: () => pantallaGrupos(),
  cultivos: () => pantallaCultivos(),
  analisis: () => pantallaAnaliticas(),
  plan: () => pantallaPlanes(),
  ventas: () => pantallaVentas(),
  medidas: () => pantallaMedidas(),
  papeles: () => pantallaDocumentos(),
  junta: () => pantallaCuadernoDeLaJunta(),
  datos: () => pantallaMisDatos(),
  ayuda: () => pantallaAyuda(),
  // Las que tienen dirección propia (T04, segunda entrega). `mapa`, `dictado` y `borrador` no están en
  // ningún renglón del menú, y `quien-entra` y `firmar` se abren desde otra pantalla: por eso sus claves no
  // coinciden con las de `MODULO_DE_LA_PANTALLA` y viven en `DIRECCION_PROPIA`.
  mapa: () => abrirElMapa(),
  dictado: () => abrirElDictado(),
  borrador: () => abrirElBorrador(),
  quien_entra: () => abrirQuienEntra(),
  firmar: () => pantallaFirmar(),
  // El libro del almacén (T09): su lista y la ficha de un albarán. La ficha se pide por su puerta (como
  // una tierra), y por eso no está aquí: la abre `abrirLaPantalla`, que es quien sabe si existe.
  libro_almacen: () => abrirElLibroDelAlmacen(),
  // Las tierras en el mapa y en la tabla (T06). La otra pantalla del ticket, la ficha de una tierra con
  // sus versiones, no está aquí por el mismo motivo que la ficha de un albarán: se comprueba que la
  // tierra sea suya antes de abrirla, y eso lo hace `abrirLaPantalla`.
  tierras_mapa: () => abrirLasTierrasDelMapa(),
  // Las semillas y lo que se ha sembrado (T10, 03/10/2026): las dos se piden al servidor al abrirlas,
  // así que su dirección las reconstruye enteras. Las dos fichas (una semilla y una siembra) **no
  // están aquí**: son formularios, y están en `PANTALLAS_SIN_DIRECCION`.
  semillas: () => abrirLasSemillas(),
  siembras: () => abrirLasSiembras(),
  // Las personas y las empresas (T11, 03/10/2026): las dos se piden al servidor al abrirlas, así que su
  // dirección las reconstruye enteras. La ficha de un contacto y la lista de nombres escritos **no
  // están aquí**: son formularios, y están en `PANTALLAS_SIN_DIRECCION`.
  contactos: () => abrirLosContactos(),
  revisar_contactos: () => abrirLaRevisionDeLosContactos(),
  // El dinero de lo que se vende (T12, 03/10/2026). Las cinco se reconstruyen enteras al abrir su
  // dirección —piden sus datos al servidor—, así que se pueden enlazar, recargar y mandar a quien
  // ayuda. La ficha de una factura y las tres pantallas de una entrega (su importe y su ajuste) **no
  // están aquí**: las abre `abrirLaPantalla`, que es quien comprueba que ese identificador sea suyo y
  // decide entre «se abre», «eso no está en tu cuaderno» y «no lo he podido comprobar».
  facturas_emitidas: () => pantallaFacturasEmitidas(),
  facturar_entregas: () => pantallaFacturarEntregas(),
  cobros: () => pantallaCobros(),
  cobro_nuevo: () => pantallaCobroNuevo(),
  // La maquinaria (T14, 03/10/2026): la lista se pide al servidor al abrirla, así que su dirección la
  // reconstruye entera. **La ficha de una máquina no está aquí**: la abre `abrirLaPantalla`, que es quien
  // comprueba que ese identificador sea de esta finca y decide entre «se abre», «eso no está en tu
  // cuaderno» y «no lo he podido comprobar».
  maquinaria: () => abrirLaMaquinaria(),
  // **Los trabajos (T15, 05/10/2026), y esta línea llegó tarde.** La agenda escribía su dirección
  // (`#/trabajos`, por su renglón del menú) pero **no había quien la abriera**: al recargar la página,
  // el agricultor volvía al panel de mando, y un enlace a los trabajos no llevaba a los trabajos. Se
  // descubrió midiendo la pantalla a 1024 px en un navegador de verdad —el guion apuntaba en el
  // `<title>` en qué dirección había acabado y la dirección era la del panel—, y es justo lo que la
  // tabla de direcciones de T04 prohíbe: **una dirección que se escribe tiene que poder leerse**. Su
  // lista se pide al servidor al abrirla, así que la reconstruye entera.
  trabajos: () => abrirLosTrabajos(),
  bandeja: () => abrirLaBandeja(),
};

/**
 * La pantalla de una dirección que no lleva a ninguna parte (T04).
 *
 * Tres casos, y el texto los distingue porque no son lo mismo: una dirección que no es de ninguna
 * pantalla (`#/lo-que-sea`), una ficha que no está en el cuaderno de este agricultor (el servidor
 * contesta 404 y no dice si existe en otra finca: eso es a propósito), y una finca a la que esta cuenta
 * no puede entrar (lo dice el servidor). En los tres, la salida es la misma y está en el botón.
 */
function pantallaDeDireccionQueNoLlevaANingunaParte() {
  const d = (clave) => t(`direccion.${clave}`, "");
  montar(() =>
    confirmacion({
      pregunta: d("titulo"),
      pista: d("explica"),
      acciones: [{ etiqueta: d("volver"), accion: "ir-inicio", clase: "boton-principal" }],
    }),
  );
}


/**
 * Los módulos del menú lateral, en el orden en que se leen.
 *
 * **El orden no es alfabético: es el del trabajo del agricultor**, de lo que más se usa a lo que se mira de
 * vez en cuando. El primer renglón es «Panel» (lo que se ve al entrar), después el cuaderno del día a día,
 * y al final lo que se toca una vez al año (los papeles, la Junta, los datos).
 *
 * **Las etiquetas son los títulos de sus propias pantallas** (`textos.py`), no nombres nuevos: «Lo que
 * tengo en el almacén» es como se llama esa pantalla y así se llama en el menú. Aquí no se escribe ni una
 * frase para el agricultor. Y `clave` es el nombre del módulo, que es lo que marca qué renglón está activo.
 */
const GRUPOS_DEL_MENU = [
  { clave: "inicio", texto: "menu.grupo_inicio" },
  { clave: "campo", texto: "menu.grupo_campo" },
  { clave: "gestion", texto: "menu.grupo_gestion" },
  { clave: "cuaderno", texto: "menu.grupo_cuaderno" },
  { clave: "ajustes", texto: "menu.grupo_ajustes" },
];

/**
 * **Los grupos del menú** (07/10/2026, del encargo del rediseño).
 *
 * El encargo pide un menú con esta forma: «Inicio; Campo (Tierras y mapa, Trabajos, Cultivos y PAC,
 * Almacén); Gestión (Documentos, Cuentas, Personas, Maquinaria); Cuaderno; Normativa; Ajustes», y avisa de
 * que «la agrupación es visual, no introduce pantallas intermedias obligatorias». Eso es exactamente lo
 * que hay aquí: **los mismos renglones de siempre, puestos por donde el agricultor los busca** —con 21
 * renglones seguidos no se encuentra nada—, sin ningún paso de más.
 *
 * **Y el grupo «Normativa» del encargo NO está, a propósito.** No hay ninguna pantalla que sea eso: la
 * biblioteca de obligaciones con su fuente, su artículo y su vigencia no existe todavía. Poner un renglón
 * que no lleva a ninguna parte —o que lleva a otra cosa para llenar el hueco— es peor que no tenerlo, y la
 * regla de la casa es que un control visible funciona o explica por qué no. Se dirá cuando exista.
 */
const MODULOS = [
  { clave: "panel", texto: "menu.panel", accion: "ir-inicio", grupo: "inicio" },
  // **La búsqueda global** (07/10/2026, del encargo del rediseño). Va en el grupo de Inicio, el
  // primero, porque sirve para todo: «¿dónde está esto?» se pregunta desde cualquier sitio. Y es
  // **la puerta que faltaba**: con su renglón, además, la pantalla puede escribir su dirección (sin
  // módulo no hay traducción de pantalla a dirección, que es lo que se midió el 07/10).
  { clave: "buscar", texto: "buscar.titulo", accion: "buscar", grupo: "inicio" },
  { clave: "tierras", texto: "maestros.titulo", accion: "inicio", datos: { ir: "mis_cosas" }, grupo: "campo" },
  // **Los trabajos (T15, E9, 05/10/2026).** El contrato lo pide **el tercero**, justo detrás de
  // «Tierras y mapa»: lo que se piensa hacer y lo que se ha hecho es lo que se mira antes de salir al
  // campo, y no al final con lo que se toca una vez al año.
  { clave: "trabajos", texto: "agenda.titulo", accion: "trabajos-ver", grupo: "campo" },
  { clave: "cultivos", texto: "cultivos.titulo", accion: "cultivo-ver-todos", grupo: "campo" },
  { clave: "grupos", texto: "grupos.titulo", accion: "inicio", datos: { ir: "grupos" }, grupo: "campo" },
  { clave: "almacen", texto: "cesta.titulo", accion: "cesta-ver", grupo: "campo" },
  // Las semillas (T10): es un insumo del almacén, y por eso va justo detrás. Lo que se mira aquí es
  // otra cosa: qué pone la etiqueta de cada semilla y cuánto queda de ella para sembrar.
  { clave: "semillas", texto: "semillas.titulo", accion: "semillas-ver", grupo: "campo" },
  { clave: "analisis", texto: "analitica.titulo", accion: "inicio", datos: { ir: "analisis" }, grupo: "campo" },
  { clave: "plan", texto: "plan.titulo", accion: "inicio", datos: { ir: "planes" }, grupo: "campo" },
  { clave: "medidas", texto: "medidas.titulo", accion: "medidas-ver", grupo: "campo" },
  // Las personas y las empresas (T11): en Gestión, porque es lo que se mira cuando se va a apuntar algo
  // con nombre y apellidos —de quién es la factura, quién vende, quién compra—.
  { clave: "contactos", texto: "contactos.titulo", accion: "contactos-ver", grupo: "gestion" },
  // **La maquinaria (T14, 03/10/2026).** Es lo que se mira cuando hay que decidir si se puede contar con
  // el tractor para un trabajo, y su ficha es donde están las cinco cosas que hay que pasarle (ITV, ITEAF,
  // mantenimiento, seguro y ROMA).
  { clave: "maquinaria", texto: "maquinaria.titulo", accion: "maquinaria-ver", grupo: "gestion" },
  // **Las cuentas (T13, 05/10/2026).** Es lo que se mira cuando se quiere saber cómo va el año —lo que ha
  // costado y lo que falta por pagar—.
  { clave: "cuentas", texto: "gastos.titulo", accion: "gastos-ver", grupo: "gestion" },
  { clave: "ventas", texto: "venta.titulo", accion: "inicio", datos: { ir: "ventas" }, grupo: "gestion" },
  { clave: "facturas", texto: "facturas.titulo", accion: "facturas-abrir", grupo: "gestion" },
  { clave: "papeles", texto: "documentos.titulo", accion: "papel-ver-todos", grupo: "gestion" },
  {
    clave: "cuaderno",
    texto: "cuaderno.titulo",
    accion: "inicio",
    datos: { ir: "mi_cuaderno" },
    grupo: "cuaderno",
  },
  { clave: "anos", texto: "campanas.titulo", accion: "campanas-abrir", grupo: "cuaderno" },
  { clave: "junta", texto: "cuaderno_cyl.titulo", accion: "cuaderno-de-la-junta-abrir", grupo: "cuaderno" },
  { clave: "datos", texto: "mis_datos.titulo", accion: "mis-datos-abrir", grupo: "ajustes" },
  { clave: "ayuda", texto: "ayuda.pantalla.titulo", accion: "inicio", datos: { ir: "ayuda" }, grupo: "ajustes" },
];

/**
 * A qué módulo del menú pertenece cada pantalla, por el nombre de su componente de React.
 *
 * POR QUÉ SE MIRA EL COMPONENTE Y NO LA ACCIÓN. Porque una misma pantalla se abre por muchos caminos (el
 * cuaderno se abre del menú, del botón de «MI CUADERNO» de la pantalla de inicio y del aviso de «lo que
 * falta»). Lo que dice en qué sitio estás es **la pantalla que está puesta**, no el botón que pulsaste.
 *
 * Y **por qué esto importa**: sin esto, el menú marcaría «Panel» siempre y el agricultor no sabría dónde
 * está — que es la mitad de para qué sirve un menú.
 */
const MODULO_DE_LA_PANTALLA = {
  PantallaInicio: "panel",
  // La búsqueda global: sin esto, al abrirla el menú no marcaría ningún renglón —y no saber dónde
  // estás es la mitad de para qué sirve un menú— y la pantalla no podría escribir su dirección.
  PantallaBuscar: "buscar",
  // **La búsqueda global todavía NO está aquí, y es a propósito**: su renglón del menú está pendiente (con
  // sus cuatro números escritos en `docs/ESTADO_DEL_REDISENO.md`), y una pantalla que marca un módulo que no
  // está en el menú deja el menú sin marcar nada. Lo cazó el guardián: «estas pantallas marcan un módulo que
  // no está en el menú: ['buscar']». Se pone el día que se ponga el renglón.
  PantallaMiCuaderno: "cuaderno",
  PantallaHecho: "cuaderno",
  PantallaAsistente: "cuaderno",
  PantallaMisCosas: "tierras",
  PantallaCultivos: "cultivos",
  PantallaDecirCultivo: "cultivos",
  PantallaGrupos: "grupos",
  PantallaCesta: "almacen",
  PantallaAnaliticas: "analisis",
  PantallaPlanes: "plan",
  PantallaVentas: "ventas",
  PantallaMedidas: "medidas",
  PantallaDocumentos: "papeles",
  PantallaNuevoDocumento: "papeles",
  PantallaFacturas: "facturas",
  PantallaNuevaFactura: "facturas",
  PantallaInterpretacionDeLaFactura: "facturas",
  PantallaCampanas: "anos",
  PantallaCuadernoDeLaJunta: "junta",
  PantallaMisDatos: "datos",
  PantallaQuienEntra: "datos",
  PantallaAyuda: "ayuda",
  // Las cuatro pantallas que tienen dirección propia pero **también** cuelgan de un renglón del menú
  // (T04, segunda entrega): el mapa se abre desde las tierras, firmar desde el cuaderno y el dictado y su
  // revisión son cosas del cuaderno. Sin estas cuatro líneas el menú se quedaba **sin ningún renglón
  // marcado** al abrirlas —no saber dónde estás es la mitad de para qué sirve un menú—; su dirección no
  // sale de aquí, sino de `DIRECCION_PROPIA`, que es la tabla que manda cuando las dos existen.
  PantallaMapa: "tierras",
  PantallaFirmar: "cuaderno",
  PantallaDictado: "cuaderno",
  PantallaBorrador: "cuaderno",
  // El libro del almacén (T09): cuelga del renglón del almacén, igual que la cesta. Y **sacar de un
  // envase** sale de un apunte del cuaderno, que es de donde viene: su botón vive en «mi cuaderno».
  PantallaLibroDelAlmacen: "almacen",
  PantallaRecepcion: "almacen",
  PantallaNuevoAlbaran: "almacen",
  PantallaMovimientoDeAlmacen: "almacen",
  PantallaEngancharLaFactura: "almacen",
  PantallaSacarDeUnLote: "cuaderno",
  // Las dos pantallas de T06 cuelgan del renglón de las tierras: son las mismas tierras, miradas de
  // otra manera. Su dirección no sale de aquí —las dos la tienen propia—, pero el menú tiene que
  // marcar el renglón: no saber dónde estás es la mitad de para qué sirve un menú.
  PantallaTierrasDeLaExplotacion: "tierras",
  PantallaVersionesDeUnaTierra: "tierras",
  // Las cuatro pantallas del T10 cuelgan del renglón de las semillas: la lista, la ficha de una
  // semilla —que es también la que confirma lo leído de una etiqueta— y lo que se ha sembrado. Las
  // dos que tienen dirección la tienen propia (`DIRECCION_PROPIA`), pero el menú tiene que marcar el
  // renglón: no saber dónde estás es la mitad de para qué sirve un menú.
  PantallaDeLasSemillas: "semillas",
  PantallaDeUnaSemilla: "semillas",
  PantallaDeLasSiembras: "semillas",
  PantallaDeUnaSiembra: "semillas",
  // Las cuatro pantallas del T11 cuelgan del renglón de las personas y las empresas: la lista, la ficha
  // de un contacto, la revisión de los nombres escritos y la lista para enlazarlos. Las dos que tienen
  // dirección la tienen propia (`DIRECCION_PROPIA`), pero el menú tiene que marcar el renglón: no saber
  // dónde estás es la mitad de para qué sirve un menú.
  PantallaDeLosContactos: "contactos",
  PantallaDeUnContacto: "contactos",
  PantallaDeLaRevisionDeLosNombres: "contactos",
  PantallaDeLosNombresEscritos: "contactos",
  // El dinero de lo que se vende (T12, 03/10/2026): las siete pantallas cuelgan del renglón de «lo que he
  // vendido», que es de donde se llega a todas. Cinco tienen dirección propia (la lista de facturas, la
  // ficha de una factura, la lista de cobros, el importe de una entrega y su ajuste) y dos no la tienen a
  // propósito (están en `PANTALLAS_SIN_DIRECCION`): juntar entregas y apuntar un cobro son formularios. El
  // menú tiene que marcar el renglón en las siete: no saber dónde estás es la mitad de para qué sirve un
  // menú.
  PantallaFacturasEmitidas: "ventas",
  PantallaFacturarEntregas: "ventas",
  PantallaUnaFacturaEmitida: "ventas",
  PantallaImporte: "ventas",
  PantallaAjuste: "ventas",
  PantallaCobros: "ventas",
  PantallaCobroNuevo: "ventas",
  // La maquinaria (T14): las dos pantallas cuelgan del renglón de la maquinaria, que es de donde se llega
  // a todas. La ficha tiene dirección propia (`DIRECCION_PROPIA`), pero el menú tiene que marcar el
  // renglón: no saber dónde estás es la mitad de para qué sirve un menú.
  PantallaDeLaMaquinaria: "maquinaria",
  PantallaDeUnaMaquina: "maquinaria",
  // Las cuentas (T13): las dos pantallas cuelgan del renglón de las cuentas, que es de donde se llega
  // y donde el agricultor tiene que verse marcado.
  PantallaDeLasCuentas: "cuentas",
  PantallaDeUnGasto: "cuentas",
  // El banco y los papeles (T20): cuelgan del renglón de las cuentas, igual que un gasto.
  PantallaDeLosBancos: "cuentas",
  PantallaDeUnMovimiento: "cuentas",
  // Los trabajos (T15, 05/10/2026): las tres pantallas cuelgan del renglón de los trabajos. La de la
  // historia de una tierra tiene dirección propia (`DIRECCION_PROPIA`), pero el menú tiene que marcar el
  // renglón: no saber dónde estás es la mitad de para qué sirve un menú.
  PantallaDeLosTrabajos: "trabajos",
  PantallaDeUnTrabajo: "trabajos",
  PantallaDeLaTierra: "trabajos",
  PantallaDeLaBandeja: "papeles",
  PantallaDeUnPapelDeLaBandeja: "papeles",
};

/**
 * El armazón: el menú de la izquierda y la barra de arriba, con lo que hay que saber siempre.
 *
 * Se monta **cuando cambia el módulo**, no cada vez que cambia la pantalla: el menú y la barra no dependen
 * de la pantalla, solo de en qué módulo se está y de en qué finca y año se apunta. Así el agricultor no ve
 * parpadear el menú cada vez que toca algo.
 *
 * Si algo falla al prepararlo (un texto que no ha llegado, un contenedor que no está), **no pasa nada**: el
 * armazón no se pinta y la pantalla sí. El armazón ayuda a moverse; la pantalla es lo que se viene a hacer.
 */
/**
 * La frase de lo que falta por apuntar, para la barra del armazón (07/10/2026, del encargo del rediseño).
 *
 * Se monta en un solo sitio y la usan dos: la pantalla del cuaderno y la barra. **Solo se dice si el
 * servidor ha mirado** (`esta_completo` no es `null`): con la lista sin llegar, «no te falta nada» sería
 * afirmar lo que no se sabe; y con cero cosas no hay nada que enseñar, así que no se pinta nada.
 */
function laFraseDeLoQueFalta() {
  const suyo = estado.faltantes;
  if (!suyo || suyo.esta_completo === null) return "";
  const cuantas = (suyo.pendientes || []).length;
  if (!cuantas) return "";
  return cuantas === 1
    ? t("marco.pendiente_uno", "")
    : rellena(t("marco.pendientes", ""), { cuantas });
}

function pintarMarco(listo) {
  // **Sin sesión no hay armazón** (06/10/2026). El menú de módulos se quedaba pintado de la sesión
  // anterior —y de la pantalla de entrar, que no es de ningún módulo, así que se pintaba con el menú
  // entero y sin ningún renglón marcado—, y como va antes que la pantalla en el HTML era **lo primero que
  // recorría el tabulador**: medido, **25 pulsaciones de Tab** para llegar al campo del correo, en un menú
  // que el agricultor no puede usar porque no ha entrado. Vaciar el marco en `pantallaEntrar` no bastaba:
  // por el camino de `/` se volvía a pintar después. Aquí no se puede escapar ninguno.
  if (!estado.token) {
    vaciarElMarco();
    return;
  }
  const nombre = listo && listo.type ? listo.type.name : "";
  const modulo = MODULO_DE_LA_PANTALLA[nombre] || "";
  // **La clave de «ya está pintado» lleva el contexto dentro** (T04, 02/10/2026): antes solo llevaba el
  // módulo, y con eso el nombre de la finca y las fincas a las que se puede cambiar **no se repintaban**
  // cuando llegaban del servidor o cuando el agricultor cambiaba de finca. Un armazón que dice la finca
  // equivocada es peor que uno que no la dice.
  const finca = (estado.miFinca || {}).nombre || "";
  // Las fincas solo se ofrecen como botones **cuando hay más de una**: con una sola, un botón para
  // «cambiar» a la que ya se está usando es un botón que no lleva a nada (y además haría repintar la barra
  // sin que cambie nada de lo que se ve).
  const fincasParaCambiar = (estado.fincas || []).length > 1 ? estado.fincas : [];
  const firma = `${modulo}|${finca}|${fincasParaCambiar.length}|${estado.menuAbierto ? "menu" : ""}|${laFraseDeLoQueFalta()}`;
  if (estado.marcoPintado === firma && modulo !== "") return;
  let contenedor = null;
  try {
    contenedor = document.getElementById("marco");
  } catch (fallo) {
    contenedor = null;
  }
  if (!contenedor) return;
  estado.marcoPintado = firma;
  // **El armazón se enseña como panel cuando el menú no cabe a la izquierda** (07/10/2026). El CSS esconde
  // el armazón por debajo de 64 rem —es de ordenador—, y con él se iban también los 21 renglones: a 712 px
  // **no había forma de llegar a las cuentas con el teclado** (medido: los renglones existían en el
  // documento pero medían 0×0). Con esta clase, el mismo armazón se abre encima de la pantalla.
  contenedor.classList.toggle("marco-abierto", Boolean(estado.menuAbierto));
  const losModulos = MODULOS.map((uno) => ({
    clave: uno.clave,
    etiqueta: t(uno.texto, ""),
    accion: uno.accion,
    datos: uno.datos,
    activo: uno.clave === modulo,
    grupo: uno.grupo,
  }));
  let armazon = null;
  try {
    armazon = marcoDeLaAplicacion({
      textos: { menu: t("menu", {}), marco: t("marco", {}), acciones: t("acciones", {}) },
      // Quién está apuntando: lo que se guardó al entrar (`estado.nombre`) y, si no está, el nombre del
      // titular de la finca. En este programa la finca no tiene nombre propio (ver `textos.MENU`), así que
      // el dato de la barra es la cuenta.
      cuenta: estado.nombre || (estado.miFinca || {}).nombre || "",
      campana: estado.campana ? String(estado.campana.anio || "") : "",
      modulos: losModulos,
      // **Los grupos del menú** (07/10/2026): los mismos renglones, puestos por donde se buscan. Se arma
      // aquí, de `GRUPOS_DEL_MENU`, y no en el componente: el armazón no decide qué grupos hay, solo los
      // pinta. Un renglón sin grupo no se pierde: sale en su propio grupo con el nombre del módulo (y eso
      // sería un fallo de esta tabla, no del menú).
      grupos: GRUPOS_DEL_MENU.map((grupo) => ({
        clave: grupo.clave,
        etiqueta: t(grupo.texto, ""),
        modulos: losModulos.filter((uno) => uno.grupo === grupo.clave),
      })).filter((grupo) => grupo.modulos.length),
      menuAbierto: Boolean(estado.menuAbierto),
      // **Lo que falta por apuntar, en la barra** (07/10/2026, del encargo del rediseño). La frase se
      // monta aquí, que es donde está la cuenta y donde ya se monta para la pantalla del cuaderno: **solo
      // se dice si el servidor ha mirado** (`esta_completo` no es `null`) y si de verdad falta algo.
      // Un aviso sin dato sería inventado, y con cero cosas no hay nada que enseñar.
      pendientes: laFraseDeLoQueFalta(),
      // El contexto de la barra (T04): en qué finca se está y a cuáles puede cambiar esta cuenta.
      //
      // **Y no se le pasan las campañas, a propósito**: cambiar de campaña no existe (el servidor no tiene
      // ninguna forma de decir «trabaja en el año 2023»; `/api/campanas/actual` devuelve siempre la más
      // nueva). Ofrecer botones de años que no cambian nada sería mentir en la barra; los años se manejan
      // en su pantalla, que es donde de verdad se puede hacer algo con ellos.
      contexto: { finca, fincas: fincasParaCambiar },
    });
  } catch (fallo) {
    armazon = null;
  }
  if (armazon) montarFueraDeLaPantalla(contenedor, armazon);
}

/**
 * Enseña un error **en vez de** la pantalla, con la salida para volver.
 *
 * Esto era un `pintar(bloqueError(...))` que escribía el aviso con `innerHTML`: era el último sitio, fuera
 * del asistente, que montaba HTML a mano. Ahora el aviso y su botón se le piden a React, que es quien pinta
 * todo lo demás. De `bloqueError()` queda **un solo usuario**: el aviso de error del propio asistente
 * (`pintarAsistente`), que se borrará con su motor.
 *
 * Dos cosas que se conservan a propósito y una que se arregla:
 *
 *  1. **El aviso va `role="alert"`**: quien use un lector de pantalla lo oye en cuanto sale, sin tener que
 *     ir a buscarlo. Lo llevaba `bloqueError()` y lo sigue llevando.
 *  2. **El botón es el de siempre** (`VOLVER`, `data-accion="ir-inicio"`, la clase `.boton` pelada, sin
 *     flecha ni icono): es el mismo botón que había en los dos avisos que ya lo llevaban (sacar el
 *     cuaderno en papel y sacar los datos).
 *  3. **Y ahora lo llevan todos.** Siete de los nueve avisos se quedaban **sin ningún botón**: el
 *     agricultor veía «No se ha podido guardar» y no tenía dónde pulsar —ni siquiera volver—, porque el
 *     `pintar()` había borrado la pantalla en la que estaba. Un aviso sin salida es un callejón sin
 *     salida, y unificarlo era la mitad del trabajo de pasar esto a React.
 *
 * `sinVolver` es para el único caso que no puede llevar botón: cuando **no ha llegado ni la interfaz**
 * (el servidor no contesta al arrancar), `accion("volver")` devuelve la clave en vez del texto y el botón
 * diría «volver» en idioma de programador. Ahí lo que se enseña es el mensaje del fallo y el navegador ya
 * tiene su propio botón de recargar.
 */
function avisarDelError(texto, { sinVolver = false } = {}) {
  montar(() =>
    html`
      <${AvisoDeError} texto=${texto} />
      ${sinVolver
        ? null
        : html`<${BotonSencillo} etiqueta=${accion("volver")} accion="ir-inicio" clase="" />`}
    `,
  );
}

/**
 * Los botones de una confirmación, con la forma que tenían.
 *
 * Los de estas pantallas son **sencillos** (sin icono y sin flecha): solo llevan a ver lo que se acaba de
 * guardar o a volver al inicio. Se preparan aquí, una vez, porque las cinco confirmaciones los piden
 * igual.
 */
function accionesDeConfirmacion(volverA = null) {
  const acciones = [];
  if (volverA) acciones.push(volverA);
  acciones.push({
    etiqueta: accion("volver"),
    accion: "ir-inicio",
    clase: "boton-claro",
    sencillo: true,
  });
  return acciones;
}

/**
 * Lo que el servidor sabe de un campo: qué es, para qué sirve, un ejemplo y qué pasa si se deja en
 * blanco, con sus cuatro rótulos.
 *
 * Los datos se preparan aquí, una vez, y los pinta la pieza de React
 * (`react/piezas/ayuda_de_un_campo.js`). Mientras quedaban pasos sin migrar había un segundo camino
 * (`ayudaDeCampo()`, que convertía estos mismos datos a HTML): se borró al migrar el último paso, para no
 * tener dos copias de lo mismo que se puedan separar el día que alguien cambie un texto.
 */
function datosDeLaAyuda(clave) {
  const campos = t("ayuda.campos", []);
  const datos = campos.find((campo) => campo.campo === clave);
  if (!datos) return null;
  // Los cuatro rótulos salen del servidor, como todo lo que lee el agricultor. **Estaban escritos
  // aquí dentro**, que es justo donde no pueden estar: no pasaban por la prueba que vigila que no
  // hay jerga y nadie podía cambiarlos sin tocar el JavaScript. Se vieron al pasar a React la
  // pantalla de entrar, que es una de las que los enseñan.
  const r = (nombre) => t(`ayuda.rotulos_de_un_campo.${nombre}`, "");
  return {
    datos,
    rotulos: {
      que_es: r("que_es"),
      por_que: r("por_que"),
      ejemplo: r("ejemplo"),
      si_falta: r("si_falta"),
    },
  };
}


// ------------------------------------------------------------- el asistente

/**
 * El asistente de apuntar: una pregunta por pantalla.
 *
 * Cada paso trae su formulario (`montar`, que devuelve un elemento de React) y `recoger` (leer lo que ha
 * puesto el agricultor). Los pasos opcionales se pueden saltar, y siempre se puede volver atrás.
 *
 * **El motor no se ha tocado al migrar la pantalla**: `irA`, `normalizaIndice`, `pasoSeMuestra` y el
 * `recoger()` de cada paso siguen haciendo lo mismo. Lo que cambió es **quién pinta** el envoltorio (las
 * barras, la pregunta, la pista, el error y los botones), que ahora es `react/pantallas/asistente.js`.
 */
function abrirAsistente(tipo, pasos) {
  // El buscador de tierras se vacía al empezar: lo que se buscó en el apunte anterior no tiene por qué
  // seguir escondiendo tierras en este. Un filtro que sobrevive sin que el agricultor lo vea es la forma
  // más fácil de que crea que ha perdido sus tierras.
  estado.filtroTierras = "";
  // **`corregir` se limpia aquí, y es lo que impide el peor fallo de esta función**: si al empezar un
  // apunte nuevo quedara puesto el «estoy corrigiendo el apunte 7», guardar un tratamiento recién
  // apuntado cambiaría el apunte 7 en vez de crear el nuevo. Todo lo que abre el asistente (apuntar,
  // repetir o corregir) pasa por aquí, así que aquí es donde se deja en blanco.
  estado.asistente = { tipo, pasos, indice: 0, borrador: {}, error: null, corregir: null, tipoOriginal: null };
  pintarAsistente();
}

function pasoActual() {
  return estado.asistente.pasos[estado.asistente.indice];
}

/**
 * Pinta el paso en el que está el asistente, **entero en React** (ver `docs/REACT.md` §6.1).
 *
 * Lo que se prepara aquí es lo que el componente no puede saber:
 *
 *  1. **La pregunta y su pista**, que pueden ser texto o función (la segunda pantalla del asistente
 *     pregunta la fecha o la nave según dónde se haya dicho que se echó el producto) y, en el atajo de
 *     repetir, el texto forzado que avisa de que se está repitiendo lo de la última vez.
 *  2. **Los botones de abajo**, con sus etiquetas del servidor: VOLVER (si no es el primer paso),
 *     DEJARLO (si el paso es opcional) y SEGUIR —o **APUNTARLO** en el último paso, que es el resumen—.
 *  3. **El formulario del paso**, que se le pide a su `montar`. Se pide **dentro** de `montar()`, que
 *     recoge el fallo y enseña el aviso de emergencia: si los ficheros de React de `vendor/` no han
 *     llegado, el agricultor ve el aviso con su botón de recargar en vez de una pantalla en blanco.
 */
function pintarAsistente() {
  const asistente = estado.asistente;
  const paso = pasoActual();
  const total = asistente.pasos.length;

  // `tituloForzado` y `pistaForzada` son para el atajo de repetir: en vez de la pregunta del paso, se dice
  // que se está repitiendo lo de la última vez y que solo hay que cambiar el día. Estaban puestos desde el
  // principio y **no los leía nadie**: el atajo abría el resumen sin avisar de que era una repetición.
  const titulo =
    asistente.tituloForzado || (typeof paso.titulo === "function" ? paso.titulo() : paso.titulo);
  const pista =
    asistente.pistaForzada || (typeof paso.pista === "function" ? paso.pista() : paso.pista);

  const botones = [];
  if (asistente.indice > 0) {
    botones.push({
      // Mientras se corrige, el botón de volver dice **sin guardar** (diseño de Stitch de la ronda 92):
      // es lo único que el agricultor no puede deducir con la pantalla llena de datos puestos, y creer
      // que ya se ha guardado algo es la forma más fácil de perder un arreglo.
      etiqueta: asistente.corregir
        ? t("corregir.volver_sin_guardar", "") || accion("volver")
        : accion("volver"),
      accion: "asistente-atras",
      sencillo: true,
    });
  }
  if (paso.opcional) {
    botones.push({ etiqueta: accion("dejarlo"), accion: "asistente-saltar", sencillo: true });
  }
  botones.push({
    // El último paso es el resumen: ahí el botón no dice SEGUIR, dice APUNTARLO —y, si se está
    // corrigiendo un apunte que ya estaba, GUARDAR LOS CAMBIOS, que es lo que se está haciendo.
    etiqueta:
      asistente.indice === total - 1
        ? asistente.corregir
          ? t("corregir.boton_guardar", "") || accion("guardar")
          : accion("apuntar")
        : accion("seguir"),
    accion: "asistente-seguir",
    principal: true,
    sencillo: true,
  });

  montar(() =>
    pantallaDelAsistente({
      titulo,
      pista,
      indice: asistente.indice,
      total,
      formulario: paso.montar ? paso.montar() : null,
      // El error del paso puede estar a nulo (no hay error): se le pasa cadena vacía, que es lo que
      // entiende el componente para no pintar nada.
      error: asistente.error || "",
      // «Paso 2 de 5»: el número se cuenta desde 1 (el agricultor no cuenta desde cero) y el texto lo
      // arma el servidor, aquí, que es donde están los textos. **Con un solo paso no se dice nada**
      // (ronda 88): «Paso 1 de 1» no cuenta nada y ocupa una línea de la pantalla.
      paso:
        total > 1
          ? rellena(t("rotulos.paso", ""), { numero: asistente.indice + 1, total })
          : "",
      // Y, si se está corrigiendo, **la etiqueta que lo dice en cada paso** (diseño de Stitch de la
      // ronda 92). El título ya lo dice, pero se lee una vez; esto va pegado a la barra de progreso,
      // que es lo que se mira para saber por dónde vas. En un alta normal va vacío y no se pinta nada.
      modo: asistente.corregir ? t("corregir.modificando", "") : "",
      botones,
    }),
  );
}

/** ¿Esta pantalla del asistente aplica en este caso concreto? */
function pasoSeMuestra(paso) {
  return typeof paso.cuando === "function" ? paso.cuando() : true;
}

/**
 * Coloca el índice en una pantalla que de verdad se muestre.
 *
 * Hay pantallas que solo aplican a algunos casos: los detalles del sitio, por ejemplo,
 * solo salen si el producto se echa en una nave. Sin esto, el agricultor se quedaría
 * mirando una pantalla vacía. **La primera y la última (el resumen) siempre se
 * muestran**: sin resumen no se puede apuntar nada.
 */
function normalizaIndice(indice) {
  const pasos = estado.asistente.pasos;
  const actual = estado.asistente.indice;
  let destino = Math.max(0, Math.min(indice, pasos.length - 1));
  const direccion = destino < actual ? -1 : 1;
  while (destino > 0 && destino < pasos.length - 1 && !pasoSeMuestra(pasos[destino])) {
    destino += direccion;
  }
  return Math.max(0, Math.min(destino, pasos.length - 1));
}

function irA(indice) {
  const asistente = estado.asistente;
  const paso = pasoActual();
  if (paso.recoger) {
    const problema = paso.recoger();
    if (problema) {
      asistente.error = problema;
      pintarAsistente();
      return;
    }
  }
  asistente.error = null;
  asistente.indice = normalizaIndice(indice);
  pintarAsistente();
}

// ------------------------------------------------------------------ pantallas

/**
 * La pantalla de entrar, ya en React (ver `docs/REACT.md`).
 *
 * Es la primera que ve cualquiera, así que aquí el detalle importa: se le pasan los textos, el modo
 * (entrar o registrarse), las provincias del servidor, si esta instalación sabe leer el certificado
 * y **la ayuda del campo del NIF ya preparada** (con sus cuatro rótulos, que también vienen del
 * servidor).
 *
 * Los seis campos conservan su `id` y los lee `entrar()`, aquí debajo.
 */
function pantallaEntrar(modo = "entrar") {
  const primeraVez = modo === "registro";
  const camposDeAyuda = t("ayuda.campos", []);
  const rotulos = t("ayuda.rotulos_de_un_campo", {});
  const datosDelNif = camposDeAyuda.find((campo) => campo.campo === "explotacion.nif");

  // **Sin sesión no hay armazón** (06/10/2026). El menú de módulos se quedaba pintado de la sesión
  // anterior, y como va antes que la pantalla en el HTML era **lo primero que recorría el tabulador**:
  // medido, hacían falta **24 pulsaciones de Tab** para llegar al campo del correo, y encima era un menú
  // que el agricultor no puede usar (no ha entrado). Se vacía y se olvida lo pintado, para que al entrar
  // se vuelva a montar con su módulo marcado.
  vaciarElMarco();
  // `montar()` pide el elemento dentro de un `try`: si los ficheros de React de `vendor/` no han
  // llegado, enseña el aviso de emergencia en vez de dejar la pantalla en blanco.
  montar(() =>
    pantallaDeEntrar({
      textos: {
        pantalla_entrar: t("pantalla_entrar", {}),
        ayuda: { porques: t("ayuda.porques", {}) },
        certificado: t("certificado", {}),
      },
      modo: primeraVez ? "registro" : "entrar",
      provincias: t("provincias", []) || [],
      certificado: estado.certificadoEstado,
      ayudaDelNif: datosDelNif ? { ...datosDelNif, rotulos } : null,
      errorEntrar: estado.errorEntrar || "",
      errorCertificado: estado.errorCertificado || "",
    }),
  );
}

/**
 * Deja el armazón del ordenador vacío (el menú y la barra de arriba).
 *
 * Se usa al enseñar la pantalla de entrar: sin sesión, ese menú no lleva a ningún sitio y estorba en el
 * teclado. Deja `estado.marcoPintado` en blanco para que la próxima pantalla lo vuelva a montar.
 */
function vaciarElMarco() {
  try {
    const contenedor = document.getElementById("marco");
    // **`replaceChildren()` y no `innerHTML = ""`**: este fichero no monta HTML a mano desde que las
    // pantallas son de React, y hay una prueba que lo vigila (`test_la_migracion_a_react.py`). Vaciar un
    // contenedor no es montar HTML, pero se hace con la API del DOM igualmente, que además no interpreta
    // nada: quitar hijos no puede inventarse una etiqueta.
    if (contenedor) contenedor.replaceChildren();
  } catch (fallo) {
    // Sin `#marco` (por ejemplo, en una prueba que monta la aplicación a medias) no hay nada que vaciar.
  }
  estado.marcoPintado = "";
}

/** Mira si esta instalación sabe leer el certificado digital. */
async function mirarCertificado() {
  try {
    estado.certificadoEstado = await apiJson("/api/cuenta/certificado/estado");
  } catch (error) {
    // Si no se puede preguntar se da por hecho que no: mejor no enseñar el botón que
    // enseñarlo para que falle.
    estado.certificadoEstado = { configurado: false };
  }
}

async function entrarConCertificado() {
  estado.errorCertificado = "";
  try {
    const datos = await apiJson("/api/cuenta/entrar-con-certificado", { method: "POST" });
    estado.token = datos.token;
    estado.nombre = datos.nombre;
    ALMACEN.setItem(CLAVE_TOKEN, datos.token);
    guardar(CLAVE_NOMBRE, datos.nombre);
  } catch (error) {
    estado.errorCertificado = error.message;
    pantallaEntrar("entrar");
    return;
  }
  await arrancarSesion();
}

/*
 * La pantalla de inicio: la primera (y hoy la única) que está escrita en React.
 *
 * Hace exactamente lo mismo que antes: el saludo con el nombre y el año de la campaña, el
 * aviso que desbloquea al agricultor nuevo cuando no hay ninguna parcela, los seis botones
 * que sirve el servidor —en su orden, con su icono y su pista—, el botón de repetir lo
 * último (o la pista de que no hay nada) y los de dictado y «mis cosas».
 *
 * Lo único que cambia es quién la pinta: se le pide el elemento a `pantallaDeInicio` (que no escribe ni
 * una frase: todo le llega de `textos.py` por `/api/interfaz`) y se monta con `montar()`, que es el único
 * sitio que habla con ReactDOM y el único que escribe en la pantalla. Los `data-accion`, las clases y los
 * textos NO cambian: los clics los sigue atendiendo el manejador delegado de `document`, y `montar()` se
 * encarga de que, si React no hubiera llegado a cargarse, el agricultor vea un aviso y un botón de
 * recargar en vez de una pantalla en blanco.
 */
function pantallaInicio() {
  montar(() =>
    pantallaDeInicio({
      textos: {
        inicio: t("pantalla_inicio", {}),
        maestros: t("maestros", {}),
        dictado: t("dictado", {}),
        // El panel de mando del ordenador (fase 4): sus textos van con los de la pantalla porque es **la
        // misma pantalla** mirada de otra forma, como la tabla y las tarjetas de una lista.
        panel_de_mando: t("panel_de_mando", {}),
      },
      nombre: estado.nombre,
      campana: estado.campana,
      hayParcelas: estado.parcelas.length > 0,
      hayUltimo: Boolean(ultimoParaRepetir()),
      sinUltimo: fraseDeRepetir(),
      // **Lo que necesita el panel de mando del ordenador** (fase 4, 30/09/2026). En el móvil no se pinta
      // (el CSS esconde `.solo-escritorio`), pero se prepara igual: los números salen de los mismos datos que
      // la pantalla ya tiene, así que no cuesta una petición más y no hay dos formas de contarlos.
      mando: datosDelPanelDeMando(),
    }),
  );
}

/**
 * Lo que enseña el panel de mando del ordenador: el estado del año de un vistazo (fase 4, 30/09/2026).
 *
 * POR QUÉ EXISTE. Es la pantalla que se abre al entrar desde un pc, y hasta hoy era la del móvil estirada
 * (ocho botones de ancho completo en un monitor). Lo que hace un programa de gestión al abrirse es enseñar
 * **el estado**: cuatro números, lo que falta con su botón y lo último apuntado.
 *
 * LAS DECISIONES QUE HAY QUE ENTENDER, porque son las que hacen que esto no invente nada:
 *
 *  1. **Los cuatro números son datos que ya están cargados** (los apuntes del año, las tierras, las ventas y
 *     lo que hay dicho de cada tierra): ni una petición más, y nada calculado por el servidor aparte.
 *  2. **No hay tarjeta de gasto en euros**, aunque el diseño de Stitch la trae: ese número no existe en el
 *     programa (no hay gasto por producto sumado para el año) y ponerlo de adorno sería inventarse un dato.
 *     En su sitio va la tarjeta de las tierras, que además dice lo que hay que hacer.
 *  3. **Lo que falta es la misma lista que la del cuaderno** (`estado.faltantes`), con sus mismos botones:
 *     si fueran dos listas, el día que una cambie la otra diría otra cosa.
 *  4. **Los últimos apuntes son los mismos cinco que la tabla del cuaderno** (misma función, mismos datos):
 *     en el ordenador se ven sin entrar a la pantalla.
 *  5. **El cierre son los tres botones de siempre** (sacar el cuaderno en papel, guardar los datos y firmar),
 *     con sus mismas acciones.
 */
function datosDelPanelDeMando() {
  const p = (clave) => t(`panel_de_mando.${clave}`, "");
  const r = (clave) => t(`rotulos.${clave}`, "");
  const apuntes = losApuntesDelAnio();

  // --- 1. Los cuatro números -------------------------------------------------------------------
  //
  // **Las hectáreas tratadas** son la suma de las de todos los apuntes del año, y el detalle dice sobre
  // cuántas se está contando: un número sin su total al lado no dice si es mucho o poco.
  //
  // **Y lo que no se sabe NO suma cero** (A14 de `docs/T02_VALORES_POR_DEFECTO.md`, 05/10/2026). Aquí
  // ponía `suma + (Number(...) || 0)`, y eso convierte un hueco en un cero: un apunte sin hectáreas
  // —o una venta sin kilos— **rebajaba el total sin decirlo**, y el número que el agricultor lee en su
  // panel de mando parecía completo. Ahora se suma lo que se sabe y **se dice cuántos faltan**, que es la
  // misma regla que el pie de la tabla de tierras. La cuenta la hace `sumandoLoQueSeSabe` (`nucleo.js`),
  // que es de donde la usan todas las pantallas: una sola forma de sumar en todo el programa.
  const tratadas = sumandoLoQueSeSabe(apuntes, (apunte) => apunte.hectareas);
  const ventas = estado.ventas || [];
  const vendido = sumandoLoQueSeSabe(ventas, (venta) => venta.kilos);
  // **Las hectáreas de la finca las dice el servidor**, que ya cuenta aparte las tierras sin superficie
  // (`cuaderno.py` → `superficie_total_ha` y `tierras_sin_superficie`). Sumarlas aquí a mano era el otro
  // sitio donde un hueco valía cero, y además podía decir un número distinto del que dice el cuaderno.
  const resumen = estado.resumen || {};
  const hectareasDeLaFinca = sumandoLoQueSeSabe(estado.parcelas, (parcela) => parcela.superficie_ha);

  // Las tierras a las que les falta decir qué tienen este año: es la cuenta que se viene a hacer aquí, y la
  // que lleva al botón que lo arregla. Si el servidor no ha contestado, **no se dice nada**.
  const dichas = estado.cultivos || {};
  const faltanCultivos =
    dichas.parcelas === undefined ? null : (dichas.parcelas || []).filter((una) => una.falta_decirlo).length;

  // Lo que hay que decir cuando falta un dato, con su singular y su plural. Si el servidor no ha
  // contestado (`estado.resumen`), se usan las tierras que hay en memoria, que es lo que se está viendo.
  const tierrasSinSuperficie =
    resumen.tierras_sin_superficie === undefined
      ? hectareasDeLaFinca.sin_decir
      : Number(resumen.tierras_sin_superficie);
  // Las tres frases viven en `TABLA` y se piden con `conCuenta`, que elige el singular: ver el porqué
  // escrito en `textos.py` (y por qué no en los textos del panel de mando).
  const faltaPorSaber = (base, cuantos) => (cuantos ? conCuenta(t("tabla", {}), base, cuantos) : "");

  const numeros = [
    {
      etiqueta: p("apuntes"),
      valor: String(apuntes.length),
      detalle: conCuenta(t("cuaderno", {}), "apuntes_titulo", apuntes.length),
    },
    {
      etiqueta: p("hectareas"),
      valor: `${formateaNumero(tratadas.suma, 2)} ${r("hectareas_corto")}`,
      detalle: [
        // De cuántas hectáreas de la finca se está contando, con lo que no se sabe dicho aparte.
        hectareasDeLaFinca.suma
          ? rellena(p("hectareas_detalle"), { hectareas: formateaNumero(hectareasDeLaFinca.suma, 2) })
          : "",
        faltaPorSaber("apuntes_sin_hectareas", tratadas.sin_decir),
        faltaPorSaber("tierras_sin_hectareas", tierrasSinSuperficie),
      ]
        .filter(Boolean)
        .join(" · "),
    },
    {
      etiqueta: p("vendido"),
      valor: `${formateaNumero(vendido.suma, 0)} ${r("kilos_corto")}`,
      detalle: [
        ventas.length ? conCuenta(t("venta", {}), "cuantas", ventas.length) : "",
        faltaPorSaber("ventas_sin_kilos", vendido.sin_decir),
      ]
        .filter(Boolean)
        .join(" · "),
    },
    {
      etiqueta: p("tierras"),
      valor: String((estado.parcelas || []).length),
      detalle:
        faltanCultivos === null
          ? ""
          : faltanCultivos
            ? conCuenta(t("panel_de_mando", {}), "tierras_sin_decir", faltanCultivos)
            : p("tierras_al_dia"),
    },
  ];

  // --- 2. Lo que falta por completar -----------------------------------------------------------
  //
  // La misma lista que la del cuaderno, con los mismos botones: aquí solo se le pone la cuenta delante.
  const faltantes = estado.faltantes || { pendientes: [] };
  const ARREGLO = { parcela_sin_cultivo: { accion: "cultivo-ver-todos", texto: "cultivos.titulo" } };
  const pendientes = (faltantes.pendientes || []).map((pendiente) => {
    const arreglo = ARREGLO[pendiente.tipo];
    return {
      mensaje: pendiente.mensaje,
      accion: arreglo ? arreglo.accion : "",
      etiqueta: arreglo ? t(arreglo.texto, "") : "",
    };
  });

  // --- 3. Los últimos apuntes ------------------------------------------------------------------
  const ultimos = apuntes.slice(0, 5).map((apunte) => [
    apunte.fecha_escrita,
    [apunte.queEs, apunte.etiqueta].filter(Boolean).join(" · "),
    apunte.donde,
    apunte.hectareas
      ? `${formateaNumero(apunte.hectareas, 2)} ${r("hectareas_corto")}`
      : "",
  ]);

  // --- 4. Apuntar algo de hoy, y el cierre -----------------------------------------------------
  //
  // Los botones de apuntar son **los mismos del móvil** (texto, icono y pista del servidor): el que ya
  // conoce la aplicación reconoce los mismos tres botones, solo que aquí van en una fila.
  const deInicio = t("pantalla_inicio.botones", []) || [];
  const apuntar = deInicio
    .filter((boton) => ["echar_producto", "abonar", "trabajo"].includes(boton.id))
    .map((boton) => ({
      etiqueta: boton.texto,
      pista: boton.pista,
      icono: boton.icono,
      accion: "inicio",
      datos: { ir: boton.id },
      clase: boton.principal ? "boton-principal" : "boton-claro",
    }));

  return {
    numeros,
    faltantes: {
      titulo: p("falta_titulo"),
      cuantas: pendientes.length
        ? conCuenta(t("panel_de_mando", {}), "falta", pendientes.length)
        : "",
      pendientes,
      // Lo mismo que en «mi cuaderno» (01/10/2026, T02): si el servidor dice que **no hay nada que revisar**
      // porque el año está sin empezar (`esta_completo: null`), se enseña **su mensaje**, no un «no te falta
      // nada» que se leería como un visto bueno sobre un cuaderno vacío.
      vacio: faltantes.esta_completo === null ? faltantes.mensaje || p("falta_vacio") : p("falta_vacio"),
    },
    ultimos: {
      titulo: p("ultimos_titulo"),
      // Los nombres de las columnas son los de las tablas: no se escriben otros para lo mismo.
      columnas: [t("tabla.fecha", ""), t("tabla.que", ""), t("tabla.tierra", ""), t("tabla.hectareas", "")],
      filas: ultimos,
      vacio: p("ultimos_vacio"),
      ver_todos: apuntes.length
        ? {
            etiqueta: apuntes.length === 1 ? p("ver_todos_uno") : rellena(p("ver_todos"), { cuantas: apuntes.length }),
            accion: "inicio",
            datos: { ir: "mi_cuaderno" },
          }
        : null,
    },
    apuntar,
    cierre: {
      titulo: p("cierre_titulo"),
      explica: p("cierre_explica"),
      botones: [
        {
          etiqueta: (deInicio.find((boton) => boton.id === "papel") || {}).texto || "",
          accion: "inicio",
          datos: { ir: "papel" },
          clase: "boton-claro",
        },
        {
          etiqueta: t("cuaderno.sacar_datos", ""),
          accion: "sacar-datos",
          clase: "boton-claro",
          // Y con su pista, por el mismo motivo que en la pantalla del cuaderno: el fichero es el del año
          // que se está mirando y hay que decirlo antes de pulsar (`cuaderno.datos_pista`).
          pista: t("cuaderno.datos_pista", ""),
        },
        // El de firmar es **el mismo botón del móvil** (`firma.boton`), no una frase nueva: firmar el cuaderno
        // es lo mismo en las dos formas de la aplicación.
        { etiqueta: t("firma.boton", ""), accion: "firmar-abrir", clase: "boton-claro" },
      ].filter((boton) => boton.etiqueta),
    },
  };
}

/**
 * Qué se puede repetir con dos toques.
 *
 * Sale de dos sitios y se queda con el más nuevo de los dos: lo que recuerda **este** aparato
 * (`localStorage`) y el último tratamiento que hay apuntado en la finca (`/api/tratamientos`).
 *
 * POR QUÉ LOS DOS. «Lo mismo que la última vez» solo miraba el móvil, así que estrenar teléfono,
 * entrar desde el ordenador de casa o que el navegador borrase sus datos dejaba al agricultor sin
 * el atajo **y con un mensaje que le decía que no había apuntado nada**. Los apuntes están en el
 * servidor; el móvil solo es más rápido cuando lo tiene.
 */
function ultimoParaRepetir() {
  return queSePuedeRepetir(estado.ultimo, ultimoDeLaFinca(estado.tratamientos));
}

/**
 * La frase que se enseña al final de la pantalla de inicio cuando no hay nada que repetir.
 *
 * Son dos casos que no tienen nada que ver, y decir la frase del primero en el segundo es
 * mentirle al agricultor:
 *
 *  - La finca no tiene ningún apunte este año: «todavía no has apuntado nada», con los números
 *    del cuaderno delante (`apuntes_de_producto`, `apuntes_de_abono` y `apuntes_de_trabajo`).
 *  - La finca sí tiene apuntes, pero ninguno se puede repetir con dos toques: se le dice eso
 *    mismo, sin llamarle mentiroso a su propio cuaderno.
 *
 * Si el resumen no ha llegado, se usa la segunda: es la que no afirma nada que no se pueda
 * comprobar.
 */
function fraseDeRepetir() {
  const resumen = estado.resumen;
  if (!resumen) return t("pantalla_inicio.repetir.sin_poder_repetir", "");
  const apuntes =
    Number(resumen.apuntes_de_producto || 0) +
    Number(resumen.apuntes_de_abono || 0) +
    Number(resumen.apuntes_de_trabajo || 0);
  return apuntes > 0
    ? t("pantalla_inicio.repetir.sin_poder_repetir", "")
    : t("pantalla_inicio.repetir.vacio", "");
}

/**
 * El buscador de tierras: lee lo escrito y vuelve a pintar la pantalla con la lista filtrada.
 *
 * Lo escrito se lee **por el `id` del campo**, como todo lo demás de esta aplicación: el campo lo pinta
 * React y lo lee `app.js`. Y se guarda para que sobreviva a volver a montar la pantalla, que es lo que pasa
 * cada vez que se busca.
 *
 * **Dos buscadores, y a propósito** (`donde`): el del asistente, donde se elige una tierra, y el de «mis
 * cosas», donde se miran. Cada uno tiene su campo, su filtro y su pantalla; con uno solo, buscar «prado» al
 * apuntar un tratamiento dejaría «mis cosas» enseñando dos de las 51 tierras sin que nadie lo hubiera pedido
 * ahí.
 *
 * Con `limpiar` se vacía: es el botón de «VERLAS TODAS», que tiene que estar siempre a mano —cuando la
 * búsqueda no encuentra nada y cuando sí— porque un filtro del que no se puede salir es una lista de tierras
 * que ha desaparecido.
 */
function buscarLaTierra(limpiar = false, donde = "asistente") {
  const enMisCosas = donde === "mis-cosas";
  let texto = "";
  if (!limpiar) {
    const campo = document.getElementById(enMisCosas ? "buscar_tierra_mis_cosas" : "buscar_tierra");
    texto = campo ? campo.value : "";
  }
  if (enMisCosas) {
    estado.filtroTierrasMisCosas = texto;
    return pantallaMisCosas();
  }
  estado.filtroTierras = texto;
  return pintarAsistente();
}

/**
 * Lo que se apuntó de ese apunte, contado igual valga lo que valga.
 *
 * POR QUÉ HAY UNA SOLA FUNCIÓN PARA LOS CUATRO TIPOS. Desde la ronda 91, «mi cuaderno» enseña **todo**
 * lo que el agricultor ha apuntado este año —producto, abono, trabajo y cosecha—, y cada uno se puede
 * **corregir** o **borrar**. Lo que se enseña en la tarjeta de la lista y lo que se enseña en la
 * pantalla que pregunta «¿seguro que quieres borrarlo?» es **lo mismo**: si fueran dos listas, el día
 * que se añada un dato a una, la otra preguntaría por borrar algo que no ha enseñado.
 *
 * Aquí no se pinta nada y no se inventa nada: lo que no está, no se pone (nunca un cero ni un
 * «sin datos»), y los números y las fechas se escriben como en el resto de la aplicación.
 */
function fichaDeUnApunte(tipo, apunte) {
  const c = (clave) => t(`cuaderno.${clave}`, "");
  const r = (clave) => t(`rotulos.${clave}`, "");
  const donde = dondeSeApunto(apunte);
  const conTierra = donde ? [{ etiqueta: c("tierra_y_parcela"), valor: donde }] : [];
  const lasHectareas = (valor) =>
    valor ? `${formateaNumero(valor, 2)} ${r("hectareas_corto")}` : "";
  const losKilos = (valor) => (valor ? `${formateaNumero(valor, 0)} ${r("kilos_corto")}` : "");

  if (tipo === "tratamiento") {
    const fin = apunte.fecha_fin_plazo_seguridad;
    const cuantas = lasHectareas(apunte.superficie_tratada_ha);
    const cuanto = apunte.dosis
      ? [formateaNumero(apunte.dosis, 2), apunte.unidad_dosis || ""].filter(Boolean).join(" ")
      : "";
    return {
      tipo,
      id: apunte.id,
      queEs: t("corregir.que_es_producto", ""),
      etiqueta: apunte.producto_nombre || "",
      cuando: formateaFecha(apunte.fecha),
      filas: [
        ...conTierra,
        cuantas ? { etiqueta: c("hectareas_tratadas"), valor: cuantas } : null,
        cuanto ? { etiqueta: c("cuanto_por_hectarea"), valor: cuanto } : null,
        apunte.cultivo ? { etiqueta: c("el_cultivo"), valor: apunte.cultivo } : null,
        // «Hasta aquí no puedes coger la cosecha: 12/07/2026»: el plazo de seguridad, que es lo que
        // impide cosechar.
        fin ? { etiqueta: r("ya_cosechado"), valor: formateaFecha(fin) } : null,
      ].filter(Boolean),
    };
  }

  if (tipo === "fertilizacion") {
    const hectareas = lasHectareas(apunte.superficie_ha);
    return {
      tipo,
      id: apunte.id,
      queEs: t("corregir.que_es_abono", ""),
      etiqueta: apunte.fertilizante_nombre || "",
      cuando: formateaFecha(apunte.fecha),
      filas: [
        ...conTierra,
        hectareas ? { etiqueta: r("hectareas"), valor: hectareas } : null,
        apunte.kg_ha_producto
          ? {
              etiqueta: r("kilos_por_hectarea"),
              valor: `${formateaNumero(apunte.kg_ha_producto, 0)} ${r("kilos_corto")}`,
            }
          : null,
        apunte.cantidad_total_kg
          ? { etiqueta: r("unidad_kilos"), valor: losKilos(apunte.cantidad_total_kg) }
          : null,
      ].filter(Boolean),
    };
  }

  if (tipo === "cosecha") {
    const detalles = apunte.detalles || {};
    const kilos = losKilos(detalles.cantidad_kg);
    return {
      tipo,
      id: apunte.id,
      queEs: t("corregir.que_es_cosecha", ""),
      etiqueta: detalles.producto || t("corregir.que_es_cosecha", ""),
      cuando: formateaFecha(apunte.fecha),
      filas: [
        ...conTierra,
        kilos ? { etiqueta: r("unidad_kilos"), valor: kilos } : null,
        apunte.cultivo ? { etiqueta: c("el_cultivo"), valor: apunte.cultivo } : null,
      ].filter(Boolean),
    };
  }

  // Y lo que queda es un trabajo del campo: lo que el agricultor llama «labrar», «podar», «regar»…
  const hectareas = lasHectareas(apunte.superficie_ha);
  return {
    // **El tipo de la ficha es la práctica de verdad** («labrar», «podar», «sembrar»…), no «labor»: con
    // eso, al corregirla se abren **los pasos de esa práctica** (los de sembrar preguntan la semilla y
    // la dosis, y los de regar el agua), que es justo lo que hay que poder cambiar. Las rutas del
    // servidor no se enteran de la diferencia: todo lo que no es un tratamiento ni un abono se guarda,
    // se corrige, se borra y se anula por las labores, que es la misma tabla.
    tipo: apunte.tipo || "otra",
    id: apunte.id,
    queEs: t("corregir.que_es_trabajo", ""),
    etiqueta: nombreDeLaPractica(apunte.tipo) || apunte.tipo || "",
    cuando: formateaFecha(apunte.fecha),
    filas: [
      ...conTierra,
      hectareas ? { etiqueta: r("hectareas"), valor: hectareas } : null,
      apunte.cultivo ? { etiqueta: c("el_cultivo"), valor: apunte.cultivo } : null,
    ].filter(Boolean),
  };
}

/**
 * Todo lo que hay apuntado en la campaña que se está llevando, de lo más nuevo a lo más viejo.
 *
 * LOS CUATRO TIPOS EN LA MISMA LISTA, Y POR QUÉ. Hasta la ronda 91, «mi cuaderno» solo enseñaba los
 * apuntes de producto: un abono, un trabajo o una cosecha **no salían en ninguna pantalla** una vez
 * guardados. Eso ya era malo para mirarlos, y con CORREGIR y BORRAR sería peor: no se puede arreglar
 * lo que no se ve. Van juntos y ordenados por fecha porque es como lo cuenta el agricultor («lo de la
 * semana pasada»), y cada ficha dice de qué clase es, para no confundir un abono con una labor.
 */
function losApuntesDelAnio() {
  const conSuTipo = [
    ...(estado.tratamientos || []).map((apunte) => ({ tipo: "tratamiento", apunte })),
    ...(estado.fertilizaciones || []).map((apunte) => ({ tipo: "fertilizacion", apunte })),
    ...(estado.labores || []).map((apunte) => ({
      tipo: apunte.tipo === "cosecha" ? "cosecha" : "labor",
      apunte,
    })),
  ];
  // Se ordena por la fecha de verdad (`2026-05-01`), **no por la fecha escrita** (`01/05/2026`): la
  // escrita se ordena como texto y pondría el 1 de mayo antes que el 2 de abril. El agricultor busca
  // lo último que apuntó, y eso tiene que estar arriba.
  return conSuTipo
    .filter((uno) => uno.apunte && uno.apunte.fecha)
    .sort((uno, otro) => String(otro.apunte.fecha).localeCompare(String(uno.apunte.fecha)))
    .map((uno) => ({
      ...fichaDeUnApunte(uno.tipo, uno.apunte),
      // **Y los datos en crudo**, que son los que necesita la tabla del ordenador (30/09/2026): la fecha
      // sin formatear (para poder ordenar por ella), dónde se hizo, las hectáreas como número, el cultivo
      // y si el apunte está firmado. Se añaden aquí, en un solo sitio, para que la ficha y la fila de la
      // tabla no puedan decir cosas distintas.
      ...enCrudoElApunte(uno.tipo, uno.apunte),
    }));
}

/**
 * Los datos de un apunte **sin formatear**, para la tabla del ordenador.
 *
 * POR QUÉ NO SE REUTILIZAN LOS `filas` DE LA FICHA. Porque son pares «nombre: valor» ya escritos en
 * castellano («Hectáreas tratadas: 4,90 ha»), y una tabla necesita el **número** (para poder ordenar por
 * hectáreas) y el nombre de la columna una sola vez, arriba. Así que aquí se devuelven los valores tal
 * como vienen del servidor, y quien pinta decide cómo se escriben.
 */
function enCrudoElApunte(tipo, apunte) {
  const detalles = apunte.detalles || {};
  return {
    fecha: apunte.fecha || "",
    fecha_escrita: formateaFecha(apunte.fecha),
    donde: dondeSeApunto(apunte),
    hectareas: apunte.superficie_tratada_ha || apunte.superficie_ha || null,
    // La cosecha guarda los kilos en `detalles` (la labor los pide ahí): para el resumen del pie y para
    // saber cuánto se recogió, que es lo que se mira de una cosecha.
    kilos: detalles.cantidad_kg || null,
    cultivo: apunte.cultivo || "",
    firmado: elApunteEstaFirmado(tipo, apunte.id),
    // **A qué tierra pertenece**, en crudo (30/09/2026). Hace falta para lo que se mira **por tierra**: los
    // últimos apuntes de una tierra, en el panel de al lado de la tabla (`panelDeLaTierra`). El nombre ya lo da
    // `donde`, pero para filtrar hace falta el identificador.
    parcela_id: apunte.parcela_id || null,
  };
}

/**
 * Dónde se hizo un apunte: la tierra, el conjunto de tierras o la nave.
 *
 * **Esto no existía, y se notaba.** El apunte guarda a qué tierra se echó el producto desde el primer
 * día, pero «mi cuaderno» no lo enseñaba: el agricultor veía «TRIGO BLANDO · 4,90 ha · 0,80 L/ha» y no
 * dónde. Y «¿dónde lo echaste?» es justo lo que se pregunta cuando llega una inspección.
 *
 * Se resuelve aquí y no en el servidor porque los nombres ya están en la pantalla (`estado.parcelas`,
 * `estado.grupos`, `estado.instalaciones`): pedir otra llamada para algo que ya se tiene sería gastar
 * cobertura del agricultor en lo que ya está descargado.
 *
 * Si no se encuentra el nombre (por ejemplo, un apunte cuya tierra no está entre las descargadas), se
 * devuelve vacío y **la fila no se pinta**: antes un hueco que un dato equivocado.
 */
function dondeSeApunto(apunte) {
  if (apunte.parcela_id) {
    const parcela = (estado.parcelas || []).find((p) => p.id === apunte.parcela_id);
    return parcela ? parcela.alias : "";
  }
  if (apunte.grupo_id) {
    const grupo = (estado.grupos || []).find((g) => g.id === apunte.grupo_id);
    return grupo ? grupo.nombre : "";
  }
  if (apunte.instalacion_id) {
    const nave = (estado.instalaciones || []).find((i) => i.id === apunte.instalacion_id);
    // En una nave no se trata la tierra: se trata lo que hay guardado, con su lote.
    const lote = [apunte.producto_cosechado, apunte.lote_cosecha].filter(Boolean).join(" · ");
    return [nave ? nave.alias : "", lote].filter(Boolean).join(" · ");
  }
  return "";
}

/**
 * Todo lo que «mi cuaderno» necesita saber, ya contado y formateado.
 *
 * Es el trabajo que hacían las siete funciones `bloqueDe…` que había aquí abajo (y que ya no están): leer
 * el estado, sumar, decidir qué botón lleva cada cosa y escribir los números en castellano. **Aquí no se
 * pinta nada**: lo que sale de esta función son los datos de los nueve bloques, y quien los pinta es
 * `react/pantallas/mi_cuaderno.js`.
 *
 * Las cuatro decisiones que se conservan tal cual, porque son las que hacen que la pantalla sirva:
 *
 *  1. **Cada cosa que falta lleva el botón que la arregla** (si tiene pantalla propia). La regla del
 *     proyecto es «si le dices al agricultor que le falta algo, le das el botón que lo arregla», y esto
 *     era justo lo contrario: el cuaderno decía «a El Prado le falta decir qué cultivo tiene este año» y
 *     no había forma de contestarle. El pendiente que no tiene pantalla propia se queda con su texto.
 *  2. **Lo que no hay, no se enseña.** La firma y el cuaderno de la Junta solo están si el servidor los
 *     ha mandado: un bloque con su título y un hueco debajo parece un fallo del programa.
 *  3. **Las listas largas se cortan**: cuatro ventas y tres análisis. La pantalla entera está a un botón
 *     de distancia (`ventas-ver`, `analisis-ver`), y así «mi cuaderno» se puede leer de arriba abajo.
 *  4. **El aviso del plan se pone rojo si alguien se ha pasado** de abono, y el de las medidas si no hay
 *     ninguna declarada. Es lo único de esta pantalla que puede costar una sanción.
 */
function datosDelCuaderno() {
  const c = (clave) => t(`cuaderno.${clave}`, "");
  const v = (clave) => t(`venta.${clave}`, "");
  const m = (clave) => t(`medidas.${clave}`, "");
  const p = (clave) => t(`plan.${clave}`, "");
  const cyl = (clave) => t(`cuaderno_cyl.${clave}`, "");

  // --- 1. Lo que tengo apuntado este año --------------------------------------------------
  //
  // Cada apunte es una ficha (rediseño de la ronda 79, `docs/stitch/rediseno/mi_cuaderno.png`): su
  // número, su fecha y **cada dato con su nombre delante**. Antes esto era una sola línea
  // —«TRIGO BLANDO · 4,90 ha · 0,80 L/ha»— con tres datos seguidos, sin decir cuál era cuál y sin la
  // tierra donde se echó.
  //
  // **Y desde la ronda 91 son los cuatro tipos de apunte y cada uno se puede arreglar**: la lista
  // enseñaba solo los de producto, así que un abono, un trabajo o una cosecha desaparecían de la vista
  // en cuanto se guardaban, y no había forma de corregir ni de borrar lo que no se ve. Lo que se
  // enseña en cada ficha —y lo que sale en la pantalla de «¿seguro que quieres borrarlo?»— lo prepara
  // `fichaDeUnApunte`, que es la misma para los cuatro.
  const apuntes = losApuntesDelAnio().map((ficha, indice) => ({
    ...ficha,
    rotulo: rellena(c("apunte_numero"), { numero: indice + 1 }),
    lineas: [ficha.cuando, ficha.queEs].filter(Boolean),
    acciones: [
      // **Sacar del almacén lo que se gastó** (T09): el botón vive donde vive el apunte, que es lo que
      // dice el encargo, y no en el almacén. El motivo no es de sitio: una salida del almacén **sale de un
      // trabajo**, y si se pudiera restar producto «porque sí», el almacén dejaría de poder contestar a la
      // única pregunta que importa cuando hay un problema con un lote —«¿esto dónde se fue?»—. Desde el
      // apunte, además, la cantidad ya se sabe: la dice el propio apunte.
      //
      // Solo en los dos apuntes que gastan producto (un tratamiento y un abono): una labor o una cosecha
      // no sacan nada del almacén, y un botón que lleva a «eso no gasta del almacén» es un botón de más.
      ficha.tipo === "tratamiento" || ficha.tipo === "fertilizacion"
        ? {
            etiqueta: t("cesta.libro_nueva_salida", ""),
            accion: "salida-de-un-lote",
            datos: { tipo: ficha.tipo, id: ficha.id },
            clase: "boton-claro",
          }
        : null,
      ...botonesDeCorregirYBorrar(ficha.tipo, ficha.id),
    ].filter(Boolean),
  }));

  // El botón de apuntar otro tratamiento, con el icono que el servidor le da en la pantalla de inicio:
  // el mismo camino, con el mismo dibujo, para que se reconozca.
  const botonDeEchar = (t("pantalla_inicio.botones", []) || []).find(
    (boton) => boton.id === "echar_producto",
  );
  const apuntarOtro = {
    etiqueta: c(apuntes.length ? "apuntar_otro" : "apuntar_uno"),
    icono: botonDeEchar ? botonDeEchar.icono : "",
    accion: "inicio",
    datos: { ir: "echar_producto" },
    clase: "boton-claro",
  };

  // --- 2. Lo que le falta al cuaderno ----------------------------------------------------
  const faltantes = estado.faltantes || { pendientes: [] };
  const ARREGLO = {
    parcela_sin_cultivo: { accion: "cultivo-ver-todos", texto: "cultivos.titulo" },
  };
  // `pendientes` se lee con red: el servidor manda la lista, pero si algún día llegara sin ella, la
  // pantalla tiene que salir sin la lista (y no con el aviso de emergencia de React).
  const pendientes = (faltantes.pendientes || []).map((pendiente) => {
    const arreglo = ARREGLO[pendiente.tipo];
    return {
      mensaje: pendiente.mensaje,
      accion: arreglo ? arreglo.accion : "",
      etiqueta: arreglo ? t(arreglo.texto, "") : "",
    };
  });

  // --- 3. Lo que se ha vendido -----------------------------------------------------------
  //
  // **Lo que no se sabe no suma cero** (A14, 05/10/2026): se suma lo que trae kilos y se cuenta lo que no,
  // para poder decirlo. Antes, `(venta.kilos || 0)` hacía que una venta sin kilos pareciera una venta de
  // cero kilos, y el total se leía como completo.
  const ventas = estado.ventas || [];
  const sinKilos = sumandoLoQueSeSabe(ventas, (venta) => venta.kilos).sin_decir;
  const kilos = sumandoLoQueSeSabe(ventas, (venta) => venta.kilos).suma;

  // --- 4. Las medidas preventivas --------------------------------------------------------
  const datosMedidas = estado.medidas;
  const aplicadas = medidasAplicadasDeLaFinca();

  // --- 5. Los análisis -------------------------------------------------------------------
  const analisis = estado.analiticas || [];

  // --- 6. El plan de abono ---------------------------------------------------------------
  const planes = estado.planes || [];

  // --- 7. La firma -----------------------------------------------------------------------
  const firma = estado.firmaEstado;

  // --- 8. El cuaderno de la Junta --------------------------------------------------------
  const junta = estado.cuadernoJunta;

  // --- 9. El registro electrónico --------------------------------------------------------
  const enlaces = t("registro_electronico.enlaces", []) || [];

  return {
    textos: { cuaderno: t("cuaderno", {}) },
    apuntes: {
      // El número con su palabra en singular o en plural: «1 apuntes» es lo primero que hace desconfiar
      // de un programa, y este título es lo primero que se lee en esta pantalla. **Y desde la ronda 91
      // cuenta los cuatro tipos** —producto, abono, trabajo y cosecha—, que son los que salen debajo.
      titulo: conCuenta(t("cuaderno", {}), "apuntes_titulo", apuntes.length),
      hay: apuntes.length > 0,
      filas: apuntes,
      // **Y la tabla, para el ordenador** (30/09/2026): la misma lista de apuntes, con las mismas acciones,
      // mirada de arriba abajo. Las dos formas van en el mismo HTML y el CSS enseña la que toca.
      tabla: apuntes.length ? tablaDeApuntes(apuntes) : null,
      vacio: c("sin_nada"),
      acciones: [apuntarOtro],
    },
    faltantes: {
      titulo: c("falta_titulo"),
      pendientes,
      // **La frase de la sección vacía, con la misma regla que el resumen de arriba** (07/10/2026).
      //
      // Aquí ponía siempre `c("falta_vacio")` («Lo tienes todo apuntado»), y con el cuaderno **sin empezar**
      // eso contradecía a la frase de arriba —«todavía no has apuntado nada este año»—: la sección afirmaba
      // que estaba todo cuando el servidor no había podido mirar nada. Se corrigió el resumen el 01/10 y
      // **este texto se quedó fijo**; lo vio David en la pantalla. Ahora las dos frases salen del mismo
      // sitio: si el servidor no ha mirado (`esta_completo: null`), esto lo dice.
      vacio: !estado.faltantes
        ? ""
        : estado.faltantes.esta_completo === null
          ? c("falta_sin_empezar")
          : c("falta_vacio"),
      // La frase de un vistazo: lo primero que se lee en la pantalla que más se mira. **Solo se dice si
      // el servidor ha contestado** (`estado.faltantes`): con la lista sin llegar, «no te falta nada»
      // sería afirmar lo que no se sabe.
      //
      // **Y «no te falta nada» exige que el servidor haya mirado algo** (01/10/2026, T02): con el año sin
      // empezar, el servidor contesta `esta_completo: null` y su propio mensaje («Todavía no hay nada
      // apuntado este año…»). Antes esta línea decía «No te falta nada por apuntar» sobre un cuaderno
      // **vacío**, y el silencio se leía como un visto bueno.
      resumen: !estado.faltantes
        ? ""
        : estado.faltantes.esta_completo === null
          ? estado.faltantes.mensaje || ""
          : pendientes.length === 0
            ? c("pendientes_ninguno")
            : pendientes.length === 1
              ? c("pendiente_uno")
              : rellena(c("pendientes_varios"), { cuantas: pendientes.length }),
    },
    ventas: {
      titulo: v("titulo"),
      hay: ventas.length > 0,
      // El número delante y con su palabra (rediseño de la ronda 81): «2 ventas apuntadas · 44.000 kg».
      // Antes era «2 · 44.000 Kilos», que ni dice qué se cuenta ni se lee bien (la unidad larga es un
      // rótulo de campo y va en mayúscula). Con el singular, que «1 ventas» es lo que hace desconfiar.
      resumen: ventas.length
        ? `${ventas.length === 1 ? v("cuantas_una") : rellena(v("cuantas"), { cuantas: ventas.length })}` +
          ` · ${formateaNumero(kilos, 0)} ${t("rotulos.kilos_corto", "")}`
        : "",
      // La fecha y su último día vienen **ya unidos** con su raya: son dos fechas del servidor, y una
      // frase que junta dos textos se monta aquí, no dentro del componente (la prueba de «ni una frase
      // escrita a mano» lo caza). La partida que sale en varios viajes se lee «18/07/2026 — 19/07/2026».
      filas: ventas.slice(0, 4).map((venta) => ({
        fecha: `${formateaFecha(venta.fecha)}${
          venta.fecha_fin ? ` — ${formateaFecha(venta.fecha_fin)}` : ""
        }`,
        producto: venta.producto || "",
        detalle: detallesDeLaVenta(venta),
      })),
      sin_nada: v("sin_nada"),
      acciones: ventas.length
        ? [
            { etiqueta: v("ver"), accion: "ventas-ver", principal: true, sencillo: true },
            { etiqueta: v("anadir"), accion: "ventas-nueva", sencillo: true },
          ]
        : [{ etiqueta: v("anadir"), accion: "ventas-nueva", sencillo: true }],
    },
    medidas: {
      titulo: m("titulo"),
      declarada: Boolean(datosMedidas && datosMedidas.declarada),
      mensaje: (datosMedidas && datosMedidas.mensaje) || "",
      aplicadas: aplicadas.map((codigo) => nombreDeMedida(codigo)),
      sin_declarar: m("sin_declarar"),
      explica: m("explica"),
      acciones: [
        {
          etiqueta: datosMedidas && datosMedidas.declarada ? m("ver") : m("hacer"),
          accion: "medidas-ver",
          sencillo: true,
        },
      ],
    },
    analiticas: {
      titulo: t("analitica.titulo", ""),
      hay: analisis.length > 0,
      // «1 análisis guardado» (rediseño de la ronda 81). Antes era «1 · Dónde se aprovecha esto:», que
      // es la explicación de para qué sirve un análisis puesta donde va el número: no decía cuántos hay.
      resumen: analisis.length
        ? analisis.length === 1
          ? t("analitica.cuantos_uno", "")
          : rellena(t("analitica.cuantos", ""), { cuantos: analisis.length })
        : "",
      filas: analisis.slice(0, 3).map((uno) => ({
        titulo: nombreDeAnalisis(uno),
        fecha: formateaFecha(uno.fecha_toma_muestra),
        // Los números del boletín, en una línea: es lo que se mira de un vistazo.
        detalle: (uno.parametros_con_nombre || [])
          .map((n) => `${n.etiqueta}: ${n.texto}`)
          .join(" · "),
      })),
      sin_analisis: t("analitica.sin_analisis", ""),
      apunta_primero: t("analitica.apunta_primero", ""),
      acciones: analisis.length
        ? [
            {
              etiqueta: t("analitica.ver", ""),
              accion: "analisis-ver",
              principal: true,
              sencillo: true,
            },
            { etiqueta: t("analitica.anadir", ""), accion: "analisis-nuevo", sencillo: true },
          ]
        : [{ etiqueta: t("analitica.anadir", ""), accion: "analisis-nuevo", sencillo: true }],
    },
    plan: {
      titulo: p("titulo"),
      hay: planes.length > 0,
      // El aviso del plan es el del servidor, y cambia a «te has pasado» si alguno se ha pasado.
      mensaje: planes.filter((plan) => plan.se_ha_pasado).length ? p("pasado") : (planes[0] || {}).mensaje || "",
      se_ha_pasado: planes.some((plan) => plan.se_ha_pasado),
      sin_planes: p("sin_planes"),
      obligatorio: p("obligatorio"),
      acciones: [
        { etiqueta: p("ver"), accion: "plan-ver", principal: true, sencillo: true },
        { etiqueta: p("hacer"), accion: "plan-hacer", sencillo: true },
      ],
      // Cuando todavía no hay plan, el botón de hacerlo va **suelto** (como estaba) y con su icono: es la
      // única cosa que se puede hacer en ese bloque, así que es el que empuja a hacerla.
      botones: [{ etiqueta: p("hacer"), icono: "🧪", accion: "plan-hacer" }],
    },
    firma: {
      hay: Boolean(firma),
      titulo: t("firma.titulo", ""),
      mensaje: (firma && firma.mensaje) || "",
      no_puede_firmar: t("firma.no_puede_firmar", ""),
      explicacion: (firma && firma.explicacion) || "",
      cambiado: Boolean(firma) && firma.estado === "cambiado_despues_de_firmar",
      puede: Boolean(firma) && Boolean(firma.puede_firmar),
      // El botón de firmar **solo sale si se puede firmar**: un botón que lleva a un error es peor que
      // no ponerlo, y para eso está `no_puede_firmar`, que dice lo que hay que hacer (entrar con el
      // certificado).
      botones: firma && firma.puede_firmar
        ? [{ etiqueta: t("firma.boton", ""), icono: "✍️", accion: "firmar-abrir", principal: true }]
        : [],
    },
    cuaderno: {
      hay: Boolean(junta),
      titulo: cyl("sacar_titulo"),
      explica: cyl("sacar_explica"),
      hojas: conCuenta(t("cuaderno_cyl", {}) || {}, "hojas_datos", (junta && junta.hojas_con_datos) || 0),
      falta_titulo: cyl("que_falta_titulo"),
      falta_pista: cyl("que_falta_pista"),
      // Cada cosa que falta dice **dónde se apunta**: una lista de lo que falta sin decir dónde se
      // arregla es una lista que no sirve para nada. Cuando el sitio es «a mano en el fichero», el
      // servidor manda un guion y aquí se cambia por la frase que lo dice.
      faltan: ((junta && junta.faltan) || []).map((falta) => ({
        que_falta: falta.que_falta,
        donde:
          falta.donde_se_pone === "—"
            ? cyl("a_mano_en_el_fichero")
            : `${cyl("donde")}: ${falta.donde_se_pone}`,
        hoja: `${cyl("hoja")}: ${falta.hoja}`,
      })),
      todo_completo: cyl("todo_completo"),
      acciones: [
        { etiqueta: cyl("sacar"), accion: "cuaderno-sacar", principal: true, sencillo: true },
        {
          etiqueta: t("mis_datos.titulo", ""),
          accion: "mis-datos-abrir",
          sencillo: true,
        },
        { etiqueta: cyl("traer"), accion: "cuaderno-de-la-junta-abrir", sencillo: true },
      ],
    },
    registro: {
      hay: enlaces.length > 0 || Boolean(t("registro_electronico.que_es", "")),
      titulo: t("registro_electronico.titulo", ""),
      que_es: t("registro_electronico.que_es", ""),
      donde: t("registro_electronico.donde", ""),
      desde_cuando: t("registro_electronico.desde_cuando", ""),
      es_voluntario: t("registro_electronico.es_voluntario", ""),
      enlaces_titulo: t("registro_electronico.enlaces_titulo", ""),
      enlaces,
    },
    // Los tres botones de abajo llevan su emoji **dentro del texto**, que es como estaban escritos: estos
    // no son los botones de la casa (no llevan el `<span class="icono">` ni la flecha).
    acciones: [
      {
        etiqueta: `🖨️ ${c("ver_papel")}`,
        accion: "sacar-papel",
        principal: true,
        sencillo: true,
      },
      // **Y la pista dice qué se lleva el fichero** (06/10/2026): el cuaderno del año que se está
      // mirando. Estaba escrita en el servidor desde siempre (`cuaderno.datos_pista`) y **no la pintaba
      // ninguna pantalla** —era texto muerto—, así que el agricultor pulsaba «GUARDAR LOS DATOS EN UN
      // FICHERO» sin saber qué se llevaba (lo encontró la comprobación de descargas).
      { etiqueta: `💾 ${c("sacar_datos")}`, accion: "sacar-datos", sencillo: true, pista: c("datos_pista") },
      { etiqueta: accion("volver"), accion: "ir-inicio", sencillo: true },
    ],
  };
}

/**
 * «Mi cuaderno»: la pantalla que más se mira, ya en React (ver `docs/REACT.md`).
 *
 * Hasta hoy era **la última grande** que se pintaba con `pintar()` y plantillas de texto: nueve bloques
 * escritos a mano y siete funciones `bloqueDe…`. Ahora se preparan los datos (`datosDelCuaderno`) y los
 * pinta `react/pantallas/mi_cuaderno.js`, con los mismos textos, las mismas clases, los mismos emojis y
 * los mismos `data-accion` que antes, porque los clics los sigue atendiendo el manejador delegado de
 * `document` que vive aquí.
 *
 * Se monta con `montar()`, que pide el elemento dentro de un `try`: si los ficheros de React de
 * `vendor/` no han llegado, o si falta un texto, sale el aviso de emergencia en vez de una pantalla en
 * blanco.
 */
function pantallaCuaderno() {
  montar(() => pantallaDeMiCuaderno(datosDelCuaderno()));
}

/**
 * Mis datos: el titular y la finca, que es la **portada del cuaderno** de la Junta (su hoja 1.1).
 *
 * Sin esta pantalla, la lista de lo que le falta al cuaderno decía «mis datos → tu finca» y ese
 * sitio **no existía**: el endpoint estaba, el modelo tenía las columnas y no había forma de
 * rellenarlas desde el móvil. Es el mismo fallo de siempre (un dato que existe y no tiene puerta), y
 * lo encontró la propia lista de lo que falta al escribir el cuaderno.
 */
const CAMPOS_DE_MIS_DATOS = [
  ["nombre", "texto"],
  ["nif", "texto"],
  ["registro_autonomico", "texto"],
  ["registro_nacional", "texto"],
  ["direccion", "texto"],
  ["localidad", "texto"],
  ["codigo_postal", "texto"],
  ["provincia", "texto"],
  ["municipio", "texto"],
  ["telefono", "texto"],
  ["correo", "texto"],
  // **Los últimos dos, y el ecológico es nuevo de hoy** (A13, 05/10/2026). Hasta ahora este campo no tenía
  // puerta: estaba en el modelo, salía en el documento que se firma y **apagaba la comprobación
  // ecológica**, y no había ninguna pantalla donde decir «sí, mi finca es ecológica». Un dato que existe y
  // no se puede rellenar es el fallo de siempre, y aquí además tenía consecuencias de ley.
  // Va con tres respuestas: el tercer estado («no lo sé») se manda como `null`, y el programa avisa
  // mientras no conste, en vez de dar por bueno que no es ecológica.
  ["produccion_ecologica", "si_no_no_se"],
];

/**
 * «Mis datos»: la portada del cuaderno. **Es la primera pantalla con campos que se rellenan** y sirve
 * de modelo para las demás (ver `docs/REACT.md`).
 *
 * Decisión que hay que entender: los campos **siguen teniendo su `id`** (`finca-nombre`, `finca-nif`…)
 * y los sigue leyendo `guardarMisDatos()`, aquí abajo, igual que antes. El manejador de clics de esta
 * aplicación es **uno solo** y vive aquí, así que el que guarda es este fichero. Poner el estado
 * dentro del componente obligaría a montar un estado compartido entre las dos mitades, y eso es otro
 * trabajo (más grande) que no es el que arregla esta pantalla. Lo que cambia es **quién dibuja los
 * campos**, que es el objetivo de la migración.
 */
function pantallaMisDatos() {
  const finca = estado.miFinca || {};
  // El valor de un campo de tres respuestas se traduce a lo que se lee en el desplegable: `true` → «si»,
  // `false` → «no» y `null`/`undefined` → «» («no lo sé»), que es la opción que sale elegida cuando nadie
  // ha contestado. Lo contrario se hace al guardar (`guardarMisDatos`).
  const paraElFormulario = (campo, tipo) => {
    const crudo = finca[campo];
    if (tipo === "si_no_no_se") {
      if (crudo === true) return "si";
      if (crudo === false) return "no";
      return "";
    }
    return crudo || "";
  };
  const campos = CAMPOS_DE_MIS_DATOS.map(([campo, tipo]) => ({
    campo,
    tipo,
    valor: paraElFormulario(campo, tipo),
  }));

  // `montar()` pide el elemento dentro de un `try`: si los ficheros de React de `vendor/` no han
  // llegado, enseña el aviso de emergencia en vez de dejar la pantalla en blanco.
  montar(() =>
    pantallaDeMisDatos({
      // Los textos de las fincas van **con** los de «mis datos» porque es en esta pantalla donde está el
      // botón que lleva a «quién entra en mi finca» (ronda 89): la puerta se pone donde está el dato (la
      // finca), que es donde el agricultor la va a buscar.
      textos: {
        mis_datos: t("mis_datos", {}),
        fincas: t("fincas", {}),
        // Los años del cuaderno también se tocan desde aquí (ronda 93): el año es de la finca, y esta es
        // la pantalla donde se dice cómo se llama y quién entra en ella.
        campanas: t("campanas", {}),
        acciones: t("acciones", {}),
      },
      campos,
      guardado: Boolean(estado.misDatosGuardados),
      error: estado.errorMisDatos,
    }),
  );
}

async function guardarMisDatos() {
  const d = (clave) => t(`mis_datos.${clave}`, "");
  const cuerpo = {};
  for (const [campo, tipo] of CAMPOS_DE_MIS_DATOS) {
    const nodo = document.getElementById(`finca-${campo}`);
    const escrito = nodo ? String(nodo.value || "").trim() : "";
    // **El campo de tres respuestas se traduce antes de mandarlo** (A13, 05/10/2026): «si» → `true`,
    // «no» → `false`, y la opción vacía → **`null`, que es «no lo sé»**. Mandarla como cadena vacía haría
    // que Pydantic no la reconociera como un booleano; y mandar `false` cuando nadie ha contestado es
    // exactamente el defecto que se está arreglando.
    if (tipo === "si_no_no_se") {
      cuerpo[campo] = escrito === "si" ? true : escrito === "no" ? false : null;
      continue;
    }
    cuerpo[campo] = escrito;
  }
  estado.errorMisDatos = "";
  estado.misDatosGuardados = false;
  try {
    const respuesta = await fetch("/api/mi-finca", {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${estado.token}`,
      },
      body: JSON.stringify(cuerpo),
    });
    const detalle = await respuesta.json().catch(() => null);
    if (!respuesta.ok) throw new Error((detalle && detalle.detail) || d("guardar"));
    estado.miFinca = detalle;
    estado.misDatosGuardados = true;
    // Y se vuelve a pedir lo que le falta al cuaderno: si con esto se ha cerrado un hueco, la lista
    // se tiene que ver más corta **en el momento**, no al día siguiente.
    estado.cuadernoJunta = await apiJson(conLaCampana("/api/cuaderno-cyl/que-falta")).catch(() => estado.cuadernoJunta);
  } catch (error) {
    estado.errorMisDatos = error.message || d("guardar");
  }
  pantallaMisDatos();
}

// ------------------------------------------------ quién entra en la finca (ronda 89)

/**
 * «Quién entra en mi finca»: quién más apunta en el mismo cuaderno, y en qué finca estás trabajando.
 *
 * POR QUÉ ESTA PANTALLA EXISTE
 *
 * El servidor sabía hacerlo desde la ronda 89 —la tabla `accesos_a_fincas`, sus cuatro endpoints y sus
 * textos— y **no había forma de llegar desde el móvil**: era otro dato con modelo, endpoint y texto, y sin
 * puerta. David lo pidió así: «también quiero que una explotación puedan acceder varias cuentas, no solo 1».
 *
 * LA DECISIÓN QUE HAY QUE ENTENDER
 *
 * Esta pantalla **no adivina nada**: quién entra, con qué papel y qué finca está activa lo dice el
 * servidor (`/api/fincas` y `/api/fincas/quien-entra`), y aquí solo se pinta. Lo único que se guarda en
 * memoria son esas dos respuestas, y se piden **al abrir la pantalla** y no al arrancar: con una sola
 * finca no hacen falta para nada, y el arranque es justo lo que va mal en el campo sin cobertura.
 */
function pantallaQuienEntra() {
  const suyos = estado.quienEntra || {};
  // Las hectáreas de cada finca se escriben aquí, con el mismo formateador que el resto de la aplicación
  // (diseño de Stitch de esta pantalla, ronda 90): al elegir en qué finca trabajas, el tamaño es lo que
  // distingue una finca de otra cuando se llaman parecido. El número lo cuenta el servidor.
  const fincas = (estado.fincas || []).map((finca) => ({
    ...finca,
    hectareas: finca.hectareas
      ? `${formateaNumero(finca.hectareas, 2)} ${t("rotulos.hectareas_corto", "")}`
      : "",
  }));
  montar(() =>
    pantallaDeQuienEntra({
      textos: { fincas: t("fincas", {}), acciones: t("acciones", {}) },
      finca: suyos.nombre || "",
      fincas,
      personas: suyos.personas || [],
      soyTitular: Boolean(suyos.soy_titular),
      aviso: estado.avisoFincas,
      error: estado.errorFincas,
    }),
  );
}

/** Abre la pantalla: primero se piden las dos listas y luego se pinta. */
async function abrirQuienEntra() {
  estado.avisoFincas = "";
  estado.errorFincas = "";
  await cargarLasFincas();
  pantallaQuienEntra();
}

/**
 * Pide las dos listas de la pantalla: en qué fincas puede entrar esta cuenta y quién entra en la actual.
 *
 * Se piden **juntas** (`Promise.all`) porque son la misma pregunta vista desde dos lados, y una sin la
 * otra deja la pantalla mintiendo: con `quienEntra` viejo, la lista de personas sería la de la finca
 * anterior.
 */
async function cargarLasFincas() {
  try {
    const [fincas, quienEntra] = await Promise.all([
      apiJson("/api/fincas"),
      apiJson("/api/fincas/quien-entra"),
    ]);
    estado.fincas = fincas;
    estado.quienEntra = quienEntra;
  } catch (error) {
    estado.errorFincas = error.message || mensaje("no_se_pudo");
  }
}

/**
 * Le da acceso a otra cuenta, por su correo. Solo el titular; si no lo eres, lo dice el servidor.
 *
 * El correo se lee **por el `id` del campo** (`persona-correo`), que es como lee esta aplicación todo lo
 * que se escribe: el manejador de clics es uno solo y vive aquí. Y se vacía después de añadirla, porque un
 * correo que se queda escrito parece que no se ha hecho nada.
 */
async function anadirCuentaALaFinca() {
  const campo = document.getElementById("persona-correo");
  const correo = campo ? String(campo.value || "").trim() : "";
  estado.errorFincas = "";
  estado.avisoFincas = "";
  try {
    estado.quienEntra = await apiJson("/api/fincas/quien-entra", {
      method: "POST",
      body: JSON.stringify({ correo }),
    });
    if (campo) campo.value = "";
    estado.avisoFincas = t("fincas.anadida", "");
  } catch (error) {
    estado.errorFincas = error.message || mensaje("no_se_pudo");
  }
  pantallaQuienEntra();
}

/**
 * Quita el acceso a una cuenta. El servidor decide quién puede quitárselo a quién (el titular, a
 * cualquiera; y cada uno, a sí mismo menos de su propia finca), así que aquí no se comprueba nada de eso.
 *
 * Se pregunta antes con el mismo `window.confirm` que usa el botón de salir: es lo único de esta pantalla
 * que no se deshace con otro toque, porque habría que volver a escribir el correo.
 */
async function quitarCuentaDeLaFinca(usuarioId) {
  if (!window.confirm(t("fincas.confirmar_quitar", ""))) return;
  estado.errorFincas = "";
  estado.avisoFincas = "";
  try {
    estado.quienEntra = await apiJson(`/api/fincas/quien-entra/${usuarioId}`, { method: "DELETE" });
    estado.avisoFincas = t("fincas.quitada", "");
  } catch (error) {
    estado.errorFincas = error.message || mensaje("no_se_pudo");
  }
  pantallaQuienEntra();
}

/**
 * Lo que hay que olvidar cuando se cambia de finca (T04, 02/10/2026).
 *
 * **`cargarDatos()` no basta.** Vuelve a pedir las listas y las sobrescribe, sí, pero hay cosas que
 * no vienen de ninguna lista y que son de la finca en la que se estaba: la **fila elegida** en una
 * tabla, los **filtros** escritos, un **formulario a medias** (`estado.asistente`), el mapa abierto,
 * la tierra de la que se estaba diciendo el cultivo, el dictado pendiente y las medidas que se
 * estaban marcando. Sin esto, cambiar de finca dejaba a la vista un panel de detalle de una tierra
 * que **no es de esta finca** —o, peor, un asistente a medias apuntando a una tierra de la otra—,
 * que es exactamente lo que el aislamiento entre explotaciones tiene que impedir.
 *
 * Lo que se vacía son **datos y vistas**, nunca el vale ni la cola de apuntes sin mandar: esos dos
 * siguen siendo del agricultor y tienen que poder mandarse (ver `salir`).
 */
function olvidarLoDeLaFincaAnterior() {
  // Lo que se estaba mirando: la fila elegida en cada tabla y por dónde iba el buscador de tierras.
  estado.filaElegida = {};
  estado.filtroTierras = "";
  estado.filtroTierrasMisCosas = "";
  // Lo que se estaba escribiendo: un formulario a medias, un borrador, un dictado, el cultivo que se
  // estaba diciendo de una tierra y el mapa (que apunta a la tierra que se estaba mirando).
  estado.asistente = null;
  estado.borradorPendiente = null;
  estado.dictadoTexto = "";
  estado.errorDictado = "";
  estado.cultivoParcela = null;
  estado.mapa = null;
  estado.medidasBorrador = null;
  estado.confirmacion = null;
  // Las otras fincas y quién entra en esta: se vuelven a pedir al abrir su pantalla.
  estado.fincas = [];
  estado.quienEntra = null;
  // Y los avisos de las pantallas de esta finca, que ya no dicen nada de la nueva.
  estado.errorDocumentos = "";
  estado.errorCesta = "";
  estado.errorCultivos = "";
  estado.errorGrupos = "";
}

/**
 * Ponerse a trabajar en otra finca de las que puede usar.
 *
 * **Y se vuelve a pedir todo**, que es la mitad del trabajo: lo que hay en memoria (las tierras, los
 * apuntes, el cuaderno de la Junta) es de la finca en la que se estaba, y enseñarlo después de cambiar
 * sería enseñarle a un agricultor los datos de otra finca.
 *
 * El vale se cambia porque el vale **dice en qué finca se está**: es lo que impide que un vale viejo siga
 * mirando la finca en la que ya no se está. Y se olvida «lo mismo que la última vez», que se guarda en el
 * móvil: ese atajo repetiría un apunte de la finca anterior, con su tierra, y esa tierra aquí no existe.
 *
 * Desde el 02/10/2026 se olvida además **lo que no viene de ninguna lista** (la fila elegida, los
 * filtros, un formulario a medias): ver `olvidarLoDeLaFincaAnterior`.
 */
async function entrarEnLaFinca(explotacionId) {
  estado.errorFincas = "";
  estado.avisoFincas = "";
  try {
    const datos = await apiJson("/api/fincas/cambiar", {
      method: "POST",
      body: JSON.stringify({ explotacion_id: explotacionId }),
    });
    estado.token = datos.token;
    ALMACEN.setItem(CLAVE_TOKEN, datos.token);
    estado.ultimo = null;
    ALMACEN.removeItem(CLAVE_ULTIMO);
    olvidarLoDeLaFincaAnterior();
    await cargarDatos();
  } catch (error) {
    estado.errorFincas = error.message || mensaje("no_se_pudo");
    // Si se venía de una dirección que apunta a esa finca, esa dirección **no se puede abrir**, y se dice:
    // callar y dejar al agricultor en la pantalla de antes sería no contestar a lo que ha pedido (o a lo
    // que le han mandado por un enlace).
    const pendiente = estado.direccionPendiente;
    estado.direccionPendiente = null;
    if (pendiente) {
      pantallaDeDireccionQueNoLlevaANingunaParte();
      return;
    }
    pantallaQuienEntra();
    return;
  }
  // Si la finca se ha cambiado **por una dirección**, se sigue abriendo lo que esa dirección pedía; si no,
  // se va al inicio, que es donde se apunta.
  const pendiente = estado.direccionPendiente;
  estado.direccionPendiente = null;
  if (pendiente) {
    abrirLaPantalla(pendiente.pantalla, pendiente.parametros);
    return;
  }
  pantallaInicio();
}

/** Descarga el cuaderno de la Junta relleno, con los datos del agricultor. */
async function sacarElCuadernoDeLaJunta() {
  const c = (clave) => t(`cuaderno_cyl.${clave}`, "");
  estado.errorCuadernoJunta = "";
  try {
    // **El año que se está mirando** (06/10/2026): sin esto, la ruta sacaba el fichero del **año en
    // curso**, así que quien tuviera delante el cuaderno de 2025 (y la pantalla diciéndole lo que le
    // faltaba de 2025) descargaba el de 2026 sin que nada se lo advirtiera.
    const campana = estado.campana ? `?campana_id=${estado.campana.id}` : "";
    const respuesta = await api(`/api/cuaderno-cyl/exportar${campana}`);
    if (!respuesta.ok) {
      const detalle = await respuesta.json().catch(() => null);
      throw new Error((detalle && detalle.detail) || c("no_se_pudo"));
    }
    const blob = await respuesta.blob();
    const enlace = document.createElement("a");
    enlace.href = URL.createObjectURL(blob);
    enlace.download = "cuaderno-de-la-junta.xlsx";
    enlace.click();
    URL.revokeObjectURL(enlace.href);
  } catch (error) {
    estado.errorCuadernoJunta = error.message || c("no_se_pudo");
    pantallaCuaderno();
  }
}

function pantallaAyuda() {
  // Ojo con el nombre: `pantalla` es el contenedor de la aplicación (arriba del fichero), así que
  // los textos de esta pantalla se llaman `guia` para no taparlo. Se llamó `pantalla` en el primer
  // intento y `montarEn` recibió un diccionario en vez del contenedor.
  const guia = t("ayuda.pantalla", {});
  const porques = t("ayuda.porques", {});
  const campos = t("ayuda.campos", []);

  // Las frases de lo que dice la ley, cada una **con su nombre** (ronda 83): eran seis párrafos seguidos
  // bajo un solo rótulo y se leían como un muro. El título va aparte del texto (`ley_*_titulo`) porque el
  // texto se sigue usando en otros sitios sin título.
  //
  // Y en la ronda 90, **la etiqueta de sí o no** (del diseño de Stitch de esta pantalla): dos de los seis
  // puntos contestan a la pregunta con la que se entra en la ayuda —«¿esto tengo que mandarlo?»—, y la
  // respuesta se lee en la etiqueta sin leer el párrafo. Son exactamente los dos que ya lo decían en su
  // texto (`ley_llevar` y `ley_mandar`, con el artículo 10.2 del Real Decreto 1054/2022 detrás). Los otros
  // cuatro no son obligación ni voluntad —son explicaciones— y por eso no llevan etiqueta.
  const LEY_CON_ETIQUETA = {
    ley_llevar: "obligatorio",
    ley_mandar: "voluntario",
  };
  const ley = [
    "ley_llevar",
    "ley_mandar",
    "ley_programa",
    "ley_fechas",
    "ley_cuando_obligatorio",
    "ley_sin_confirmar",
  ].map((clave) => {
    const tipo = LEY_CON_ETIQUETA[clave] || "";
    return {
      titulo: guia[`${clave}_titulo`] || "",
      texto: guia[clave] || "",
      etiqueta: tipo ? guia[tipo] || "" : "",
      tipo,
    };
  });

  // Las reglas de abono de las zonas de nitratos, con su número y su fuente. Se enseñan
  // porque son las que pueden costar una sanción, y el agricultor tiene derecho a leerlas sin
  // tener que buscar la Orden en el BOE.
  // Las reglas del abono en zonas de nitratos: se resuelve aquí qué hace el programa con cada una,
  // porque eso no es cosa de la pantalla.
  const reglas = (t("reglas_nitratos", []) || []).map((regla) => ({
    que: regla.que,
    texto_valor: regla.texto_valor,
    con_numero: t("ayuda.pantalla.regla_con_numero", ""),
    como_lo_hace:
      regla.que_hace_la_app === "avisa"
        ? t("ayuda.pantalla.la_app_avisa", "")
        : regla.que_hace_la_app === "consulta"
          ? t("ayuda.pantalla.la_app_consulta", "")
          : t("ayuda.pantalla.la_app_no_puede", ""),
  }));

  const faltan = t("limites_que_faltan", []) || [];

  const aportes = (t("aportes_maximos_n", []) || []).map((fila) => {
    const cifra = (celda) =>
      celda
        ? `${String(celda.maximo_kg_n_ha)} ${t("ayuda.pantalla.unidad_nitrogeno", "")} · ${celda.texto}`
        : t("ayuda.pantalla.sin_cifra", "");
    return {
      cultivo: fila.cultivo,
      secano: `${t("ayuda.pantalla.secano", "")}: ${cifra(fila.secano)}`,
      regadio: `${t("ayuda.pantalla.regadio", "")}: ${cifra(fila.regadio)}`,
    };
  });
  const periodos = (t("periodos_prohibidos_n", []) || []).map((fila) => ({
    grupo_cultivos: fila.grupo_cultivos,
    organicos: `${t("ayuda.pantalla.organicos", "")}: ${fila.fertilizantes_organicos}`,
    minerales: `${t("ayuda.pantalla.minerales", "")}: ${fila.fertilizantes_inorganicos_o_minerales}`,
  }));

  // Esta pantalla ya está en React (ver `docs/REACT.md`): es de leer, sin ningún campo que rellenar.
  // `montar()` pide el elemento dentro de un `try`: si los ficheros de React de `vendor/` no han
  // llegado, enseña el aviso de emergencia en vez de dejar la pantalla en blanco.
  montar(() =>
    pantallaDeAyuda({
      textos: { pantalla: guia, acciones: t("acciones", {}) },
      ley,
      // Los porqués, **todos y con su nombre**, en el orden del servidor: aquí no se elige ninguno. El
      // título corto lo sirve el servidor aparte (`ayuda.porque_titulos`), porque el mismo porqué se
      // enseña en otras pantallas donde el título no pinta nada (ronda 83).
      porques: Object.entries(porques).map(([clave, texto]) => ({
        titulo: (t("ayuda.porque_titulos", {}) || {})[clave] || "",
        texto,
      })),
      campos,
      reglas,
      aportes,
      periodos,
      limites: faltan,
    }),
  );
}

function pantallaHecho(resultado, tipo) {
  // El nombre del tipo de apunte, que es el título de la tabla: «Tratamiento con producto», «Abonado»…
  //
  // **El nombre de una práctica del campo se busca primero en su propia lista** (ronda 91): un trabajo
  // venía escrito en minúscula y como lo guarda la base de datos («laboreo»), porque el primer sitio
  // donde se buscaba —la lista de tipos de tratamiento— no lo tiene y devolvía el valor tal cual. Aquí
  // se lee «Laboreo», que es como se llama en la pantalla de inicio.
  const queEs =
    nombreDeLaPractica(tipo) || etiquetaDeValor("tipos_tratamiento", tipo) || tipo || "";
  // **Lo que se acaba de apuntar, en su tabla** (diseño de Stitch de la lámina de piezas, ronda 90): la
  // pantalla decía «Apuntado» y nada más, así que el agricultor no podía comprobar que se había entendido lo
  // que él quería apuntar. Las filas se arman aquí, con los datos del apunte que ha devuelto el servidor.
  const apunte = (resultado || {}).datos || {};
  const filas = [];
  if (resultado && resultado.datos) {
    const donde = dondeSeApunto(apunte);
    if (donde) filas.push({ etiqueta: t("cuaderno.tierra_y_parcela", ""), valor: donde });
    if (apunte.fecha) {
      filas.push({ etiqueta: t("etiquetas.comun.fecha.pregunta", ""), valor: formateaFecha(apunte.fecha) });
    }
  }

  // Esta pantalla ya está en React (ver `docs/REACT.md`). No tiene campos que leer del DOM: lo que
  // se enseña son los datos del apunte que se acaba de guardar y los textos del servidor. Se monta
  // con `montar()`, que pide el elemento dentro de un `try` por el mismo motivo que en la pantalla de
  // inicio: si los ficheros de React de `vendor/` no han llegado, enseña el aviso de emergencia en
  // vez de dejar la pantalla en blanco.
  montar(() =>
    pantallaDeHecho({
      textos: {
        aviso: t("aviso", {}),
        mensajes: t("mensajes", {}),
        acciones: t("acciones", {}),
        // Los textos de corregir: esta pantalla también sale después de **corregir** un apunte, y
        // entonces dice «Corregido» y ofrece volver a corregirlo (ronda 91).
        corregir: t("corregir", {}),
      },
      resultado: resultado || {},
      tipo,
      // El nombre de lo que se ha apuntado («Tratamiento con producto», «Abonado»…), que es el título de la
      // tabla de arriba.
      queEs,
      filas,
    }),
  );
}

// ------------------------------------------- pasos del asistente de tratamiento

/**
 * El paso de elegir la tierra, ya en React (es una **pieza**: ver `docs/REACT.md`).
 *
 * Es el primer paso de tres asistentes (echar producto, abonar y hacer un trabajo), así que es la
 * pantalla que más se ve después del resumen. El motor del asistente no se toca: el paso dice
 * `montar` en vez de `pintar` y React llena el hueco del formulario.
 *
 * **Y desde la ronda 82 lleva el buscador** (`docs/stitch/rediseno/mis_tierras.png`: «Buscar entre tus
 * fincas»). David tiene 51 tierras: sin buscador, apuntar dónde ha echado el producto es recorrer una
 * lista de cincuenta y una tarjetas con el pulgar. Se compone con `html` —el buscador y la lista son dos
 * piezas seguidas—, que es lo que ya se hace en los pasos que piden dos cosas a la vez.
 */
function montarParcelas() {
  if (estado.parcelas.length === 0) {
    // El aviso, solo, deja al agricultor sin salida: dice que añada una parcela y no
    // hay dónde. Va con el botón que lo arregla.
    return listaParaElegir({
      aviso: {
        texto: aviso("no_hay_parcelas"),
        boton: {
          etiqueta: t("maestros.anadir_primera_parcela", ""),
          icono: "📍",
          accion: "anadir-maestro",
          datos: { tipo: "parcela" },
          clase: "boton-principal",
        },
      },
    });
  }

  const buscador = campoDeReact(buscadorDeTierras());
  const tierras = tierrasQueCasen(estado.parcelas, estado.filtroTierras);
  if (tierras.length === 0) {
    // Un buscador que no encuentra nada y no dice nada deja al agricultor creyendo que ha perdido sus
    // tierras. Se dice, y se le da el botón para volver a verlas todas: la lista vacía es la única
    // pantalla de este programa que tiene que traer su propia salida.
    return html`
      ${buscador}
      ${listaParaElegir({
        aviso: {
          texto: t("maestros.buscar_sin_nada", ""),
          pista: t("maestros.buscar_sin_nada_pista", ""),
          boton: {
            etiqueta: t("maestros.verlas_todas", ""),
            icono: "🔁",
            accion: "buscar-tierra-limpiar",
            clase: "boton-principal",
          },
        },
      })}
    `;
  }

  return html`
    ${buscador}
    ${listaParaElegir({
      bloques: [bloqueDeParcelas(), bloqueDeGrupos(), bloqueDeOtrosSitios()].filter(Boolean),
    })}
  `;
}

/**
 * El buscador de tierras del paso: su casilla, su pista y sus dos botones.
 *
 * Va con la **pieza del campo** (`piezas/campo.js`), que es la que ya sabe hacer esto: una casilla con su
 * `id` (que es como `app.js` lee lo escrito: **no es decoración**), su etiqueta, su ejemplo y sus atajos
 * de abajo. Escribir una pieza nueva para una casilla con un botón sería tener dos sitios donde se
 * escribe un `<label>`.
 *
 * El `valor` es lo que ya había escrito: al buscar, la pantalla se vuelve a montar y sin esto el
 * agricultor vería su texto borrado, que es la forma más rápida de que no vuelva a usar el buscador.
 */
function buscadorDeTierras() {
  const botones = [{ etiqueta: t("maestros.buscar_boton", ""), accion: "buscar-tierra" }];
  if (estado.filtroTierras) {
    botones.push({ etiqueta: t("maestros.verlas_todas", ""), accion: "buscar-tierra-limpiar" });
  }
  return {
    id: "buscar_tierra",
    etiqueta: t("maestros.buscar_tierra", ""),
    valor: estado.filtroTierras || "",
    placeholder: t("maestros.buscar_tierra_ejemplo", ""),
    sufijo: t("maestros.buscar_tierra_pista", ""),
    botones,
  };
}

/**
 * El mismo buscador, en su pantalla de «mis cosas» (ronda 87).
 *
 * Es la misma casilla con los mismos textos, pero con **su propio `id` y sus propias acciones**: la de
 * «mis cosas» filtra la lista que se mira, la del asistente la lista donde se elige, y cada una se vacía
 * por su cuenta. Compartir el estado haría que buscar en un sitio escondiera tierras en el otro sin que
 * nadie lo hubiera pedido.
 */
function buscadorDeTierrasDeMisCosas() {
  const botones = [{ etiqueta: t("maestros.buscar_boton", ""), accion: "buscar-tierra-mis-cosas" }];
  if (estado.filtroTierrasMisCosas) {
    botones.push({
      etiqueta: t("maestros.verlas_todas", ""),
      accion: "buscar-tierra-limpiar-mis-cosas",
    });
  }
  return {
    id: "buscar_tierra_mis_cosas",
    etiqueta: t("maestros.buscar_tierra", ""),
    valor: estado.filtroTierrasMisCosas || "",
    placeholder: t("maestros.buscar_tierra_ejemplo", ""),
    sufijo: t("maestros.buscar_tierra_pista", ""),
    botones,
  };
}

/**
 * Los grupos de parcelas, para apuntar de una vez lo que se hace en todas.
 *
 * Es lo que la app oficial dice de las unidades homogéneas de cultivo: «tienen como fin facilitar
 * la cumplimentación del Cuaderno». Con seis parcelas de cebada, un tratamiento es **un apunte**.
 *
 * Se ofrecen **después de las parcelas** y antes de la salida de «no es una parcela», por el
 * mismo motivo que aquella: lo normal es tratar una parcela, y quien tiene grupos los ve ahí
 * mismo sin tener que buscarlos.
 */
function bloqueDeGrupos() {
  const grupos = estado.grupos || [];
  if (grupos.length === 0) return null;
  const elegido = estado.asistente.borrador.grupo_id;
  return {
    titulo: t("grupos.en_varias", ""),
    pista: t("grupos.en_varias_pista", ""),
    botones: grupos.map((grupo) => ({
      etiqueta: grupo.nombre,
      pista:
        rellena(t("grupos.cuantas", ""), { cuantas: (grupo.parcela_ids || []).length }) +
        ` · ${formateaNumero(grupo.superficie_total_ha, 2)} ${t("rotulos.hectareas_corto", "")}`,
      icono: "🔗",
      accion: "elegir",
      datos: {
        campo: "grupo_id",
        valor: grupo.id,
        superficie: grupo.superficie_total_ha,
      },
      clase: Number(elegido) === grupo.id ? "boton-elegido" : "boton-claro",
    })),
  };
}

/**
 * Lo que hay que mirar de una tierra, para su tarjeta en el asistente.
 *
 * **Solo se enseña lo que ya se sabe**: la zona de nitratos (comprobada contra la capa oficial o contra
 * la lista de municipios al dar de alta la tierra) y la masa de agua cerca (del SIGPAC). No hay aquí
 * ninguna suposición: si un dato no está, no se dice nada. Un aviso inventado en el momento de elegir la
 * tierra es justo lo que este programa no puede hacer.
 */
function avisosDeLaTierra(parcela) {
  const avisos = [];
  if (parcela.zona_vulnerable_nitratos) avisos.push(t("rotulos.tierra_en_nitratos", ""));
  if (parcela.masa_agua_cerca) avisos.push(t("rotulos.tierra_masa_agua", ""));
  return avisos;
}

/**
 * Lo que se sabe de una tierra y cómo se enseña en su tarjeta: el dibujo, la superficie con su palabra,
 * el pueblo y sus avisos.
 *
 * Está aparte porque la tarjeta de una tierra se usa ya en **dos sitios** (el asistente, donde se elige,
 * y «Mis parcelas, productos y máquinas», donde se mira), y las dos tienen que decir lo mismo de la misma
 * tierra. Dos copias de esto es como se acaba enseñando la superficie en un sitio y no en el otro.
 *
 * La superficie va con su palabra («4,90 hectáreas») juntando **solo** lo que hay: si el servidor no
 * diera la palabra, sale el número sin un espacio colgando.
 */
function formaDeLaTierra(parcela) {
  return {
    dibujo: parcela.dibujo || "",
    lineas: [
      [formateaNumero(parcela.superficie_ha, 2), t("rotulos.unidad_hectareas", "")]
        .filter(Boolean)
        .join(" "),
      parcela.municipio || "",
    ].filter(Boolean),
    avisos: avisosDeLaTierra(parcela),
  };
}

/**
 * Los botones de las tierras, **como tarjetas** y no como filas de texto.
 *
 * POR QUÉ TARJETAS. Con 51 tierras, una lista de filas iguales («El Prado · 4,90 ha · secano») no se
 * distingue de la de al lado, y elegir la tierra equivocada apunta el tratamiento en el sitio que no es
 * —y eso no se nota hasta que alguien mira el cuaderno—. La tarjeta lleva **el dibujo de la forma de la
 * tierra** (que es como el agricultor la reconoce: la ve así en el SIGPAC), su superficie, su pueblo,
 * sus avisos y la palabra «ELEGIDA» en la que acaba de tocar. Sale del rediseño con Stitch
 * (`docs/stitch/rediseno/asistente.png`).
 *
 * Los `data-*` son **los mismos de siempre** (`data-campo`, `data-valor`, `data-superficie`): el
 * manejador de clics es uno solo y vive aquí, y lee esos atributos.
 */
function bloqueDeParcelas() {
  const elegida = estado.asistente.borrador.parcela_id;
  // **Las que se enseñan, no todas**: si el agricultor ha buscado, la lista es lo que ha encontrado
  // (ver `tierrasQueCasen`, en `nucleo.js`, que es donde se puede probar sin navegador).
  return {
    botones: tierrasQueCasen(estado.parcelas, estado.filtroTierras).map((parcela) => ({
      tarjeta: true,
      etiqueta: parcela.alias,
      ...formaDeLaTierra(parcela),
      elegida: Number(elegida) === parcela.id,
      accion: "elegir",
      datos: {
        campo: "parcela_id",
        valor: parcela.id,
        superficie: parcela.superficie_ha,
      },
      textos: { elegida: t("rotulos.elegida", "") },
    })),
  };
}

/**
 * La salida para los dos casos que NO son la tierra.
 *
 * Decisión de usabilidad: se ofrecen aquí, al final de la lista de parcelas, y no como
 * una pantalla previa. Nueve de cada diez veces el producto se echa en una parcela, y
 * hacer pasar a todo el mundo por una pregunta que casi nunca aplica es justo lo que
 * la guía de interfaz prohíbe. Quien trata una nave, lo ve aquí abajo.
 */
function bloqueDeOtrosSitios() {
  return {
    titulo: t("etiquetas.tratamiento.no_es_parcela.pregunta", ""),
    pista: t("etiquetas.tratamiento.no_es_parcela.pista", ""),
    botones: (t("tipos_tratamiento", []) || [])
      .filter((tipo) => tipo.valor === "instalaciones" || tipo.valor === "postcosecha")
      .map((tipo) => ({
        etiqueta: tipo.texto,
        accion: "tipo-tratamiento",
        datos: { tipo: tipo.valor },
        clase: "boton-claro",
      })),
  };
}

/** ¿Lo que se está apuntando es en una nave o al producto ya recogido? */
function esEnInstalacion() {
  const tipo = estado.asistente ? estado.asistente.borrador.tipo : null;
  return tipo === "instalaciones" || tipo === "postcosecha";
}

/** Elegir la nave o el almacén donde se ha echado el producto. Ya en React. */
function montarInstalaciones() {
  const b = estado.asistente.borrador;
  if (estado.instalaciones.length === 0) {
    // Igual que con las parcelas: el aviso va con el botón que lo arregla.
    return listaParaElegir({
      aviso: {
        texto: aviso("no_hay_instalaciones"),
        boton: {
          etiqueta: t("maestros.anadir_instalacion", ""),
          icono: "🏠",
          accion: "anadir-maestro",
          datos: { tipo: "instalacion" },
          clase: "boton-principal",
        },
      },
    });
  }
  return listaParaElegir({
    bloques: [
      {
        botones: estado.instalaciones.map((instalacion) => ({
          etiqueta: instalacion.alias,
          pista: etiquetaDeValor("tipos_instalacion", instalacion.tipo),
          icono: "🏠",
          accion: "elegir",
          datos: { campo: "instalacion_id", valor: instalacion.id },
          clase: Number(b.instalacion_id) === instalacion.id ? "boton-elegido" : "boton-claro",
        })),
      },
    ],
  });
}

/** Los detalles que solo se piden cuando el producto se aplica fuera de la tierra. */
function detallesDeSitio() {
  const b = estado.asistente.borrador;
  const campos = [];
  if (esEnInstalacion()) {
    campos.push("tratamiento.plazo_reentrada_dias");
  }
  if (b.tipo === "postcosecha") {
    campos.push("tratamiento.producto_cosechado", "tratamiento.lote_cosecha");
  }
  return campos;
}

/**
 * El paso de los detalles del sitio, ya en React: el plazo de reentrada de una nave y, si el producto
 * se echó sobre lo ya recogido, de qué producto y de qué partida era.
 *
 * Se pintan con la pieza de los grupos de campos, que es la misma que usan las fichas del maestro: al
 * final es lo mismo, unos datos seguidos, cada uno con su pregunta.
 */
function montarDetallesDeSitio() {
  return camposDelMaestro({ bloques: bloquesDelMaestro(detallesDeSitio()) });
}


/**
 * Un paso de elegir una opción de una lista corta, ya en React.
 *
 * Es el hermano pequeño de `montarParcelas`: aquí la lista no viene de los datos de la finca sino del
 * vocabulario del servidor (los motivos por los que se echó el producto, las clases de análisis), y la
 * opción **es** el valor que se guarda. Lo que se lee en el botón es lo mismo que se apunta.
 */
function montarOpciones(campo, opciones, ayudaClave) {
  const elegido = estado.asistente.borrador[campo];
  return listaParaElegir({
    bloques: [
      {
        botones: opciones.map((opcion) => ({
          etiqueta: opcion,
          accion: "elegir",
          datos: { campo, valor: opcion },
          clase: elegido === opcion ? "boton-elegido" : "boton-claro",
        })),
      },
    ],
    ayuda: ayudaClave ? datosDeLaAyuda(ayudaClave) : null,
  });
}

/** Elegir el producto que se ha echado. Ya en React. */
function montarProductos() {
  if (estado.productos.length === 0) {
    return listaParaElegir({
      aviso: {
        texto: aviso("no_hay_productos"),
        boton: {
          etiqueta: t("maestros.anadir_producto", ""),
          icono: "🧴",
          accion: "anadir-maestro",
          datos: { tipo: "producto" },
          clase: "boton-principal",
        },
      },
    });
  }
  return listaParaElegir({
    bloques: [
      {
        botones: estado.productos.map((producto) => ({
          etiqueta: producto.nombre_comercial,
          pista: [
            producto.numero_registro
              ? `${t("rotulos.etiqueta_numero", "")} ${producto.numero_registro}`
              : "",
            producto.plazo_seguridad_dias !== null && producto.plazo_seguridad_dias !== undefined
              ? `${producto.plazo_seguridad_dias} ${t("rotulos.dias_espera_corto", "")}`
              : "",
          ]
            .filter(Boolean)
            .join(" · "),
          icono: "🧴",
          accion: "elegir",
          datos: { campo: "producto_id", valor: producto.id },
          clase:
            Number(estado.asistente.borrador.producto_id) === producto.id
              ? "boton-elegido"
              : "boton-claro",
        })),
      },
    ],
  });
}

/** Elegir el abono que se ha echado. Ya en React, con la misma pieza que las demás listas. */
function montarAbonos() {
  if (estado.abonos.length === 0) {
    return listaParaElegir({
      aviso: {
        texto: aviso("no_hay_abonos"),
        boton: {
          etiqueta: t("maestros.anadir_abono", ""),
          icono: "🟤",
          accion: "anadir-maestro",
          datos: { tipo: "abono" },
          clase: "boton-principal",
        },
      },
    });
  }
  return listaParaElegir({
    bloques: [
      {
        botones: estado.abonos.map((abono) => ({
          etiqueta: abono.nombre,
          // La riqueza del abono (nitrógeno-fósforo-potasio), que es lo que el agricultor reconoce
          // de un vistazo: dos abonos de la misma casa se distinguen por estos tres números. Y cuando no
          // consta la composición lo dice con palabras: `null-null-null` no es una respuesta (A6).
          pista: composicionDelAbono(abono),
          icono: "🟤",
          accion: "elegir",
          datos: { campo: "fertilizante_id", valor: abono.id },
          clase:
            Number(estado.asistente.borrador.fertilizante_id) === abono.id
              ? "boton-elegido"
              : "boton-claro",
        })),
      },
    ],
  });
}

/**
 * El paso de la fecha, ya en React (una **pieza**: ver `docs/REACT.md`).
 *
 * **Y sigue apuntando la fecha en el borrador al pintarse**, que es lo que hacía `pintaFecha`: si el
 * agricultor no toca nada, la fecha del apunte es hoy. Eso no es un adorno — es lo que hace que
 * apuntar lo de hoy sean dos toques— y por eso se queda aquí, en el lado que conoce el borrador, y no
 * dentro del componente (que es puro y no sabe de fechas).
 */
function elementoDeFecha(campo = "fecha", ayudaClave = "tratamiento.fecha") {
  const valor = estado.asistente.borrador[campo] || hoyISO();
  estado.asistente.borrador[campo] = valor;
  return campoDeReact({
    id: campo,
    // La fecha se lee de dos formas: «10/04/2026» y «viernes, 10 de abril». La frase compuesta se
    // monta **aquí**, que es quien conoce la fecha: un componente no une dos textos del servidor.
    etiqueta: `${formateaFecha(valor)} — ${fechaEnPalabras(valor)}`,
    tipo: "fecha",
    valor,
    ayuda: datosDeLaAyuda(ayudaClave),
    // Los dos atajos de debajo: son los que hacen que apuntar lo de hoy (o lo de ayer) sean dos
    // toques, y por eso van pegados al campo.
    botones: [
      { etiqueta: accion("hoy"), accion: "fecha-rapida", datos: { campo, valor: hoyISO() } },
      { etiqueta: accion("ayer"), accion: "fecha-rapida", datos: { campo, valor: ayerISO() } },
    ],
  });
}

/** El paso de la fecha, ya en React (el elemento lo monta `elementoDeFecha`, ver arriba). */
function montarFecha(campo = "fecha", ayudaClave = "tratamiento.fecha") {
  return elementoDeFecha(campo, ayudaClave);
}

/**
 * El paso de un número, ya en React: las hectáreas, la dosis, los kilos por hectárea.
 *
 * `sufijo` es la pista de debajo (la unidad) y `etiquetaClave` de dónde sale la pregunta; los dos
 * vienen del servidor. Se aceptan vacíos: hay campos que solo llevan una cosa de las dos.
 */
function montarNumero(campo, sufijo, etiquetaClave, ayudaClave) {
  return campoDeReact({
    id: campo,
    etiqueta: etiquetaClave ? t(`etiquetas.${etiquetaClave}.pregunta`, "") : "",
    tipo: "numero",
    valor: estado.asistente.borrador[campo] || "",
    sufijo: sufijo || "",
    ayuda: ayudaClave ? datosDeLaAyuda(ayudaClave) : null,
  });
}

/**
 * Quién echó el producto y con qué máquina, ya en React.
 *
 * Los dos títulos salen **siempre**, aunque no haya ninguno dado de alta: es lo que hacía la interfaz de
 * siempre, y sirve para que el agricultor sepa que ese dato existe aunque todavía no lo tenga apuntado
 * (se dan de alta en «mis cosas»).
 */
function montarQuienYMaquina() {
  const b = estado.asistente.borrador;
  return listaParaElegir({
    bloques: [
      {
        titulo: t("etiquetas.tratamiento.aplicador_id", "").pregunta || "",
        botones: estado.aplicadores.map((a) => ({
          etiqueta: a.nombre,
          accion: "elegir",
          datos: { campo: "aplicador_id", valor: a.id },
          clase: Number(b.aplicador_id) === a.id ? "boton-elegido" : "boton-claro",
        })),
      },
      {
        titulo: t("etiquetas.tratamiento.equipo_id", "").pregunta || "",
        botones: estado.equipos.map((e) => ({
          etiqueta: e.nombre,
          // La fecha de la próxima ITV, cuando el papel la trae: es lo que avisa de que la máquina
          // puede estar sin pasar la inspección, y con eso no se puede tratar.
          pista: e.fecha_proxima_iteaf
            ? `${t("rotulos.itv_hasta", "")} ${formateaFecha(e.fecha_proxima_iteaf)}`
            : "",
          accion: "elegir",
          datos: { campo: "equipo_id", valor: e.id },
          clase: Number(b.equipo_id) === e.id ? "boton-elegido" : "boton-claro",
        })),
      },
    ],
    ayuda: datosDeLaAyuda("tratamiento.equipo_id"),
  });
}

/**
 * Un solo campo de escribir, ya en React: una casilla de texto, un número o un párrafo.
 *
 * Es para los pasos que solo piden una cosa: las observaciones de un apunte, los detalles de una labor,
 * cuánto se ha recogido. **La etiqueta puede venir vacía** y entonces no se pinta ninguna: en esos pasos
 * la pregunta ya es el título de la pantalla, y repetirla dos veces no ayuda a nadie (es lo que hacía la
 * interfaz de siempre). El párrafo es lo normal aquí porque suele ser texto libre; los números y las
 * cantidades piden `tipo: "numero"`, que es lo que hace salir el teclado de números con coma en el móvil.
 */
function montarTexto({ id, etiqueta = "", sufijo = "", tipo = "area", ayuda = null }) {
  return campoDeReact({
    id,
    etiqueta,
    tipo,
    valor: estado.asistente.borrador[id] || "",
    sufijo,
    ayuda,
  });
}

/**
 * Los datos del resumen del asistente, ya preparados para el componente.
 *
 * **Lo que NO hace esto:** pintar. Devuelve las filas —y **solo las que tienen dato**, porque un
 * resumen con cinco «—» no ayuda a repasar— y el aviso del plazo de espera. Quien pinta es
 * `react/piezas/resumen_del_apunte.js`.
 */
function datosDelResumen(carga, opciones = {}) {
  const parcela = estado.parcelas.find((p) => p.id === Number(carga.parcela_id));
  const producto = estado.productos.find((p) => p.id === Number(carga.producto_id));
  const abono = estado.abonos.find((a) => a.id === Number(carga.fertilizante_id));
  const filas = [];

  filas.push([t("etiquetas.comun.parcela_id.pregunta", ""), parcela ? parcela.alias : ""]);
  filas.push([t("etiquetas.comun.fecha.pregunta", ""), formateaFecha(carga.fecha)]);
  // La hora: se enseña junto a la fecha porque es parte de lo mismo, «cuándo».
  if (carga.hora_inicio) {
    filas.push([
      t("etiquetas.tratamiento.hora_inicio.pregunta", ""),
      carga.hora_fin ? `${carga.hora_inicio} – ${carga.hora_fin}` : carga.hora_inicio,
    ]);
  }
  if (carga.estado_cultivo) {
    filas.push([t("etiquetas.tratamiento.estado_cultivo.pregunta", ""), carga.estado_cultivo]);
  }
  // El tipo de labor, con su nombre. Sin esto, una labor se resumía solo con la parcela y la
  // fecha, y el agricultor no podía ver si había apuntado un laboreo o un pastoreo.
  if (carga.tipo && carga.tipo !== "otra") {
    const etiquetas = t("etiquetas_labor", {}) || {};
    if (etiquetas[carga.tipo]) filas.push([t("rotulos.trabajo", ""), etiquetas[carga.tipo]]);
  }
  if (producto) filas.push([t("rotulos.producto", ""), producto.nombre_comercial]);
  if (abono) {
    filas.push([
      t("rotulos.abono", ""),
      `${abono.nombre} (${composicionDelAbono(abono)})`,
    ]);
  }
  if (carga.superficie_tratada_ha !== undefined && carga.superficie_tratada_ha !== null) {
    filas.push([t("rotulos.hectareas", ""), formateaNumero(carga.superficie_tratada_ha, 2)]);
  }
  if (carga.superficie_ha !== undefined && carga.superficie_ha !== null) {
    filas.push([t("rotulos.hectareas", ""), formateaNumero(carga.superficie_ha, 2)]);
  }
  if (carga.kg_ha_producto) {
    filas.push([t("rotulos.kilos_por_hectarea", ""), formateaNumero(carga.kg_ha_producto, 1)]);
  }
  if (carga.dosis) {
    filas.push([
      t("rotulos.por_hectarea", ""),
      `${formateaNumero(carga.dosis, 2)} ${carga.unidad_dosis || ""}`,
    ]);
  }
  if (carga.justificacion) filas.push([t("rotulos.por_que", ""), carga.justificacion]);
  if (carga.medidas && carga.medidas.length) {
    // Se enseña en el resumen porque es lo que demuestra que se miraron otras opciones
    // antes de tratar, y porque si sale mal se puede volver atrás y corregirlo.
    filas.push([
      t("medidas.en_el_apunte", ""),
      carga.medidas.map((codigo) => nombreDeMedida(codigo)).join(" · "),
    ]);
  }
  if (carga.cantidad_kg) {
    filas.push([t("rotulos.recogido", ""), `${formateaNumero(carga.cantidad_kg, 1)} kg`]);
  }
  // Cómo estaba el día, si lo ha apuntado. Va al final porque es lo accesorio, y solo sale si
  // hay algo: un resumen con cinco «—» no ayuda a repasar antes de guardar.
  const tiempo = [
    carga.temperatura_c !== null && carga.temperatura_c !== undefined
      ? `${formateaNumero(carga.temperatura_c, 1)} °C`
      : "",
    carga.viento_kmh !== null && carga.viento_kmh !== undefined
      ? `${formateaNumero(carga.viento_kmh, 0)} km/h ${carga.viento_direccion || ""}`.trim()
      : "",
    carga.humedad_pct !== null && carga.humedad_pct !== undefined
      ? `${formateaNumero(carga.humedad_pct, 0)} %`
      : "",
  ].filter(Boolean);
  if (tiempo.length) {
    filas.push([t("etiquetas.tratamiento.como_estaba_el_dia.pregunta", ""), tiempo.join(" · ")]);
  }

  // El plazo de espera: es lo que evita que el agricultor coja la cosecha antes de tiempo.
  const espera = opciones.finDeEspera;
  let avisoDeEspera = null;
  if (espera && espera.plazo !== null && espera.plazo !== undefined && espera.fecha) {
    const dias = diasDeEspera(espera.fecha, espera.plazo, hoyISO());
    const desde = formateaFecha(
      (() => {
        const d = new Date(`${espera.fecha}T00:00:00`);
        d.setDate(d.getDate() + Number(espera.plazo));
        return iso(d);
      })(),
    );
    avisoDeEspera = {
      texto: rellena(t("mensajes.V8_dias_de_espera", ""), { fin: desde }),
      dias: dias !== null ? rellena(t("mensajes.V8_cuantos_dias_faltan", ""), { dias }) : "",
    };
  }

  return { filas, espera: avisoDeEspera };
}

/**
 * El resumen del asistente, ya en React (ver `docs/REACT.md`).
 *
 * **Es la primera pieza del asistente que se migra**, y se hace así: el paso dice `montar` en vez de
 * `pintar`, y React llena el hueco del formulario. El motor del asistente no se toca.
 */
function montarResumenDelApunte(carga, opciones = {}) {
  const datos = datosDelResumen(carga, opciones);
  return resumenDelApunte({ filas: datos.filas, espera: datos.espera });
}
// ------------------------------------------------------- cargas (lo que se manda)

function cargaTratamiento() {
  const b = estado.asistente.borrador;
  const producto = estado.productos.find((p) => p.id === Number(b.producto_id));
  const parcela = estado.parcelas.find((p) => p.id === Number(b.parcela_id));
  const enInstalacion = b.tipo === "instalaciones" || b.tipo === "postcosecha";
  return {
    campana_id: estado.campana.id,
    fecha: b.fecha,
    tipo: b.tipo || "parcela",
    // Solo se manda el sitio que corresponde: si es en una nave, no se manda parcela. Y si es en
    // un grupo de parcelas, se manda el grupo y no una parcela suelta.
    parcela_id: enInstalacion ? null : Number(b.parcela_id) || null,
    grupo_id: enInstalacion || !b.grupo_id ? null : Number(b.grupo_id),
    instalacion_id: enInstalacion ? Number(b.instalacion_id) || null : null,
    producto_cosechado: b.producto_cosechado || null,
    lote_cosecha: b.lote_cosecha || null,
    plazo_reentrada_dias: aNumero(b.plazo_reentrada_dias),
    // **En una nave no hay hectáreas, y se manda a nulo, no a cero** (ronda 91). Un cero no vale: la
    // API pide que la superficie sea mayor que cero cuando se manda, porque «0 ha» no es un dato sino
    // un hueco. Mandarlo hacía que un tratamiento de una nave (o del grano ya recogido) **no se pudiera
    // guardar** desde la aplicación: el servidor contestaba un error de superficie. Lo encontró la
    // prueba de humo al añadirle la corrección de un apunte, que es cuando se mandan los datos que ya
    // estaban guardados —y el de una nave tiene cero hectáreas—.
    superficie_tratada_ha: enInstalacion
      ? null
      : aNumero(b.superficie_tratada_ha) ?? (parcela ? parcela.superficie_ha : 0),
    justificacion: b.justificacion,
    plaga: b.plaga || null,
    producto_id: Number(b.producto_id),
    dosis: aNumero(b.dosis),
    unidad_dosis: (producto && producto.unidad_dosis) || "L/ha",
    // ── Lo que el asistente no pregunta, pero el apunte puede tener ──
    //
    // Estos campos no los pregunta ninguna pantalla, así que en un apunte nuevo van a nulo y el
    // servidor los rellena como siempre (el cultivo, del que el agricultor ya declaró en la tierra;
    // el lote, de la ficha del producto). Pero **se mandan tal cual venían cuando se está
    // corrigiendo**: sin esto, corregir la dosis de un tratamiento borraría el asesoramiento, la
    // variedad o el lote sin que nadie se enterara. Un dato que el formulario no enseña no puede
    // desaparecer porque se pase por él.
    cultivo: b.cultivo || null,
    variedad: b.variedad || null,
    lote_producto: b.lote_producto || null,
    asesor_id: b.asesor_id ?? null,
    asesor_fecha: b.asesor_fecha || null,
    asesoramiento_validado: b.asesoramiento_validado ?? null,
    asesoramiento_contrato: b.asesoramiento_contrato ?? null,
    aplicador_id: b.aplicador_id ? Number(b.aplicador_id) : null,
    equipo_id: b.equipo_id ? Number(b.equipo_id) : null,
    // Lo que se hizo antes de decidir echar el producto. Sale marcado de lo que el
    // agricultor declaró que hace en su finca; ver `pintaMedidasDelTratamiento`.
    medidas: Array.isArray(b.medidas) ? b.medidas : medidasAplicadasDeLaFinca(),
    observaciones: b.observaciones || null,
    // Cómo se echó: la hora, cómo estaba la planta y cómo estaba el día. Si el agricultor se
    // salta la pantalla, van a nulo y el cuaderno no dice nada — que es distinto de decir que
    // hizo buen tiempo.
    hora_inicio: b.hora_inicio || null,
    hora_fin: b.hora_fin || null,
    estado_cultivo: b.estado_cultivo || null,
    temperatura_c: b.temperatura_c ?? null,
    humedad_pct: b.humedad_pct ?? null,
    viento_kmh: b.viento_kmh ?? null,
    viento_direccion: b.viento_direccion || null,
    volumen_caldo_l_ha: b.volumen_caldo_l_ha ?? null,
    operadores_expuestos: b.operadores_expuestos ?? null,
    incidencias: b.incidencias || null,
    franja_seguridad_respetada:
      b.franja_seguridad_respetada === undefined ? null : b.franja_seguridad_respetada,
    // Estas dos las pide el interfaz de la Junta como obligatorias y el cuaderno no las
    // preguntaba. Se mandan a nulo si no se contestan: «no lo sé» no es «no».
    aplicado_a_mano: b.aplicado_a_mano === undefined ? null : b.aplicado_a_mano,
    eficacia: b.eficacia || null,
    unidad_cantidad_aplicada: b.unidad_cantidad_aplicada || null,
  };
}

function cargaFertilizacion() {
  const b = estado.asistente.borrador;
  const parcela = estado.parcelas.find((p) => p.id === Number(b.parcela_id));
  return {
    campana_id: estado.campana.id,
    fecha: b.fecha,
    parcela_id: Number(b.parcela_id) || null,
    grupo_id: b.grupo_id ? Number(b.grupo_id) : null,
    superficie_ha: aNumero(b.superficie_ha) ?? (parcela ? parcela.superficie_ha : 0),
    fertilizante_id: Number(b.fertilizante_id),
    kg_ha_producto: aNumero(b.kg_ha_producto),
    observaciones: b.observaciones || null,
    // Lo mismo que en los tratamientos: lo que el asistente no pregunta se manda tal cual venía.
    // Estos seis campos son de la hoja 6 del cuaderno de la Junta (el nº de albarán, el tipo de
    // abonado, el modo y el momento) y hoy no hay ninguna pantalla que los rellene, pero un abono
    // que los tenga apuntados no los puede perder por corregir los kilos.
    modo_aplicacion: b.modo_aplicacion || null,
    momento: b.momento || null,
    plan_id: b.plan_id ?? null,
    numero_albaran: b.numero_albaran || null,
    tipo_fertilizacion: b.tipo_fertilizacion || null,
    factura_id: b.factura_id ?? null,
    nitratos_agua_riego: aNumero(b.nitratos_agua_riego),
  };
}

function cargaLabor(tipo) {
  const b = estado.asistente.borrador;
  const parcela = estado.parcelas.find((p) => p.id === Number(b.parcela_id));
  // Cuando se ha entrado por «OTRO TRABAJO», lo que se guarda es la práctica que ha elegido el
  // agricultor (cubierta, pastoreo, poda…), no la palabra «otra». Si no se elige ninguna, se
  // queda «otra», que es lo que había antes: un cajón, pero un cajón honesto.
  const tipoDeVerdad = tipo === "otra" && b.tipo ? b.tipo : tipo;
  if (tipo === "cosecha") {
    return {
      campana_id: estado.campana.id,
      fecha: b.fecha,
      parcela_id: Number(b.parcela_id),
      // Qué se cosechó. Va dentro de `detalles` en la base de datos, y sin mandarlo aquí una
      // cosecha corregida se quedaba sin decir de qué era (el campo se guardaba y se perdía al
      // corregir).
      producto: b.producto || null,
      cantidad_kg: aNumero(b.cantidad_kg),
      semillas_siembra: b.semillas_siembra === undefined ? null : b.semillas_siembra,
      plantas_cosechadas: b.plantas_cosechadas === undefined ? null : b.plantas_cosechadas,
      sin_cosechar_ambiental: b.sin_cosechar_ambiental === undefined ? null : b.sin_cosechar_ambiental,
      restos_cosecha_depositados: b.restos_cosecha_depositados === undefined ? null : b.restos_cosecha_depositados,
      // Con qué máquina se cosechó. El contenido mínimo pide la maquinaria en las labores, y
      // cosechar se cosecha con una máquina.
      equipo_id: b.equipo_id ? Number(b.equipo_id) : null,
    };
  }
  const base = {
    campana_id: estado.campana.id,
    tipo: tipoDeVerdad,
    fecha: b.fecha,
    parcela_id: Number(b.parcela_id) || null,
    grupo_id: b.grupo_id ? Number(b.grupo_id) : null,
    superficie_ha: aNumero(b.superficie_ha) ?? (parcela ? parcela.superficie_ha : 0),
    detalles: b.detalles ? { nota: b.detalles } : null,
    observaciones: b.observaciones || null,
    // El cultivo y la variedad: el asistente no los pregunta (el cultivo lo rellena el servidor con
    // lo que el agricultor ya declaró en la tierra), pero si el apunte los traía, se devuelven.
    cultivo: b.cultivo || null,
    variedad: b.variedad || null,
    // Lo de la siembra y lo del riego. Van siempre: los que no apliquen vienen vacíos y la
    // base de datos los guarda como «no lo sé», que es distinto de cero.
    cantidad_semilla_kg: aNumero(b.cantidad_semilla_kg),
    dosis_siembra_kg_ha: aNumero(b.dosis_siembra_kg_ha),
    lote_semilla: b.lote_semilla || null,
    material_tratado: b.material_tratado === undefined ? null : b.material_tratado,
    tratamiento_semilla: b.tratamiento_semilla || null,
    fecha_tratamiento_semilla: b.fecha_tratamiento_semilla || null,
    eficacia_tratamiento_semilla: b.eficacia_tratamiento_semilla || null,
    material_adquirido: b.material_adquirido === undefined ? null : b.material_adquirido,
    fecha_adquisicion: b.fecha_adquisicion || null,
    siembra_directa: b.siembra_directa === undefined ? null : b.siembra_directa,
    densidad_plantacion: aNumero(b.densidad_plantacion),
    marco_plantacion: b.marco_plantacion || null,
    volumen_agua: aNumero(b.volumen_agua),
    unidad_agua: b.unidad_agua || null,
    origen_agua: b.origen_agua || null,
    sistema_riego: b.sistema_riego || null,
    numero_contador: b.numero_contador || null,
    nitratos_agua: aNumero(b.nitratos_agua),
    fecha_establecimiento_cubierta: b.fecha_establecimiento_cubierta || null,
    tipo_cobertura: b.tipo_cobertura || null,
    anchura_cubierta_m: aNumero(b.anchura_cubierta_m),
    anchura_libre_proyeccion_m: aNumero(b.anchura_libre_proyeccion_m),
    restos_desbroce_depositados: b.restos_desbroce_depositados === undefined ? null : b.restos_desbroce_depositados,
    restos_poda_depositados: b.restos_poda_depositados === undefined ? null : b.restos_poda_depositados,
    // El pastoreo. El interfaz de la Junta pide estas dos como obligatorias y el cuaderno no las
    // preguntaba: sin ellas no se puede armar el bloque del pastoreo.
    animales_terceros: b.animales_terceros === undefined ? null : b.animales_terceros,
    animales_propios: b.animales_propios === undefined ? null : b.animales_propios,
    // Con qué máquina se hizo. Va también en la cosecha, porque cosechar se cosecha con una
    // máquina, y el contenido mínimo pide la maquinaria en las labores.
    equipo_id: b.equipo_id ? Number(b.equipo_id) : null,
  };
  return base;
}

/** El paso que recoge lo que se ha escrito en los campos del formulario. */
function recogeCampos(campos) {
  return () => {
    for (const campo of campos) {
      const elemento = document.getElementById(campo);
      if (elemento) {
        estado.asistente.borrador[campo] = elemento.value;
      }
    }
    return null;
  };
}

/** Comprueba que lo obligatorio está puesto, antes de seguir. */
function exige(campo, obligatorio = true) {
  const valor = estado.asistente.borrador[campo];
  if (!obligatorio) return null;
  const codigo = validaPaso(campo, valor);
  return codigo ? mensaje(codigo) : null;
}

/**
 * «¿Dónde?»: vale una tierra **o un grupo de tierras**.
 *
 * El grupo es el atajo que pide el documento oficial de la Junta —las «unidades homogéneas de
 * cultivo»—: con seis parcelas de cebada, un tratamiento es **un apunte**, no seis.
 *
 * **Y aquí estaba el fallo.** Al elegir un grupo se borra la parcela (un apunte es de una tierra o de
 * un grupo, nunca de las dos) y el paso seguía exigiendo la parcela: el agricultor se quedaba
 * encerrado con un aviso de que le faltaba justo lo que acababa de sustituir, y no había forma de
 * seguir. Se arregla aquí y no en el paso, porque los cuatro asistentes que preguntan dónde (echar
 * producto, abonar, hacer un trabajo y el plan de abono) tienen el mismo problema.
 *
 * Lo tapaba una prueba que leía la superficie del grupo **en la propia lista** (el «10,00 ha» del
 * botón) y creía estar leyendo el resumen del apunte: pasaba sin haber llegado nunca al resumen. Se
 * vio al reescribirla contra la pieza de React.
 */
function exigeSitio() {
  if (estado.asistente.borrador.grupo_id) return null;
  return exige("parcela_id");
}

// -------------------------------------------------------- asistentes concretos

function pasosTratamiento() {
  return [
    {
      titulo: t("etiquetas.comun.parcela_id.pregunta", ""),
      pista: t("etiquetas.comun.parcela_id.pista", ""),
      montar: montarParcelas,
      recoger: () => {
        // Si ha dicho que no es en una parcela, aquí no hay nada que exigir: el sitio se
        // elige en la pantalla siguiente. Y si ha elegido un grupo de tierras, ya ha dicho
        // dónde: exigirle además la parcela lo dejaría encerrado (ver `exigeSitio`).
        if (esEnInstalacion()) return null;
        return exigeSitio();
      },
    },
    {
      // Solo sale cuando el producto NO se echa en la tierra: entonces hay que elegir la
      // nave. En el caso normal (nueve de cada diez veces) este paso se salta y se
      // pregunta directamente la fecha, como siempre.
      titulo: t("etiquetas.tratamiento.instalacion_id.pregunta", ""),
      pista: t("etiquetas.tratamiento.instalacion_id.pista", ""),
      cuando: () => esEnInstalacion(),
      montar: montarInstalaciones,
      recoger: () => {
        const codigo = validaPaso("instalacion_id", estado.asistente.borrador.instalacion_id);
        return codigo ? mensaje(codigo) : null;
      },
    },
    {
      titulo: t("etiquetas.comun.fecha.pregunta", ""),
      pista: t("etiquetas.comun.fecha.pista", ""),
      montar: montarFecha,
      recoger: recogeCampos(["fecha"]),
    },
    {
      titulo: t("etiquetas.tratamiento.superficie.pregunta", ""),
      pista: t("etiquetas.tratamiento.superficie.pista", ""),
      montar: () =>
        montarNumero(
          "superficie_tratada_ha",
          t("rotulos.unidad_hectareas", ""),
          "tratamiento.superficie",
          "tratamiento.superficie_tratada_ha",
        ),
      recoger: () => {
        recogeCampos(["superficie_tratada_ha"])();
        const b = estado.asistente.borrador;
        const parcela = estado.parcelas.find((p) => p.id === Number(b.parcela_id));
        if (!parcela) return null;
        const codigo = validaSuperficie(b.superficie_tratada_ha, parcela.superficie_ha);
        return codigo
          ? mensaje(codigo, {
              parcela: formateaNumero(parcela.superficie_ha, 2),
              usada: formateaNumero(aNumero(b.superficie_tratada_ha) || 0, 2),
            })
          : null;
      },
    },
    {
      titulo: t("etiquetas.tratamiento.justificacion.pregunta", ""),
      pista: t("etiquetas.tratamiento.justificacion.pista", ""),
      montar: () => montarOpciones("justificacion", t("justificaciones", []), "tratamiento.justificacion"),
      recoger: () => exige("justificacion"),
    },
    {
      titulo: t("etiquetas.tratamiento.producto_id.pregunta", ""),
      pista: t("etiquetas.tratamiento.producto_id.pista", ""),
      montar: montarProductos,
      recoger: () => exige("producto_id"),
    },
    {
      titulo: t("etiquetas.tratamiento.dosis.pregunta", ""),
      pista: t("etiquetas.tratamiento.dosis.pista", ""),
      montar: () =>
        montarNumero("dosis", t("unidades", []).join(" / "), "tratamiento.dosis", "tratamiento.dosis"),
      recoger: recogeCampos(["dosis"]),
    },
    {
      titulo: t("etiquetas.tratamiento.quien_maquina.pregunta", ""),
      pista: t("etiquetas.tratamiento.quien_maquina.pista", ""),
      opcional: true,
      montar: montarQuienYMaquina,
    },
    {
      // Las medidas preventivas: lo que se hizo ANTES de decidir echar el producto.
      //
      // Va después de quién y con qué máquina, y no antes, por dos motivos: son los
      // opcionales los que van juntos al final (regla de la guía), y porque la pregunta
      // se contesta sola —lo declarado en la finca ya viene marcado— así que no puede
      // estorbar en medio del recorrido obligatorio.
      titulo: t("medidas.pregunta_en_el_tratamiento", ""),
      pista: t("medidas.pista_en_el_tratamiento", ""),
      opcional: true,
      montar: montarMedidasDelTratamiento,
      recoger: () => {
        const b = estado.asistente.borrador;
        if (!Array.isArray(b.medidas)) b.medidas = medidasAplicadasDeLaFinca();
        return null;
      },
    },
    {
      // Solo sale cuando el producto se aplica fuera de la tierra: la nave pide el plazo
      // de reentrada, y el producto ya recogido pide de qué partida era.
      titulo: () => t("etiquetas.tratamiento.tipo.pregunta", ""),
      pista: () => "",
      opcional: true,
      cuando: () => esEnInstalacion(),
      montar: montarDetallesDeSitio,
      recoger: () => {
        recogeCampos(["plazo_reentrada_dias", "producto_cosechado", "lote_cosecha"])();
        return null;
      },
    },
    {
      titulo: t("etiquetas.tratamiento.observaciones.pregunta", ""),
      pista: t("etiquetas.tratamiento.observaciones.pista", ""),
      opcional: true,
      montar: () => montarTexto({ id: "observaciones" }),
      recoger: recogeCampos(["observaciones"]),
    },
    {
      // Una sola pantalla opcional para «cómo se echó». Se salta con un toque.
      titulo: t("etiquetas.tratamiento.como_fue.pregunta", ""),
      pista: t("etiquetas.tratamiento.como_fue.pista", ""),
      opcional: true,
      montar: montarComoFueElTratamiento,
      recoger: recogeComoFueElTratamiento(),
    },
    {
      titulo: t("etiquetas.tratamiento.resumen.pregunta", ""),
      pista: t("etiquetas.tratamiento.resumen.pista", ""),
      montar: () =>
        montarResumenDelApunte(cargaTratamiento(), {
          finDeEspera: {
            fecha: estado.asistente.borrador.fecha,
            plazo: (estado.productos.find(
              (p) => p.id === Number(estado.asistente.borrador.producto_id),
            ) || {}).plazo_seguridad_dias,
          },
        }),
    },
  ];
}

/**
 * Cómo se echó el producto: la hora, cómo estaba la planta y cómo estaba el día.
 *
 * **Una sola pantalla para todo, y opcional, a propósito.** Son once campos que llevaban desde
 * el principio en la base de datos y no llegaban a ninguna pantalla. Lo natural sería hacer
 * tres preguntas, pero el asistente del tratamiento es el que más se usa: tres pantallas más
 * que hay que saltar cada vez es un precio que no vale la pena.
 *
 * Así que van agrupados, con las tres partes separadas por su título, y se saltan con **un solo
 * toque** en SEGUIR. El que tiene prisa apunta el tratamiento y sigue; el que quiere dejar el
 * cuaderno completo —o el que tuvo un problema con un vecino por el viento— lo tiene ahí.
 */
/**
 * «Cómo se echó»: la pantalla larga del tratamiento, ya en React.
 *
 * Es el paso con más cosas de todo el asistente y está hecho de **secciones**: la hora, el estado del
 * cultivo, cómo estaba el día y lo que quedó por apuntar. Cada sección lleva su encabezado (el `titulo`
 * del bloque, que es lo que pinta el `<h2>`) y sus campos, y los cuatro datos de la franja de seguridad
 * se piden con las mismas claves del maestro que en la ficha del producto.
 *
 * Tres cosas que se conservan tal y como estaban, porque están pensadas para el móvil y para el campo:
 *
 *  1. **La ayuda de la hora va encima del campo** (`ayudaAntes`): es la introducción de la pantalla y se
 *     lee antes de empezar a escribir.
 *  2. **Las horas llevan ejemplo dentro** («07:30») y sin el historial del navegador (`autocompletar`):
 *     un ejemplo vale más que una explicación, y el historial tapa la pantalla.
 *  3. **Las horas y los operarios piden el teclado de números sin coma** (`tipo: "entero"`) y las
 *     temperaturas con coma (`tipo: "numero"`).
 *
 * **Una cosa cambia, y se dice aquí para que no se busque:** la pista de las incidencias («si pasó algo
 * raro, cuéntalo aquí») va ahora **debajo** del área de escribir, y antes iba encima. Es como está en
 * todos los demás campos de la aplicación, y no merecía otra bandera en la pieza del campo.
 */
function montarComoFueElTratamiento() {
  const b = estado.asistente.borrador;
  const delTratamiento = (id, extra = {}) => ({
    tipo: "texto",
    id,
    etiqueta: t(`etiquetas.tratamiento.${id}.pregunta`, ""),
    valor: b[id] || "",
    pista: t(`etiquetas.tratamiento.${id}.pista`, ""),
    ...extra,
  });

  // Los cuatro datos de la franja de seguridad, con su ayuda **encima** del primero (como estaba: esa
  // explicación es la que dice qué es la franja y por qué importa).
  const franja = bloquesDelMaestro([
    "tratamiento.franja_seguridad_respetada",
    "tratamiento.aplicado_a_mano",
    "tratamiento.eficacia",
    "tratamiento.unidad_cantidad_aplicada",
  ]);
  franja[0] = {
    ...franja[0],
    ayuda: datosDeLaAyuda("tratamiento.franja_seguridad_respetada"),
    ayudaAntes: true,
  };

  return camposDelMaestro({
    bloques: [
      {
        ...delTratamiento("hora_inicio", { tipo: "entero", placeholder: "07:30", autocompletar: "off" }),
        ayudaAntes: true,
      },
      delTratamiento("hora_fin", { tipo: "entero", placeholder: "10:15", autocompletar: "off" }),
      {
        ...delTratamiento("estado_cultivo", { autocompletar: "off" }),
        // Este campo **no lleva etiqueta**: su pregunta es el título de la sección, justo encima. Se
        // conserva así porque es como estaba, y repetir la pregunta dos veces no ayuda a nadie.
        etiqueta: "",
        titulo: t("etiquetas.tratamiento.estado_cultivo.pregunta", ""),
      },
      {
        ...delTratamiento("temperatura_c", { tipo: "numero" }),
        // Y aquí empieza la sección del tiempo: su encabezado va en el primer campo de la sección.
        etiqueta: "",
        titulo: t("etiquetas.tratamiento.como_estaba_el_dia.pregunta", ""),
      },
      delTratamiento("humedad_pct", { tipo: "numero" }),
      delTratamiento("viento_kmh", { tipo: "numero" }),
      delTratamiento("viento_direccion", { autocompletar: "off" }),
      delTratamiento("volumen_caldo_l_ha", { tipo: "numero" }),
      ...franja,
      delTratamiento("operadores_expuestos", { tipo: "entero" }),
      {
        ...delTratamiento("incidencias"),
        tipo: "area",
        filas: 2,
      },
    ],
  });
}


/** Los campos de «cómo se echó», tal y como se recogen de la pantalla. */
function recogeComoFueElTratamiento() {
  return () => {
    const b = estado.asistente.borrador;
    b.hora_inicio = valorDe("hora_inicio").trim() || null;
    b.hora_fin = valorDe("hora_fin").trim() || null;
    b.estado_cultivo = valorDe("estado_cultivo").trim() || null;
    b.temperatura_c = aNumero(valorDe("temperatura_c"));
    b.humedad_pct = aNumero(valorDe("humedad_pct"));
    b.viento_kmh = aNumero(valorDe("viento_kmh"));
    b.viento_direccion = valorDe("viento_direccion").trim() || null;
    b.volumen_caldo_l_ha = aNumero(valorDe("volumen_caldo_l_ha"));
    b.operadores_expuestos = aNumero(valorDe("operadores_expuestos"));
    b.incidencias = valorDe("incidencias").trim() || null;
    b.unidad_cantidad_aplicada = valorDe("unidad_cantidad_aplicada").trim() || null;
    // La orilla sin tratar la pone el botón de sí/no, que ya la deja en el borrador: aquí no se
    // toca, para no borrarla al recoger los demás campos.
    return null;
  };
}

function pasosAbonar() {
  return [
    {
      titulo: t("etiquetas.comun.parcela_id.pregunta", ""),
      pista: t("etiquetas.comun.parcela_id.pista", ""),
      montar: montarParcelas,
      recoger: exigeSitio,
    },
    {
      titulo: t("etiquetas.comun.fecha.pregunta", ""),
      pista: t("etiquetas.comun.fecha.pista", ""),
      montar: montarFecha,
      recoger: recogeCampos(["fecha"]),
    },
    {
      titulo: t("etiquetas.fertilizacion.fertilizante_id.pregunta", ""),
      pista: t("etiquetas.fertilizacion.fertilizante_id.pista", ""),
      montar: montarAbonos,
      recoger: () => exige("fertilizante_id"),
    },
    {
      titulo: t("etiquetas.fertilizacion.kg_ha_producto.pregunta", ""),
      pista: t("etiquetas.fertilizacion.kg_ha_producto.pista", ""),
      montar: () =>
        montarNumero(
          "kg_ha_producto",
          t("rotulos.unidad_kilos_ha", ""),
          "fertilizacion.kg_ha_producto",
          "fertilizacion.kg_ha_producto",
        ),
      recoger: () => {
        recogeCampos(["kg_ha_producto"])();
        return exige("kg_ha_producto");
      },
    },
    {
      titulo: t("etiquetas.comun.superficie_ha.pregunta", ""),
      pista: t("etiquetas.comun.superficie_ha.pista", ""),
      montar: () => montarNumero("superficie_ha", t("rotulos.unidad_hectareas", ""), "comun.superficie_ha", null),
      recoger: () => {
        recogeCampos(["superficie_ha"])();
        const b = estado.asistente.borrador;
        const parcela = estado.parcelas.find((p) => p.id === Number(b.parcela_id));
        if (!parcela) return null;
        const codigo = validaSuperficie(b.superficie_ha, parcela.superficie_ha, true);
        return codigo
          ? mensaje(codigo, {
              parcela: formateaNumero(parcela.superficie_ha, 2),
              usada: formateaNumero(aNumero(b.superficie_ha) || 0, 2),
            })
          : null;
      },
    },
    {
      titulo: t("etiquetas.fertilizacion.resumen.pregunta", ""),
      pista: t("etiquetas.fertilizacion.resumen.pista", ""),
      montar: () => montarResumenDelApunte(cargaFertilizacion()),
    },
  ];
}

/**
 * ¿Qué has hecho? Las prácticas que no tienen botón propio en la pantalla de inicio.
 *
 * Existe porque «OTRO TRABAJO» no dice nada: antes se guardaba la palabra «otra» y ahí se
 * acababa la historia. El cuaderno tiene un apartado entero —«Otras Prácticas Culturales»— para
 * el laboreo, el mantenimiento de la cubierta y el pastoreo, y los tres acababan en el mismo
 * cajón sin nombre.
 *
 * La lista viene del servidor (`trabajos_de_labor`), no de aquí: si estuviera en el JavaScript
 * habría dos listas y un día dirían cosas distintas.
 */
function montarTrabajosDeLabor() {
  const elegido = estado.asistente.borrador.tipo;
  return listaParaElegir({
    bloques: [
      {
        botones: (t("trabajos_de_labor", []) || []).map((trabajo) => ({
          etiqueta: trabajo.texto,
          icono: trabajo.icono,
          accion: "elegir",
          datos: { campo: "tipo", valor: trabajo.id },
          clase: elegido === trabajo.id ? "boton-elegido" : "boton-claro",
        })),
      },
    ],
  });
}

function pasosLabor(tipo) {
  const pasos = [
    {
      titulo: t("etiquetas.comun.parcela_id.pregunta", ""),
      pista: t("etiquetas.comun.parcela_id.pista", ""),
      montar: montarParcelas,
      recoger: exigeSitio,
    },
    {
      titulo: t("etiquetas.comun.fecha.pregunta", ""),
      pista: t("etiquetas.comun.fecha.pista", ""),
      montar: montarFecha,
      recoger: recogeCampos(["fecha"]),
    },
  ];

  // «OTRO TRABAJO» no es un trabajo: es un cajón. Antes se guardaba así, con la palabra «otra»,
  // y ni el agricultor podía decir qué había hecho ni el cuaderno lo podía contar. La lista de
  // prácticas sale del servidor (`trabajos_de_labor`), y dos de ellas —mantener la cubierta y
  // pastorear— las nombra el documento oficial de la Junta.
  if (tipo === "otra") {
    pasos.push({
      titulo: t("etiquetas.labor.cual.pregunta", ""),
      pista: t("etiquetas.labor.cual.pista", ""),
      montar: montarTrabajosDeLabor,
      recoger: () => exige("tipo"),
    });
  }

  if (tipo === "cosecha") {
    pasos.push({
      titulo: t("etiquetas.labor.cosecha_cantidad.pregunta", ""),
      pista: t("etiquetas.labor.cosecha_cantidad.pista", ""),
      opcional: true,
      // La etiqueta es la unidad («kilos») y no una pregunta: la pregunta ya es el título del paso
      // («¿Cuánto has recogido?»), y repetirla dos veces no ayuda a nadie.
      montar: () => montarTexto({ id: "cantidad_kg", etiqueta: t("rotulos.unidad_kilos", ""), tipo: "numero" }),
      recoger: recogeCampos(["cantidad_kg"]),
    });
    const camposCosecha = ["labor.semillas_siembra", "labor.plantas_cosechadas", "labor.sin_cosechar_ambiental", "labor.restos_cosecha_depositados"];
    pasos.push({
      titulo: t("etiquetas.labor.destino_cosecha.pregunta", ""),
      pista: t("etiquetas.labor.destino_cosecha.pista", ""),
      opcional: true,
      montar: () => montarCamposMaestro(camposCosecha),
      recoger: recogeCamposMaestro(camposCosecha),
    });
  } else if (tipo === "siembra" || tipo === "plantacion") {
    pasos.push(
      {
        titulo: t("etiquetas.comun.superficie_ha.pregunta", ""),
        pista: t("etiquetas.comun.superficie_ha.pista", ""),
        montar: () => montarNumero("superficie_ha", t("rotulos.unidad_hectareas", ""), "comun.superficie_ha", null),
        recoger: recogeCampos(["superficie_ha"]),
      },
      {
        titulo: t("etiquetas.labor.semilla.pregunta", ""),
        pista: t("etiquetas.labor.semilla.pista", ""),
        opcional: true,
        montar: () =>
          montarCamposMaestro(["labor.cantidad_semilla_kg", "labor.dosis_siembra_kg_ha"]),
        recoger: recogeCamposMaestro(["labor.cantidad_semilla_kg", "labor.dosis_siembra_kg_ha"]),
      },
      {
        // El lote de la semilla es lo que permite responder «¿de qué saco salió esto?» si un
        // día hay un problema con una partida: por eso se pregunta aunque sea opcional.
        titulo: t("etiquetas.labor.semilla_detalle.pregunta", ""),
        pista: t("etiquetas.labor.semilla_detalle.pista", ""),
        opcional: true,
        montar: () =>
          montarCamposMaestro([
            "labor.lote_semilla",
            "labor.material_adquirido",
            "labor.fecha_adquisicion",
            "labor.material_tratado",
          ]),
        recoger: recogeCamposMaestro([
          "labor.lote_semilla",
          "labor.material_adquirido",
          "labor.fecha_adquisicion",
          "labor.material_tratado",
        ]),
      },
      {
        // **Solo si la semilla venía tratada.** Es el bloque «uso de semilla tratada» del anexo II,
        // y se pregunta justo después de que el agricultor diga que sí: preguntar por el
        // tratamiento de una semilla sin tratar sería preguntar por algo que no existe.
        titulo: t("etiquetas.labor.tratamiento_semilla.pregunta", ""),
        pista: t("etiquetas.labor.tratamiento_semilla.pista", ""),
        opcional: true,
        cuando: () => estado.asistente.borrador.material_tratado === true,
        montar: () =>
          montarCamposMaestro([
            "labor.tratamiento_semilla",
            "labor.fecha_tratamiento_semilla",
            "labor.eficacia_tratamiento_semilla",
          ]),
        recoger: recogeCamposMaestro([
          "labor.tratamiento_semilla",
          "labor.fecha_tratamiento_semilla",
          "labor.eficacia_tratamiento_semilla",
        ]),
      },
      {
        titulo: t("etiquetas.labor.plantacion_detalle.pregunta", ""),
        pista: t("etiquetas.labor.plantacion_detalle.pista", ""),
        opcional: true,
        montar: () =>
          montarCamposMaestro([
            "labor.siembra_directa",
            "labor.densidad_plantacion",
            "labor.marco_plantacion",
          ]),
        recoger: recogeCamposMaestro([
          "labor.siembra_directa",
          "labor.densidad_plantacion",
          "labor.marco_plantacion",
        ]),
      },
    );
  } else if (tipo === "riego") {
    pasos.push(
      {
        titulo: t("etiquetas.comun.superficie_ha.pregunta", ""),
        pista: t("etiquetas.comun.superficie_ha.pista", ""),
        montar: () => montarNumero("superficie_ha", t("rotulos.unidad_hectareas", ""), "comun.superficie_ha", null),
        recoger: recogeCampos(["superficie_ha"]),
      },
      {
        // El agua de riego no es un detalle: de dónde sale y cuánto nitrato trae cambia
        // cuánto abono hay que echar. Es el subbloque de fertirrigación del cuaderno.
        titulo: t("etiquetas.labor.agua.pregunta", ""),
        pista: t("etiquetas.labor.agua.pista", ""),
        opcional: true,
        montar: () =>
          montarCamposMaestro(["labor.volumen_agua", "labor.unidad_agua", "labor.sistema_riego"]),
        recoger: recogeCamposMaestro(["labor.volumen_agua", "labor.unidad_agua", "labor.sistema_riego"]),
      },
      {
        titulo: t("etiquetas.labor.origen_agua.pregunta", ""),
        pista: t("etiquetas.labor.origen_agua.pista", ""),
        opcional: true,
        montar: () => montarCamposMaestro(["labor.origen_agua"]),
        recoger: recogeCamposMaestro(["labor.origen_agua"]),
      },
      {
        titulo: t("etiquetas.labor.agua_detalle.pregunta", ""),
        pista: t("etiquetas.labor.agua_detalle.pista", ""),
        opcional: true,
        montar: () => montarCamposMaestro(["labor.numero_contador", "labor.nitratos_agua"]),
        recoger: recogeCamposMaestro(["labor.numero_contador", "labor.nitratos_agua"]),
      },
    );
  } else {
    pasos.push(
      {
        titulo: t("etiquetas.comun.superficie_ha.pregunta", ""),
        pista: t("etiquetas.comun.superficie_ha.pista", ""),
        montar: () => montarNumero("superficie_ha", t("rotulos.unidad_hectareas", ""), "comun.superficie_ha", null),
        recoger: recogeCampos(["superficie_ha"]),
      },
      {
        titulo: t("etiquetas.labor.detalles.pregunta", ""),
        pista: t("etiquetas.labor.detalles.pista", ""),
        opcional: true,
      montar: () => montarTexto({ id: "detalles" }),
      recoger: recogeCampos(["detalles"]),
      },
    );
  }

  // El pastoreo tiene dos preguntas propias, y el interfaz de la Junta las pide como
  // obligatorias. Van en un paso suyo y solo para el pastoreo: a los demás trabajos no se les
  // pregunta por el ganado.
  if (tipo === "pastoreo") {
    pasos.push({
      titulo: t("etiquetas.labor.animales.pregunta", ""),
      pista: t("etiquetas.labor.animales.pista", ""),
      opcional: true,
      montar: () => montarCamposMaestro(["labor.animales_terceros", "labor.animales_propios"]),
      recoger: recogeCamposMaestro(["labor.animales_terceros", "labor.animales_propios"]),
    });
  }
  if (tipo === "otra") {
    const camposCubierta = ["labor.fecha_establecimiento_cubierta", "labor.tipo_cobertura", "labor.anchura_cubierta_m", "labor.anchura_libre_proyeccion_m"];
    const camposRestos = ["labor.restos_desbroce_depositados", "labor.restos_poda_depositados"];
    pasos.push({
      titulo: t("etiquetas.labor.datos_propios.pregunta", ""),
      pista: t("etiquetas.labor.datos_propios.pista", ""),
      opcional: true,
      montar: () => montarDatosPropiosDeLaLabor(camposCubierta, camposRestos),
      recoger: () => recogeCamposMaestro([...camposCubierta, ...camposRestos, "labor.animales_terceros", "labor.animales_propios"])(),
    });
  }

  pasos.push({
    titulo: t("etiquetas.tratamiento.resumen.pregunta", ""),
    pista: t("etiquetas.tratamiento.resumen.pista", ""),
    montar: () => montarResumenDelApunte(cargaLabor(tipo)),
  });

  // **Con qué máquina se hizo.** El contenido mínimo del CUE lo pide en los bloques de labores y
  // de siembra, y hasta ahora solo lo preguntaban los tratamientos: se podía apuntar que se labró,
  // y no con qué. Va al final y es opcional a propósito: hay labores a mano, y obligar a tener la
  // máquina dada de alta antes de apuntar el trabajo es la forma de que no se apunte.
  pasos.push({
    titulo: t("etiquetas.labor.equipo_id.pregunta", ""),
    pista: t("etiquetas.labor.equipo_id.pista", ""),
    opcional: true,
    montar: montarEquiposDeLaLabor,
    recoger: () => null, // se elige pulsando, como los aplicadores y las máquinas del tratamiento
  });

  return pasos;
}

/**
 * La lista de máquinas para elegir con cuál se hizo la labor, ya en React.
 *
 * Sin máquinas dadas de alta **no se deja la pantalla en blanco**: se dice lo que pasa y dónde se
 * añaden, que es la diferencia entre poder seguir y quedarse mirando un hueco.
 */
function montarEquiposDeLaLabor() {
  const b = estado.asistente.borrador;
  if (!estado.equipos.length) {
    // El aviso va con su explicación aparte, como estaba: el aviso dice qué pasa y la pista dice qué
    // se puede hacer igualmente («el trabajo se apunta sin máquina»), que es lo que evita que el
    // agricultor crea que no puede seguir.
    return listaParaElegir({
      aviso: {
        texto: t("maestros.sin_equipo", ""),
        pista: t("etiquetas.labor.equipo_id.sin_maquinas", ""),
      },
    });
  }
  return listaParaElegir({
    bloques: [
      {
        titulo: t("etiquetas.labor.equipo_id.pregunta", ""),
        botones: estado.equipos.map((equipo) => ({
          etiqueta: equipo.nombre,
          // **La fecha de la ITEAF, y el aviso de la máquina** (T14): si esa máquina no está para trabajar o
          // se le ha pasado una inspección, se dice aquí, que es donde se está decidiendo con qué se hace el
          // trabajo. El aviso es el mismo que enseña su ficha, así que las dos pantallas no pueden decir
          // cosas distintas.
          pista: [
            equipo.fecha_proxima_iteaf
              ? `${t("rotulos.itv_hasta", "")} ${formateaFecha(equipo.fecha_proxima_iteaf)}`
              : "",
            avisoDeLaMaquinaDeUnEquipo(equipo.id),
          ]
            .filter(Boolean)
            .join(" · "),
          accion: "elegir",
          datos: { campo: "equipo_id", valor: equipo.id },
          clase: Number(b.equipo_id) === equipo.id ? "boton-elegido" : "boton-claro",
        })),
      },
    ],
  });
}

// -------------------------------------------------------------- cargar datos

async function cargarInterfaz() {
  try {
    estado.interfaz = await apiJson("/api/interfaz");
    guardar(CLAVE_INTERFAZ, estado.interfaz);
  } catch (error) {
    // Sin cobertura se usa lo que se guardó la última vez. La aplicación tiene que
    // abrirse en el campo aunque el servidor no esté a mano.
    estado.interfaz = leer(CLAVE_INTERFAZ, null);
    if (!estado.interfaz) throw error;
  }
}

function olvidarLaVistaDeLasTierras() {
  // **La vista de las tierras no se puede quedar vieja.** Se pide una sola vez por sesión (son 64
  // tierras con sus anillos), así que si el agricultor apunta, corrige o borra una tierra desde otra
  // pantalla, esta tiene que olvidarla: si no, volvería al mapa y seguiría contando las de antes, con
  // una tierra que ya no está o sin la que acaba de apuntar. Lo encontró la revisión de T06 (D11).
  //
  // Se llama desde `cargarDatos()`, que es el único sitio por el que pasa volver a leer la finca, así
  // que cualquier pantalla que recargue los datos se lleva la vista por delante sola.
  if (estado.t06) {
    estado.t06.vista = null;
    estado.t06.elegida = null;
    estado.t06.mismoRecinto = [];
  }
}

async function cargarDatos() {  const [
    campana,
    campanas,
    parcelas,
    productos,
    abonos,
    aplicadores,
    asesores,
    equipos,
    instalaciones,
    planes,
    analiticas,
    medidas,
    ventas,
    documentos,
    cesta,
    cultivos,
    grupos,
    faltantes,
    firma,
    facturas,
    lectorDeFacturas,
    cuadernoJunta,
    miFinca,
    tratamientos,
    // Los abonos, los trabajos y las firmas: los tres hacen falta para **corregir y borrar** lo que ya
    // está apuntado (ronda 91). Sin los dos primeros, «mi cuaderno» no podría enseñar ni un abono ni un
    // trabajo —hasta esta ronda no los enseñaba—, y sin las firmas no se puede saber si un apunte está
    // firmado, que es lo único que impide borrarlo.
    fertilizaciones,
    labores,
    firmas,
    resumen,
    // T12: la tabla del dinero (con su pie y sus totales), las facturas nuestras y los cobros. Se piden
    // con el resto porque las tres pantallas se abren desde la pantalla de inicio del módulo y sin
    // ellas habría que esperar a una segunda llamada con la pantalla ya montada.
    ventasTabla,
    facturasEmitidas,
    cobros,
    // Los avisos de la maquinaria (T14): ver el porqué donde se piden.
    avisosDeLaMaquinaria,
  ] = await Promise.all([
    apiJson("/api/campanas/actual").catch(() => null),
    // **Los años del cuaderno** (ronda 93): sin la lista no se puede corregir ni borrar ninguno, porque
    // `cosaCargada` busca la cosa entre lo que hay cargado. Se pide con el resto: es una lista de dos o
    // tres filas.
    apiJson("/api/campanas").catch(() => []),    apiJson("/api/parcelas").catch(() => []),
    apiJson("/api/productos").catch(() => []),
    apiJson("/api/fertilizantes").catch(() => []),
    apiJson("/api/aplicadores").catch(() => []),
    apiJson("/api/asesores").catch(() => []),
    apiJson("/api/equipos").catch(() => []),
    apiJson("/api/instalaciones").catch(() => []),
    apiJson("/api/planes").catch(() => []),
    apiJson("/api/analiticas").catch(() => []),
    apiJson("/api/medidas").catch(() => null),
    apiJson("/api/ventas").catch(() => []),
    apiJson("/api/documentos").catch(() => null),
    apiJson("/api/productos/cesta/situacion").catch(() => null),
    apiJson("/api/cultivos").catch(() => null),
    apiJson("/api/grupos").catch(() => []),
    apiJson(conLaCampana("/api/cuaderno/falta")).catch(() => null),
    apiJson(conLaCampana("/api/firmas/estado")).catch(() => null),
    apiJson("/api/facturas").catch(() => []),
    apiJson("/api/facturas/estado").catch(() => null),
    apiJson(conLaCampana("/api/cuaderno-cyl/que-falta")).catch(() => null),
    apiJson("/api/mi-finca").catch(() => null),
    // **Estos dos faltaban, y se notaba en pantalla.** `estado.tratamientos` no lo rellenaba
    // nadie: la pantalla «mi cuaderno» enseñaba «0 apuntes de producto» y una lista vacía
    // aunque el agricultor tuviera el año lleno de tratamientos. Y el resumen es lo que permite
    // decir la verdad al final de la pantalla de inicio («todavía no has apuntado nada» solo se
    // dice si de verdad no hay nada apuntado). Los dos se piden aquí, con el resto.
    apiJson("/api/tratamientos").catch(() => []),
    apiJson("/api/fertilizaciones").catch(() => []),
    apiJson("/api/labores").catch(() => []),
    apiJson(conLaCampana("/api/firmas")).catch(() => []),
    apiJson("/api/cuaderno/resumen").catch(() => null),
    // T12: la tabla de lo que se ha vendido con su pie (el servidor calcula el agregado del conjunto
    // filtrado), las facturas nuestras y los cobros.
    apiJson("/api/ventas/tabla").catch(() => null),
    apiJson("/api/facturas-emitidas").catch(() => []),
    apiJson("/api/cobros").catch(() => []),
    // **Los avisos de la maquinaria** (T14, 03/10/2026). Se piden aquí, con el resto, y no al abrir su
    // pantalla, por un motivo: el aviso de «esa máquina no está para trabajar» o «se le ha pasado la
    // inspección» hace falta **donde se elige la máquina para un trabajo**, que es el asistente. Sin
    // esto, el agricultor se enteraría al abrir la lista de maquinaria… y para entonces ya ha hecho el
    // trabajo. Es una consulta pequeña (una fila por máquina con algo que mirar) y no trae la lista
    // entera: solo lo que hay que mirar.
    apiJson("/api/maquinaria/avisos").catch(() => []),
  ]);
  // **Antes de quedarse con las tierras de ahora, se olvida la vista de antes**: es lo que hace que
  // apuntar, corregir o borrar una tierra desde cualquier pantalla no deje al mapa contando las de
  // ayer (ver `olvidarLaVistaDeLasTierras`).
  olvidarLaVistaDeLasTierras();
  Object.assign(estado, {
    campana,
    campanas,
    parcelas,
    productos,
    abonos,
    aplicadores,
    asesores,
    equipos,
    instalaciones,
    planes,
    analiticas,
    medidas,
    ventas,
    // Y el dinero de lo que se vende (T12): la tabla con su pie, las facturas nuestras y los cobros.
    ventasTabla,
    facturasEmitidas,
    cobros,
    // Y los avisos de la maquinaria (T14), aparte del resto del estado de la maquinaria a propósito: esto
    // se pide al arrancar —porque hace falta en el asistente, al elegir la máquina de un trabajo— y la
    // lista entera de máquinas **no**, porque solo hace falta al abrir su pantalla.
    maquinariaAvisos: Array.isArray(avisosDeLaMaquinaria) ? avisosDeLaMaquinaria : [],
    documentos,
    cesta,
    cultivos,
    grupos,
    faltantes,
    firmaEstado: firma,
    // Las facturas: la lista y lo que hace falta para saber si se pueden leer las fotos.
    facturasLista: facturas,
    lectorDeFacturas,
    // Lo que le falta al cuaderno de la Junta, para poder decirlo en «mi cuaderno».
    cuadernoJunta,
    // Los datos del titular y de la finca: la portada del cuaderno.
    miFinca,
    // Los tratamientos **del año que se está llevando**: la pantalla «mi cuaderno» enseña lo
    // apuntado este año, no lo de campañas pasadas. El servidor los devuelve del más nuevo al
    // más viejo, y de ese orden sale también «lo mismo que la última vez».
    tratamientos: (Array.isArray(tratamientos) ? tratamientos : []).filter(
      (apunte) => !campana || apunte.campana_id === campana.id,
    ),
    // Los abonos y los trabajos de esta campaña, con el mismo filtro y por el mismo motivo: es lo que
    // sale en la lista de lo apuntado, y de ahí es de donde se corrige y se borra.
    fertilizaciones: (Array.isArray(fertilizaciones) ? fertilizaciones : []).filter(
      (apunte) => !campana || apunte.campana_id === campana.id,
    ),
    labores: (Array.isArray(labores) ? labores : []).filter(
      (apunte) => !campana || apunte.campana_id === campana.id,
    ),
    // Las firmas: no se enseñan en ninguna pantalla, pero son lo que decide si un apunte se puede
    // borrar o solo anular.
    firmas: Array.isArray(firmas) ? firmas : [],
    // Los números del cuaderno (cuántos apuntes de producto, de abono y de trabajo). Son para la
    // pantalla de inicio: con ellos, «no has apuntado nada» es un dato y no una suposición.
    resumen,
  });
}

// ------------------------------------------------------------------- acciones

async function entrar(modo) {
  const correo = (document.getElementById("correo") || {}).value || "";
  const clave = (document.getElementById("clave") || {}).value || "";
  estado.errorEntrar = "";

  try {
    let datos;
    if (modo === "registro") {
      const cuerpo = {
        explotacion: {
          nombre: (document.getElementById("nombre") || {}).value || correo,
          nif: (document.getElementById("nif") || {}).value || "",
          municipio: (document.getElementById("municipio") || {}).value || "",
          provincia: (document.getElementById("provincia") || {}).value || "",
        },
        nombre: (document.getElementById("nombre") || {}).value || correo,
        correo,
        clave,
      };
      datos = await apiJson("/api/cuenta/registro", { method: "POST", body: JSON.stringify(cuerpo) });
    } else {
      datos = await apiJson("/api/cuenta/entrar", {
        method: "POST",
        body: JSON.stringify({ correo, clave }),
      });
    }
    estado.token = datos.token;
    estado.nombre = datos.nombre;
    ALMACEN.setItem(CLAVE_TOKEN, datos.token);
    guardar(CLAVE_NOMBRE, datos.nombre);
  } catch (error) {
    estado.errorEntrar = error.message;
    pantallaEntrar(modo);
    return;
  }

  await arrancarSesion();
}

/**
 * La versión de la aplicación, a la vista, en el pie de todas las pantallas.
 *
 * POR QUÉ HACE FALTA (30/09/2026, lo pidió David). Con la aplicación en el móvil y en el ordenador y con
 * una caché por medio, la pregunta «¿estoy viendo lo nuevo o lo viejo?» no tenía respuesta: si alguien
 * veía una pantalla antigua, no había forma de saberlo sin abrir las herramientas del navegador. Ahora el
 * pie dice la versión, y **es la misma cadena que el nombre de la caché del `service-worker.js`**: hay una
 * prueba que comprueba que las dos no se separan (si se separan, o el móvil no se descarga lo nuevo, o el
 * número que se enseña no es el de verdad).
 */
const VERSION_DE_LA_APLICACION = "2026-10-06-71";

function pintarPie() {
  const pie = document.getElementById("pie");
  if (pie) {
    // El texto del servidor y la versión se juntan **aquí**, no dentro de un componente (regla de la casa).
    const suyo = t("aviso.pie", "");
    pie.textContent = suyo ? `${suyo} · versión ${VERSION_DE_LA_APLICACION}` : `versión ${VERSION_DE_LA_APLICACION}`;
  }
}

async function arrancarSesion() {
  cabeceraTexto.textContent = t("aviso.cargando", "");
  try {
    await cargarInterfaz();
    await cargarDatos();
  } catch (error) {
    // **Sin botón, y es el único**: aquí no ha llegado ni la interfaz, así que no hay ni un texto del
    // servidor que ponerle al botón (`accion("volver")` devolvería la clave). Ver `avisarDelError`.
    avisarDelError(error.message, { sinVolver: true });
    return;
  }
  cabeceraTexto.textContent = t("cuaderno.titulo", "");
  pintarPie();
  pintarAvisoPendientes();
  mandarPendientes();
  // **Abrir por la dirección, no por el principio** (T04, 02/10/2026). Es lo que hace que recargar la
  // página deje al agricultor donde estaba —en su tierra, con su campaña y sus filtros— y que un enlace
  // directo a una ficha funcione. Si no hay dirección, esto abre el inicio, que es lo de antes.
  //
  // `completando` va puesto durante el primer pintado: si la dirección venía sin la campaña o sin la
  // finca (o no había dirección), se **reemplaza** en vez de añadir una entrada, porque si no el primer
  // «atrás» del agricultor no haría nada.
  estado.completando = true;
  await abrirLaDireccion();
  estado.completando = false;
}

/**
 * Atrás y adelante del navegador (T04).
 *
 * Se escucha `popstate`, que es el evento de **la navegación del historial**, y no `hashchange`, que
 * también salta cuando se escribe la dirección desde aquí: con `hashchange` cada pantalla que se abriera
 * se volvería a abrir en un bucle.
 */
window.addEventListener("popstate", () => {
  estado.completando = true;
  Promise.resolve(abrirLaDireccion())
    .catch(() => {})
    .then(() => {
      estado.completando = false;
    });
});

/**
 * Lo que cierra la tecla **Escape** (06/10/2026).
 *
 * **Por qué es una lista escrita a mano y corta.** En esta aplicación «cancelar» significa dos cosas
 * distintas: cerrar un formulario **sin guardar** (`gasto-cancelar`) y **anular un plan de trabajo**
 * (`trabajo-cancelar`), que sí apunta algo. Un Escape que buscara «cualquier botón que se llame
 * cancelar» **anularía un plan de trabajo de un toque de tecla**, y eso no se arregla con un aviso: se
 * arregla no poniéndolo en la lista. Tampoco está el asistente de apuntar: dejarlo a medias con una tecla
 * es perder lo que el agricultor llevaba escrito.
 *
 * Se pulsan **como si se tocaran** (`click()`), así que hacen exactamente lo mismo que el dedo: cerrar el
 * panel, volver a la lista o dejar la pantalla como estaba.
 */
const LO_QUE_CIERRA_ESCAPE = [
  "gasto-cancelar",
  "banco-cancelar",
  "bandeja-cancelar",
  "maquina-cancelar",
  "maquina-anular-cancelar",
  // El menú del móvil, que tapa la pantalla: cerrarlo con Escape es lo que espera cualquiera.
  "menu-cerrar",
  // **«Volver a mis tierras» antes que «volver a los trabajos»** (07/10/2026, E4 de la revisión del
  // recorrido). La ficha de una tierra tiene los dos botones, y Escape pulsaba el primero de la lista:
  // salía a la agenda de trabajos, y desde ahí **no hay camino de vuelta a la tierra** de la que se
  // salió. Escape tiene que hacer lo mismo que el botón que cierra esa pantalla, y la ficha se cierra
  // volviendo a la lista de tierras, que es de donde se entra.
  "mis-cosas",
  // Volver a la lista: la ficha de un trabajo se cierra con «volver a los trabajos», no con un cancelar.
  "trabajos-ver",
  "cuaderno-volver",
  "mapa-volver",
  "t06-volver",
];

/** ¿Se ve este elemento? (Un botón escondido no puede ser lo que cierre el Escape.) */
function seVeElElemento(elemento) {
  if (typeof elemento.checkVisibility === "function") return elemento.checkVisibility();
  return elemento.offsetParent !== null;
}

/**
 * Escape cierra lo que esté abierto.
 *
 * Antes **no había ni un manejador de teclado en toda la aplicación**: quien va con el teclado tenía que
 * tabular hasta el botón de cancelar (medido). Se busca el primer botón de la lista que esté **visible**
 * —el de la pantalla que se está mirando, no el de otra que quedó montada— y se pulsa.
 */
window.addEventListener("keydown", (suceso) => {
  if (suceso.key !== "Escape" || suceso.defaultPrevented) return;
  for (const accion of LO_QUE_CIERRA_ESCAPE) {
    const boton = document.querySelector(`[data-accion="${accion}"]`);
    if (boton && seVeElElemento(boton) && !boton.disabled) {
      boton.click();
      return;
    }
  }
});

function salir(confirmar = true) {
  if (confirmar && !window.confirm(t("aviso.confirmar_salida", ""))) return;
  estado.token = null;
  ALMACEN.removeItem(CLAVE_TOKEN);
  // La cola NO se borra al salir: si alguien apuntó algo sin cobertura y cierra la
  // sesión, ese apunte sigue siendo suyo y tiene que poder mandarse.
  pantallaEntrar("entrar");
}

async function guardarAsistente() {
  const asistente = estado.asistente;
  const tipo = asistente.tipo;

  // ¿Esto es un alta o la corrección de algo que ya estaba? Lo dice `estado.asistente.corregir`, que se
  // pone al abrir el asistente desde CORREGIR. Lo usan **todas** las ramas de aquí abajo: con `POST` se
  // crea una fila nueva y con `PUT` se cambia la que ya existe. Poner una cosa donde había otra es lo
  // que hace que el agricultor acabe con dos tierras, dos productos o dos planes.
  const correccion = asistente.corregir;

  /** Guarda lo del asistente: corrige la fila que ya está, o crea una nueva. */
  async function guardarOcorregir(ruta, carga, { repetible = false } = {}) {
    if (correccion) return mandarCambio(`${ruta}/${correccion.id}`, "PUT", carga);
    return enviarOApuntar(ruta, carga, tipo, repetible);
  }

  // El año del cuaderno (ronda 93). Se crea y se corrige con el mismo formulario (cuatro campos), así que
  // comparte motor con los maestros; lo que es propio es **el final**: el año no se «apunta», se
  // **empieza**, y el primer botón lleva a ver los años, no a mis tierras.
  if (tipo === "campana") {
    const resultado = await guardarOcorregir("/api/campanas", cargaCampana());
    if (resultado.error) {
      asistente.error = resultado.error;
      pintarAsistente();
      return;
    }
    estado.asistente = null;
    await cargarDatos().catch(() => {});
    if (resultado.encolado) {
      pintarAvisoPendientes();
      pantallaHecho({ encolado: true }, tipo);
      return;
    }
    if (correccion) {
      // **«Corregido»** y no «Año guardado»: al corregir no se ha empezado ningún año, se ha arreglado el
      // que ya estaba, y decirle «guardado» le haría dudar de si tiene dos.
      pantallaCosaCorregida("campanas", t("campanas.titulo", ""));
      return;
    }
    pantallaCampanaGuardada();
    return;
  }

  // El plan de abono del año. Se puede corregir, así que no entra en "lo mismo que la
  // última vez" ni tiene sentido deshacerlo.
  if (tipo === "plan") {
    const resultado = await guardarOcorregir("/api/planes", cargaPlan());
    if (resultado.error) {
      asistente.error = resultado.error;
      pintarAsistente();
      return;
    }
    estado.asistente = null;
    await cargarDatos().catch(() => {});
    if (resultado.encolado) {
      pintarAvisoPendientes();
      pantallaHecho({ encolado: true }, tipo);
      return;
    }
    if (correccion) {
      pantallaCosaCorregida("planes", t("plan.ver", ""));
      return;
    }
    pantallaPlanGuardado();
    return;
  }

  // Lo que se vende. No entra en «lo mismo que la última vez»: cada venta tiene su fecha y
  // su albarán, y repetirla apuntaría una venta que no ha pasado. Tampoco se deshace: no es
  // un apunte del agricultor sobre el campo, es un papel que existe.
  if (tipo === "venta") {
    const resultado = await guardarOcorregir("/api/ventas", cargaVenta());
    if (resultado.error) {
      asistente.error = resultado.error;
      pintarAsistente();
      return;
    }
    estado.asistente = null;
    await cargarDatos().catch(() => {});
    if (resultado.encolado) {
      pintarAvisoPendientes();
      pantallaHecho({ encolado: true }, tipo);
      return;
    }
    if (correccion) {
      pantallaCosaCorregida("ventas", t("venta.ver", ""));
      return;
    }
    pantallaVentaGuardada();
    return;
  }

  // El análisis de laboratorio. No entra en «lo mismo que la última vez»: un análisis se
  // hace una vez al año, y repetir el mismo boletín sería apuntar un dato falso. Tampoco
  // tiene sentido deshacerlo, porque no es un apunte del agricultor.
  if (tipo === "analitica") {
    const carga = cargaAnalitica();
    const resultado = await guardarOcorregir("/api/analiticas", carga);
    if (resultado.error) {
      asistente.error = resultado.error;
      pintarAsistente();
      return;
    }
    estado.asistente = null;
    await cargarDatos().catch(() => {});
    if (resultado.encolado) {
      pintarAvisoPendientes();
      pantallaHecho({ encolado: true }, tipo);
      return;
    }
    if (correccion) {
      pantallaCosaCorregida("analisis", t("analitica.ver", ""));
      return;
    }
    pantallaAnaliticaGuardado(resultado.datos);
    return;
  }

  // Dar de alta algo que se usa: parcela, producto, abono, quién aplica, máquina o nave.
  //
  // **Y corregirlo** (ronda 92): con lo mismo. La carga se arma igual (`cargaMaestro(tipo)` lee los
  // campos del asistente, que están puestos con lo que ya había), y lo único que cambia es a dónde va:
  // a la fila que ya existe, con un `PUT`, en vez de a una nueva con un `POST`. Corregir el nombre de
  // una tierra no puede crear una tierra nueva: el agricultor tendría las dos, y la vieja con todos sus
  // apuntes.
  if (MAESTROS_API[tipo]) {
    const ruta = MAESTROS_API[tipo].ruta;
    const resultado = correccion
      ? await mandarCambio(`${ruta}/${correccion.id}`, "PUT", cargaMaestro(tipo))
      : await enviarOApuntar(
          ruta,
          cargaMaestro(tipo),
          tipo,
          false, // no es algo que se repita: no entra en "lo mismo que la última vez"
        );
    if (resultado.error) {
      asistente.error = resultado.error;
      pintarAsistente();
      return;
    }
    estado.asistente = null;
    await cargarDatos().catch(() => {});
    if (resultado.encolado) {
      pintarAvisoPendientes();
      pantallaHecho({ encolado: true }, tipo);
      return;
    }
    pantallaMaestroGuardado(tipo, Boolean(correccion));
    return;
  }

  let ruta = "/api/tratamientos";
  let carga;
  if (tipo === "tratamiento") {
    carga = cargaTratamiento();
  } else if (tipo === "fertilizacion") {
    ruta = "/api/fertilizaciones";
    carga = cargaFertilizacion();
  } else if (tipo === "cosecha") {
    ruta = "/api/cosecha";
    carga = cargaLabor("cosecha");
  } else {
    ruta = "/api/labores";
    carga = cargaLabor(tipo);
  }

  // ¿Esto es un apunte nuevo o la corrección de uno que ya estaba? Lo dice `estado.asistente.corregir`,
  // que se pone al abrir el asistente desde CORREGIR (en la ficha de un apunte o después de guardarlo),
  // y ya está leído arriba.
  //
  // Las dos cosas usan **la misma carga**: los campos del asistente se leen igual, así que una
  // corrección pasa por las mismas comprobaciones que un apunte nuevo (`cargaTratamiento()` y sus
  // hermanas son las que arman lo que se manda). Lo único que cambia es a dónde va: al apunte que ya
  // existe, en vez de a uno nuevo.
  const resultado = correccion
    ? await mandarCambio(`${ruta}/${correccion.id}`, "PUT", carga)
    : await enviarOApuntar(ruta, carga, tipo);
  if (resultado.error) {
    asistente.error = resultado.error;
    pintarAsistente();
    return;
  }
  estado.asistente = null;
  if (resultado.encolado) {
    pintarAvisoPendientes();
    pantallaHecho({ encolado: true }, tipo);
    return;
  }
  await cargarDatos().catch(() => {});
  pantallaHecho(
    { ...resultado, id: resultado.datos ? resultado.datos.id : null, corregido: Boolean(correccion) },
    tipo,
  );
}

/**
 * Abre el asistente con lo que ya estaba apuntado, para cambiarlo.
 *
 * POR QUÉ SE REUTILIZA EL ASISTENTE Y NO SE HACE UN FORMULARIO NUEVO. Porque el asistente **ya es** el
 * formulario: tiene los 65 pasos escritos, cada uno con sus campos, sus listas y sus comprobaciones, y
 * hacer una pantalla de corregir aparte sería tener dos formularios del mismo apunte —y el día que se
 * añada un dato, el de corregir se quedaría sin él sin que nadie se entere—. Es la misma decisión que
 * se tomó con «lo mismo que la última vez»: el asistente sabe abrirse con un borrador puesto
 * (`estado.asistente.borrador`), y lo único que hace falta es **traducir el apunte guardado a ese
 * borrador**.
 *
 * Y `corregir` se pone **después** de abrir, porque `abrirAsistente()` lo deja en blanco a propósito
 * (ver allí): así no hay forma de que un apunte nuevo acabe cambiando el apunte que se estaba
 * corrigiendo antes.
 */
function corregirApunte(apunte, tipo) {
  const borrador = borradorDeLaCosa(tipo, apunte);
  if (!borrador) {
    pantallaInicio();
    return;
  }
  abrirAsistente(tipo, pasosDeLaCosa(tipo, apunte));
  estado.asistente.borrador = borrador;
  estado.asistente.corregir = { id: apunte.id };
  // Lo que ya estaba, para poder distinguir «lo ha cambiado el agricultor» de «es lo que había»: hay
  // pasos que limpian datos cuando cambia una elección (la clase de un análisis limpia sus números) y
  // al corregir no pueden limpiar nada mientras la elección siga siendo la misma.
  estado.asistente.tipoOriginal = borrador.tipo || null;
  estado.asistente.tituloForzado = t("corregir.pregunta", "");
  estado.asistente.pistaForzada = t("corregir.pista", "");
  pintarAsistente();
}

/** Con qué formulario se corrige esa cosa: el mismo con el que se da de alta. */
function pasosDeLaCosa(tipo, registro) {
  const cosa = OTRAS_COSAS[tipo];
  if (cosa) return cosa.pasos(registro);
  if (tipo === "tratamiento") return pasosTratamiento();
  if (tipo === "fertilizacion") return pasosAbonar();
  return pasosLabor(tipo);
}

/** Lo que hay que poner en el formulario para que salga con lo que ya había. */
function borradorDeLaCosa(tipo, registro) {
  const cosa = OTRAS_COSAS[tipo];
  return cosa ? cosa.borrador(registro) : borradorDeUnApunte(tipo, registro);
}

/**
 * Una tierra, contada como en su tarjeta de «mis cosas».
 *
 * Se reutiliza **la misma forma** (`etiqueta`, `filas`, `queEs`) que la de un apunte, para que la
 * pantalla que pregunta «¿seguro que quieres borrarla?» enseñe lo mismo que la tarjeta que se acaba de
 * tocar: es lo que permite comprobar que es esa tierra y no la de al lado.
 */
function fichaDeUnaTierra(parcela) {
  const m = (clave) => t(`maestros.${clave}`, "");
  const dichas = (estado.cultivos || {});
  const suya = ((dichas.parcelas || []).find((p) => p.parcela_id === parcela.id)) || {};
  const actual = suya.actual || null;
  const cultivo = actual
    ? [actual.especie, actual.variedad, etiquetaDeValor("sistemas", actual.sistema || parcela.sistema)]
        .filter(Boolean)
        .join(" · ")
    : "";
  const numero = (estado.parcelas || []).findIndex((p) => p.id === parcela.id) + 1;
  return {
    tipo: "parcela",
    id: parcela.id,
    queEs: queEsLaCosa("parcela"),
    etiqueta: parcela.alias,
    cuando: rellena(m("tierra_numero"), { numero }),
    filas: [
      parcela.ref_sigpac ? { etiqueta: m("tierra_sigpac"), valor: parcela.ref_sigpac } : null,
      parcela.superficie_ha
        ? {
            etiqueta: t("rotulos.hectareas", ""),
            valor: `${formateaNumero(parcela.superficie_ha, 2)} ${t("rotulos.hectareas_corto", "")}`,
          }
        : null,
      parcela.municipio ? { etiqueta: m("tierra_pueblo"), valor: parcela.municipio } : null,
      cultivo ? { etiqueta: m("tierra_cultivo"), valor: cultivo } : null,
    ].filter(Boolean),
  };
}

/** Un grupo de parcelas, contado como en su lista. */
function fichaDeUnGrupo(grupo) {  const g = (clave) => t(`grupos.${clave}`, "");
  const suyas = (grupo.parcela_ids || [])
    .map((id) => (estado.parcelas || []).find((p) => p.id === id))
    .filter(Boolean);
  return {
    tipo: "grupo",
    id: grupo.id,
    queEs: queEsLaCosa("grupo"),
    etiqueta: grupo.nombre,
    cuando: "",
    filas: [
      {
        etiqueta: t("rotulos.parcelas_corto", ""),
        valor: String(suyas.length),
      },
      grupo.superficie_total_ha
        ? {
            etiqueta: t("rotulos.hectareas", ""),
            valor: `${formateaNumero(grupo.superficie_total_ha, 2)} ${t("rotulos.hectareas_corto", "")}`,
          }
        : null,
      suyas.length ? { etiqueta: g("tierras_del_grupo") || "", valor: suyas.map((p) => p.alias).join(" · ") } : null,
    ].filter((fila) => fila.etiqueta),
  };
}

/**
 * Una tierra, traducida al borrador del asistente.
 *
 * **Tiene que llevar TODOS los campos que el formulario manda**, y no solo los que se ven: al corregir,
 * lo que no viaja se queda en blanco en el servidor. Por eso se copian también los que la pantalla no
 * pregunta (la referencia del SIGPAC con sus siete números, la pendiente, la zona de nitratos, la
 * superficie oficial): si no, corregir el nombre de una tierra le borraría la referencia y el mapa se
 * quedaría sin saber dónde está.
 */
function borradorDeUnaTierra(parcela) {
  return {
    alias: parcela.alias,
    ref_sigpac: parcela.ref_sigpac,
    provincia: parcela.provincia,
    municipio: parcela.municipio,
    codigo_ine: parcela.codigo_ine,
    poligono: parcela.poligono,
    numero_parcela: parcela.numero_parcela,
    numero_recinto: parcela.numero_recinto,
    agregado: parcela.agregado,
    zona: parcela.zona,
    referencia_catastral: parcela.referencia_catastral,
    superficie_ha: parcela.superficie_ha,
    superficie_oficial: parcela.superficie_oficial,
    uso_sigpac: parcela.uso_sigpac,
    sistema: parcela.sistema,
    pendiente_pct: parcela.pendiente_pct,
    masa_agua_cerca: parcela.masa_agua_cerca,
    captacion_consumo_humano: parcela.captacion_consumo_humano,
    zona_vulnerable_nitratos: parcela.zona_vulnerable_nitratos,
  };
}

/**
 * Un grupo, traducido al borrador del asistente.
 *
 * Se lleva también **las tierras que lo forman** (`parcela_ids`) y la campaña: el formulario no las
 * pregunta —un grupo se llama como el agricultor quiera y nada más—, pero si no viajaran, renombrar un
 * grupo lo dejaría sin tierras.
 */
function borradorDeUnGrupo(grupo) {
  return {
    nombre: grupo.nombre,
    campana_id: grupo.campana_id,
    cultivo: grupo.cultivo,
    sistema: grupo.sistema,
    parcela_ids: grupo.parcela_ids || [],
  };
}

/**
 * Una ficha de lo que se usa (un producto, un abono, quién aplica, un asesor, una máquina, una nave),
 * contada como en su renglón de «Mis parcelas, productos y máquinas».
 *
 * El nombre y el detalle salen de las mismas funciones que usa la lista (`pantallaMisCosas`), para que
 * la pantalla que pregunta «¿seguro que quieres borrarlo?» enseñe **exactamente lo mismo** que el
 * renglón que el agricultor acaba de tocar: es lo que le permite comprobar que es ese y no el de al lado.
 */
function fichaDeUnMaestro(tipo, registro) {
  const renglon = renglonDeUnMaestro(tipo, registro);
  return {
    tipo,
    id: registro.id,
    queEs: queEsLaCosa(tipo),
    etiqueta: renglon.nombre,
    cuando: "",
    filas: renglon.detalle ? [{ etiqueta: "", valor: renglon.detalle }] : [],
  };
}

/**
 * Un maestro, traducido al borrador del asistente.
 *
 * **Se copian todos los campos que el formulario manda**, y no solo los que se ven: al corregir, lo que
 * no viaja se queda en blanco en el servidor. Los campos que se preguntan salen aquí porque los lee
 * `cargaMaestro()`, que recorre el mapa `CAMPOS`; los que no se preguntan (el lote de un producto, la
 * fecha de compra de una máquina) van igual, para que corregir el nombre de una máquina no le borre
 * cuándo se compró.
 */
function borradorDeUnMaestro(tipo, registro) {
  const borrador = {};
  for (const [clave, spec] of Object.entries(CAMPOS)) {
    if (!clave.startsWith(`${tipo}.`)) continue;
    const valor = registro[spec.campo];
    // **Un «sí o no» viaja como "bool:true"/"bool:false"** (`opcionesDe`), y en la base de datos es
    // verdadero o falso. Sin esta conversión, la opción que ya estaba elegida **no salía marcada** al
    // corregir (se comparan como texto) y el agricultor tenía que volver a elegirla, con el riesgo de
    // elegir lo contrario de lo que había. Lo cazó el año del cuaderno, que trae un «sí o no» propio.
    if (typeof valor === "boolean") {
      borrador[spec.campo] = valor ? "bool:true" : "bool:false";
      continue;
    }
    // `null` y no `undefined`: `cargaMaestro()` no manda lo que está sin definir, y una ficha que se
    // corrige tiene que llegar entera. Con `null` viaja el hueco, que es lo que el agricultor tiene.
    borrador[spec.campo] = valor === undefined ? null : valor;
  }
  return borrador;
}

/** Cómo se llama esa cosa y qué se dice de ella en su renglón de «mis cosas». */
function renglonDeUnMaestro(tipo, registro) {
  if (tipo === "producto") {
    return {
      nombre: registro.nombre_comercial,
      detalle: [
        registro.numero_registro,
        registro.plazo_seguridad_dias
          ? `${registro.plazo_seguridad_dias} ${t("rotulos.dias_espera_corto", "")}`
          : "",
      ]
        .filter(Boolean)
        .join(" · "),
    };
  }
  if (tipo === "abono") {
    return { nombre: registro.nombre, detalle: composicionDelAbono(registro) };
  }
  if (tipo === "aplicador") {
    return { nombre: registro.nombre, detalle: registro.numero_carne || "" };
  }
  if (tipo === "asesor") {
    return {
      nombre: registro.nombre,
      detalle: [
        registro.numero_ropo ? `${t("rotulos.ropo_corto", "")} ${registro.numero_ropo}` : "",
        registro.ambito ? etiquetaDeValor("ambitos_asesor", registro.ambito) : "",
      ]
        .filter(Boolean)
        .join(" · "),
    };
  }
  if (tipo === "equipo") {
    return {
      nombre: registro.nombre,
      detalle: registro.fecha_proxima_iteaf
        ? `${t("rotulos.itv_hasta", "")} ${formateaFecha(registro.fecha_proxima_iteaf)}`
        : "",
    };
  }
  return {
    nombre: registro.alias,
    detalle: [etiquetaDeValor("tipos_instalacion", registro.tipo), registro.uso]
      .filter(Boolean)
      .join(" · "),
  };
}

/**
 * Un análisis de laboratorio, traducido al borrador del asistente.
 *
 * Los números del boletín se guardan **por clave** (`parametros` es una lista de `{clave, valor}`), y el
 * asistente los lee de un diccionario (`borrador.parametros[clave]`): se traducen en los dos sentidos.
 * Sin esto, corregir la fecha de un análisis le borraría los nueve números del boletín.
 */
function borradorDeUnAnalisis(uno) {
  const parametros = {};
  for (const parametro of uno.parametros || []) {
    if (parametro && parametro.clave !== undefined) parametros[parametro.clave] = parametro.valor;
  }
  return {
    tipo: uno.tipo,
    fecha_toma_muestra: uno.fecha_toma_muestra,
    fecha_resultado: uno.fecha_resultado,
    parcela_id: uno.parcela_id,
    instalacion_id: uno.instalacion_id,
    lote: uno.lote,
    laboratorio: uno.laboratorio,
    nif_laboratorio: uno.nif_laboratorio,
    numero_informe: uno.numero_informe,
    tipo_analisis: uno.tipo_analisis,
    sustancia_detectada: uno.sustancia_detectada,
    observaciones: uno.observaciones,
    parametros,
  };
}

/** Un análisis, contado como en su pantalla. */
function fichaDeUnAnalisis(uno) {
  return {
    tipo: "analitica",
    id: uno.id,
    queEs: queEsLaCosa("analitica"),
    etiqueta: nombreDeAnalisis(uno),
    cuando: formateaFecha(uno.fecha_toma_muestra),
    filas: [
      uno.laboratorio ? { etiqueta: t("rotulos.laboratorio", ""), valor: uno.laboratorio } : null,
      uno.numero_informe ? { etiqueta: t("rotulos.informe", ""), valor: uno.numero_informe } : null,
      uno.donde ? { etiqueta: t("analitica.sitio", ""), valor: uno.donde } : null,
    ].filter(Boolean),
  };
}

/** Una venta, traducida al borrador del asistente. */
function borradorDeUnaVenta(venta) {
  return {
    tipo: venta.tipo,
    fecha: venta.fecha,
    fecha_fin: venta.fecha_fin,
    producto: venta.producto,
    variedad: venta.variedad,
    cantidad: venta.cantidad,
    unidad: venta.unidad,
    lote: venta.lote,
    comprador: venta.comprador,
    numero_albaran: venta.numero_albaran,
    parcela_id: venta.parcela_id,
    // El grupo, cuando la partida salió de varias tierras a la vez: el asistente no lo pregunta, así que
    // si no viajara, corregir los kilos de una venta la dejaría sin decir de dónde salió.
    grupo_id: venta.grupo_id,
    observaciones: venta.observaciones,
    // **Y el dinero, por el mismo motivo y con más consecuencias** (T12, 03/10/2026): el asistente no
    // pregunta el importe, el precio ni el vencimiento —se apuntan en la pantalla de la entrega—, pero el
    // `PUT` es el mismo para el alta y para la corrección, así que **lo que no viaje se queda en blanco en
    // el servidor**: corregir los kilos de una entrega le borraría el importe y volvería a dejarla «sin
    // importe» (el caso A08) sin que nadie se enterara. Es el fallo que este proyecto ya ha pagado dos veces
    // —el campo de la máquina al cosechar y los datos de la portada del cuaderno— y aquí se cierra igual:
    // lo que el formulario no pregunta **se devuelve tal y como estaba**.
    importe: venta.importe,
    precio_unitario: venta.precio_unitario,
    vencimiento: venta.vencimiento,
    cosecha_id: venta.cosecha_id,
    contacto_id: venta.contacto_id,
  };
}

/** Una venta, contada como en su lista. */
function fichaDeUnaVenta(venta) {
  const v = (clave) => t(`venta.${clave}`, "");
  return {
    tipo: "venta",
    id: venta.id,
    queEs: queEsLaCosa("venta"),
    etiqueta: venta.producto || "",
    cuando: `${formateaFecha(venta.fecha)}${venta.fecha_fin ? ` — ${formateaFecha(venta.fecha_fin)}` : ""}`,
    filas: [
      venta.texto_cantidad ? { etiqueta: v("tabla_cuanto"), valor: venta.texto_cantidad } : null,
      venta.comprador ? { etiqueta: v("tabla_quien"), valor: venta.comprador } : null,
      venta.donde ? { etiqueta: v("tabla_donde"), valor: venta.donde } : null,
      venta.numero_albaran ? { etiqueta: v("tabla_albaran"), valor: venta.numero_albaran } : null,
    ].filter(Boolean),
  };
}

/**
 * Un plan de abono, traducido al borrador del asistente.
 *
 * Se lleva también el `detalle` (el reparto previsto: qué abono, cuánto y en qué momento) y el `grupo_id`
 * aunque el asistente no los pregunte: sin ellos, corregir los kilos previstos de un plan borraría el
 * reparto y las tierras de las que es.
 */
function borradorDeUnPlan(plan) {
  return {
    parcela_id: plan.parcela_id,
    grupo_id: plan.grupo_id,
    cultivo: plan.cultivo,
    superficie_ha: plan.superficie_ha,
    produccion_esperada_kg_ha: plan.produccion_esperada_kg_ha,
    necesidad_n: plan.necesidad_n,
    necesidad_p: plan.necesidad_p,
    necesidad_k: plan.necesidad_k,
    aportes_suelo_agua: plan.aportes_suelo_agua,
    notas: plan.notas,
    herramienta: plan.herramienta,
    analitica_id: plan.analitica_id,
    detalle: plan.detalle || [],
  };
}

/** Un plan de abono, contado como en su lista. */
function fichaDeUnPlan(plan) {
  const p = (clave) => t(`plan.${clave}`, "");
  const parcela = (estado.parcelas || []).find((x) => x.id === Number(plan.parcela_id));
  return {
    tipo: "plan",
    id: plan.id,
    queEs: queEsLaCosa("plan"),
    etiqueta: rellena(p("plan_de"), { cultivo: plan.cultivo }),
    cuando: "",
    filas: [
      parcela ? { etiqueta: t("cuaderno.tierra_y_parcela", ""), valor: parcela.alias } : null,
      plan.superficie_ha
        ? {
            etiqueta: t("rotulos.hectareas", ""),
            valor: `${formateaNumero(plan.superficie_ha, 2)} ${t("rotulos.hectareas_corto", "")}`,
          }
        : null,
      plan.necesidad_n !== null && plan.necesidad_n !== undefined
        ? {
            etiqueta: p("tabla_previsto"),
            valor: `N ${formateaNumero(plan.necesidad_n, 1)} · P ${formateaNumero(
              plan.necesidad_p,
              1,
            )} · K ${formateaNumero(plan.necesidad_k, 1)}`,
          }
        : null,
    ].filter(Boolean),
  };
}

/**
 * El formulario de un grupo: **una sola pregunta**, cómo se llama.
 *
 * Un grupo no se da de alta a mano (los junta el programa: las tierras que se llevan igual) y lo único
 * que el agricultor puede cambiar es el nombre —«Cebada (3 parcelas)» es como lo llama el programa;
 * él lo llamará «el de mi hermano»—. Se monta con los pasos del asistente, que es el formulario de
 * toda la aplicación: así el grupo se corrige igual que todo lo demás, con su GUARDAR LOS CAMBIOS.
 */
function pasosDeUnGrupo() {
  return [
    {
      titulo: t("etiquetas.grupo.nombre.pregunta", ""),
      pista: t("etiquetas.grupo.nombre.pista", ""),
      montar: () => montarCamposMaestro(["grupo.nombre"]),
      recoger: recogeCamposMaestro(["grupo.nombre"]),
    },
  ];
}

/**
 * Lo que se apuntó, con las mismas palabras que espera el asistente.
 *
 * Es la traducción de un apunte guardado al borrador del asistente, y **tiene que dar exactamente los
 * mismos nombres de campo que leen los pasos** (`estado.asistente.borrador[…]`, `cargaTratamiento()` y
 * sus hermanas). Si un nombre se cambia aquí y no allí, el asistente se abre con campos vacíos y el
 * agricultor guarda una corrección que borra datos: por eso hay pruebas que comprueban, campo a campo,
 * que lo que se lee del servidor es lo que sale en el resumen antes de guardar.
 */
function borradorDeUnApunte(tipo, apunte) {
  if (!apunte) return null;
  if (tipo === "tratamiento") {
    // El mismo que usa «lo mismo que la última vez» (`ultimoDeLaFinca`), que ya estaba escrito y
    // probado: no se copia, se reutiliza.
    return borradorDeTratamiento(apunte);
  }
  if (tipo === "fertilizacion") {
    return {
      fecha: apunte.fecha,
      parcela_id: apunte.parcela_id,
      grupo_id: apunte.grupo_id,
      superficie_ha: apunte.superficie_ha,
      fertilizante_id: apunte.fertilizante_id,
      kg_ha_producto: apunte.kg_ha_producto,
      observaciones: apunte.observaciones,
      tipo_fertilizacion: apunte.tipo_fertilizacion,
      modo_aplicacion: apunte.modo_aplicacion,
      momento: apunte.momento,
      numero_albaran: apunte.numero_albaran,
    };
  }
  if (tipo === "cosecha") {
    const detalles = apunte.detalles || {};
    return {
      fecha: apunte.fecha,
      parcela_id: apunte.parcela_id,
      // Qué se cosechó: vive dentro de `detalles` en la base de datos.
      producto: detalles.producto || null,
      cantidad_kg: detalles.cantidad_kg,
      semillas_siembra: apunte.semillas_siembra,
      plantas_cosechadas: apunte.plantas_cosechadas,
      sin_cosechar_ambiental: apunte.sin_cosechar_ambiental,
      restos_cosecha_depositados: apunte.restos_cosecha_depositados,
      equipo_id: apunte.equipo_id,
    };
  }
  const detalles = apunte.detalles || {};
  return {
    // La práctica de verdad («labrar», «podar»…), que es lo que el asistente espera en `tipo`: con
    // «labor» a secas, la corrección guardaría la labor como «otro trabajo».
    tipo: apunte.tipo,
    fecha: apunte.fecha,
    parcela_id: apunte.parcela_id,
    grupo_id: apunte.grupo_id,
    superficie_ha: apunte.superficie_ha,
    cultivo: apunte.cultivo,
    variedad: apunte.variedad,
    // Las observaciones de una labor se guardan dentro de `detalles.nota`, y el asistente las lee en
    // `borrador.detalles` como texto. Se traduce en los dos sentidos (ver `cargaLabor`).
    detalles: detalles.nota || null,
    observaciones: apunte.observaciones,
    equipo_id: apunte.equipo_id,
    cantidad_semilla_kg: apunte.cantidad_semilla_kg,
    dosis_siembra_kg_ha: apunte.dosis_siembra_kg_ha,
    lote_semilla: apunte.lote_semilla,
    material_tratado: apunte.material_tratado,
    tratamiento_semilla: apunte.tratamiento_semilla,
    fecha_tratamiento_semilla: apunte.fecha_tratamiento_semilla,
    eficacia_tratamiento_semilla: apunte.eficacia_tratamiento_semilla,
    material_adquirido: apunte.material_adquirido,
    fecha_adquisicion: apunte.fecha_adquisicion,
    siembra_directa: apunte.siembra_directa,
    densidad_plantacion: apunte.densidad_plantacion,
    marco_plantacion: apunte.marco_plantacion,
    volumen_agua: apunte.volumen_agua,
    unidad_agua: apunte.unidad_agua,
    origen_agua: apunte.origen_agua,
    sistema_riego: apunte.sistema_riego,
    numero_contador: apunte.numero_contador,
    nitratos_agua: apunte.nitratos_agua,
    fecha_establecimiento_cubierta: apunte.fecha_establecimiento_cubierta,
    tipo_cobertura: apunte.tipo_cobertura,
    anchura_cubierta_m: apunte.anchura_cubierta_m,
    anchura_libre_proyeccion_m: apunte.anchura_libre_proyeccion_m,
    restos_desbroce_depositados: apunte.restos_desbroce_depositados,
    restos_poda_depositados: apunte.restos_poda_depositados,
    animales_terceros: apunte.animales_terceros,
    animales_propios: apunte.animales_propios,
  };
}

/** La ruta del apunte, que es lo que hace falta para corregirlo o borrarlo. */
function rutaDelApunte(tipo, id) {
  if (tipo === "tratamiento") return `/api/tratamientos/${id}`;
  if (tipo === "fertilizacion") return `/api/fertilizaciones/${id}`;
  if (tipo === "cosecha") return `/api/cosecha/${id}`;
  return `/api/labores/${id}`;
}

async function deshacer(tipo, id) {
  const ruta = rutaDeAnulacion(tipo, id);
  if (!ruta) {
    pantallaInicio();
    return;
  }
  const resultado = await enviarOApuntar(ruta, { motivo: "Me he equivocado" }, `${tipo}-anular`);
  if (resultado.error) {
    avisarDelError(resultado.error);
    return;
  }
  await cargarDatos().catch(() => {});
  pantallaInicio();
}

// ------------------------------------------- corregir y borrar lo que ya está apuntado (ronda 91)

/**
 * La ruta para anular un apunte, sea del tipo que sea.
 *
 * Los tratamientos y los abonos tienen la suya. **Todo lo demás que se apunta en el cuaderno es una
 * labor** —una práctica del campo («labrar», «podar»…) o una cosecha—, y las dos se anulan por la ruta
 * de las labores porque las dos son la misma tabla. Se comprueba que el tipo sea de verdad una labor
 * (`etiquetas_labor`) para no anular una fila por un tipo que no existe: un «no sé qué es esto» no
 * puede acabar tachando un apunte del agricultor.
 */
function rutaDeAnulacion(tipo, id) {
  if (tipo === "tratamiento") return `/api/tratamientos/${id}/anular`;
  if (tipo === "fertilizacion") return `/api/fertilizaciones/${id}/anular`;
  if (tipo === "cosecha" || nombreDeLaPractica(tipo)) {
    return `/api/labores/${id}/anular`;
  }
  return "";
}

/**
 * **Las cosas que se pueden corregir y borrar**, y por dónde va cada una.
 *
 * POR QUÉ HAY UN REGISTRO Y NO UN `if` POR TIPO. Desde la ronda 91 se pueden corregir y borrar los
 * apuntes (tratamiento, abono, trabajo y cosecha), y desde la 92 también las tierras y los grupos —y
 * detrás van los papeles, las facturas, los análisis, las ventas, los planes, el almacén y las fichas
 * de lo que se usa—. Las cuatro cosas que hacen falta para eso son **las mismas siempre**: de dónde
 * sale la lista, por dónde se manda el cambio, cómo se cuenta en una ficha y con qué formulario se
 * abre. Teniéndolas en un solo sitio, añadir una cosa nueva es añadir cuatro líneas y **no** una
 * pantalla de borrar nueva (que es como acaban habiendo cinco pantallas de borrar y dos que se
 * olvidan de preguntar).
 *
 * Lo que **no** entra aquí son los apuntes del cuaderno, y no es un olvido: tienen cosas que ninguna
 * otra tiene (se pueden anular, se firmar, el asistente tiene un flujo distinto para cada uno) y están
 * resueltos con sus propias funciones desde la ronda 91. `cosaCargada()`, `rutaDeLaCosa()` y
 * `fichaDeLaCosa()` preguntan primero aquí y, si no está, van a las de los apuntes.
 */
const OTRAS_COSAS = {
  parcela: {
    // Cómo se llama lo que se borra, para la pantalla que pregunta («Tierra», «Grupo»…).
    que_es: "corregir.que_es_tierra",
    // De dónde sale la lista de esas cosas y por dónde se manda el cambio.
    lista: () => estado.parcelas,
    ruta: (id) => `/api/parcelas/${id}`,
    // Cómo se cuenta una de ellas en una ficha: el mismo formato que usan las tarjetas de la lista.
    ficha: fichaDeUnaTierra,
    // El formulario con el que se corrige (el mismo con el que se da de alta) y lo que hay que poner
    // en él para que salga con lo que ya estaba.
    pasos: () => pasosDeMaestro("parcela"),
    borrador: borradorDeUnaTierra,
    // A dónde se vuelve al terminar (el nombre que entiende `irAInicio`), y cómo se dice.
    volver_a: "mis_cosas",
    volver_texto: "corregir.volver_a_las_tierras",
    borrado_texto: "corregir.borrado_ok_tierra",
    // Lo que se dice al borrar una tierra y **no** se dice al borrar un apunte: de una tierra cuelgan
    // los apuntes, y el servidor no deja borrarla si tiene alguno.
    pista_borrar: "corregir.borrar_tierra_pista",
  },
  grupo: {
    que_es: "corregir.que_es_grupo",
    lista: () => estado.grupos,
    ruta: (id) => `/api/grupos/${id}`,
    ficha: fichaDeUnGrupo,
    pasos: () => pasosDeUnGrupo(),
    borrador: borradorDeUnGrupo,
    volver_a: "grupos",
    volver_texto: "corregir.volver_a_los_grupos",
    borrado_texto: "corregir.borrado_ok_grupo",
    pista_borrar: "corregir.borrar_grupo_pista",
  },
  // ── Las fichas de lo que se usa (ronda 93) ─────────────────────────────────────────────────────
  //
  // Los seis maestros comparten absolutamente todo: se dan de alta con el asistente (`pasosDeMaestro`),
  // se guardan por su ruta, y lo único que cambia es la lista de la que salen y cómo se llama cada uno.
  // Se ve en que sus cinco líneas son idénticas salvo la ruta: el `tipo` es el mismo que usa el
  // asistente, así que **corregir abre el formulario del alta con lo que ya estaba puesto**.
  producto: cosaDeUnMaestro("producto", "corregir.que_es_producto", () => estado.productos),
  abono: cosaDeUnMaestro("abono", "corregir.que_es_abono", () => estado.abonos),
  aplicador: cosaDeUnMaestro("aplicador", "corregir.que_es_aplicador", () => estado.aplicadores),
  asesor: cosaDeUnMaestro("asesor", "corregir.que_es_asesor", () => estado.asesores),
  equipo: cosaDeUnMaestro("equipo", "corregir.que_es_equipo", () => estado.equipos),
  instalacion: cosaDeUnMaestro("instalacion", "corregir.que_es_instalacion", () => estado.instalaciones),
  // ── Y lo que se apunta fuera del cuaderno: un análisis, una venta y el plan de abono ────────────
  //
  // Los tres tienen su propio asistente (no el de los maestros) y su propia ruta, y los tres se
  // corrigen con el asistente con el que se hacen.
  analitica: {
    que_es: "corregir.que_es_analisis",
    lista: () => estado.analiticas,
    ruta: (id) => `/api/analiticas/${id}`,
    ficha: fichaDeUnAnalisis,
    pasos: () => pasosAnalitica(),
    borrador: borradorDeUnAnalisis,
    volver_a: "analisis",
  },
  venta: {
    que_es: "corregir.que_es_venta",
    lista: () => estado.ventas,
    ruta: (id) => `/api/ventas/${id}`,
    ficha: fichaDeUnaVenta,
    pasos: () => pasosVenta(),
    borrador: borradorDeUnaVenta,
    volver_a: "ventas",
  },
  plan: {
    que_es: "corregir.que_es_plan",
    lista: () => estado.planes,
    ruta: (id) => `/api/planes/${id}`,
    ficha: fichaDeUnPlan,
    pasos: () => pasosPlanAbonado(),
    borrador: borradorDeUnPlan,
    volver_a: "planes",
  },
  // ── Los papeles y las facturas (ronda 93) ───────────────────────────────────────────────────────
  //
  // Estas dos **no se corrigen con el asistente**: cada una tiene su propia pantalla (la de guardar un
  // papel, con sus seis campos; y la de revisar una factura, con sus líneas). Se dice aquí, en `corregir`,
  // y `corregirAlgo()` la usa en vez de abrir el asistente. Es la misma decisión de siempre: corregir
  // abre **el formulario con el que se guardó**, y no una copia que se quedaría sin los campos nuevos.
  documento: {
    que_es: "corregir.que_es_documento",
    lista: () => (estado.documentos || {}).documentos || [],
    ruta: (id) => `/api/documentos/${id}`,
    ficha: fichaDeUnDocumento,
    corregir: (papel) => {
      estado.documentoEnEdicion = papel;
      estado.errorDocumentos = "";
      pantallaNuevoDocumento();
    },
    // Se vuelve a la lista de papeles **por su acción** (`papel-ver-todos`), no por un nombre de pantalla:
    // el nombre `papel` de `irAInicio` es otra cosa (descargar el cuaderno en papel). Eso es exactamente
    // el fallo que se arregló en la ronda 92 con `mis_cosas`: un destino que no lleva a donde dice.
    volver_accion: "papel-ver-todos",
  },
  factura: {
    que_es: "corregir.que_es_factura",
    lista: () => estado.facturasLista || [],
    ruta: (id) => `/api/facturas/${id}`,
    ficha: fichaDeUnaFactura,
    // **Corregir una factura es revisar lo que se guardó** (ronda 93). Se abre la misma pantalla que
    // confirma una factura recién leída —la que enseña los ocho datos de la cabecera y las líneas, toda
    // editable—, pero con lo que ya está en el cuaderno puesto y guardando con `PUT` a esa misma
    // factura. No se inventa una pantalla nueva: corregir una factura **es el mismo trabajo** (mirar lo
    // que dice el papel y arreglar lo que esté mal), y dos pantallas para lo mismo acabarían diciendo
    // cosas distintas. El porqué del `PUT` está en `guardarFactura()`.
    corregir: (factura) => {
      const facturas = estadoDeLasFacturas();
      facturas.corrigiendo = factura;
      facturas.interpretacion = facturaComoInterpretacion(factura);
      facturas.fichero = null;
      facturas.error = "";
      pantallaInterpretacionDeLaFactura();
    },
    // Se vuelve a la lista de facturas **por su acción** (`facturas-abrir`), no por un nombre de
    // pantalla: es la misma decisión que con los papeles (`volver_accion`).
    volver_accion: "facturas-abrir",
  },
  // ── El año del cuaderno (la campaña), ronda 93 ──────────────────────────────────────────────────
  //
  // Es lo último que faltaba por poder tocar, y lo que más pesa: **de la campaña cuelga el año entero**
  // (cada apunte guarda su `campana_id`), así que un año mal escrito dejaba todos los apuntes de ese año
  // colgando de un año que no es el suyo. No tiene `volver_accion`: su lista se abre con `irAInicio`
  // (`campanas`), que es lo que usan las tierras, los grupos, las ventas y los planes.
  campana: {
    que_es: "corregir.que_es_campana",
    lista: () => estado.campanas || [],
    ruta: (id) => `/api/campanas/${id}`,
    ficha: fichaDeUnaCampana,
    pasos: () => pasosDeMaestro("campana"),
    borrador: (registro) => borradorDeUnMaestro("campana", registro),
    volver_a: "campanas",
    volver_texto: "corregir.volver_a_los_anos",
  },
};

/**
 * Un año del cuaderno, contado como en su ficha de la lista.
 *
 * Se reutiliza **la misma forma** (`etiqueta`, `filas`, `queEs`) que la de una tierra o un apunte, para
 * que la pantalla que pregunta «¿seguro que quieres borrarlo?» enseñe lo mismo que la ficha que se acaba
 * de tocar: es lo que permite comprobar que es ese año y no el de al lado.
 */
function fichaDeUnaCampana(campana) {
  const c = (clave) => t(`campanas.${clave}`, "");
  return {
    tipo: "campana",
    id: campana.id,
    queEs: queEsLaCosa("campana"),
    etiqueta: String(campana.anio || ""),
    cuando: campana.cerrada ? c("cerrado") : c("abierto"),
    filas: [
      campana.fecha_inicio
        ? { etiqueta: c("empieza"), valor: formateaFecha(campana.fecha_inicio) }
        : null,
      campana.fecha_fin ? { etiqueta: c("termina"), valor: formateaFecha(campana.fecha_fin) } : null,
      // Lo que hay dentro, que es **lo que explica por qué no se puede quitar**. Se cuenta con el
      // ayudante de siempre, así que con una sola cosa dice «1 cosa» y no «1 cosas».
      campana.cuantas_cosas === null || campana.cuantas_cosas === undefined
        ? null
        : {
            etiqueta: c("rotulo"),
            valor: campana.cuantas_cosas
              ? conCuenta(t("campanas", {}), "dentro", campana.cuantas_cosas)
              : c("vacio"),
          },
    ].filter(Boolean),
  };
}

/** Un papel, contado como en su lista. */
function fichaDeUnDocumento(papel) {
  const d = (clave) => t(`documentos.${clave}`, "");
  return {
    tipo: "documento",
    id: papel.id,
    queEs: queEsLaCosa("documento"),
    etiqueta: papel.titulo || "",
    cuando: papel.fecha ? formateaFecha(papel.fecha) : "",
    filas: [
      papel.etiqueta_tipo ? { etiqueta: d("que_es"), valor: papel.etiqueta_tipo } : null,
      papel.carpeta ? { etiqueta: d("carpeta"), valor: papel.carpeta } : null,
      papel.quien ? { etiqueta: d("quien"), valor: papel.quien } : null,
      { etiqueta: d("el_fichero"), valor: papel.tiene_fichero ? d("tiene_fichero") : d("no_tiene_fichero") },
    ].filter(Boolean),
  };
}

/** Una factura, contada como en su lista. */
function fichaDeUnaFactura(factura) {
  const f = (clave) => t(`facturas.${clave}`, "");
  return {
    tipo: "factura",
    id: factura.id,
    queEs: queEsLaCosa("factura"),
    etiqueta: factura.proveedor || "",
    cuando: factura.fecha ? formateaFecha(factura.fecha) : "",
    filas: [
      factura.numero ? { etiqueta: f("tabla_numero"), valor: factura.numero } : null,
      factura.total !== null && factura.total !== undefined
        ? { etiqueta: f("tabla_total"), valor: formateaNumero(factura.total, 2) }
        : null,
    ].filter(Boolean),
  };
}

/**
 * Una ficha de lo que se usa, montada de la misma forma que las demás.
 *
 * Existe porque los seis maestros solo se diferencian en la lista de la que salen, su ruta y su nombre:
 * escribir seis veces las mismas cinco líneas es la forma más segura de que a uno se le olvide la mitad
 * (y de que corregir una máquina acabe abriendo el formulario de un abono).
 */
function cosaDeUnMaestro(tipo, que_es, lista) {
  return {
    que_es,
    lista,
    ruta: (id) => `${MAESTROS_API[tipo].ruta}/${id}`,
    ficha: (registro) => fichaDeUnMaestro(tipo, registro),
    pasos: () => pasosDeMaestro(tipo),
    borrador: (registro) => borradorDeUnMaestro(tipo, registro),
    // Se vuelve a la pantalla de la que salen, que es «Mis parcelas, productos y máquinas».
    volver_a: "mis_cosas",
  };
}

/** ¿Esa cosa es una de las de arriba? (lo contrario de un apunte del cuaderno). */
function esOtraCosa(tipo) {
  return Boolean(OTRAS_COSAS[tipo]);
}

/** El apunte que se está mirando, buscado entre los que hay cargados. */
function apunteCargado(tipo, id) {
  const coleccion =
    tipo === "tratamiento"
      ? estado.tratamientos
      : tipo === "fertilizacion"
        ? estado.fertilizaciones
        : estado.labores;
  return (coleccion || []).find((apunte) => Number(apunte.id) === Number(id)) || null;
}

/** Lo que se está mirando (un apunte o una tierra o un grupo), buscado entre lo que hay cargado. */
function cosaCargada(tipo, id) {
  const cosa = OTRAS_COSAS[tipo];
  if (!cosa) return apunteCargado(tipo, id);
  return (cosa.lista() || []).find((una) => Number(una.id) === Number(id)) || null;
}

/** Por dónde se corrige y se borra esa cosa. */
function rutaDeLaCosa(tipo, id) {
  const cosa = OTRAS_COSAS[tipo];
  return cosa ? cosa.ruta(id) : rutaDelApunte(tipo, id);
}

/**
 * Los dos botones de una ficha: **CORREGIR** y **BORRAR**.
 *
 * El mismo par en las tres pantallas que los tienen (los apuntes del cuaderno, las tierras y los
 * grupos), y por eso se prepara en un solo sitio: el día que se cambie el orden, la clase o el texto de
 * uno, se cambia en los tres. **CORREGIR va primero**: es lo que arregla el cuaderno sin dejar hueco, y
 * BORRAR es lo único que quita algo, así que no puede ser lo que más a mano esté (y va en el color de
 * peligro, que es la única señal de la aplicación que dice «esto quita»).
 */
function botonesDeCorregirYBorrar(tipo, id) {
  const cosa = OTRAS_COSAS[tipo];
  const botones = [];
  // Hay fichas que hoy solo se pueden borrar (una factura, hasta que su corregir esté montado): un botón
  // de CORREGIR que no lleva a ninguna parte promete una salida que no existe, que es lo que este
  // programa no hace. Se dice en la propia cosa (`sin_corregir`).
  if (!(cosa && cosa.sin_corregir)) {
    botones.push({
      etiqueta: t("corregir.boton", ""),
      accion: "cosa-corregir",
      datos: { tipo, id },
      clase: "boton-claro",
    });
  }
  // **Un apunte firmado no se borra: se anula** (30/09/2026). El servidor no lo deja borrar y la pantalla que
  // pregunta lo dice, pero el botón seguía diciendo «BORRAR»: el agricultor pulsaba creyendo que iba a
  // quitar algo y se encontraba otra cosa. Lo pide el diseño de escritorio del cuaderno
  // (`docs/stitch/escritorio/cuaderno.png`: «los apuntes firmados llevan su sello y el botón de borrado
  // sustituido por ANULAR»). El rótulo lo decide quien llama, que es quien sabe si está firmado.
  botones.push({
    etiqueta: elApunteEstaFirmado(tipo, id) ? t("corregir.anular_este", "") : t("corregir.borrar", ""),
    accion: "cosa-borrar",
    datos: { tipo, id },
    clase: "boton-peligro",
  });
  return botones;
}

/** Cómo se cuenta esa cosa en una ficha (lo mismo que enseña su tarjeta en la lista). */
function fichaDeLaCosa(tipo, registro) {
  const cosa = OTRAS_COSAS[tipo];
  return cosa ? cosa.ficha(registro) : fichaDeUnApunte(tipo, registro);
}

/** El texto que dice cómo se llama esa cosa («Tierra», «Grupo», «Producto»…). */
function queEsLaCosa(tipo) {
  const cosa = OTRAS_COSAS[tipo];
  return cosa ? t(cosa.que_es, "") : "";
}

/** ¿Ese apunte está firmado? Un apunte firmado no se borra: se anula (ver `corregir.esta_firmado`). */
function elApunteEstaFirmado(tipo, id) {
  // La firma guarda la entidad como «tratamiento», «fertilizacion» o «labor»: una práctica del campo y
  // una cosecha se firman como «labor», que es la tabla donde viven las dos. Las tierras y los grupos
  // no se firman: la firma es del cuaderno o de un apunte suelto.
  if (esOtraCosa(tipo)) return false;
  const entidad = tipo === "tratamiento" || tipo === "fertilizacion" ? tipo : "labor";
  return (estado.firmas || []).some(
    (firma) => firma.entidad === entidad && Number(firma.entidad_id) === Number(id),
  );
}

/** CORREGIR: abre el asistente con lo que ya había, sea un apunte o una tierra. */
async function corregirAlgo(tipo, id) {
  const registro = cosaCargada(tipo, id);
  const cosa = OTRAS_COSAS[tipo];
  if (!registro) {
    // No está entre los cargados (la lista es vieja, o alguien lo ha borrado desde otro sitio): se
    // recarga y se vuelve a la pantalla de la que salió. Abrir el formulario vacío guardaría datos en
    // blanco encima, que es justo lo que no puede pasar.
    await cargarDatos().catch(() => {});
    pantallaInicio();
    return;
  }
  // Hay cosas que no se corrigen con el asistente sino con **su propia pantalla** (un papel se corrige
  // en la pantalla con la que se guarda, con sus seis campos). Lo dice la propia cosa en `corregir`, y
  // se le hace caso antes de intentar abrir el asistente: un `pasos` que no existe dejaría la pantalla
  // en blanco.
  if (cosa && cosa.corregir) {
    cosa.corregir(registro);
    return;
  }
  corregirApunte(registro, tipo);
}

/**
 * BORRAR: primero se pregunta, y la pregunta lleva **lo que va a desaparecer**.
 *
 * POR QUÉ NO SE BORRA DIRECTAMENTE. Es la única acción de la aplicación que quita algo del cuaderno sin
 * dejar nada en su sitio, y en un móvil, en el campo y con guantes, un toque de más pasa. La pantalla
 * que pregunta enseña el mismo contenido que la tarjeta que se acaba de tocar (misma ficha) para poder
 * comprobar que es esa y no la de al lado, y ofrece **la otra salida**: corregirla.
 *
 * Y **si el apunte está firmado, ni se ofrece borrar**: se dice que no se puede y se ofrece anularlo,
 * que es lo que sí vale. Un aviso que manda a hacer algo que no existe deja al agricultor sin salida.
 */
async function preguntarSiBorrarAlgo(tipo, id) {
  const registro = cosaCargada(tipo, id);
  const cosa = OTRAS_COSAS[tipo];
  if (!registro) {
    await cargarDatos().catch(() => {});
    pantallaInicio();
    return;
  }
  const cb = (clave) => t(`corregir.${clave}`, "");
  const ficha = fichaDeLaCosa(tipo, registro);
  const firmado = elApunteEstaFirmado(tipo, id);

  const volverA = cosa ? cosa.volver_a : "cuaderno";
  const acciones = [];
  if (firmado) {
    // Firmado: la única salida honesta es anularlo, que lo deja tachado y con la firma cuadrando.
    acciones.push({
      etiqueta: cb("anular_este"),
      accion: "cosa-anular",
      datos: { tipo, id },
      clase: "boton-principal",
      sencillo: true,
    });
  } else {
    acciones.push({
      etiqueta: cb("boton_borrar_si"),
      accion: "cosa-borrar-si",
      datos: { tipo, id },
      clase: "boton-peligro",
      sencillo: true,
    });
    // **MEJOR CORREGIRLO solo si de verdad se puede corregir**: hay fichas que hoy solo se borran (una
    // factura), y ofrecer ahí la otra salida mandaría al agricultor a un botón que no existe.
    if (!(cosa && cosa.sin_corregir)) {
      acciones.push({
        etiqueta: cb("boton_mejor_corregirlo"),
        accion: "cosa-corregir",
        datos: { tipo, id },
        clase: "boton-claro",
        sencillo: true,
      });
    }
  }
  acciones.push(botonParaVolver(cosa));

  // Las dos cosas que se dicen **siempre**, y que son la mitad de la pantalla: que se puede corregir
  // en vez de borrar, y que lo que se borra no desaparece sin dejar rastro. De una tierra, además, se
  // dice lo suyo: de ella cuelgan los apuntes, y el servidor no la deja borrar si los tiene.
  //
  // Y cuando está firmado, se explica **qué significa anular** (diseño de Stitch de la ronda 92): no es
  // lo mismo que borrar, y el agricultor tiene que entender qué va a quedar en su cuaderno antes de
  // pulsar. Un aviso que solo dice «no se puede» deja al agricultor sin saber qué está eligiendo.
  const avisos = firmado
    ? [{ texto: cb("que_es_anular") }]
    : [
        { texto: cosa && cosa.pista_borrar ? t(cosa.pista_borrar, "") : cb("borrar_mejor_corregir") },
        { texto: cb("borrar_queda_rastro") },
      ].filter((aviso) => aviso.texto);

  montar(() =>
    confirmacion({
      // La pregunta, en grande: lo que viene después de esta pantalla no se puede deshacer.
      pregunta: firmado ? cb("esta_firmado") : cb("pregunta_borrar"),
      pista: firmado ? "" : cb("borrar_pista"),
      // Lo que va a desaparecer, con los mismos datos que la ficha que se acaba de tocar.
      //
      // **Ojo con la forma de `filas`**: la pieza `resumenDelApunte` espera **pares**
      // (`[[etiqueta, valor], …]`, que es como los prepara `datosDelResumen`) y no objetos
      // (`{etiqueta, valor}`). Pasarle objetos no se ve en las pruebas —el componente no se dibuja en
      // ellas, solo se mira lo que se le pide— y en un navegador la pantalla se queda **en blanco**:
      // lo cazó la comprobación en un navegador de verdad, que es justo para lo que está.
      contenido: resumenDelApunte({
        // El rótulo de la caja (diseño de Stitch de la ronda 92): una caja de datos sin título es una
        // caja de datos, y aquí lo que se lee **es lo que va a desaparecer**. Se pide el texto al
        // servidor, como todos.
        titulo: cb("lo_que_desaparece"),
        filas: [
          [ficha.queEs, ficha.etiqueta],
          ...ficha.filas.map((fila) => [fila.etiqueta, fila.valor]),
        ],
      }),
      avisos,
      acciones,
    }),
  );
}

/**
 * El botón que devuelve a la lista de la que se salió.
 *
 * Casi todas las cosas vuelven **por el nombre de su pantalla** (`irAInicio`: `mis_cosas`, `grupos`,
 * `analisis`, `ventas`, `planes`), pero las dos cuya lista se abre **por su acción** (los papeles y las
 * facturas) llevan `volver_accion`. Es el fallo que se arregló en la ronda 92: un destino que no lleva a
 * donde dice. Está en una función porque lo usan las dos pantallas que preguntan y confirman el borrado.
 */
function botonParaVolver(cosa, clase = "boton-claro") {
  const etiqueta = cosa && cosa.volver_texto ? t(cosa.volver_texto, "") : accion("volver");
  if (cosa && cosa.volver_accion) {
    return { etiqueta, accion: cosa.volver_accion, clase, sencillo: true };
  }
  return {
    etiqueta,
    accion: "inicio",
    datos: { ir: cosa ? cosa.volver_a : "cuaderno" },
    clase,
    sencillo: true,
  };
}

/** El borrado, ya decidido: se manda al servidor y se dice qué ha pasado. */
async function borrarAlgo(tipo, id) {
  const cosa = OTRAS_COSAS[tipo];
  const resultado = await mandarCambio(rutaDeLaCosa(tipo, id), "DELETE");
  if (resultado.error) {
    avisarDelError(resultado.error);
    return;
  }
  await cargarDatos().catch(() => {});
  const cb = (clave) => t(`corregir.${clave}`, "");
  montar(() =>
    confirmacion({
      titulo: cb("borrado_titulo"),
      // Lo que se dice después de borrar: cada cosa tiene su frase (una tierra, un grupo), y las demás
      // —un producto, una máquina, un análisis, una venta— usan la genérica, que dice lo único que
      // comparten. Los apuntes del cuaderno llevan la suya, que habla de apuntes.
      pista: cosa
        ? cosa.borrado_texto
          ? t(cosa.borrado_texto, "")
          : cb("borrado_ok_cosa")
        : cb("borrado_ok"),
      ayuda: { titulo: cb("rastro_titulo"), texto: cb("borrar_queda_rastro") },
      acciones: [
        // El botón grande devuelve a la lista de la que salió: por su pantalla o, en los papeles y las
        // facturas, por su acción (ver `volver_accion`).
        botonParaVolver(cosa, "boton-principal"),
        { etiqueta: accion("volver"), accion: "ir-inicio", clase: "boton-claro", sencillo: true },
      ],
    }),
  );
}

/** Anular: lo que sí se puede hacer con un apunte firmado. Queda tachado y con su motivo. */
async function anularAlgo(tipo, id) {
  const ruta = rutaDeAnulacion(tipo, id);
  if (!ruta) {
    pantallaInicio();
    return;
  }
  const resultado = await enviarOApuntar(ruta, { motivo: "Me he equivocado" }, `${tipo}-anular`);
  if (resultado.error) {
    avisarDelError(resultado.error);
    return;
  }
  await cargarDatos().catch(() => {});
  const cb = (clave) => t(`corregir.${clave}`, "");
  montar(() =>
    confirmacion({
      titulo: cb("borrado_titulo"),
      pista: cb("anulado_ok"),
      acciones: [
        {
          etiqueta: cb("volver_al_cuaderno"),
          accion: "inicio",
          datos: { ir: "cuaderno" },
          clase: "boton-principal",
          sencillo: true,
        },
        { etiqueta: accion("volver"), accion: "ir-inicio", clase: "boton-claro", sencillo: true },
      ],
    }),
  );
}

async function sacarPapel() {
  try {
    // **El año que se está mirando** (06/10/2026), como las otras tres descargas del cuaderno: la ruta,
    // sin decírselo, sacaba la campaña **más nueva** de la finca (`_campana`, `anio.desc()`), así que el
    // papel que se imprimía podía ser de otro año que el que se tenía delante.
    const respuesta = await api(conLaCampana("/api/cuaderno/pdf"));
    if (!respuesta.ok) throw new Error(mensaje("no_se_pudo"));
    const blob = await respuesta.blob();
    const enlace = document.createElement("a");
    enlace.href = URL.createObjectURL(blob);
    enlace.download = "cuaderno.pdf";
    document.body.appendChild(enlace);
    enlace.click();
    enlace.remove();
  } catch (error) {
    avisarDelError(error.message);
  }
}

/**
 * El fichero de datos del cuaderno.
 *
 * Es el registro en un formato que se puede guardar, abrir con Excel y entregar si algún día lo
 * piden. La ley pide **llevar el registro** y poder enseñarlo —y deja claro que usar un programa
 * propio es válido—, mientras que mandarlo a la Junta es **voluntario** (artículo 10.2 del Real
 * Decreto 1054/2022). Así que este fichero es lo que de verdad hace falta tener, y por eso está
 * en la misma pantalla que el papel.
 */
async function sacarDatos() {
  try {
    // **El año que se está mirando**, por el mismo motivo que el cuaderno de la Junta: sin esto, el
    // servidor sacaba el año **más nuevo** de la finca mientras el fichero se llamaba como el año que
    // el agricultor tenía delante. Y el fichero tiene que ser el que se está viendo.
    const campana = estado.campana ? `?campana_id=${estado.campana.id}` : "";
    const respuesta = await api(`/api/cuaderno/export.csv${campana}`);
    if (!respuesta.ok) throw new Error(mensaje("no_se_pudo"));
    const blob = await respuesta.blob();
    const enlace = document.createElement("a");
    enlace.href = URL.createObjectURL(blob);
    const anio = estado.campana ? estado.campana.anio : "";
    enlace.download = `cuaderno_${anio}.csv`;
    document.body.appendChild(enlace);
    enlace.click();
    enlace.remove();
  } catch (error) {
    avisarDelError(error.message);
  }
}

function irAInicio(irA) {  switch (irA) {
    case "echar_producto":
      abrirAsistente("tratamiento", pasosTratamiento());
      break;
    case "abonar":
      abrirAsistente("fertilizacion", pasosAbonar());
      break;
    case "trabajo":
      // «¿Qué has hecho?»: la pregunta y las prácticas que no tienen botón propio en la pantalla de
      // inicio. Se monta con la pieza de la confirmación (la de las pantallas pequeñas) porque tiene su
      // forma: una pregunta grande arriba y sus caminos debajo. El último botón saca de aquí sin apuntar
      // nada.
      montar(() =>
        confirmacion({
          pregunta: t("etiquetas.labor.que_has_hecho.pregunta", ""),
          acciones: [
            ...(t("trabajos", []) || []).map((trabajo) => ({
              etiqueta: trabajo.texto,
              icono: trabajo.icono,
              accion: "trabajo",
              datos: { tipo: trabajo.id },
            })),
            { etiqueta: accion("volver"), accion: "ir-inicio", clase: "boton-claro", sencillo: true },
          ],
        }),
      );
      break;
    case "mi_cuaderno":
      pantallaCuaderno();
      break;
    case "mis_cosas":
      // `mis_cosas` es el nombre que usa el botón de volver de lo que se da de alta (una tierra, un
      // producto, un abono…) y **faltaba aquí** (ronda 93): el botón decía «VOLVER A MIS TIERRAS» y
      // llevaba a la pantalla de inicio, porque un `ir` que no está en esta lista cae en el `default`.
      // Lo encontró una prueba que pulsa el botón y mira **en qué pantalla acaba**, no lo que dice el
      // `data-ir`.
      pantallaMisCosas();
      break;
    case "grupos":
      pantallaGrupos();
      break;
    case "planes":
      pantallaPlanes();
      break;
    case "analisis":
      pantallaAnaliticas();
      break;
    case "medidas":
      pantallaMedidas();
      break;
    case "ventas":
      pantallaVentas();
      break;
    case "cultivos":
      // El destino de «VER QUÉ HAY SEMBRADO», que es donde acaba la corrección del cultivo de una tierra
      // (ronda 93). Se añade aquí por el mismo motivo que `mis_cosas` en la ronda 93: un `ir` que no esté
      // en esta lista **cae en el `default`** y lleva al inicio sin decir nada, y el botón diría «QUÉ HAY
      // SEMBRADO» mientras el agricultor aparece en la pantalla de casa.
      pantallaCultivos();
      break;
    case "campanas":
      // Los años del cuaderno (ronda 93): es a donde vuelven el botón de corregir y el de borrar un año, y
      // a donde lleva el final de «empezar un año nuevo».
      pantallaCampanas();
      break;
    case "papel":
      sacarPapel();
      break;
    case "maquinaria":
      // La maquinaria (T14): su renglón del menú lleva la acción `maquinaria-ver`, pero también se llega
      // aquí con `ir`, y un `ir` que no esté en esta lista cae en el `default` y lleva al inicio sin decir
      // nada. Se pone por el mismo motivo que `cultivos` y `campanas`.
      abrirLaMaquinaria();
      break;
    case "ayuda":
      pantallaAyuda();
      break;
    default:
      pantallaInicio();
  }
}

function repetir() {
  const repetido = repetirUltimo(ultimoParaRepetir(), hoyISO());
  if (!repetido) {
    pantallaInicio();
    return;
  }
  const pasos =
    repetido.tipo === "tratamiento"
      ? pasosTratamiento()
      : repetido.tipo === "fertilizacion"
        ? pasosAbonar()
        : pasosLabor(repetido.tipo);
  abrirAsistente(repetido.tipo, pasos);
  estado.asistente.borrador = { ...repetido.datos };
  estado.asistente.indice = pasos.length - 1; // directo al resumen: se cambia el día y se apunta
  estado.asistente.tituloForzado = t("etiquetas.cuaderno.repetir.pregunta", "");
  estado.asistente.pistaForzada = t("etiquetas.cuaderno.repetir.pista", "");
  pintarAsistente();
}

/** Elegir entre traer la parcela del SIGPAC, verla en el mapa o apuntarla a mano. */
function pantallaTraerOApuntar() {
  const s = (clave) => t(`sigpac.${clave}`, "");
  const m = (clave) => t(`mapa.${clave}`, "");
  const c = (clave) => t(`cuaderno_cyl.${clave}`, "");

  const acciones = [
    {
      etiqueta: m("elegir_en_el_mapa"),
      icono: "🗺️",
      accion: "mapa-abrir",
      clase: "boton-principal",
    },
  ];
  // Traer el cuaderno de la Junta: para quien ya lo lleva en el Cuecyl, esto le apunta sus tierras de una
  // vez, con su polígono, su parcela, su recinto y su cultivo. Va el segundo porque el mapa es lo que
  // entiende cualquiera, y este solo vale para quien tiene cuaderno de la Junta.
  if (c("traer") !== "") {
    acciones.push({
      etiqueta: c("traer"),
      icono: "📄",
      accion: "cuaderno-abrir",
      clase: "boton-claro",
    });
  }
  acciones.push({ etiqueta: s("traer"), accion: "sigpac-si", clase: "boton-claro" });
  acciones.push({ etiqueta: s("a_mano"), accion: "sigpac-no", clase: "boton-claro" });

  montar(() =>
    confirmacion({
      titulo: s("titulo"),
      pista: s("explica"),
      // La pista del final va **después de los botones**: avisa de que el mapa necesita conexión, y se lee
      // cuando ya se está decidiendo cuál de los caminos coger.
      contenido: html`<p className="pista-campo">${m("necesita_conexion")}</p>`,
      acciones,
    }),
  );
}

// ------------------------------------------- el cuaderno de la Junta (el Cuecyl)

/**
 * Traer las tierras del cuaderno que el agricultor descarga de la aplicación de la Junta.
 *
 * **Para qué está esto.** En Castilla y León, quien lleva el cuaderno en la aplicación de la
 * Junta (el Cuecyl) ya tiene ahí escritas todas sus parcelas: las que declaró en la Solicitud
 * Única, con su polígono, su parcela, su recinto, su cultivo y sus hectáreas. En el cuaderno de
 * una explotación normal son decenas de líneas. Volver a teclearlas sería una tontería y, sobre
 * todo, una fuente de errores: un número cambiado y la tierra ya no es la suya.
 *
 * **Cómo funciona, y por qué en dos pasos.** Primero se lee el fichero y se enseña lo que trae
 * («tu cuaderno tiene 54 tierras en 7 pueblos, 128,28 hectáreas»), y solo después se apunta. Dar
 * de alta 51 parcelas sin avisar no es una función, es una sorpresa. Y el segundo paso se puede
 * repetir las veces que haga falta: la misma tierra no se apunta dos veces.
 */
function estadoDelCuadernoCyl() {
  if (!estado.cuadernoCyl) {
    estado.cuadernoCyl = {
      leyendo: false,
      fichero: null,
      resumen: null,
      resultado: null,
      error: "",
    };
  }
  return estado.cuadernoCyl;
}

/** Las filas del resumen: solo las que tienen algo que enseñar. */
function filasDelCuaderno(cuaderno, c) {
  const filas = [];
  if (cuaderno.anio) filas.push([c("resumen_campana"), String(cuaderno.anio)]);
  filas.push([c("resumen_titular"), cuaderno.titular || cuaderno.nif || ""]);
  const r = cuaderno.resumen || {};
  filas.push([c("resumen_lineas"), String(r.lineas ?? "")]);
  filas.push([c("resumen_tierras"), String(r.tierras ?? "")]);
  filas.push([c("resumen_hectareas"), formateaNumero(r.hectareas_declaradas ?? 0)]);
  if ((r.municipios || []).length) {
    filas.push([c("resumen_pueblos"), r.municipios.join(" · ")]);
  }
  if ((r.cultivos || []).length) {
    filas.push([c("resumen_cultivos"), r.cultivos.join(" · ")]);
  }
  // La zona de nitratos y los trozos solo se enseñan si hay: un «0» en un resumen invita a
  // pensar que se ha mirado algo que no se ha mirado.
  if (r.en_zona_nitratos) {
    filas.push([c("resumen_nitratos"), String(r.en_zona_nitratos)]);
  }
  if (r.tierras_partidas) {
    filas.push([c("resumen_partidas"), String(r.tierras_partidas)]);
  }
  return filas;
}

/**
 * «Traer tus tierras del cuaderno de la Junta»: la pantalla, ya en React (ver `docs/REACT.md`).
 *
 * Tres estados y una regla que no se toca: **leer el fichero no apunta nada**. Primero se enseña lo
 * que trae —con sus cuentas y sus tierras— y solo cuando el agricultor confirma se apunta. Traer 51
 * tierras sin preguntar sería meterle en el cuaderno cosas que no ha visto.
 *
 * Lo que se prepara aquí: las cuentas del resultado ya en frases (y **sin las que están a cero**,
 * menos «tierras nuevas», que sale siempre porque el cero también hay que decirlo), las filas del
 * resumen del fichero —con los trozos ya en texto— y los avisos de las dos cosas.
 */
function pantallaCuadernoDeLaJunta() {
  const c = (clave) => t(`cuaderno_cyl.${clave}`, "");
  const cuaderno = estadoDelCuadernoCyl();

  let resultado = null;
  if (cuaderno.resultado) {
    const r = cuaderno.resultado;
    // Los números se enseñan como frases, no como una tabla: lo que el agricultor quiere saber es
    // «cuántas tierras me has apuntado», y unas frases se leen de un vistazo. Las que están a cero no
    // salen (menos «tierras nuevas», que sale siempre).
    resultado = {
      cuentas: [
        rellena(c("creadas"), { cuantas: r.creadas }),
        r.con_cultivo ? rellena(c("con_cultivo"), { cuantas: r.con_cultivo }) : "",
        r.ya_estaban ? rellena(c("ya_estaban"), { cuantas: r.ya_estaban }) : "",
      ].filter(Boolean),
      sin_apuntar: r.sin_apuntar ? rellena(c("no_vinieron"), { cuantas: r.sin_apuntar }) : "",
      titular: r.titular_rellenado.length
        ? rellena(c("titular_rellenado"), { cuales: r.titular_rellenado.join(", ") })
        : c("titular_ya_estaba"),
      avisos: r.avisos || [],
    };
  }

  let resumen = null;
  if (cuaderno.resumen) {
    resumen = {
      filas: filasDelCuaderno(cuaderno.resumen, c),
      // Solo los doce primeros trozos: una lista de 51 no se lee, y el agricultor lo que quiere es
      // ver que están y confirmar.
      lineas: (cuaderno.resumen.lineas || []).slice(0, 12).map((linea) => [
        `${linea.ref_sigpac} · ${linea.municipio}`,
        `${linea.especie} · ${formateaNumero(linea.superficie_cultivada_ha ?? 0)} ha`,
      ]),
      avisos: (cuaderno.resumen.resumen || {}).avisos || [],
    };
  }

  montar(() =>
    pantallaDeCuadernoDeLaJunta({
      textos: { cuaderno_cyl: t("cuaderno_cyl", {}), acciones: t("acciones", {}) },
      resultado,
      resumen,
      leyendo: Boolean(cuaderno.leyendo),
      error: cuaderno.error || "",
    }),
  );
}
/** Sube el fichero y enseña lo que trae. **No apunta nada**: para eso está `cuaderno-traer`. */
async function leerElCuadernoDeLaJunta() {
  const c = (clave) => t(`cuaderno_cyl.${clave}`, "");
  const cuaderno = estadoDelCuadernoCyl();
  const entrada = document.getElementById("cuaderno-fichero");
  if (!entrada || !entrada.files || entrada.files.length === 0) {
    cuaderno.error = c("que_fichero");
    return pantallaCuadernoDeLaJunta();
  }
  // El fichero se guarda en el estado **antes** de repintar la pantalla. Pintar la pantalla
  // cambia la casilla del fichero por una nueva y vacía: si el fichero solo viviera ahí, al
  // repintar se perdería y el agricultor vería que «no ha elegido nada» después de elegirlo.
  cuaderno.fichero = entrada.files[0];
  if (!navigator.onLine) {
    cuaderno.error = c("sin_conexion");
    return pantallaCuadernoDeLaJunta();
  }
  cuaderno.error = "";
  cuaderno.leyendo = true;
  pantallaCuadernoDeLaJunta();
  const cuerpo = new FormData();
  cuerpo.append("fichero", cuaderno.fichero);
  try {
    const respuesta = await fetch("/api/cuaderno-cyl/leer", {
      method: "POST",
      headers: { Authorization: `Bearer ${estado.token}` },
      body: cuerpo,
    });
    const detalle = await respuesta.json().catch(() => null);
    if (!respuesta.ok) {
      throw new Error((detalle && detalle.detail) || c("no_se_pudo"));
    }
    cuaderno.resumen = detalle;
  } catch (error) {
    cuaderno.error = error.message || c("no_se_pudo");
  }
  cuaderno.leyendo = false;
  pantallaCuadernoDeLaJunta();
}

/** Apunta las tierras del cuaderno que ya se ha leído y enseñado. */
async function traerLasTierrasDelCuaderno() {
  const c = (clave) => t(`cuaderno_cyl.${clave}`, "");
  const cuaderno = estadoDelCuadernoCyl();
  if (!cuaderno.fichero) {
    // Si por lo que sea el fichero ya no está (se recargó la página, por ejemplo), se vuelve a
    // pedir en vez de apuntar otra cosa o de soltar un error que no explica nada.
    cuaderno.resumen = null;
    cuaderno.error = c("que_fichero");
    return pantallaCuadernoDeLaJunta();
  }
  cuaderno.error = "";
  cuaderno.leyendo = true;
  pantallaCuadernoDeLaJunta();
  const cuerpo = new FormData();
  cuerpo.append("fichero", cuaderno.fichero);
  try {
    const respuesta = await fetch("/api/cuaderno-cyl/importar", {
      method: "POST",
      headers: { Authorization: `Bearer ${estado.token}` },
      body: cuerpo,
    });
    const detalle = await respuesta.json().catch(() => null);
    if (!respuesta.ok) {
      throw new Error((detalle && detalle.detail) || c("no_se_pudo"));
    }
    cuaderno.resultado = detalle;
    cuaderno.resumen = null;
    cuaderno.fichero = null;
    await cargarDatos().catch(() => {});
  } catch (error) {
    cuaderno.error = error.message || c("no_se_pudo");
  }
  cuaderno.leyendo = false;
  pantallaCuadernoDeLaJunta();
}

// ------------------------------------------------------------- el mapa

/**
 * El mapa: la foto del campo con los linderos, para elegir la tierra tocándola.
 *
 * **Cómo está montado, y por qué así.** La imagen la pide el programa a los servicios oficiales
 * (la ortofoto del IGN y los linderos del SIGPAC) y la sirve él; el navegador solo pide una foto
 * por cada trozo de mapa que se ve. No hay librería de mapas: hay una caja de coordenadas
 * (oeste, sur, este, norte) y todo se coloca con una regla de tres, que es exactamente lo que
 * hace el servicio al pintar la imagen. Así no hay nada que compilar, la pantalla pesa poco y se
 * puede leer entera de un vistazo.
 *
 * **Lo que se ve en el centro es lo que se pregunta.** El agricultor mueve el mapa hasta poner su
 * tierra detrás de la cruz y pulsa el botón grande; también puede tocar directamente el trozo. En
 * los dos casos se pregunta al SIGPAC qué parcela hay en ese punto, y **se le enseña antes de
 * apuntarla**: un dedo al lado de una linde es otra parcela, y quien lo sabe es él.
 */
const MAPA_LADO_POR_DEFECTO = 0.012; // unos 800 metros de ancho: una finca entera se ve
const MAPA_LADO_MINIMO = 0.0012; // unos 90 metros
const MAPA_LADO_MAXIMO = 0.5; // el tope que acepta el servidor
const MAPA_ANCHO = 900;
const MAPA_ALTO = 600;

function estadoDelMapa() {
  if (!estado.mapa) {
    estado.mapa = {
      oeste: 0,
      sur: 0,
      este: 0,
      norte: 0,
      lado: MAPA_LADO_POR_DEFECTO,
      // Lo que ha respondido el SIGPAC del último punto preguntado.
      elegido: null,
      // El sistema de la tierra que se va a apuntar: **sin decir hasta que el agricultor lo diga**
      // (A10, 05/10/2026). Aquí ponía `"secano"`, así que los botones salían con «Secano» marcado
      // antes de preguntar y quien no lo tocara declaraba de secano una tierra de regadío.
      sistema: null,
      cargando: false,
      buscando: false,
      // Si no se sabe por dónde empezar (sin parcelas y sin ubicación), no se pinta el mapa: se
      // dice. Una caja de coordenadas inventada enseñaría el mapa de otro sitio.
      centrado: false,
      error: null,
      // El punto que se está mirando, en píxeles, para pintar la cruz donde ha tocado.
      tocado: null,
    };
  }
  return estado.mapa;
}

/** Coloca la caja de coordenadas alrededor de un punto, con el ancho que toque. */
function centrarElMapa(lon, lat, lado) {
  const m = estadoDelMapa();
  m.lado = Math.min(MAPA_LADO_MAXIMO, Math.max(MAPA_LADO_MINIMO, lado || m.lado));
  const alto = m.lado * (MAPA_ALTO / MAPA_ANCHO);
  m.oeste = lon - m.lado / 2;
  m.este = lon + m.lado / 2;
  m.sur = lat - alto / 2;
  m.norte = lat + alto / 2;
  m.elegido = null;
  m.tocado = null;
  m.centrado = true;
}

/** El centro de la caja que se está mirando. */
function elCentroDelMapa() {
  const m = estadoDelMapa();
  return { lon: (m.oeste + m.este) / 2, lat: (m.sur + m.norte) / 2 };
}

/** De coordenadas a píxeles de la imagen, y al revés. Es una regla de tres, y nada más. */
function aPixeles(lon, lat) {
  const m = estadoDelMapa();
  return {
    x: ((lon - m.oeste) / (m.este - m.oeste)) * MAPA_ANCHO,
    y: ((m.norte - lat) / (m.norte - m.sur)) * MAPA_ALTO,
  };
}

function aCoordenadas(x, y) {
  const m = estadoDelMapa();
  return {
    lon: m.oeste + (x / MAPA_ANCHO) * (m.este - m.oeste),
    lat: m.norte - (y / MAPA_ALTO) * (m.norte - m.sur),
  };
}

/** Las direcciones de las dos imágenes del mapa, con la caja que se está mirando. */
function direccionDeLaImagen(capa) {
  const m = estadoDelMapa();
  const parametros = [
    `capa=${encodeURIComponent(capa)}`,
    `oeste=${m.oeste}`,
    `sur=${m.sur}`,
    `este=${m.este}`,
    `norte=${m.norte}`,
    `ancho=${MAPA_ANCHO}`,
    `alto=${MAPA_ALTO}`,
  ];
  return `/api/mapa/imagen?${parametros.join("&")}`;
}

/** Abre el mapa, centrado en la tierra del agricultor si ya tiene alguna parcela. */
async function abrirElMapa() {
  // Se empieza de cero: el mapa no guarda la búsqueda anterior, para que volver a abrirlo no
  // enseñe la parcela que se estaba mirando hace media hora.
  estado.mapa = null;
  const mapa = estadoDelMapa();
  mapa.lado = MAPA_LADO_POR_DEFECTO;

  const conForma = (estado.parcelas || []).find((parcela) => parcela.centro);
  if (conForma) {
    centrarElMapa(conForma.centro[0], conForma.centro[1], 0.02);
  } else {
    // Sin parcelas no se puede saber por dónde empezar: se pide la ubicación y, si no la da, se
    // dice. Abrir el mapa en un sitio cualquiera sería peor que no abrirlo.
    const suyo = await pedirLaUbicacion();
    if (suyo) {
      centrarElMapa(suyo.lon, suyo.lat, MAPA_LADO_POR_DEFECTO);
    } else {
      mapa.error = t("mapa.sin_centro", "");
    }
  }
  pantallaMapa();
}

/** La ubicación del móvil, si el navegador la da y el agricultor la permite. */
function pedirLaUbicacion() {
  return new Promise((resolver) => {
    const geo = navigator && navigator.geolocation;
    if (!geo || typeof geo.getCurrentPosition !== "function") return resolver(null);
    try {
      geo.getCurrentPosition(
        (posicion) =>
          resolver({ lon: posicion.coords.longitude, lat: posicion.coords.latitude }),
        () => resolver(null),
        { enableHighAccuracy: true, timeout: 8000 },
      );
    } catch (error) {
      resolver(null);
    }
  });
}

/**
 * «El mapa»: la pantalla, ya en React (ver `docs/REACT.md`).
 *
 * **Es la primera pantalla migrada que se toca con el dedo**, y por eso aquí no hay ningún manejador
 * de React: el toque lo sigue atendiendo el manejador delegado de `document`, que lee **dónde** se ha
 * tocado de las coordenadas del propio evento. Si el toque se enganchara al componente, se perdería
 * la posición y el agricultor pulsaría el mapa sin que pasara nada.
 *
 * Lo que se prepara aquí es todo lo que hay que contar: las dos direcciones de las imágenes, los
 * puntos del trozo **ya convertidos a píxeles**, las coordenadas del centro escritas, y lo que ha
 * contestado el SIGPAC de ese punto (con su referencia, su superficie, su uso, su pueblo, su
 * referencia catastral y si cae en zona de nitratos).
 */
function pantallaMapa() {
  const m = estadoDelMapa();
  const texto = (clave) => t(`mapa.${clave}`, "");
  const s = (clave) => t(`sigpac.${clave}`, "");
  const centro = elCentroDelMapa();

  // El trozo que ha encontrado el SIGPAC, con sus puntos ya en píxeles: el componente no sabe de
  // coordenadas ni de reglas de tres.
  const elegido = m.elegido
    ? {
        filas: [
          [s("referencia_como_sea"), m.elegido.referencia || ""],
          [
            texto("superficie"),
            `${formateaNumero(m.elegido.superficie_ha, 4)} ${t("rotulos.hectareas_corto", "")}`,
          ],
          [
            s("uso"),
            m.elegido.uso_sigpac ? `${m.elegido.uso_sigpac} — ${m.elegido.uso}` : "",
          ],
          m.elegido.municipio
            ? [
                texto("pueblo"),
                `${m.elegido.municipio.nombre} (${m.elegido.municipio.provincia})`,
              ]
            : null,
          m.elegido.referencia_catastral
            ? [texto("referencia_catastral"), m.elegido.referencia_catastral]
            : null,
          [texto("zona_nitratos"), loQueSeSabeDeLosNitratos(m.elegido)],
        ].filter(Boolean),
        sistema_etiqueta: s("sistema"),
        // **Las tres respuestas, y la de «no lo sé» sale marcada cuando no se ha dicho nada** (A10):
        // el catálogo del servidor trae secano, regadío y «no lo sé» (`catalogos.SISTEMAS_PARA_ELEGIR`).
        // Antes se ofrecían dos y el que no tocaba nada se guardaba como secano.
        sistemas: (t("sistemas", []) || []).map((sistema) => ({
          valor: sistema.valor,
          texto: sistema.texto,
          elegido:
            sistema.valor === "nulo" ? !m.sistema : m.sistema === sistema.valor,
        })),
        alias_etiqueta: s("alias"),
        alias: m.alias || "",
      }
    : null;

  montar(() =>
    pantallaDeMapa({
      textos: { mapa: t("mapa", {}), sigpac: t("sigpac", {}), acciones: t("acciones", {}) },
      centrado: Boolean(m.centrado),
      imagenes: {
        foto: direccionDeLaImagen("foto"),
        linderos: direccionDeLaImagen("linderos"),
        vista: `0 0 ${MAPA_ANCHO} ${MAPA_ALTO}`,
      },
      poligono:
        m.elegido && m.elegido.puntos && m.elegido.puntos.length > 2
          ? m.elegido.puntos
              .map(([lon, lat]) => {
                const pixel = aPixeles(lon, lat);
                return `${pixel.x.toFixed(1)},${pixel.y.toFixed(1)}`;
              })
              .join(" ")
          : "",
      centro: `${formateaNumero(centro.lat, 5)}, ${formateaNumero(centro.lon, 5)}`,
      elegido,
      cargando: Boolean(m.cargando),
      error: m.error || "",
    }),
  );
}
/** Lee lo que hay escrito en el mapa (el nombre de la parcela) antes de volver a pintarlo. */
function recogeElMapa() {
  const m = estadoDelMapa();
  const elemento = document.getElementById("alias_mapa");
  if (elemento) m.alias = elemento.value;
  return m;
}

/**
 * «Estoy aquí»: pone el mapa donde está el agricultor y le dice qué parcela es.
 *
 * Es lo que hace alguien que está de pie en medio del campo: no mira coordenadas, pulsa un botón.
 * Si el móvil no da la ubicación (o él no deja usarla), se dice con palabras y se puede seguir
 * buscando a mano; lo que no se hace es poner el mapa en un sitio inventado.
 */
async function irAEstoyAqui() {
  const mapa = estadoDelMapa();
  mapa.error = null;
  mapa.buscando = true;
  pantallaMapa();
  const suyo = await pedirLaUbicacion();
  mapa.buscando = false;
  if (!suyo) {
    mapa.error = t("mapa.sin_ubicacion", "");
    return pantallaMapa();
  }
  centrarElMapa(suyo.lon, suyo.lat, MAPA_LADO_POR_DEFECTO);
  const pixel = aPixeles(suyo.lon, suyo.lat);
  return preguntarPorUnPunto(pixel.x, pixel.y);
}

/** Lo que se puede decir de la zona de nitratos: sí, parte, no, o que no se ha podido mirar. */
function loQueSeSabeDeLosNitratos(datos) {
  if (datos.en_zona_de_nitratos === null || datos.en_zona_de_nitratos === undefined) {
    return t("mapa.zona_nitratos_no_se", "");
  }
  if (!datos.en_zona_de_nitratos) return t("mapa.zona_nitratos_no", "");
  const porcentaje = datos.zona_de_nitratos_porcentaje;
  if (porcentaje !== null && porcentaje !== undefined && porcentaje < 99.5) {
    return t("mapa.zona_nitratos_parte", "").replace(
      "{porcentaje}",
      formateaNumero(porcentaje, 0),
    );
  }
  return t("mapa.zona_nitratos_si", "");
}

/** Pregunta al SIGPAC qué parcela hay en un punto del mapa. */
async function preguntarPorUnPunto(x, y) {
  const m = estadoDelMapa();
  const punto = aCoordenadas(x, y);
  m.tocado = { x, y };
  m.buscando = true;
  m.error = null;
  pantallaMapa();
  try {
    const datos = await apiJson("/api/mapa/punto", {
      method: "POST",
      body: JSON.stringify({ x: punto.lon, y: punto.lat }),
    });
    m.elegido = datos.encontrado ? datos : null;
    if (!datos.encontrado) m.error = datos.mensaje || t("mapa.no_hay_nada", "");
  } catch (error) {
    m.elegido = null;
    m.error = error.message || t("mapa.sin_conexion", "");
  }
  m.buscando = false;
  pantallaMapa();
}

/** Mueve el mapa y vuelve a pedir la imagen. */
function moverElMapa(dLon, dLat) {
  const m = estadoDelMapa();
  m.oeste += dLon;
  m.este += dLon;
  m.sur += dLat;
  m.norte += dLat;
  pantallaMapa();
}

/** Apunta la parcela que se ha elegido en el mapa. */
async function apuntarLaParcelaDelMapa() {
  const m = estadoDelMapa();
  if (!m.elegido) return;
  m.error = null;
  try {
    const parcela = await apiJson("/api/parcelas/desde-sigpac", {
      method: "POST",
      body: JSON.stringify({
        ref_sigpac: m.elegido.referencia,
        alias: (m.alias || "").trim() || null,
        // A10: lo que no ha dicho el agricultor viaja como `null` («no lo sé»), no como «secano».
        sistema: m.sistema || null,
        municipio: m.elegido.municipio ? m.elegido.municipio.nombre : null,
        provincia: m.elegido.municipio ? m.elegido.municipio.provincia : null,
        referencia_catastral: m.elegido.referencia_catastral || null,
      }),
    });
    estado.mapa = null;
    await cargarDatos().catch(() => {});
    pantallaParcelaTraida(parcela);
  } catch (error) {
    m.error = error.message || t("mapa.no_se_pudo_apuntar", "");
    pantallaMapa();
  }
}

/** Los pasos del alta por SIGPAC: solo lo que el SIGPAC no sabe. */
function pasosDeSigpac() {
  return [
    {
      titulo: t("sigpac.referencia_como_sea", ""),
      // **Sin pista, y a propósito** (ronda 88): esta pantalla explica ella misma lo que hace (el texto del
      // SIGPAC va dentro, en la pieza) y la casilla de la referencia lleva debajo su propia explicación. La
      // pista del paso era **esa misma explicación**, y salía dos veces en la misma pantalla.
      pista: "",
      montar: () => { const d = datosDeTraerDelSigpac(); return pantallaTraerDelSigpac(d); },
      // El paso se da por bueno cuando ya se han traído parcelas: lo que hace el trabajo son los
      // botones (BUSCAR y TRAERME LOS MARCADOS), no el botón de seguir. Si el agricultor no ha
      // traído ninguna, se le dice qué le falta en vez de dejarle pasar a ciegas.
      recoger: () => {
        recogeElSigpac();
        const b = estado.asistente.borrador;
        if (b.traidas) return null;
        return t("sigpac.busca_antes", "");
      },
    },
  ];
}

// ------------------------------------------------------ elegir el pueblo y buscar los trozos

/**
 * Lee lo que hay escrito en la pantalla del SIGPAC y lo guarda en el borrador.
 *
 * Hace falta porque en esta pantalla los botones cambian la pantalla (al elegir el pueblo, al
 * marcar un trozo) y al volver a pintarla se perdería lo escrito. Se recoge **antes** de tocar
 * nada, así que lo que el agricultor ha tecleado no se pierde nunca.
 */
function recogeElSigpac() {
  const b = estado.asistente.borrador;
  const valor = (id) => {
    const elemento = document.getElementById(id);
    return elemento ? elemento.value : null;
  };
  for (const [id, campo] of [
    ["ref_sigpac", "ref_sigpac"],
    ["alias_sigpac", "alias"],
    ["municipio_sigpac", "municipio"],
    ["provincia_sigpac", "provincia"],
    ["poligono_sigpac", "poligono"],
    ["parcela_sigpac", "parcela"],
  ]) {
    const leido = valor(id);
    if (leido !== null) b[campo] = leido;
  }
  return b;
}

/**
 * Traer una parcela del SIGPAC sin saberse ningún código.
 *
 * Es lo que quita de en medio el momento en el que más gente abandona: dar de alta cuarenta
 * parcelas escribiendo ocho datos en cada una. Está montado **como lo hacen las aplicaciones
 * oficiales del FEGA** («Añadir recintos de SigPac»): provincia, municipio, agregado, zona,
 * polígono y parcela, un botón de buscar, y la lista de trozos que hay en esa parcela para
 * marcar los que son suyos. La diferencia es que aquí el municipio y la provincia se **eligen de
 * la lista oficial**, así que no hay que saberse ningún código.
 *
 * Y se admite lo que el agricultor tenga en la mano: también se puede pegar la referencia tal
 * cual sale del visor (`37:70:0:0:503:51`) o la referencia catastral del Catastro, que trae
 * dentro el polígono y la parcela.
 *
 * Sigue estando **APUNTARLA A MANO** para quien no tenga nada a mano: un conector que obliga a
 * tener un papel para empezar sería peor que no tenerlo.
 */
/**
 * Los datos del paso de traer la tierra del SIGPAC, ya preparados para la pantalla.
 *
 * **Lo que NO hace esto:** pintar. Devuelve los textos del servidor y los datos ya montados: las
 * provincias del desplegable, los pueblos que ha traído la búsqueda y los recintos con su detalle
 * (**el detalle se junta aquí**, que es quien conoce los números: la superficie con cuatro decimales, el
 * uso con su código delante como lo enseña el visor del SIGPAC, la pendiente y la altitud).
 */
function datosDeTraerDelSigpac() {
  const b = estado.asistente.borrador;
  const s = (clave) => t(`sigpac.${clave}`, "");

  return {
    textos: { sigpac: t("sigpac", {}), municipios: t("municipios", {}) },
    datos: {
      provincias: (t("provincias", []) || []).map((nombre) => ({
        valor: nombre,
        etiqueta: nombre,
        elegido: b.provincia === nombre,
      })),
      municipio: b.municipio || "",
      pueblos: (b.pueblos || []).map((pueblo) => ({
        // El nombre con su provincia entre paréntesis: hay pueblos que se llaman igual en dos provincias.
        etiqueta: `${pueblo.nombre} (${pueblo.provincia})`,
        pista: rellena(t("municipios.codigo_pista", ""), { codigo: pueblo.codigo_ine }),
        nombre: pueblo.nombre,
        provincia: pueblo.provincia,
        elegido: b.municipio === pueblo.nombre,
      })),
      poligono: b.poligono || "",
      parcela: b.parcela || "",
      ref_sigpac: b.ref_sigpac || "",
      alias: b.alias || "",
      sistemas: (t("sistemas", []) || []).map((sistema) => ({
        etiqueta: sistema.texto,
        valor: sistema.valor,
        // **El sistema nace sin decir** (A10): antes salía «Secano» marcado «porque es lo normal en estas
        // tierras», y eso es exactamente lo que no se puede hacer —adivinar por el agricultor un dato del
        // que depende contra qué límite del anexo III se compara su abonado—. Lo que no se ha dicho sale
        // como «no lo sé» marcado, y él decide si lo deja así.
        elegido: sistema.valor === "nulo" ? !b.sistema : sistema.valor === b.sistema,
      })),
      trozos: (b.trozos || []).map((trozo) => ({
        etiqueta: rellena(s("recinto_numero"), { numero: trozo.recinto }),
        pista: [
          trozo.superficie_ha ? `${formateaNumero(trozo.superficie_ha, 4)} ha` : "",
          // El uso con su código delante, igual que lo enseña el visor del SIGPAC
          // («TA — TIERRAS ARABLES»): es así como el agricultor lo reconoce en su papel.
          trozo.uso_sigpac && trozo.uso
            ? `${trozo.uso_sigpac} — ${trozo.uso}`
            : trozo.uso || trozo.uso_sigpac || "",
          trozo.pendiente_pct !== null && trozo.pendiente_pct !== undefined
            ? `${s("pendiente")} ${formateaNumero(trozo.pendiente_pct, 2)} %`
            : "",
          trozo.altitud ? `${s("altitud")} ${trozo.altitud} m` : "",
        ]
          .filter(Boolean)
          .join(" · "),
        referencia: trozo.referencia || "",
        marcado: (b.marcados || []).includes(trozo.referencia),
      })),
    },
  };
}


/** El pueblo: se busca por las primeras letras y se elige de la lista oficial. */
async function buscarElPueblo() {
  const b = recogeElSigpac();
  const buscado = (b.municipio || "").trim();
  if (!buscado) {
    estado.asistente.error = t("municipios.pista", "");
    pintarAsistente();
    return;
  }
  try {
    const datos = await apiJson(
      `/api/municipios?buscar=${encodeURIComponent(buscado)}&provincia=${encodeURIComponent(b.provincia || "")}`,
    );
    b.pueblos = datos.municipios || [];
    estado.asistente.error = b.pueblos.length ? null : t("municipios.no_esta_en_la_lista", "");
  } catch (error) {
    estado.asistente.error = t("municipios.sin_lista", "");
  }
  pintarAsistente();
}

/** Pregunta al SIGPAC por los trozos de la parcela que se ha dicho. */
async function buscarLosTrozos() {
  const b = recogeElSigpac();
  const cuerpo = {};
  const referencia = (b.ref_sigpac || "").trim();
  const poligono = Number((b.poligono || "").trim());
  const parcela = Number((b.parcela || "").trim());

  if (referencia) {
    cuerpo.referencia = referencia;
  } else if ((b.municipio || "").trim() && Number.isInteger(poligono) && Number.isInteger(parcela)) {
    cuerpo.municipio = (b.municipio || "").trim();
    cuerpo.provincia = (b.provincia || "").trim();
    cuerpo.poligono = poligono;
    cuerpo.parcela = parcela;
  } else {
    // Sin nada que buscar no se llama al SIGPAC: se dice qué falta. Una llamada que se sabe que va
    // a fallar solo hace esperar al agricultor delante de una pantalla parada.
    estado.asistente.error = t("sigpac.busqueda_incompleta", "");
    pintarAsistente();
    return;
  }

  try {
    const datos = await apiJson("/api/sigpac/buscar", {
      method: "POST",
      body: JSON.stringify(cuerpo),
    });
    b.trozos = datos.recintos || [];
    // **No se marca nada solo, salvo cuando solo hay un trozo.** Si la parcela tiene cinco y el
    // agricultor quiere uno, marcarlos todos le daría de alta cuatro parcelas que no son suyas (o
    // repetidas, que es peor). Con un solo trozo no hay duda: la parcela entera es ese.
    b.marcados = b.trozos.length === 1 ? [b.trozos[0].referencia] : [];
    b.referencia_catastral = datos.referencia_catastral || null;
    if (datos.municipio) {
      b.municipio = datos.municipio.nombre;
      b.provincia = datos.municipio.provincia;
    }
    estado.asistente.error = datos.mensaje || null;
  } catch (error) {
    estado.asistente.error = error.message;
  }
  pintarAsistente();
}

/** Marca o desmarca un trozo de los que ha encontrado el SIGPAC. */
function marcarElTrozo(referencia) {
  const b = recogeElSigpac();
  const marcados = b.marcados || [];
  b.marcados = marcados.includes(referencia)
    ? marcados.filter((otra) => otra !== referencia)
    : [...marcados, referencia];
  estado.asistente.error = null;
  pintarAsistente();
}

/** Trae los trozos marcados: se dan de alta todos de una vez. */
async function traerLosMarcados() {
  const b = recogeElSigpac();
  const marcados = (b.marcados || []).filter(Boolean);
  if (!marcados.length) {
    estado.asistente.error = t("sigpac.marca_alguno", "");
    pintarAsistente();
    return;
  }
  if (!navigator.onLine) {
    estado.asistente.error = t("sigpac.sin_permiso_red", "");
    pintarAsistente();
    return;
  }

  try {
    const datos = await apiJson("/api/parcelas/desde-sigpac/varias", {
      method: "POST",
      body: JSON.stringify({
        referencias: marcados,
        alias: (b.alias || "").trim() || null,
        municipio: (b.municipio || "").trim() || null,
        provincia: (b.provincia || "").trim() || null,
        // A10: sin decirlo se manda `null`, no «secano».
        sistema: b.sistema || null,
        referencia_catastral: b.referencia_catastral || null,
      }),
    });
    b.traidas = datos;
    estado.asistente = null;
    await cargarDatos().catch(() => {});
    pantallaParcelasTraidas(datos);
  } catch (error) {
    estado.asistente.error = error.message;
    pintarAsistente();
  }
}

/** Lo que se ha traído, para que el agricultor lo vea antes de fiarse. */
/**
 * Lo que se ha traído, para que el agricultor lo vea antes de fiarse.
 *
 * Los cuatro datos de la tierra traída van con la pieza del resumen (la misma que el resumen del
 * asistente), porque al final es lo mismo: una lista de etiqueta y valor para mirar antes de seguir.
 */
function pantallaParcelaTraida(parcela) {
  const s = (clave) => t(`sigpac.${clave}`, "");
  montar(() =>
    confirmacion({
      titulo: s("traido_titulo"),
      pista: s("traido"),
      contenido: html`
        <h2>${parcela.alias}</h2>
        ${resumenDelApunte({
          filas: [
            [
              s("superficie_oficial"),
              `${formateaNumero(parcela.superficie_ha, 4)} ${t("rotulos.hectareas_corto", "")}`,
            ],
            [s("uso"), parcela.uso_sigpac || ""],
            [s("pendiente"), `${formateaNumero(parcela.pendiente_pct, 1)} %`],
            [s("referencia"), parcela.ref_sigpac || ""],
          ],
        })}
        <p className="pista-campo">${s("y_el_dibujo")}</p>
      `,
      avisos: [{ texto: s("los_nombres_no_vienen") }],
      acciones: [
        {
          etiqueta: accion("volver"),
          accion: "inicio",
          datos: { ir: "mi_cuaderno" },
          clase: "boton",
          sencillo: true,
        },
      ],
    }),
  );
}

/**
 * Lo que se dice cuando se han traído varias parcelas de una vez.
 *
 * Se dicen **las que han entrado y las que no, con su motivo**: si tres de cuarenta referencias
 * están mal copiadas, el agricultor tiene que saber cuáles para arreglarlas, y saber que las
 * otras treinta y siete están dentro. Un «error» a secas le deja sin saber qué ha pasado.
 */
function pantallaParcelasTraidas(datos) {
  const s = (clave) => t(`sigpac.${clave}`, "");
  const creadas = datos.creadas || [];
  const fallos = datos.fallos || [];
  montar(() =>
    confirmacion({
      titulo: datos.mensaje || s("traido_titulo"),
      listas: [
        // Las que han entrado, con su referencia.
        {
          elementos: creadas.map((parcela) => ({
            cabecera: parcela.alias,
            detalle: parcela.ref_sigpac || "",
          })),
        },
        // Y las que no, cada una con su motivo: si tres de cuarenta referencias están mal copiadas, el
        // agricultor tiene que saber cuáles para arreglarlas, y saber que las otras treinta y siete están
        // dentro. Un «error» a secas le deja sin saber qué ha pasado.
        ...(fallos.length
          ? [
              {
                titulo: s("estas_no"),
                elementos: fallos.map((fallo) => ({
                  cabecera: fallo.referencia,
                  detalle: fallo.motivo,
                })),
              },
            ]
          : []),
      ].filter((lista) => lista.elementos.length),
      contenido: html`<p className="pista-campo">${s("y_el_dibujo")}</p>`,
      acciones: [
        {
          etiqueta: accion("volver"),
          accion: "parcela-traida-seguir",
          clase: "boton",
          sencillo: true,
        },
      ],
    }),
  );
}

// ------------------------------------------------- mis cosas: dar de alta

/**
 * Sin estas pantallas la aplicación no se puede usar.
 *
 * Antes de tenerlas, al agricultor nuevo se le decía "añade tu primera parcela" y no
 * había ninguna forma de hacerlo: se quedaba mirando una pantalla que le pedía algo
 * imposible. Es el fallo más tonto y más grave que tenía esto.
 */
const MAESTROS_API = {
  parcela: { ruta: "/api/parcelas", numeros: ["superficie_ha"] },
  // Un grupo de parcelas no se da de alta a mano: los junta el programa (ver `calcularGrupos`). Está
  // aquí porque **se puede corregir** —su nombre— desde la ronda 92, y el formulario de corregir es el
  // mismo motor que el de las altas.
  grupo: { ruta: "/api/grupos" },
  // El año del cuaderno (la campaña). Está en esta lista porque **se crea y se corrige con el mismo
  // formulario** que un maestro: el año, las dos fechas y si está terminado. Lo que no pasa por aquí es
  // el final (la pantalla que sale después), que es propio: decir «guardado» y ofrecer «MIS PARCELAS,
  // PRODUCTOS Y MÁQUINAS» sería mandar al agricultor a un sitio que no tiene nada que ver.
  campana: { ruta: "/api/campanas", numeros: ["anio"] },
  producto: {
    ruta: "/api/productos",
    numeros: ["dosis_maxima", "plazo_seguridad_dias"],
  },
  abono: { ruta: "/api/fertilizantes", numeros: ["riqueza_n", "riqueza_p", "riqueza_k"] },
  aplicador: { ruta: "/api/aplicadores" },
  asesor: { ruta: "/api/asesores" },
  equipo: { ruta: "/api/equipos" },
  instalacion: { ruta: "/api/instalaciones", numeros: ["superficie_m2"] },
};

/**
 * Qué es cada campo: cómo se llama en la API y qué clase de dato es.
 *
 * La clave lleva delante el tipo de alta ("parcela.alias") porque el mismo nombre
 * ("nombre") significa cosas distintas en un abono y en una persona, y las preguntas
 * no son las mismas.
 */
const CAMPOS = {
  "parcela.alias": { campo: "alias", tipo: "texto", obligatorio: true },
  "parcela.superficie_ha": {
    campo: "superficie_ha", tipo: "numero", obligatorio: true, ayuda: "parcela.superficie_ha",
  },
  "parcela.sistema": { campo: "sistema", tipo: "opciones", opciones: "sistemas" },
  "parcela.ref_sigpac": { campo: "ref_sigpac", tipo: "texto", ayuda: "parcela.ref_sigpac" },
  "parcela.municipio": { campo: "municipio", tipo: "texto" },
  "parcela.provincia": { campo: "provincia", tipo: "texto" },
  // El uso del suelo, de la lista oficial del SIGPAC. Se pregunta con la lista delante porque
  // hasta ahora el campo existía en el modelo y **ninguna pantalla lo preguntaba**: el agricultor
  // que apuntaba su parcela a mano se quedaba sin poder decir qué era su tierra.
  "parcela.uso_sigpac": { campo: "uso_sigpac", tipo: "opciones", opciones: "usos_sigpac" },
  // **Las dos del agua, con tres respuestas** (A12, 05/10/2026). Se preguntaban con `si_no`, así que la
  // casilla nacía sin marcar y el programa leía **«no hay agua»**: de eso dependen las restricciones de
  // abonado y la franja de seguridad de un tratamiento, o sea que un «no» que nadie ha dicho **aligeraba
  // las reglas que le aplican al agricultor**. Es la misma decisión que la zona de nitratos, unas líneas
  // más abajo, y por el mismo motivo: hay tres casos de verdad y el intermedio importa.
  "parcela.masa_agua_cerca": {
    campo: "masa_agua_cerca", tipo: "si_no_no_se", ayuda: "parcela.masa_agua_cerca",
  },
  "parcela.captacion_consumo_humano": {
    campo: "captacion_consumo_humano", tipo: "si_no_no_se",
  },
  // La zona de nitratos: se pregunta con tres respuestas porque hay tres casos de verdad, y el
  // intermedio importa —«no lo sé» no es «no está»—. Ver `zona_vulnerable_nitratos` en el modelo.
  "parcela.zona_vulnerable_nitratos": {
    campo: "zona_vulnerable_nitratos", tipo: "si_no_no_se", ayuda: "parcela.zona_vulnerable_nitratos",
  },

  // ── Un grupo de parcelas (ronda 92): lo único que tiene nombre propio ───────────────────────────
  //
  // Un grupo lo junta el programa, así que el agricultor no lo da de alta: lo **renombra** («Cebada (3
  // parcelas)» es como lo llama el programa; él lo llamará «el de mi hermano»). Los otros tres campos
  // no se preguntan (no hay paso que los pinte) y están aquí por un motivo concreto: `cargaMaestro`
  // solo manda lo que está en esta tabla, así que **sin ellos, renombrar un grupo lo dejaría sin
  // tierras**. Es la misma trampa que la máquina de la cosecha, en la ronda 91.
  "grupo.nombre": { campo: "nombre", tipo: "texto", obligatorio: true },
  "grupo.parcela_ids": { campo: "parcela_ids", tipo: "lista" },
  "grupo.campana_id": { campo: "campana_id", tipo: "numero" },
  "grupo.cultivo": { campo: "cultivo", tipo: "texto" },
  "grupo.sistema": { campo: "sistema", tipo: "opciones", opciones: "sistemas" },

  "producto.nombre_comercial": { campo: "nombre_comercial", tipo: "texto", obligatorio: true },
  "producto.numero_registro": {
    campo: "numero_registro", tipo: "texto", obligatorio: true, ayuda: "producto.numero_registro",
  },
  "producto.dosis_maxima": {
    campo: "dosis_maxima", tipo: "numero", obligatorio: true, ayuda: "producto.dosis_maxima",
  },
  "producto.unidad_dosis": { campo: "unidad_dosis", tipo: "opciones", opciones: "unidades_dosis" },
  "producto.plazo_seguridad_dias": {
    campo: "plazo_seguridad_dias", tipo: "numero", obligatorio: true,
    ayuda: "producto.plazo_seguridad_dias",
  },
  "producto.materia_activa": {
    campo: "materia_activa", tipo: "texto", ayuda: "producto.materia_activa",
  },
  "producto.tipo_producto": { campo: "tipo_producto", tipo: "texto" },
  "producto.lote": { campo: "lote", tipo: "texto" },
  "producto.fecha_caducidad": { campo: "fecha_caducidad", tipo: "fecha" },
  "producto.proveedor": { campo: "proveedor", tipo: "texto" },
  // La compra: cuánto, en qué unidad y cuándo. Son los datos del libro de movimientos, y sin
  // ellos la pantalla del almacén no puede decir cuánto queda. Estaban en la base de datos desde
  // el principio y **no los pedía nadie**, así que la pregunta «¿me queda producto?» no tenía
  // respuesta.
  "producto.cantidad_comprada": { campo: "cantidad_comprada", tipo: "numero" },
  "producto.unidad_compra": { campo: "unidad_compra", tipo: "opciones", opciones: "unidades_producto" },
  "producto.fecha_compra": { campo: "fecha_compra", tipo: "fecha" },
  // La autorización del producto. Son los campos que faltaban para que **tres comprobaciones que
  // ya existían** pudieran saltar: la de «producto no autorizado», la de «no se puede usar en
  // ecológico» y la de «la autorización excepcional caducó». Las tres estaban escritas y probadas
  // y ninguna podía saltar nunca, porque estos datos no se podían meter desde ninguna pantalla.
  // La autorización del producto: **tres respuestas**, por el mismo motivo que la zona de nitratos.
  // Con dos, dejar el bloque plegado —que es lo que hace todo el mundo, porque pone «opcional»—
  // dejaba el producto como autorizado y como permitido en ecológico sin que nadie lo hubiera
  // dicho. Ver `autorizado` en `models.ProductoFitosanitario`.
  "producto.autorizado": { campo: "autorizado", tipo: "si_no_no_se" },
  "producto.permitido_ecologico": { campo: "permitido_ecologico", tipo: "si_no_no_se" },
  "producto.autorizacion_excepcional": { campo: "autorizacion_excepcional", tipo: "texto" },
  "producto.autorizacion_hasta": { campo: "autorizacion_hasta", tipo: "fecha" },

  "abono.nombre": { campo: "nombre", tipo: "texto", obligatorio: true },
  "abono.riqueza_n": { campo: "riqueza_n", tipo: "numero", obligatorio: true },
  "abono.riqueza_p": { campo: "riqueza_p", tipo: "numero", obligatorio: true },
  "abono.riqueza_k": { campo: "riqueza_k", tipo: "numero", obligatorio: true },
  "abono.tipo": { campo: "tipo", tipo: "opciones", opciones: "tipos_abono" },

  "aplicador.nombre": { campo: "nombre", tipo: "texto", obligatorio: true },
  "aplicador.es_empresa": { campo: "es_empresa", tipo: "si_no" },
  "aplicador.numero_carne": {
    campo: "numero_carne", tipo: "texto", ayuda: "producto.numero_registro",
  },
  "aplicador.fecha_caducidad_carne": { campo: "fecha_caducidad_carne", tipo: "fecha" },
  "aplicador.numero_ropo": { campo: "numero_ropo", tipo: "texto" },
  // El tipo de carné y el número del registro de equipos de aplicación aérea. Estaban en la
  // tabla, no salían en la respuesta y no los pedía nadie (ronda 19).
  // El tipo de carné, de la lista del cuaderno de la Junta (básico, cualificado, fumigador y
  // piloto): es lo que le permite marcar la casilla que toca en su hoja 1.2.
  "aplicador.tipo_carne": { campo: "tipo_carne", tipo: "opciones", opciones: "tipos_carne" },
  "aplicador.numero_reganip": { campo: "numero_reganip", tipo: "texto" },

  "equipo.nombre": { campo: "nombre", tipo: "texto", obligatorio: true },
  // El cuaderno de la Junta pide la **descripción del equipo con su tipo, marca y modelo**, el **nº
  // de ROMA** cuando lo tiene, la **fecha de adquisición** y la de la última inspección. Y las tres
  // pestañas de la app oficial son tres cosas distintas: maquinaria propia, maquinaria ajena (la del
  // ROMA que no es tuya, por ejemplo la de una empresa de servicios) y equipos que no van en el ROMA
  // (mochilas, carretillas, aperos).
  "equipo.tipo": { campo: "tipo", tipo: "texto" },
  "equipo.marca": { campo: "marca", tipo: "texto" },
  "equipo.modelo": { campo: "modelo", tipo: "texto" },
  "equipo.titularidad": { campo: "titularidad", tipo: "opciones", opciones: "titularidades_equipo" },
  "equipo.numero_roma": { campo: "numero_roma", tipo: "texto" },
  "equipo.fecha_adquisicion": { campo: "fecha_adquisicion", tipo: "fecha" },
  "equipo.fecha_iteaf": { campo: "fecha_iteaf", tipo: "fecha" },
  "equipo.fecha_proxima_iteaf": { campo: "fecha_proxima_iteaf", tipo: "fecha" },

  // El técnico que asesora. El número de ROPO es obligatorio porque sin él la Junta rechaza
  // el tratamiento entero (error 7 del interfaz): mejor no dejar guardarlo a medias.
  "asesor.nombre": { campo: "nombre", tipo: "texto", obligatorio: true },
  "asesor.numero_ropo": { campo: "numero_ropo", tipo: "texto", obligatorio: true, ayuda: "asesor.numero_ropo" },
  "asesor.ambito": { campo: "ambito", tipo: "opciones", opciones: "ambitos_asesor" },
  "asesor.entidad_certificacion": { campo: "entidad_certificacion", tipo: "texto" },
  "asesor.telefono": { campo: "telefono", tipo: "texto" },

  "instalacion.alias": { campo: "alias", tipo: "texto", obligatorio: true },
  "instalacion.tipo": { campo: "tipo", tipo: "opciones", opciones: "tipos_instalacion" },
  "instalacion.referencia_catastral": { campo: "referencia_catastral", tipo: "texto" },
  "instalacion.municipio": { campo: "municipio", tipo: "texto" },
  "instalacion.uso": { campo: "uso", tipo: "texto" },
  "instalacion.superficie_m2": { campo: "superficie_m2", tipo: "numero" },

  "plan.cultivo": { campo: "cultivo", tipo: "texto", obligatorio: true },
  "plan.necesidad_n": { campo: "necesidad_n", tipo: "numero" },
  "plan.necesidad_p": { campo: "necesidad_p", tipo: "numero" },
  "plan.necesidad_k": { campo: "necesidad_k", tipo: "numero" },
  "plan.produccion_esperada_kg_ha": { campo: "produccion_esperada_kg_ha", tipo: "numero" },
  "plan.aportes_suelo_agua": { campo: "aportes_suelo_agua", tipo: "numero" },
  "plan.notas": { campo: "notas", tipo: "texto" },
  // Si se usó una herramienta para el plan. Es un sí o un no, igual que el campo del anexo II.
  // El año del cuaderno (la campaña). Cuatro campos, y los cuatro se contestan solos la primera vez: el
  // año nuevo sale con el año natural puesto y el agricultor solo lo cambia si su cosecha empieza en
  // septiembre. `fecha_inicio` y `fecha_fin` son obligatorios porque la API los exige (una campaña sin
  // fechas no puede saber a qué año pertenece un apunte).
  "campana.anio": { campo: "anio", tipo: "numero", obligatorio: true },
  "campana.fecha_inicio": { campo: "fecha_inicio", tipo: "fecha", obligatorio: true },
  "campana.fecha_fin": { campo: "fecha_fin", tipo: "fecha", obligatorio: true },
  "campana.cerrada": { campo: "cerrada", tipo: "si_no" },
  "plan.herramienta": { campo: "herramienta", tipo: "si_no" },
  // El asesoramiento de un tratamiento.
  "tratamiento.asesor_fecha": { campo: "asesor_fecha", tipo: "fecha" },
  "tratamiento.asesoramiento_validado": { campo: "asesoramiento_validado", tipo: "si_no" },

  // Cómo se echó: la hora, el estado de la planta y las condiciones del día.
  //
  // Esto se añadió en la ronda 18 después de mirar qué campos de la tabla **no llegaban a
  // ninguna pantalla**: había once escritos y ninguno se podía rellenar. Dos de ellos los pide
  // el contenido mínimo del CUE por su número (la hora, campo 3, y el estado de la planta,
  // campo 8), y el volcado declaraba la hora como campo suyo sin que hubiera forma de meterla.
  // Y el aviso «¿has dejado la orilla sin tratar?» **saltaba siempre**, porque la pregunta no
  // existía: su etiqueta estaba escrita y nunca se había puesto en ninguna pantalla.
  "tratamiento.hora_inicio": { campo: "hora_inicio", tipo: "texto" },
  "tratamiento.hora_fin": { campo: "hora_fin", tipo: "texto" },
  "tratamiento.estado_cultivo": { campo: "estado_cultivo", tipo: "texto" },
  "tratamiento.temperatura_c": { campo: "temperatura_c", tipo: "numero" },
  "tratamiento.humedad_pct": { campo: "humedad_pct", tipo: "numero" },
  "tratamiento.viento_kmh": { campo: "viento_kmh", tipo: "numero" },
  "tratamiento.viento_direccion": { campo: "viento_direccion", tipo: "texto" },
  "tratamiento.volumen_caldo_l_ha": { campo: "volumen_caldo_l_ha", tipo: "numero" },
  "tratamiento.franja_seguridad_respetada": { campo: "franja_seguridad_respetada", tipo: "si_no" },
  "tratamiento.aplicado_a_mano": { campo: "aplicado_a_mano", tipo: "si_no" },
  "tratamiento.eficacia": {
    campo: "eficacia",
    tipo: "opciones",
    opciones: "eficacia_del_tratamiento",
  },
  "tratamiento.unidad_cantidad_aplicada": { campo: "unidad_cantidad_aplicada", tipo: "texto" },
  "tratamiento.operadores_expuestos": { campo: "operadores_expuestos", tipo: "numero" },
  "tratamiento.incidencias": { campo: "incidencias", tipo: "texto" },

  // Lo que se siembra y el agua del riego. Son columnas propias y no texto libre porque el
  // cuaderno oficial las pide una por una (bloques 6 y 9 del contenido mínimo).
  "labor.cantidad_semilla_kg": { campo: "cantidad_semilla_kg", tipo: "numero" },
  "labor.dosis_siembra_kg_ha": { campo: "dosis_siembra_kg_ha", tipo: "numero" },
  "labor.lote_semilla": { campo: "lote_semilla", tipo: "texto" },
  // El tratamiento que recibió la semilla y cómo de bien funcionó. Es el bloque «uso de semilla
  // tratada» del anexo II: hoy solo se apuntaba «semilla tratada: sí», y eso no dice qué se le
  // hizo a la semilla, que es lo que hay que poder contestar si se pregunta por una partida.
  "labor.tratamiento_semilla": { campo: "tratamiento_semilla", tipo: "texto" },
  "labor.fecha_tratamiento_semilla": { campo: "fecha_tratamiento_semilla", tipo: "fecha" },
  "labor.eficacia_tratamiento_semilla": {
    campo: "eficacia_tratamiento_semilla",
    tipo: "opciones",
    opciones: "eficacia_del_tratamiento",
  },
  "labor.material_tratado": { campo: "material_tratado", tipo: "si_no" },
  "labor.animales_terceros": { campo: "animales_terceros", tipo: "si_no" },
  "labor.animales_propios": { campo: "animales_propios", tipo: "si_no" },
  "labor.semillas_siembra": { campo: "semillas_siembra", tipo: "si_no" },
  "labor.plantas_cosechadas": { campo: "plantas_cosechadas", tipo: "si_no" },
  "labor.sin_cosechar_ambiental": { campo: "sin_cosechar_ambiental", tipo: "si_no" },
  "labor.restos_cosecha_depositados": { campo: "restos_cosecha_depositados", tipo: "si_no" },
  "labor.fecha_establecimiento_cubierta": { campo: "fecha_establecimiento_cubierta", tipo: "fecha" },
  "labor.tipo_cobertura": { campo: "tipo_cobertura", tipo: "texto" },
  "labor.anchura_cubierta_m": { campo: "anchura_cubierta_m", tipo: "numero" },
  "labor.anchura_libre_proyeccion_m": { campo: "anchura_libre_proyeccion_m", tipo: "numero" },
  "labor.restos_desbroce_depositados": { campo: "restos_desbroce_depositados", tipo: "si_no" },
  "labor.restos_poda_depositados": { campo: "restos_poda_depositados", tipo: "si_no" },
  "labor.material_adquirido": { campo: "material_adquirido", tipo: "si_no" },
  "labor.fecha_adquisicion": { campo: "fecha_adquisicion", tipo: "fecha" },
  "labor.siembra_directa": { campo: "siembra_directa", tipo: "si_no" },
  "labor.densidad_plantacion": { campo: "densidad_plantacion", tipo: "numero" },
  "labor.marco_plantacion": { campo: "marco_plantacion", tipo: "texto" },
  "labor.volumen_agua": { campo: "volumen_agua", tipo: "numero" },
  "labor.unidad_agua": { campo: "unidad_agua", tipo: "opciones", opciones: "unidades_agua" },
  "labor.origen_agua": { campo: "origen_agua", tipo: "opciones", opciones: "origenes_agua" },
  "labor.sistema_riego": { campo: "sistema_riego", tipo: "opciones", opciones: "sistemas_riego" },
  "labor.numero_contador": { campo: "numero_contador", tipo: "texto" },
  "labor.nitratos_agua": { campo: "nitratos_agua", tipo: "numero" },

  // Los datos de un análisis que se copian del boletín del laboratorio. Los números que
  // trae cada clase de análisis no están aquí: salen del catálogo del servidor, porque
  // cambian según lo que se haya analizado.
  "analitica.lote": { campo: "lote", tipo: "texto" },
  "analitica.laboratorio": {
    campo: "laboratorio", tipo: "texto", ayuda: "analitica.laboratorio",
  },
  "analitica.numero_informe": { campo: "numero_informe", tipo: "texto" },
  "analitica.fecha_resultado": { campo: "fecha_resultado", tipo: "fecha" },
  "analitica.sustancia_detectada": { campo: "sustancia_detectada", tipo: "texto" },
  "analitica.observaciones": { campo: "observaciones", tipo: "texto" },

  // Lo que se vende. El producto y la variedad se escriben: el catálogo oficial de
  // «producto vegetal» no lo tenemos, y una lista inventada sería peor que dejar escribir
  // lo que pone el albarán.
  "venta.producto": { campo: "producto", tipo: "texto", obligatorio: true },
  "venta.tipo": { campo: "tipo", tipo: "opciones", opciones: "tipos_venta" },
  "venta.variedad": { campo: "variedad", tipo: "texto" },
  "venta.cantidad": { campo: "cantidad", tipo: "numero", obligatorio: true },
  "venta.unidad": { campo: "unidad", tipo: "opciones", opciones: "unidades_venta" },
  "venta.lote": { campo: "lote", tipo: "texto" },
  "venta.comprador": { campo: "comprador", tipo: "texto" },
  "venta.numero_albaran": { campo: "numero_albaran", tipo: "texto" },
  "venta.observaciones": { campo: "observaciones", tipo: "texto" },
  // **El dinero de una entrega NO está en este mapa, y es una decisión** (T12, 03/10/2026). Podría estar
  // —son cuatro campos más del asistente— y se quitó al comprobar lo que costaba: el asistente de la venta
  // es el recorrido **del campo** («qué saqué, cuánto, cuándo y a quién»), y el dinero se apunta después,
  // en su propia pantalla (`#/ventas/<id>/importe`), que es donde el caso A08 del contrato tiene sentido:
  // **una entrega se apunta sin precio** el día que sale de la finca y el importe se sabe cuando llega el
  // papel del comprador, que puede ser tres días después. Meterse aquí habría alargado el asistente con dos
  // pantallas más para un dato que casi nunca se tiene en la parcela.
  //
  // Lo que sí hace falta, y por eso se dice: **los cuatro campos tienen su puerta** en esa pantalla (el
  // importe, el precio, el vencimiento y de qué cosecha salió). Un campo del modelo sin ninguna pantalla
  // que lo pregunte es el fallo que este proyecto ha pagado más veces (`AGENTS.md` §4).
};

/**
 * En qué pantallas se pregunta cada cosa, y en qué orden.
 *
 * La regla del asistente es una pregunta por pantalla. Aquí hay una excepción
 * deliberada: **los campos opcionales van todos juntos en el último paso**. El motivo
 * es que la regla existe para no marear con decisiones obligatorias, y cinco pantallas
 * seguidas de datos que se pueden dejar en blanco marean más que una sola con un botón
 * grande de DEJARLO debajo.
 */
const MAESTRO_PASOS = {
  // El año del cuaderno: el año, las dos fechas (juntas, porque son una sola idea: **cuándo empieza y
  // cuándo termina ese año**) y si lo ha dado por terminado.
  //
  // Los dos números del año van en pantallas separadas de las fechas a propósito: el año es lo primero que
  // se contesta y lo que más se equivoca (2027 donde iba 2026), así que se pregunta solo.
  campana: [
    { campos: ["campana.anio"] },
    { campos: ["campana.fecha_inicio", "campana.fecha_fin"], titulo: "campana.fechas" },
    { campos: ["campana.cerrada"] },
  ],
  parcela: [
    { campos: ["parcela.alias"] },
    { campos: ["parcela.superficie_ha"] },
    { campos: ["parcela.sistema"] },
    {
      opcional: true,
      campos: [
        "parcela.ref_sigpac",
        "parcela.municipio",
        "parcela.provincia",
        "parcela.uso_sigpac",
        "parcela.masa_agua_cerca",
        "parcela.captacion_consumo_humano",
        "parcela.zona_vulnerable_nitratos",
      ],
    },
  ],
  producto: [
    { campos: ["producto.nombre_comercial"] },
    { campos: ["producto.numero_registro"] },
    { campos: ["producto.dosis_maxima"] },
    { campos: ["producto.unidad_dosis"] },
    { campos: ["producto.plazo_seguridad_dias"] },
    {
      opcional: true,
      campos: [
        "producto.materia_activa",
        "producto.tipo_producto",
        "producto.lote",
        "producto.fecha_caducidad",
        "producto.proveedor",
      ],
    },
    {
      // Cuánto compraste. Es opcional porque hay agricultores que no lo saben de memoria, y
      // obligarles a inventarse un número sería peor que dejarlo en blanco: la pantalla del
      // almacén dirá que no se puede saber, en vez de dar una cuenta falsa.
      opcional: true,
      campos: [
        "producto.cantidad_comprada",
        "producto.unidad_compra",
        "producto.fecha_compra",
      ],
    },
    {
      // La autorización del producto. Sin esto, las tres comprobaciones que dependen de ella no
      // podían saltar nunca: el programa daba por bueno que todo producto está autorizado, que se
      // puede usar en ecológico y que no tiene autorización excepcional caducada, sin preguntarlo.
      opcional: true,
      campos: [
        "producto.autorizado",
        "producto.permitido_ecologico",
        "producto.autorizacion_excepcional",
        "producto.autorizacion_hasta",
      ],
    },
  ],
  abono: [
    { campos: ["abono.nombre"] },
    { campos: ["abono.riqueza_n", "abono.riqueza_p", "abono.riqueza_k"], titulo: "abono.riqueza" },
    { opcional: true, campos: ["abono.tipo"] },
  ],
  aplicador: [
    { campos: ["aplicador.nombre"] },
    { campos: ["aplicador.es_empresa"] },
    { campos: ["aplicador.numero_carne"] },
    {
      opcional: true,
      campos: ["aplicador.fecha_caducidad_carne", "aplicador.numero_ropo"],
    },
    {
      // El tipo de carné y, si aplica, el número del registro de equipos de aplicación aérea.
      opcional: true,
      campos: ["aplicador.tipo_carne", "aplicador.numero_reganip"],
    },
  ],
  equipo: [
    // Lo primero: cómo se llama, qué es y de quién es. El «de quién es» es lo que distingue las tres
    // pestañas de la app oficial: maquinaria propia, ajena (la del ROMA que no es tuya) y equipos que
    // no van en el ROMA (mochilas, carretillas, aperos).
    { campos: ["equipo.nombre", "equipo.tipo", "equipo.titularidad"] },
    {
      opcional: true,
      campos: ["equipo.marca", "equipo.modelo", "equipo.fecha_adquisicion"],
    },
    {
      opcional: true,
      campos: ["equipo.numero_roma", "equipo.fecha_iteaf", "equipo.fecha_proxima_iteaf"],
    },
  ],
  asesor: [
    { campos: ["asesor.nombre"] },
    { campos: ["asesor.numero_ropo"] },
    { campos: ["asesor.ambito"] },
    {
      opcional: true,
      campos: ["asesor.entidad_certificacion", "asesor.telefono"],
    },
  ],
  instalacion: [
    { campos: ["instalacion.alias"] },
    { campos: ["instalacion.tipo"] },
    {
      opcional: true,
      campos: [
        "instalacion.uso",
        "instalacion.referencia_catastral",
        "instalacion.municipio",
        "instalacion.superficie_m2",
      ],
    },
  ],
};

/**
 * Convierte lo que devuelve un botón en el valor de verdad.
 *
 * Los atributos de un botón son texto, así que "sí", "no" y "no lo sé" viajan con un
 * prefijo. Sin esto, `false` llegaría a la API como la cadena "false", que es
 * verdadera: el clásico error que apunta justo lo contrario de lo que dijo el
 * agricultor.
 */
function valorDeEleccion(bruto) {
  if (bruto === "bool:true") return true;
  if (bruto === "bool:false") return false;
  if (bruto === "nulo") return null;
  return bruto;
}

/** Cómo se le enseña al agricultor un valor guardado en la base de datos. */
function etiquetaDeValor(clave, valor) {
  const tabla = t(clave, []) || [];
  // **El servidor manda esta tabla de dos formas, y las dos son la misma cosa**: una lista de
  // `{valor, texto}` (los catálogos de elegir) o un diccionario `valor → texto` (`etiquetas_labor`).
  // Sin esto, pedir la etiqueta de un trabajo revienta con «lista.find is not a function», y el
  // reviente no se ve hasta que el agricultor apunta un trabajo. Se descubrió en la ronda 91, al
  // enseñar un trabajo en la lista del cuaderno.
  if (!Array.isArray(tabla)) {
    const texto = tabla[String(valor)];
    return texto === undefined ? String(valor || "") : texto;
  }
  const encontrado = tabla.find((item) => item && item.valor === valor);
  return encontrado ? encontrado.texto : String(valor || "");
}

/** El nombre de una práctica del campo («siembra», «podar», «pastorear»…) tal y como se lee. */
function nombreDeLaPractica(tipo) {
  const etiquetas = t("etiquetas_labor", {}) || {};
  return (etiquetas && etiquetas[tipo]) || "";
}

/**
 * La composición de un abono: «4-0-0», o **«no consta»** si no se sabe (A6, 03/10/2026).
 *
 * Las riquezas de un abono pueden ser «no lo sé» desde que dejaron de valer `0.0` por defecto, y esto se
 * pintaba con un guion entre los tres números: una ficha sin composición habría salido en pantalla como
 * **«null-null-null»**. Un 0 y un «no lo sé» no son lo mismo —el 0 dice que el abono no lleva nada—, así que
 * cuando falta alguno de los tres se dice con palabras, que es lo que se puede leer.
 */
function composicionDelAbono(abono) {
  const numeros = [abono.riqueza_n, abono.riqueza_p, abono.riqueza_k];
  if (numeros.some((uno) => uno === null || uno === undefined)) {
    return t("rotulos.composicion_no_se", "");
  }
  return numeros.join("-");
}

/** Las opciones de un campo de elegir, o null si el campo se escribe. */
function opcionesDe(spec) {
  if (spec.tipo === "si_no") {
    return [
      { valor: "bool:true", texto: accion("si") },
      { valor: "bool:false", texto: accion("no") },
    ];
  }
  if (spec.tipo === "si_no_no_se") {
    return [...opcionesDe({ tipo: "si_no" }), { valor: "nulo", texto: accion("no_se") }];
  }
  if (spec.tipo === "opciones") {
    const lista = t(spec.opciones, []) || [];
    return lista.map((opcion) =>
      typeof opcion === "string" ? { valor: opcion, texto: opcion } : opcion,
    );
  }
  return null;
}


/**
 * Los datos de un maestro (un producto, una máquina, un asesor…), **como datos** y no como HTML.
 *
 * Es un bloque por dato, y cada uno puede ser **de escribir** (con su `id`, que es lo único que tiene
 * `app.js` para leerlo) o **de elegir** (con sus botones, que llevan `data-campo` y `data-valor`).
 * Quien los pinta es la pieza `react/piezas/campos_del_maestro.js`.
 *
 * Los prepara esta función **una sola vez** para los dos caminos: los pasos ya migrados se los pasan a
 * la pieza, y los que todavía se pintan con `pintar()` los convierten a HTML con
 * `pintaCamposMaestro()`. Así el día que se migre el último paso no hay dos listas que se puedan
 * separar.
 */
function bloquesDelMaestro(claves) {
  return claves
    .map((clave) => {
      const spec = CAMPOS[clave];
      if (!spec) return null;
      const etiqueta = t(`etiquetas.${clave}.pregunta`, "");
      const pista = t(`etiquetas.${clave}.pista`, "");
      const valor = estado.asistente.borrador[spec.campo];
      const ayuda = spec.ayuda ? datosDeLaAyuda(spec.ayuda) : null;
      const opciones = opcionesDe(spec);
      if (opciones) {
        return {
          tipo: "opciones",
          campo: spec.campo,
          etiqueta,
          pista,
          ayuda,
          opciones: opciones.map((opcion) => ({
            etiqueta: opcion.texto,
            valor: opcion.valor,
            // **En un campo de tres estados, `null` ES la respuesta «no lo sé»**, no un hueco sin
            // contestar. Se comparan como texto, así que sin esto el `null` de la base no casaba con
            // la opción `nulo`: al corregir una ficha que decía «no lo sé» no salía marcada ninguna
            // opción y el agricultor tenía que volver a elegir, con el riesgo de elegir otra cosa.
            // En un «sí o no» de dos estados, en cambio, `null` sí es un hueco y no se marca nada.
            //
            // **Y vale para cualquier lista que ofrezca «no lo sé»**, no solo para los «sí o no»
            // (A10, 05/10/2026): el sistema de una tierra (`secano | regadio | nulo`) es una lista de
            // catálogo, y sin esto una tierra sin sistema declarado salía con las tres opciones sin
            // marcar —como si nadie hubiera contestado nunca— en vez de con «no lo sé» marcado, que es
            // lo que dice la base. Se pregunta por la lista y no por el tipo: `"nulo"` es el valor de
            // la opción de «no lo sé» en toda la aplicación (`valorDeEleccion`).
            elegido:
              valor === null && opciones.some((cual) => cual.valor === "nulo")
                ? opcion.valor === "nulo"
                : String(valor) === String(opcion.valor),
          })),
        };
      }
      return {
        // `si_no` y `si_no_no_se` salen por `opcionesDe`, así que aquí solo quedan los tipos que se
        // escriben: texto, número y fecha. Cualquier otro se pinta como texto, que es lo que hacía la
        // interfaz de siempre, en vez de dejar el dato sin pintar.
        tipo: spec.tipo === "numero" ? "numero" : spec.tipo === "fecha" ? "fecha" : "texto",
        id: spec.campo,
        etiqueta,
        valor: valor === undefined || valor === null ? "" : valor,
        pista,
        ayuda,
      };
    })
    .filter(Boolean);
}

/**
 * El paso de los datos de un maestro, ya en React.
 *
 * Los usa casi todo el asistente: dar de alta un producto, una máquina o un asesor, y los números del
 * plan de abono.
 */
function montarCamposMaestro(claves) {
  return camposDelMaestro({ bloques: bloquesDelMaestro(claves) });
}

function recogeCamposMaestro(claves) {
  return () => {
    for (const clave of claves) {
      const spec = CAMPOS[clave];
      if (opcionesDe(spec)) continue; // los de elegir se rellenan al pulsar
      const elemento = document.getElementById(spec.campo);
      if (elemento) estado.asistente.borrador[spec.campo] = elemento.value;
    }
    for (const clave of claves) {
      const spec = CAMPOS[clave];
      const valor = estado.asistente.borrador[spec.campo];
      const vacio = valor === undefined || valor === null || String(valor).trim() === "";
      if (spec.obligatorio && vacio) {
        return rellena(t("maestros.falta_este_dato", ""), {
          pregunta: t(`etiquetas.${clave}.pregunta`, ""),
        });
      }
    }
    return null;
  };
}

function pasosDeMaestro(tipo) {
  return MAESTRO_PASOS[tipo].map((paso) => {
    const varios = paso.campos.length > 1;
    const agrupado = varios && !paso.titulo;
    const primera = CAMPOS[paso.campos[0]];
    return {
      campos: paso.campos,
      opcional: paso.opcional,
      titulo: paso.titulo
        ? t(`etiquetas.${paso.titulo}.pregunta`, "")
        : agrupado
          ? t("maestros.grupo_opcional", "")
          : t(`etiquetas.${paso.campos[0]}.pregunta`, ""),
      pista: agrupado
        ? t("maestros.grupo_opcional_pista", "")
        : varios
          ? ""
          : t(`etiquetas.${paso.campos[0]}.pista`, ""),
      montar: () => montarCamposMaestro(paso.campos),
      recoger: recogeCamposMaestro(paso.campos),
      _ayuda: primera.ayuda,
    };
  });
}

/** Convierte el borrador del asistente en lo que espera la API. */
function cargaMaestro(tipo) {
  const api = MAESTROS_API[tipo];
  const borrador = estado.asistente.borrador;
  const carga = {};
  for (const spec of Object.values(CAMPOS)) {
    const campo = spec.campo;
    if (!(campo in borrador)) continue;
    const valor = borrador[campo];
    if (valor === undefined) continue;
    if (valor === "") continue;
    // Los «sí o no» vuelven a ser verdadero o falso antes de salir hacia la API: en la pantalla viajan
    // como "bool:true"/"bool:false" (ver `opcionesDe`), y mandar la cadena "false" sería mandar
    // **verdadero**, que es el clásico error que apunta lo contrario de lo que dijo el agricultor.
    if (spec.tipo === "si_no" || spec.tipo === "si_no_no_se") {
      carga[campo] = typeof valor === "boolean" ? valor : valorDeEleccion(String(valor));
      continue;
    }
    if (api.numeros && api.numeros.includes(campo)) {
      const numero = aNumero(valor);
      if (numero !== null) carga[campo] = numero;
    } else {
      carga[campo] = valor;
    }
  }
  return carga;
}

/**
 * Las tierras de «Mis parcelas, productos y máquinas», ya como tarjetas (rediseño de la ronda 78).
 *
 * POR QUÉ. Esta sección era **un muro de renglones iguales**: con 51 tierras dadas de alta, «El Prado ·
 * 4,90 ha · 47-370-0-0-503-51-1» y el de al lado se leen igual, y del muro no se podía hacer nada. El
 * rediseño (`docs/stitch/rediseno/mis_tierras.png`) pone en cada tierra lo que ya hace falta para
 * reconocerla —la forma del SIGPAC, el pueblo— y, además, **lo que le falta a esa tierra y el camino
 * para arreglarlo dentro de la misma tarjeta**, que es lo que evita que el agricultor tenga que ir a otra
 * pantalla a buscar la tierra por su nombre.
 *
 * DOS COSAS QUE NO SE INVENTAN AQUÍ:
 *
 *  1. **Si le falta el cultivo lo dice el servidor**, no esta función: `/api/cultivos` devuelve
 *     `falta_decirlo` ya calculado («el agricultor mira esto para ver si le falta algo: se lo decimos
 *     calculado»). Si no se sabe, no se dice nada: un aviso inventado al lado de una tierra es
 *     exactamente lo que este programa no puede hacer.
 *  2. **La tarjeta no elige nada: abre** lo que hay sembrado en esa tierra (`cultivo-decir`, que es la
 *     pantalla donde se ve y se cambia). Por eso va sin el círculo de elegir (`marca: false`) y con el
 *     pie que dice qué hace: un círculo sin marcar en una lista que no se elige es una promesa que no se
 *     cumple.
 */
function tierrasParaMisCosas() {
  const dichas = estado.cultivos || {};
  const porTierra = new Map((dichas.parcelas || []).map((p) => [p.parcela_id, p]));
  const claveSigpac = t("maestros.tierra_sigpac", "");
  const claveCultivo = t("maestros.tierra_cultivo", "");
  const faltaDecirlo = t("maestros.tierra_sin_cultivo", "");
  // **Las que se enseñan**: si el agricultor ha buscado en esta pantalla, las que casan (ronda 87). El
  // número de la tarjeta ("Tierra n.º 12") sigue siendo el suyo de la lista entera: es como el agricultor
  // la llama, y renumerarlas al buscar sería mentirle.
  const suyas = tierrasQueCasen(estado.parcelas, estado.filtroTierrasMisCosas);
  // El número que le toca a cada tierra en la lista **entera** (1, 2, 3…): es como la llama el agricultor.
  const numeros = new Map(estado.parcelas.map((parcela, posicion) => [parcela.id, posicion + 1]));

  return suyas.map((parcela) => {
    const numero = numeros.get(parcela.id) || 1;
    const suya = porTierra.get(parcela.id) || {};
    const actual = suya.actual || null;
    // Lo que hay sembrado, con su variedad y su secano o regadío. Solo con lo que hay: si no hay
    // variedad apuntada, no se deja un hueco en medio.
    const cultivo = actual
      ? [actual.especie, actual.variedad, etiquetaDeValor("sistemas", actual.sistema || parcela.sistema)]
          .filter(Boolean)
          .join(" · ")
      : "";

    return {
      etiqueta: parcela.alias,
      rotulo: rellena(t("maestros.tierra_numero", ""), { numero }),
      ...formaDeLaTierra(parcela),
      // Los datos van **con su nombre delante**: una referencia del SIGPAC suelta no dice qué es.
      filas: [
        parcela.ref_sigpac ? { etiqueta: claveSigpac, valor: parcela.ref_sigpac } : null,
        cultivo ? { etiqueta: claveCultivo, valor: cultivo } : null,
      ].filter(Boolean),
      pendiente: suya.falta_decirlo ? faltaDecirlo : "",
      /** Lo mismo, en crudo, para la **tabla del ordenador** (30/09/2026): así la tabla y la tarjeta
       *  enseñan lo mismo porque salen del mismo sitio, y no hay dos formas de contar una tierra que se
       *  puedan separar. */
      numero,
      alias: parcela.alias,
      ref_sigpac: parcela.ref_sigpac || "",
      municipio: parcela.municipio || "",
      // **La superficie, tal cual viene, incluido el `null`** (A7, 03/10/2026). Aquí ponía
      // `parcela.superficie_ha || 0`, y eso es convertir «no lo sé» en «0 hectáreas» en la pantalla: la
      // tabla del ordenador enseñaría un cero y el pie sumaría un cero que no existe. Quien lo pinte tiene
      // que poder decir «falta» (ver `numeroConUnidad` y la columna de hectáreas de la tabla).
      superficie_ha: parcela.superficie_ha === undefined ? null : parcela.superficie_ha,
      cultivo: actual ? actual.especie || "" : "",
      falta_decirlo: Boolean(suya.falta_decirlo),
      // **La tarjeta abre la FICHA de la tierra, la misma que abre la fila en el ordenador** (07/10/2026).
      //
      // Antes abría «lo que hay sembrado» (`cultivo-decir`), así que **la misma tierra llevaba a dos
      // pantallas distintas según el aparato**: en el móvil al cultivo y en el ordenador al panel con su
      // historia. Eso es justo lo contrario de la ficha única que pide el encargo, y además el cultivo
      // **ya se ve dentro de la ficha** («Qué hay hoy», con la especie, la variedad y desde cuándo), así
      // que abrir la ficha no quita nada de lo que se miraba antes. Lo señaló la revisión del recorrido:
      // la misma tierra tenía cuatro pantallas.
      //
      // El rótulo de la tarjeta va con la acción: una tarjeta que diga «VER EL CULTIVO» y abra otra cosa
      // sería peor que el problema que se arregla.
      accionTexto: t("panel.tierra_historia", ""),
      marca: false,
      elegida: false,
      accion: "tierra-historia",
      datos: { id: parcela.id },
      textos: {},
      // Y sus dos botones (ronda 92): corregir la tierra (el nombre, las hectáreas, la referencia… lo que
      // se equivocó al darla de alta) o borrarla. **Y el de «su historia»** (T15, 05/10/2026), que en el
      // **panel del ordenador** es la única forma de entrar (allí la fila abre el panel, no la ficha).
      //
      // **En la tarjeta del móvil ese botón ya no sale**: desde el 07/10/2026 la propia tarjeta abre la
      // ficha, así que repetirlo debajo sobra — y es la pantalla del móvil la que lo quita, no esta lista,
      // porque el panel del ordenador sí lo necesita.
      acciones: [
        {
          etiqueta: t("panel.tierra_historia", ""),
          accion: "tierra-historia",
          datos: { id: parcela.id },
          clase: "boton-claro",
        },
        ...botonesDeCorregirYBorrar("parcela", parcela.id),
      ],
    };
  });
}

/**
 * Las tierras, en el orden que ha pedido el agricultor en la tabla.
 *
 * **El orden es de la pantalla, no del aparato**: si ordena por hectáreas en el ordenador, las tarjetas del
 * móvil salen en el mismo orden (es la misma lista, mirada de dos formas). Y el nombre de cada tierra no
 * cambia nunca: «Tierra n.º 12» es su número de siempre, se ordene como se ordene.
 */
function tierrasOrdenadas(tierras) {
  return ordenarFichas(tierras, elOrdenDeLaTabla("tierras"), "numero");
}

/**
 * Los apuntes del año, en el orden que ha pedido el agricultor en su tabla.
 *
 * **De lo más nuevo a lo más viejo de entrada**: es como lo cuenta el agricultor («lo de la semana pasada»)
 * y como estaba ya en las tarjetas. El orden se puede cambiar pulsando una cabecera, y entonces vale para
 * las dos formas de ver la lista (la tabla del ordenador y las tarjetas del móvil).
 */
function apuntesOrdenados(fichas) {
  // La fecha se compara como texto, y las fechas del programa son `2026-05-01`: así se ordenan bien sin
  // convertirlas a nada (que es justo el motivo de guardarlas así).
  return ordenarFichas(fichas, elOrdenDeLaTabla("apuntes"), "id");
}

/**
 * El orden de una tabla, que se acuerda de lo que ha pulsado el agricultor.
 *
 * Cada tabla tiene el suyo (mirar las tierras por hectáreas no tiene por qué cambiar el orden del
 * cuaderno), y cada uno **empieza por lo que tiene sentido en esa lista**: las tierras por número (como las
 * dio de alta) y los apuntes por fecha, de lo más nuevo a lo más viejo.
 */
function elOrdenDeLaTabla(clave) {
  estado.ordenDeLaTabla = estado.ordenDeLaTabla || {};
  if (!estado.ordenDeLaTabla[clave]) {
    estado.ordenDeLaTabla[clave] = { ...ORDEN_DE_ENTRADA[clave] };
  }
  return estado.ordenDeLaTabla[clave];
}

/**
 * Por dónde empieza el orden de cada tabla, y por qué.
 *
 * **Cada lista empieza por lo que se viene a mirar en ella** (30/09/2026): las tierras por su número (como
 * las dio de alta el agricultor), el cuaderno y las facturas por fecha **de lo más nuevo a lo más viejo**
 * (es como lo cuenta: «lo de la semana pasada»), los años del más nuevo al más viejo y el almacén por el
 * nombre del producto, que es como se busca uno en una estantería.
 *
 * Antes esto era un `if` con dos casos y todo lo demás caía en «por número»: la tabla de facturas y la de
 * los años se ordenaban por un campo que no tienen, así que salían por el orden de dentro **y su cabecera no
 * marcaba por dónde iba el orden** —una tabla que no dice por qué está ordenada es una tabla que el
 * agricultor no sabe si ha ordenado él—. Ahora cada tabla tiene su entrada, y la que se añada mañana tiene
 * que traer la suya.
 *
 * El campo es **el nombre del dato en crudo** de la ficha (`fecha_iso`, `anio_numero`…), no el de lo que se
 * enseña: se ordena por el dato, no por el texto ya escrito.
 */
const ORDEN_DE_ENTRADA = {
  tierras: { campo: "numero", sentido: 1 },
  apuntes: { campo: "fecha", sentido: -1 },
  facturas: { campo: "fecha_iso", sentido: -1 },
  anos: { campo: "anio_numero", sentido: -1 },
  cesta: { campo: "nombre_comercial", sentido: 1 },
  cultivos: { campo: "alias", sentido: 1 },
  // La maquinaria (T14): por nombre, que es como se busca una máquina en una lista. Se ordena por el dato
  // en crudo (`nombre`), no por el texto ya montado de la fila.
  maquinaria: { campo: "nombre", sentido: 1 },
};

/**
 * Ordena una lista de fichas por el campo que ha pedido el agricultor en una tabla.
 *
 * **El orden es de la pantalla, no del aparato**: si ordena por hectáreas en el ordenador, las tarjetas del
 * móvil salen en el mismo orden (es la misma lista, mirada de dos formas). Y el número de cada cosa no
 * cambia nunca: «Tierra n.º 12» es su número de siempre, se ordene como se ordene.
 *
 * Los números se comparan como números y los textos como texto en castellano (`toLocaleLowerCase`), que es
 * lo que hace que «Ávila» no acabe detrás de «Zamora». A igualdad, se ordena por el campo de desempate
 * (normalmente el número de la ficha): así el orden no baila entre dos pulsaciones.
 */
function ordenarFichas(fichas, orden, desempate) {
  const valor = (ficha) => {
    const suyo = ficha[orden.campo];
    if (typeof suyo === "number") return suyo;
    if (suyo === null || suyo === undefined || suyo === "") return "";
    const numero = Number(suyo);
    if (suyo !== "" && Number.isFinite(numero) && String(suyo).trim() !== "") return numero;
    return String(suyo).toLocaleLowerCase("es");
  };
  return [...fichas].sort((una, otra) => {
    const a = valor(una);
    const b = valor(otra);
    // Lo que no tiene dato se va al final, se ordene como se ordene: un hueco en medio de la tabla no
    // dice nada y estorba para comparar.
    if (a === "" && b !== "") return 1;
    if (b === "" && a !== "") return -1;
    if (a < b) return -1 * orden.sentido;
    if (a > b) return 1 * orden.sentido;
    return (Number(una[desempate]) || 0) - (Number(otra[desempate]) || 0);
  });
}

/** Las cabeceras de una tabla, con la marca de por dónde va el orden. */
function columnasDeLaTabla(clave, columnas) {
  const orden = elOrdenDeLaTabla(clave);
  return columnas.map((columna) => ({
    ...columna,
    ordenada: Boolean(columna.campo) && columna.campo === orden.campo,
    descendente: Boolean(columna.campo) && columna.campo === orden.campo && orden.sentido < 0,
    orden: columna.campo
      ? rellena(t("tabla.ordenar_por", ""), { columna: columna.texto })
      : "",
  }));
}

/** El pie de una tabla: cuántas cosas y el total que se viene a mirar. */
function resumenDeLaTabla(base, cuantas, totales) {
  const texto = conCuenta(t("tabla", {}), base, cuantas);
  return rellena(texto, totales);
}

/**
 * La tabla de las tierras, para el ordenador (30/09/2026).
 *
 * POR QUÉ. Son 64 tierras: en el móvil se miran de una en una con su tarjeta, y en el ordenador lo que se
 * quiere es **verlas todas de arriba abajo, comparar las hectáreas y ordenarlas**. Es lo que David pidió con
 * «una aplicación de gestión».
 *
 * Lo que se prepara aquí es lo que el componente no puede saber: los nombres de las columnas (del servidor),
 * **qué columna está ordenada y hacia dónde**, las celdas de cada tierra y **el total del pie**, que es la
 * cuenta que se viene a hacer en una tabla de tierras.
 *
 * La última columna son los botones de la fila: los mismos dos de siempre (CORREGIR y BORRAR) más el que
 * abre lo que hay sembrado, que es lo que hace la tarjeta en el móvil.
 */
function tablaDeTierras(tierras, buscando) {
  const col = (clave) => t(`tabla.${clave}`, "");
  const ordenadas = tierrasOrdenadas(tierras);
  const elegida = filaElegida("tierras");
  // **Cinco columnas, no siete** (30/09/2026). El pueblo y la referencia del SIGPAC **están en el panel de al
  // lado** (y en la tarjeta del móvil): repetirlos en la tabla la ensancha hasta que los botones de la última
  // columna quedan cortados por el borde. Una tabla de lista lleva lo que hace falta para **reconocer** la
  // fila y compararla (su número, su nombre, sus hectáreas y qué tiene); el resto, en su ficha.
  const columnas = columnasDeLaTabla("tierras", [
    { texto: col("numero"), campo: "numero", clase: "tabla-numero" },
    { texto: col("nombre"), campo: "alias" },
    { texto: col("hectareas"), campo: "superficie_ha", clase: "tabla-numero" },
    { texto: col("cultivo"), campo: "cultivo" },
    { texto: col("acciones") },
  ]);

  const filas = ordenadas.map((tierra) => ({
    elegida: Number(tierra.datos.id) === Number(elegida),
    celdas: [
      { texto: String(tierra.numero), clase: "tabla-numero" },
      {
        // **El nombre abre la FICHA de la tierra** (07/10/2026, opción (a) del encargo del rediseño: «la
        // historia es la ficha»).
        //
        // Antes el nombre solo marcaba la fila y la tierra se veía en el panel de al lado; desde el
        // 07/10 la ficha tiene **todo** lo que tenía el panel (nombre, hectáreas y la referencia oficial),
        // así que tocar el nombre lleva directo a ella. Es como se hace en cualquier programa: se toca el
        // nombre. **Y el resto de la fila sigue marcando**, así que el panel no ha desaparecido: la decisión
        // de quitarlo (o dejarlo como vista previa) es el paso siguiente del plan, y para eso este cambio
        // no estorba — al revés, es la mitad del camino.
        texto: tierra.alias,
        accion: "tierra-historia",
        datos: { id: tierra.datos.id },
      },
      { texto: formateaNumero(tierra.superficie_ha, 2), clase: "tabla-numero" },
      tierra.cultivo
        ? { texto: tierra.cultivo }
        : {
            // Cuando a una tierra le falta decir qué tiene, la celda lo dice con su etiqueta en ámbar y
            // **con palabras**: el color solo no informa (regla de la casa). La frase es la **corta**
            // (`tabla.sin_decir`): la larga («Todavía no has dicho qué hay aquí este año.») ocupaba tres
            // renglones en la celda y dejaba la columna alta y estrecha, y sigue estando donde se lee: en la
            // tarjeta del móvil y en el panel de al lado.
            estado: { texto: col("sin_decir"), tipo: "mirar" },
            pista: "",
          },
    ],
    acciones: [
      {
        // **En la tabla, un solo botón por fila**: el de la fila (`DECIRLO` / `VER`). Corregir y borrar
        // están **en el panel de al lado**, que es donde se mira la ficha al detalle; con los tres botones en
        // cada fila, cada renglón ocupaba tres líneas y una tabla de 64 tierras se hacía interminable. La
        // etiqueta larga («VER O CAMBIAR LO QUE HAY SEMBRADO») también se queda en el panel: en la columna
        // ensancharía la tabla hasta cortar los botones.
        etiqueta: tierra.falta_decirlo ? col("decirlo") : col("ver_cultivo"),
        accion: "cultivo-decir",
        datos: { id: tierra.datos.id },
        clase: "boton-claro",
      },
    ],
  }));

  // **El pie suma lo que se sabe y dice cuántas tierras no traen su superficie** (A14, 05/10/2026). Antes
  // era `Number(tierra.superficie_ha) || 0`: la tierra sin hectáreas sumaba cero y el pie daba un total
  // que parecía completo. El dato de cuántas faltan lo tiene la propia lista (la columna conserva el
  // hueco, ver `superficie_ha: parcela.superficie_ha === undefined ? null : …`), así que se cuenta aquí
  // —sobre las que se están viendo, que con un filtro puesto no son todas— y se dice con la misma frase
  // que usa la pantalla nueva de tierras.
  const sumando = sumandoLoQueSeSabe(ordenadas, (tierra) => tierra.superficie_ha);
  const hectareas = sumando.suma;
  const sinSuSuperficie = sumando.sin_decir
    ? conCuenta(t("tabla", {}), "tierras_sin_hectareas", sumando.sin_decir)
    : "";
  const resumen = [
    buscando
      ? rellena(col("resumen_filtrado"), {
          cuantas: ordenadas.length,
          total: estado.parcelas.length,
          hectareas: formateaNumero(hectareas, 2),
        })
      : resumenDeLaTabla("resumen_tierras", ordenadas.length, {
          hectareas: formateaNumero(hectareas, 2),
        }),
    // Y lo que no se sabe, en el mismo pie: «Sin hectáreas dichas: 3». Si no se dijera, el total de
    // arriba se leería como el de la finca entera cuando es el de las tierras que lo traen.
    sinSuSuperficie,
  ]
    .filter(Boolean)
    .join(" · ");

  return {
    clave: "tierras",
    etiqueta: col("tierras_etiqueta"),
    columnas,
    filas,
    resumen,
    // El panel de al lado: la tierra elegida, o el aviso de que no hay ninguna elegida.
    panel: panelDeLaTierra(ordenadas),
  };
}

/**
 * Vuelve a pintar la pantalla de la que salió una tabla.
 *
 * POR QUÉ EXISTE (30/09/2026). Ordenar una tabla y elegir una fila **se hacen desde dentro de la tabla**, y
 * las dos cosas tienen que repintar *su* pantalla. Cuando había dos tablas esto era un `if` de una línea
 * («¿es la del cuaderno?»); con cinco, ese `if` hacía lo peor que puede hacer un programa de gestión: pulsar
 * la cabecera de la tabla de facturas ordenaba la lista de tierras y llevaba al agricultor a otra pantalla sin
 * decirle nada. Aquí está escrito una vez, y la tabla que se añada mañana tiene que traer su línea.
 *
 * **Cada clave es la de una tabla** (`clave` en `tablaDe…`, que es la misma que llevan sus botones en
 * `data-tabla`), y la de por defecto son las tierras: es la tabla de la que salen todas las demás.
 */
function repintarLaPantallaDeLaTabla(clave) {
  if (clave === "apuntes") return pantallaCuaderno();
  if (clave === "facturas") return pantallaFacturas();
  if (clave === "anos") return pantallaCampanas();
  if (clave === "cesta") return pantallaCesta();
  if (clave === "cultivos") return pantallaCultivos();
  // La tabla de la maquinaria (T14): se ordena por el dato en crudo (la fecha de la próxima revisión, las
  // horas, el nombre), así que repintarla es volver a montarla con el orden nuevo.
  if (clave === "maquinaria") return pantallaMaquinaria();
  // La tabla de lo que se vende (T12): su orden lo hace **el servidor** —el importe está guardado como
  // texto decimal y en SQL no se puede ordenar por su valor—, así que repintarla es volver a
  // preguntarle con el orden nuevo.
  if (clave === "ventas") return recargarLaTablaDeVentas();
  return pantallaMisCosas();
}

/**
 * La fila que está elegida en una tabla (o vacío).
 *
 * Se acuerda **por tabla**: elegir una tierra no cambia lo que está elegido en el cuaderno. Y se guarda el
 * identificador, no la fila: si el agricultor ordena o busca después, la que está elegida sigue siendo la
 * misma (o desaparece del panel si el filtro la deja fuera, que es lo honesto).
 */
function filaElegida(clave) {
  estado.filaElegida = estado.filaElegida || {};
  return estado.filaElegida[clave] || null;
}

/**
 * El panel de la tierra elegida (fase 3): sus datos, lo que le falta y sus botones, al lado de la lista.
 *
 * Se prepara desde **la misma ficha que la tarjeta del móvil** (`tierrasParaMisCosas`), así que el panel y
 * la tarjeta no pueden decir cosas distintas de la misma tierra.
 */
function panelDeLaTierra(tierras) {
  const p = (clave) => t(`panel.${clave}`, "");
  const m = (clave) => t(`maestros.${clave}`, "");
  const elegida = filaElegida("tierras");
  const tierra = elegida ? tierras.find((una) => Number(una.datos.id) === Number(elegida)) : null;
  const panel = {
    etiqueta: p("etiqueta"),
    titulo: p("tierra"),
    vacio: p("vacio"),
    elegida: Boolean(tierra),
  };
  if (!tierra) return panel;
  return {
    ...panel,
    detalle: rellena(m("tierra_numero"), { numero: tierra.numero }),
    // Los datos **con su nombre delante**: es la misma forma que la ficha de la tarjeta y la de la pantalla
    // que pregunta antes de borrar.
    filas: [
      ...(tierra.filas || []),
      {
        etiqueta: t("rotulos.hectareas", ""),
        valor: `${formateaNumero(tierra.superficie_ha, 2)} ${t("rotulos.hectareas_corto", "")}`,
      },
      ...(tierra.municipio ? [{ etiqueta: p("tierra_pueblo"), valor: tierra.municipio }] : []),
    ],
    avisos: tierra.pendiente ? [tierra.pendiente] : [],
    // **La forma de su recinto**, que es como el agricultor reconoce una tierra (la ve así en el SIGPAC). El
    // diseño de escritorio de esta pantalla la pide y el dato ya venía en la ficha desde la ronda 78.
    dibujo: tierra.dibujo || "",
    // Y **sus últimos apuntes**, que es la pregunta que se hace al mirar una tierra en el despacho
    // («¿qué le he hecho este año?»). Se sacan de los mismos apuntes del año que ya están cargados, sin pedir
    // nada más al servidor, y se enseñan con la fecha delante.
    ultimos: (() => {
      const suyos = losApuntesDelAnio()
        .filter((apunte) => Number(apunte.parcela_id) === Number(tierra.datos.id))
        .slice(0, 3)
        .map((apunte) =>
          [apunte.fecha_escrita, apunte.etiqueta || apunte.queEs].filter(Boolean).join(" · "),
        );
      return { titulo: p("tierra_ultimos"), filas: suyos };
    })(),
    acciones: [
      {
        etiqueta: tierra.accionTexto,
        accion: "cultivo-decir",
        datos: { id: tierra.datos.id },
        clase: "boton-principal",
        sencillo: true,
      },
      ...(tierra.acciones || []).map((una) => ({ ...una, sencillo: true })),
    ],
  };
}

/**
 * La tabla de los apuntes del año, para el ordenador (30/09/2026).
 *
 * POR QUÉ. «Mi cuaderno» es lo que más se mira del programa, y en el móvil se mira apunte a apunte con su
 * tarjeta. En el ordenador lo que quiere un agricultor es **la lista del año entera**: qué hizo, dónde,
 * cuántas hectáreas y cuándo, con lo último arriba, y pudiendo ordenar por hectáreas o por tierra para
 * comparar. Al pie, el total de hectáreas tratadas del año, que es el número que se pregunta el primero.
 *
 * El orden de partida es **por fecha, de lo más nuevo a lo más viejo** (que es como lo cuenta el
 * agricultor), y el pie no cuenta lo que no se puede contar: las cosechas van en kilos, así que solo suman
 * hectáreas los tratamientos, los abonos y las labores.
 */
function tablaDeApuntes(fichas) {
  const col = (clave) => t(`tabla.${clave}`, "");
  const c = (clave) => t(`cuaderno.${clave}`, "");
  const ordenadas = apuntesOrdenados(fichas);
  const columnas = columnasDeLaTabla("apuntes", [
    { texto: col("fecha"), campo: "fecha", clase: "tabla-numero" },
    { texto: col("clase"), campo: "queEs" },
    { texto: col("que"), campo: "etiqueta" },
    { texto: col("tierra"), campo: "donde" },
    { texto: col("hectareas"), campo: "hectareas", clase: "tabla-numero" },
    { texto: c("el_cultivo"), campo: "cultivo" },
    { texto: col("acciones") },
  ]);

  const filas = ordenadas.map((ficha) => ({
    celdas: [
      { texto: ficha.fecha_escrita, clase: "tabla-numero" },
      {
        texto: ficha.queEs,
        // Si el apunte está firmado se dice aquí, con su etiqueta: es lo que impide borrarlo (se anula) y
        // lo que hay que ver antes de intentarlo.
        estado: ficha.firmado ? { texto: col("firmado"), tipo: "voluntario" } : null,
      },
      { texto: ficha.etiqueta },
      { texto: ficha.donde },
      ficha.hectareas
        ? { texto: formateaNumero(ficha.hectareas, 2), clase: "tabla-numero" }
        : { texto: "", clase: "tabla-numero" },
      { texto: ficha.cultivo },
    ],
    acciones: ficha.acciones || [],
  }));

  const hectareas = sumandoLoQueSeSabe(ordenadas, (ficha) => ficha.hectareas).suma;
  // **Y al pie, los que están firmados** (30/09/2026): lo pide el diseño de escritorio del cuaderno
  // (`docs/stitch/escritorio/cuaderno.png`) y es lo que mira una inspección —un apunte firmado no se puede
  // borrar, se anula—. Solo se dice cuando hay alguno: «0 firmados» sería una noticia que nadie ha pedido.
  const firmados = ordenadas.filter((ficha) => ficha.firmado).length;
  // **Y lo mismo que en el pie de las tierras** (A14, 05/10/2026): la suma de hectáreas es la de los
  // apuntes que la traen, así que se dice cuántos no la traen. La frase es **la misma** que usa el panel de
  // mando (`tabla.apuntes_sin_hectareas`, con su singular): es el mismo dato dicho igual, y tener la misma
  // frase escrita en dos diccionarios es la forma de que un día digan cosas distintas.
  const sinHectareas = sumandoLoQueSeSabe(ordenadas, (ficha) => ficha.hectareas).sin_decir;
  const resumen = [
    resumenDeLaTabla("resumen_apuntes", ordenadas.length, {
      hectareas: formateaNumero(hectareas, 2),
    }),
    sinHectareas ? conCuenta(t("tabla", {}), "apuntes_sin_hectareas", sinHectareas) : "",
    firmados ? conCuenta(t("tabla", {}), "firmados", firmados) : "",
  ]
    .filter(Boolean)
    .join(" · ");
  return {
    clave: "apuntes",
    etiqueta: col("apuntes_etiqueta"),
    columnas,
    filas,
    resumen,
  };
}

function pantallaMisCosas() {
  const m = (clave) => t(`maestros.${clave}`, "");
  const cuantas = estado.parcelas.length;
  const tierras = tierrasParaMisCosas();
  const buscando = Boolean(estado.filtroTierrasMisCosas);
  const secciones = [
    {
      tipo: "parcela",
      // Las tierras van como tarjetas y no como lista de renglones: ver `tierrasParaMisCosas()`.
      tarjetas: true,
      // **Y en el ordenador, como tabla** (30/09/2026): son 64 tierras, y esto es lo que pidió David. Las
      // dos formas van en el mismo HTML y el CSS enseña la que toca según el ancho: los mismos datos, los
      // mismos botones y el mismo manejador de clics.
      tabla: tablaDeTierras(tierras, buscando),
      // El buscador de tierras (ronda 87), que es lo que pide el diseño en esta pantalla: con 51 tierras,
      // mirar una concreta era recorrerlas todas.
      buscar: campoDeReact(buscadorDeTierrasDeMisCosas()),
      // Cuando no casa ninguna se dice, con el botón que devuelve la lista entera: el aviso de «todavía no
      // tienes parcelas» sería mentira —las tiene— y sin salida se queda creyendo que las ha perdido.
      sinResultados: buscando
        ? {
            texto: m("buscar_sin_nada"),
            pista: m("buscar_sin_nada_pista"),
            boton: {
              etiqueta: m("verlas_todas"),
              accion: "buscar-tierra-limpiar-mis-cosas",
              clase: "boton-principal",
            },
          }
        : null,
      cuantas: cuantas
        ? rellena(m(cuantas === 1 ? "cuantas_tierras_una" : "cuantas_tierras"), { cuantas })
        : "",
      elementos: tierras,
    },
    {
      tipo: "producto",
      lista: estado.productos,
    },
    {
      tipo: "abono",
      lista: estado.abonos,
    },
    {
      tipo: "aplicador",
      lista: estado.aplicadores,
    },
    {
      // El técnico que asesora es otra cosa que quien aplica: tiene su propio registro (ROPO)
      // y la Junta rechaza el tratamiento si no se encuentra en él.
      tipo: "asesor",
      lista: estado.asesores || [],
    },
    {
      tipo: "equipo",
      lista: estado.equipos,
    },
    {
      tipo: "instalacion",
      lista: estado.instalaciones,
    },
  ];

  // Las secciones, ya preparadas: el componente solo tiene que pintarlas. Se arma aquí y no allí
  // porque estos datos (y cómo se enseña cada uno) son cosa de `app.js`, que es quien los tiene.
  //
  // Hay **dos formas de sección**, y no es un capricho: las tierras van con la tarjeta (`tarjetas: true`,
  // ver `tierrasParaMisCosas()`) porque son cincuenta y una y hay que reconocerlas de un vistazo; las
  // otras seis van como lista de renglones, que es lo que se lee de un tirón cuando son diez.
  const preparadas = secciones.map((seccion) => ({
    tipo: seccion.tipo,
    titulo: m(`seccion_${seccion.tipo}`),
    pista: m(`pista_${seccion.tipo}`),
    vacio: m(`sin_${seccion.tipo}`),
    anadir: m(`anadir_${seccion.tipo}`),
    cuantas: seccion.cuantas || "",
    tarjetas: Boolean(seccion.tarjetas),
    buscar: seccion.buscar || null,
    // **La tabla, para el ordenador** (30/09/2026): la misma lista que las tarjetas, mirada de otra forma.
    tabla: seccion.tabla || null,
    sinResultados: seccion.sinResultados || null,
    etiquetaDelDibujo: t("maestros.dibujo_de_la_parcela", ""),
    elementos: seccion.tarjetas
      ? seccion.elementos
      : seccion.lista.map((item) => {
          // Cómo se llama y qué se dice de él: **lo mismo que enseña la ficha** que sale al corregirlo o
          // al borrarlo (`renglonDeUnMaestro`), y no una segunda copia que se quedaría vieja.
          const renglon = renglonDeUnMaestro(seccion.tipo, item);
          return {
            nombre: renglon.nombre,
            detalle: renglon.detalle,
            // **Y sus dos botones** (ronda 93): cada ficha se puede corregir y borrar, como las
            // tierras. El `tipo` de la sección es el mismo que usa el asistente para dar de alta, así
            // que corregir abre **el mismo formulario** con lo que ya estaba puesto.
            acciones: botonesDeCorregirYBorrar(seccion.tipo, item.id),
          };
        }),
  }));

  const atajos = [
    {
      titulo: t("documentos.titulo", ""),
      explica: t("documentos.explica", ""),
      icono: "📄",
      accion: "papel-ver-todos",
    },
    {
      titulo: t("cesta.titulo", ""),
      explica: t("cesta.explica", ""),
      icono: "🧴",
      accion: "cesta-ver",
    },
    {
      titulo: t("cultivos.titulo", ""),
      explica: t("cultivos.explica", ""),
      icono: "🌱",
      accion: "cultivo-ver-todos",
    },
    {
      titulo: t("grupos.titulo", ""),
      explica: t("grupos.explica", ""),
      icono: "🔗",
      accion: "grupo-ver",
    },
  ];

  // Esta pantalla ya está en React (ver `docs/REACT.md`): es de mirar y pulsar, sin campos que leer
  // del DOM. Se monta con `montar()`, que pide el elemento dentro de un `try`: si los ficheros de
  // React de `vendor/` no han llegado, enseña el aviso de emergencia en vez de una pantalla en blanco.
  montar(() =>
    pantallaDeMisCosas({
      textos: { maestros: t("maestros", {}), acciones: t("acciones", {}) },
      secciones: preparadas,
      atajos,
    }),
  );
}

/**
 * Los papeles: el contrato, las facturas, los resguardos de los envases.
 *
 * **Esta pantalla faltaba, y se encontró leyendo las instrucciones de la app de la Junta**, que
 * tiene un apartado «Documentación» para guardar «contratos, facturas, albaranes de entrega de
 * envases a Sigfito, etc.». No es un adorno: el cuaderno dice lo que se hizo, y estos papeles
 * son los que lo demuestran cuando llega una inspección.
 *
 * Dos decisiones que se notan al usarla:
 *
 * 1. **Se puede apuntar un papel sin subir el fichero.** El agricultor que no sabe hacerle una
 *    foto al contrato puede escribir «está en el cajón de arriba» y eso ya le sirve. Obligar a
 *    subir el fichero dejaría fuera justo a quien más lo necesita.
 * 2. **Se agrupa por carpetas**, como las tiene él en casa. La carpeta la escribe él; las que
 *    salen en la lista son sugerencias.
 */
function pantallaDocumentos() {
  const d = (clave) => t(`documentos.${clave}`, "");
  const datos = estado.documentos || {};
  const lista = datos.documentos || [];
  const carpetas = (datos.carpetas || []).filter((c) => c.cuantos > 0);

  // El detalle de cada papel se arma aquí: es cosa de estos datos, no de la pantalla.
  const comoSeVe = (papel) => ({
    id: papel.id,
    titulo: papel.titulo,
    tiene_fichero: Boolean(papel.tiene_fichero),
    detalle: [
      papel.etiqueta_tipo,
      papel.fecha ? formateaFecha(papel.fecha) : "",
      papel.quien || "",
      papel.tiene_fichero ? d("tiene_fichero") : d("no_tiene_fichero"),
    ]
      .filter(Boolean)
      .join(" · "),
    // **Y sus dos botones** (ronda 93): el título, la carpeta, la fecha o el nombre de quien lo firmó se
    // corrigen aquí sin borrar el papel (y sin perder su fichero).
    acciones: botonesDeCorregirYBorrar("documento", papel.id),
  });

  const conocidas = carpetas.map((carpeta) => ({
    nombre: carpeta.nombre,
    papeles: lista.filter((papel) => papel.carpeta === carpeta.nombre).map(comoSeVe),
  }));
  const sinCarpeta = lista
    .filter((papel) => !carpetas.some((c) => c.nombre === papel.carpeta))
    .map(comoSeVe);

  // Esta pantalla ya está en React (ver `docs/REACT.md`). Se monta con `montar()`, que pide el
  // elemento dentro de un `try`: si los ficheros de React de `vendor/` no han llegado, enseña el
  // aviso de emergencia en vez de dejar la pantalla en blanco.
  montar(() =>
    pantallaDeDocumentos({
      textos: {
        documentos: t("documentos", {}),
        maestros: t("maestros", {}),
        acciones: t("acciones", {}),
      },
      carpetas: conocidas,
      sinCarpeta,
      total: lista.length,
      error: estado.errorDocumentos,
    }),
  );
}

/**
 * «Guardar un papel»: el formulario, ya en React (ver `docs/REACT.md`).
 *
 * **Los seis campos se quedan con su `id`** y los lee `guardarDocumento()`, aquí abajo: el
 * manejador de clics es uno solo y vive en este fichero. Lo que se prepara aquí son las dos listas
 * que vienen del servidor (las clases de papel y las carpetas que ya tiene) y el error.
 */
function pantallaNuevoDocumento() {
  const datos = estado.documentos || {};
  // Cuando se está **corrigiendo** un papel, la pantalla es la misma con los campos puestos (ronda 93):
  // los seis campos siguen leyéndose por su `id` y lo único que cambia es a dónde va lo que se guarde
  // —un `PUT` a ese papel, en vez de un `POST`— y lo que dicen el título y el botón.
  const papel = estado.documentoEnEdicion || null;

  // `montar()` pide el elemento dentro de un `try`: si los ficheros de React de `vendor/` no han
  // llegado, enseña el aviso de emergencia en vez de dejar la pantalla en blanco.
  montar(() =>
    pantallaDeNuevoDocumento({
      textos: {
        documentos: t("documentos", {}),
        acciones: t("acciones", {}),
        corregir_el_papel: t("corregir.pregunta", ""),
        pista_corregir: t("corregir.pista", ""),
        guardar_cambios: t("corregir.boton_guardar", ""),
      },
      tipos: datos.tipos || [],
      carpetas: datos.sugeridas || [],
      error: estado.errorDocumentos || "",
      papel,
      corrigiendo: Boolean(papel),
    }),
  );
}

function valorDe(id) {
  const campo = document.getElementById(id);
  return campo ? campo.value : "";
}

async function guardarDocumento() {
  const d = (clave) => t(`documentos.${clave}`, "");
  const titulo = valorDe("papel-titulo").trim();
  if (!titulo) {
    estado.errorDocumentos = d("el_titulo");
    pantallaNuevoDocumento();
    return;
  }
  const cuerpo = {
    titulo,
    tipo: valorDe("papel-tipo") || "otros",
    carpeta: valorDe("papel-carpeta").trim(),
    quien: valorDe("papel-quien").trim() || null,
    notas: valorDe("papel-notas").trim() || null,
    campana_id: estado.campana ? estado.campana.id : null,
  };
  const fecha = valorDe("papel-fecha");
  if (fecha) cuerpo.fecha = fecha;

  // El papel que se haya elegido en la misma pantalla (diseño de Stitch de «guardar un papel», ronda 90): se
  // sube **después** de crear el papel, por el camino que ya existe (`POST /api/documentos/{id}/fichero`).
  // Antes había que guardar el papel, ir a la lista y subirlo desde allí.
  const entradaDelFichero = document.getElementById("papel-fichero");
  const fichero = entradaDelFichero && entradaDelFichero.files ? entradaDelFichero.files[0] : null;

  // ¿Se está guardando un papel nuevo o corrigiendo uno que ya estaba? Lo dice `documentoEnEdicion`, que
  // se pone al pulsar CORREGIR en la lista.
  const corrigiendo = estado.documentoEnEdicion || null;

  let creado = null;
  try {
    creado = corrigiendo
      ? await apiJson(`/api/documentos/${corrigiendo.id}`, {
          method: "PUT",
          body: JSON.stringify(cuerpo),
        })
      : await apiJson("/api/documentos", { method: "POST", body: JSON.stringify(cuerpo) });
  } catch (error) {
    estado.errorDocumentos = error.message;
    pantallaNuevoDocumento();
    return;
  }
  if (fichero && creado) {
    // Sin cobertura no se sube un fichero de un tirón: el papel ya está apuntado (que es lo que no se puede
    // perder) y se dice que el papel se sube luego, en vez de dejar al agricultor esperando.
    if (!navigator.onLine) {
      estado.errorDocumentos = aviso("no_se_pudo");
      await cargarDatos().catch(() => {});
      pantallaDocumentos();
      return;
    }
    try {
      const conFichero = new FormData();
      conFichero.append("fichero", fichero);
      // Con `fetch` y no con `api()`: `api()` pone la cabecera de JSON, y con un fichero la pone el navegador
      // sola (con su `boundary`). Las dos juntas rompen el envío sin decir por qué.
      const respuesta = await fetch(`/api/documentos/${creado.id}/fichero`, {
        method: "POST",
        headers: { Authorization: `Bearer ${estado.token}` },
        body: conFichero,
      });
      if (!respuesta.ok) {
        const detalle = await respuesta.json().catch(() => null);
        throw new Error(avisoDelServidor(detalle) || mensaje("no_se_pudo"));
      }
    } catch (error) {
      // El papel **ya está guardado**: si el fichero no sube, se dice y se queda en la lista, donde se puede
      // volver a subir. Perder el apunte por un fichero que falla sería lo peor que puede pasar aquí.
      estado.errorDocumentos = error.message;
      await cargarDatos().catch(() => {});
      pantallaDocumentos();
      return;
    }
  }
  estado.errorDocumentos = "";
  await cargarDatos().catch(() => {});
  pantallaDocumentos();
}

async function subirFicheroDeDocumento(id) {
  const d = (clave) => t(`documentos.${clave}`, "");
  const entrada = document.getElementById(`papel-${id}`);
  if (!entrada || !entrada.files || entrada.files.length === 0) {
    estado.errorDocumentos = d("el_fichero");
    pantallaDocumentos();
    return;
  }
  // Sin cobertura no se puede subir un fichero de un tirón, así que se dice claro en vez de
  // dejar al agricultor esperando delante de una barra que no avanza.
  if (!navigator.onLine) {
    estado.errorDocumentos = aviso("no_se_pudo");
    pantallaDocumentos();
    return;
  }
  const cuerpo = new FormData();
  cuerpo.append("fichero", entrada.files[0]);
  try {
    const respuesta = await fetch(`/api/documentos/${id}/fichero`, {
      method: "POST",
      headers: { Authorization: `Bearer ${estado.token}` },
      body: cuerpo,
    });
    if (!respuesta.ok) {
      const detalle = await respuesta.json().catch(() => null);
      throw new Error((detalle && detalle.detail) || mensaje("no_se_pudo"));
    }
  } catch (error) {
    estado.errorDocumentos = error.message;
    pantallaDocumentos();
    return;
  }
  estado.errorDocumentos = d("fichero_subido");
  await cargarDatos().catch(() => {});
  pantallaDocumentos();
}

async function descargarDocumento(id) {
  const respuesta = await api(`/api/documentos/${id}/fichero`);
  if (!respuesta.ok) {
    const detalle = await respuesta.json().catch(() => null);
    const papel = (estado.documentos?.documentos || []).find((p) => String(p.id) === String(id));
    estado.errorDocumentos = (detalle && detalle.detail) || mensaje("no_se_pudo");
    pantallaDocumentos();
    return;
  }
  const blob = await respuesta.blob();
  const papel = (estado.documentos?.documentos || []).find((p) => String(p.id) === String(id));
  const enlace = document.createElement("a");
  enlace.href = URL.createObjectURL(blob);
  enlace.download = (papel && papel.nombre_del_fichero) || `papel-${id}`;
  document.body.appendChild(enlace);
  enlace.click();
  enlace.remove();
}

async function verListadoDePapeles() {
  const d = (clave) => t(`documentos.${clave}`, "");
  try {
    const datos = await apiJson("/api/documentos/listado");
    montar(() =>
      confirmacion({
        titulo: d("titulo"),
        pista: d("listado_pista"),
        // El listado llega ya escrito del servidor: se enseña tal cual, en su bloque de texto.
        contenido: html`
          ${estado.errorDocumentos ? html`<${AvisoDeError} texto=${estado.errorDocumentos} />` : null}
          <pre className="listado">${datos.texto}</pre>
        `,
        acciones: [
          {
            etiqueta: accion("volver"),
            accion: "papel-ver-todos",
            clase: "boton-claro",
            sencillo: true,
          },
        ],
      }),
    );
  } catch (error) {
    estado.errorDocumentos = error.message;
    pantallaDocumentos();
  }
}

/**
 * Lo que tengo en el almacén: lo comprado, lo echado y lo que queda.
 *
 * Es el botón «Situación Cesta» de la app de la Junta. Aquí faltaba entero: los campos de la
 * compra (`cantidad_comprada`, `unidad_compra`, `fecha_compra`) estaban en la base de datos y
 * **no los pedía ninguna pantalla**, así que la pregunta que se hace de verdad —«¿me queda
 * producto para tratar esta parcela?»— no tenía respuesta.
 *
 * Lo que se enseña cuando **no se puede** hacer la cuenta es tan importante como la cuenta:
 * un producto comprado en kilos y echado con dosis en litros no se puede restar sin saber la
 * densidad, y decir «te quedan -3 kg» sería inventarse un dato. Ahí se dice por qué no se puede.
 */
function pantallaCesta() {
  const c = (clave) => t(`cesta.${clave}`, "");
  const col = (clave) => t(`tabla.${clave}`, "");
  const datos = estado.cesta || {};
  const productos = datos.productos || [];

  // Las filas de cada producto se preparan aquí: son estos datos, no la pantalla, y las cuentas ya
  // vienen contadas del servidor.
  //
  // Dos cosas del diseño de Stitch de esta pantalla (ronda 90, `docs/stitch/rediseno/cesta.png`):
  //
  //  1. **«Te queda» va siempre y va la última, destacada.** Es la pregunta con la que se entra aquí
  //     («¿me queda producto para tratar la parcela?»), y estaba en medio, con el mismo tamaño que las
  //     demás filas. Ahora cierra la tarjeta en su recuadro, con el número grande. Y va **siempre**,
  //     también cuando no se sabe: un «—» con su motivo debajo contesta igual de bien que un número, y
  //     esconder la fila dejaba al agricultor buscando algo que no estaba.
  //  2. **Cada producto lleva su etiqueta de estado** («Las cuentas cuadran», «Sin saber cuánto
  //     compraste», «No se puede comparar», «Míralo»): de un vistazo se ve cuál está bien y cuál hay que
  //     mirar, sin leer los tres números y hacer la cuenta de cabeza.
  const conSusFilas = productos.map((producto) => {
    const filas = [];
    if (producto.comprado !== null && producto.comprado !== undefined) {
      filas.push({ etiqueta: c("comprado"), valor: numeroConUnidad(producto.comprado, producto.unidad_compra) });
    }
    if (producto.gastado) {
      filas.push({
        etiqueta: c("gastado"),
        valor: `${numeroConUnidad(producto.gastado, producto.unidad_gastado)} · ${rellena(c("apuntes"), {
          cuantos: producto.apuntes,
        })}`,
      });
    }
    if (producto.fecha_compra) {
      filas.push({ etiqueta: c("cuando"), valor: formateaFecha(producto.fecha_compra) });
    }
    if (producto.proveedor) {
      filas.push({ etiqueta: c("donde_lo_compraste"), valor: producto.proveedor });
    }
    // **Y la fila de «te queda»: la del almacén si se sabe, y los papeles con su nombre** (T21,
    // 06/10/2026). Antes esta fila era *lo comprado menos lo echado* y el libro del almacén contestaba
    // otra cosa al mismo producto; ahora la destacada es **lo que hay de verdad dentro** y la cuenta de
    // los papeles va debajo, etiquetada como lo que es. **No se suman**: son dos hechos distintos.
    //
    // Y cuando el saldo físico no se puede saber (el producto no está enlazado con el almacén, o no hay
    // ninguna entrada suya), se dice **por qué** y la fila destacada sigue siendo la de los papeles con
    // su nombre: un hueco explicado, nunca un cero.
    const elFisicoSeSabe = Boolean(producto.saldo_fisico_conocido) && producto.saldo_fisico !== null && producto.saldo_fisico !== undefined;
    if (elFisicoSeSabe) {
      filas.push({
        etiqueta: c("queda_en_el_almacen"),
        valor: numeroConUnidad(producto.saldo_fisico, producto.unidad_compra),
        destacada: true,
      });
      filas.push({
        etiqueta: c("queda_segun_los_papeles"),
        valor: numeroConUnidad(producto.queda, producto.unidad_compra),
      });
    } else {
      filas.push({
        etiqueta: c("queda_segun_los_papeles"),
        valor: numeroConUnidad(producto.queda, producto.unidad_compra),
        destacada: true,
      });
    }

    const sinCompra = producto.comprado === null || producto.comprado === undefined;
    // **Dos formas de lo mismo, y a propósito** (30/09/2026): la frase entera para la tarjeta del móvil
    // («Las cuentas cuadran») y la corta para la celda de la tabla («Cuadra»), que es donde cuatro
    // renglones ponían la fila altísima. Los dos textos dicen lo mismo **con palabras**: el color solo no
    // informa. Ver `TABLA.estado_*` en `textos.py`.
    let estado = { texto: c("cuadra"), tipo: "bien" };
    let estadoCorto = { texto: col("estado_cuadra"), tipo: "bien" };
    if (sinCompra) {
      estado = { texto: c("sin_cantidad"), tipo: "falta" };
      estadoCorto = { texto: col("estado_sin_dato"), tipo: "falta" };
    } else if (!producto.se_puede_comparar) {
      estado = { texto: c("no_se_puede_comparar"), tipo: "mirar" };
      estadoCorto = { texto: col("estado_no_se_compara"), tipo: "mirar" };
    } else if (producto.queda !== null && producto.queda !== undefined && producto.queda < 0) {
      estado = { texto: c("mirar"), tipo: "mirar" };
      estadoCorto = { texto: col("estado_mirar"), tipo: "mirar" };
    }

    // **El motivo de que no haya número físico también se dice** (T21): si el producto no está enlazado
    // con el almacén, o no hay ninguna entrada suya, el agricultor tiene que leer **por qué** en vez de
    // ver una fila con un hueco. Se añade al motivo de la cuenta de los papeles, que es otro.
    const motivoFisico = elFisicoSeSabe ? "" : producto.motivo_fisico || "";
    const motivos = [producto.motivo, motivoFisico].filter(Boolean);
    const motivo = motivos.length > 1 && motivos[0] !== motivos[1] ? motivos.join(" ") : motivos[0] || "";

    return {
      nombre_comercial: producto.nombre_comercial,
      materia_activa: producto.materia_activa,
      motivo,
      estado,
      estadoCorto,
      filas,
      // **Lo mismo, en crudo, para la tabla del ordenador** (30/09/2026): así la tabla y la tarjeta enseñan
      // lo mismo porque salen del mismo sitio, y no hay dos formas de contar un producto que se puedan
      // separar. Es la misma idea que en las tierras (`tierrasParaMisCosas`).
      producto_id: producto.producto_id,
      numero_registro: producto.numero_registro || "",
      comprado: producto.comprado,
      unidad_compra: producto.unidad_compra || "",
      gastado: producto.gastado,
      unidad_gastado: producto.unidad_gastado || "",
      apuntes: producto.apuntes,
      // **La columna «Te queda» de la tabla lleva el mismo número que el titular de la tarjeta**: el del
      // almacén cuando se sabe, y el de los papeles cuando no. Si llevara otro, la misma pantalla
      // enseñaría dos números distintos del mismo producto según se mire en el móvil o en el ordenador.
      queda: elFisicoSeSabe ? producto.saldo_fisico : producto.queda,
      saldo_fisico: producto.saldo_fisico,
      saldo_fisico_conocido: Boolean(producto.saldo_fisico_conocido),
      // El número de los papeles, aparte y con su nombre: es el que se enseña en la fila «según los
      // papeles», y no se pierde al cambiar el titular.
      queda_segun_los_papeles: producto.queda,
      motivo_fisico: producto.motivo_fisico || "",
      se_puede_comparar: producto.se_puede_comparar,
      comprado_de_donde: producto.comprado_de_donde || "",
      fecha_compra: producto.fecha_compra || "",
      proveedor: producto.proveedor || "",
      // Y sus dos botones: corregir el producto (lo que se escribió mal al darlo de alta) o borrarlo. Son los
      // mismos que lleva su renglón en «mis parcelas, productos y máquinas», porque es la misma ficha
      // (`botonesDeCorregirYBorrar`): aquí hacen la misma falta, que el almacén también se equivoca.
      acciones: botonesDeCorregirYBorrar("producto", producto.producto_id),
    };
  });

  // Esta pantalla ya está en React (ver `docs/REACT.md`). Se monta con `montar()`, que pide el
  // elemento dentro de un `try`: si los ficheros de React de `vendor/` no han llegado, enseña el
  // aviso de emergencia en vez de dejar la pantalla en blanco.
  montar(() =>
    pantallaDeCesta({
      textos: {
        cesta: t("cesta", {}),
        facturas: t("facturas", {}),
        acciones: t("acciones", {}),
      },
      productos: conSusFilas,
      // **La tabla del ordenador** (30/09/2026, fase 2): la misma lista que las tarjetas del móvil, con sus
      // columnas ordenables y su panel de al lado. Las dos formas van en el mismo HTML y el CSS enseña la que
      // toca según el ancho.
      tabla: tablaDeLaCesta(conSusFilas),
      // Cuántos productos hay, que es lo que el servidor ya contaba y no enseñaba nadie (ronda 84): va en
      // singular o en plural según cuántos sean, y eso lo decide el servidor (`con_cuenta`).
      resumen: datos.resumen || "",
      error: estado.errorCesta,
    }),
  );
}

/**
 * Un número con su unidad, o un guion si no se sabe.
 *
 * **El guion no es un adorno**: en el almacén, lo que no se sabe no se pone como cero. Un «0 L» en el libro de
 * entradas y salidas es un dato inventado, y este programa antes prefiere no contestar. La unidad la manda el
 * servidor (lo comprado va en litros o en kilos, y lo echado, en la unidad de la dosis del producto).
 */
function numeroConUnidad(valor, unidad) {
  return valor === null || valor === undefined
    ? "—"
    : `${formateaNumero(valor, 2)} ${unidad || ""}`.trim();
}

/**
 * La tabla de lo que tengo en el almacén, para el ordenador (30/09/2026).
 *
 * POR QUÉ. Es la pantalla del diseño de escritorio que pidió Stitch (`docs/stitch/escritorio/almacen.png`): el
 * libro de entradas y salidas, producto por producto, con lo comprado, lo echado y lo que queda uno debajo de
 * otro para poder compararlos. En el móvil la misma lista va en tarjetas, con el número grande de «te queda».
 *
 * Lo que la tabla **no** lleva, y es a propósito: **el gasto en euros**. El diseño de Stitch le pone una
 * columna y tres tarjetas de números, y en este programa ese número no existe (las líneas de factura traen su
 * importe, pero no hay un gasto por producto sumado para el año). Ponerlo de adorno sería inventarse un dato,
 * que es lo único que este programa no hace; el día que exista, tiene su columna.
 */
function tablaDeLaCesta(productos) {
  const col = (clave) => t(`tabla.${clave}`, "");
  const c = (clave) => t(`cesta.${clave}`, "");
  const ordenados = ordenarFichas(productos, elOrdenDeLaTabla("cesta"), "producto_id");
  const elegido = filaElegida("cesta");

  const columnas = columnasDeLaTabla("cesta", [
    { texto: col("producto"), campo: "nombre_comercial" },
    // **Seis columnas, no siete** (30/09/2026). El número de registro **está en el panel** (y en la tarjeta
    // del móvil): en la tabla ensanchaba lo justo para que los dos botones de la última columna se pusieran
    // uno debajo de otro y la tabla acabara desplazándose en horizontal —se vio en la captura de la versión
    // de ordenador—. Es la misma decisión que en la tabla de tierras con el pueblo y la referencia del
    // SIGPAC: la tabla lleva lo que hace falta para **reconocer y comparar** la fila; el resto, en su ficha.
    { texto: col("comprado"), campo: "comprado", clase: "tabla-numero" },
    { texto: col("echado"), campo: "gastado", clase: "tabla-numero" },
    { texto: col("te_queda"), campo: "queda", clase: "tabla-numero" },
    { texto: col("estado") },
    { texto: col("acciones") },
  ]);

  const filas = ordenados.map((producto) => ({
    elegida: Number(producto.producto_id) === Number(elegido),
    celdas: [
      {
        // El nombre del producto **es un botón**: se toca y su ficha sale en el panel de al lado, como en las
        // tierras. La fila entera no es un botón: en una tabla, eso es lo que menos se espera.
        texto: producto.nombre_comercial,
        accion: "elegir-fila",
        datos: { tabla: "cesta", id: producto.producto_id },
      },
      { texto: numeroConUnidad(producto.comprado, producto.unidad_compra), clase: "tabla-numero" },
      { texto: numeroConUnidad(producto.gastado, producto.unidad_gastado), clase: "tabla-numero" },
      { texto: numeroConUnidad(producto.queda, producto.unidad_compra), clase: "tabla-numero" },
      // El estado va **con palabras** (y con su color), en su **etiqueta corta**: es lo que dice de un
      // vistazo cuál hay que mirar, y en la celda la frase entera ponía la fila altísima. El porqué va en el
      // panel: en una celda no cabe, y no es un dato de la fila.
      { texto: "", estado: producto.estadoCorto, pista: "" },
    ],
    acciones: producto.acciones || [],
  }));

  // El pie: cuántos productos hay y **cuántos hay que mirar**, que es la cuenta que se viene a hacer aquí
  // (como las hectáreas en la tabla de tierras). El contador de los que hay que mirar solo sale si hay
  // alguno: decir «0 hay que mirarlos» sería dar una noticia con un número que no hace falta.
  const queMirar = ordenados.filter(
    (producto) => producto.estadoCorto && producto.estadoCorto.tipo !== "bien",
  ).length;
  const resumen = [
    resumenDeLaTabla("resumen_cesta", ordenados.length, {}),
    queMirar ? rellena(conCuenta(t("tabla", {}), "resumen_cesta_mirar", queMirar), {}) : "",
  ]
    .filter(Boolean)
    .join(" · ");

  return {
    clave: "cesta",
    etiqueta: col("cesta_etiqueta"),
    columnas,
    filas,
    resumen,
    // El panel de al lado: el producto elegido, o el aviso de que no hay ninguno elegido.
    panel: panelDelProducto(ordenados),
  };
}

/**
 * El panel del producto elegido en el almacén (30/09/2026): su ficha al lado de la tabla, sin salir de la
 * página.
 *
 * Lleva lo que en la celda no cabe y lo que hace falta para **comprobar** un número: de dónde sale lo
 * comprado (`comprado_de_donde`, que el servidor manda desde siempre y no enseñaba ninguna pantalla), la fecha
 * y el proveedor de la compra, y el motivo cuando las cuentas no se pueden hacer. Y sus dos botones:
 * corregirlo o borrarlo.
 */
function panelDelProducto(productos) {
  const p = (clave) => t(`panel.${clave}`, "");
  const col = (clave) => t(`tabla.${clave}`, "");
  const c = (clave) => t(`cesta.${clave}`, "");
  const elegido = filaElegida("cesta");
  const producto = elegido
    ? productos.find((uno) => Number(uno.producto_id) === Number(elegido))
    : null;
  const panel = {
    etiqueta: p("etiqueta"),
    titulo: p("producto"),
    vacio: p("producto_vacio"),
    elegida: Boolean(producto),
  };
  if (!producto) return panel;

  // De dónde sale el número de lo comprado. Cuando el servidor no dice ninguno (no hay ni factura ni dato en
  // la ficha), **no se pone la fila**: un origen inventado es peor que no tenerlo.
  const origen =
    producto.comprado_de_donde === "facturas"
      ? c("de_las_facturas")
      : producto.comprado_de_donde === "ficha"
        ? c("de_la_ficha")
        : "";

  return {
    ...panel,
    detalle: producto.materia_activa,
    filas: [
      producto.numero_registro ? { etiqueta: col("registro"), valor: producto.numero_registro } : null,
      { etiqueta: col("comprado"), valor: numeroConUnidad(producto.comprado, producto.unidad_compra) },
      {
        etiqueta: col("echado"),
        valor: [
          numeroConUnidad(producto.gastado, producto.unidad_gastado),
          producto.apuntes ? rellena(c("apuntes"), { cuantos: producto.apuntes }) : "",
        ]
          .filter(Boolean)
          .join(" · "),
      },
      { etiqueta: col("te_queda"), valor: numeroConUnidad(producto.queda, producto.unidad_compra) },
      origen ? { etiqueta: p("producto_origen"), valor: origen } : null,
      producto.fecha_compra ? { etiqueta: c("cuando"), valor: formateaFecha(producto.fecha_compra) } : null,
      producto.proveedor ? { etiqueta: c("donde_lo_compraste"), valor: producto.proveedor } : null,
    ].filter(Boolean),
    // El motivo por el que no hay cuenta posible (o por el que sale negativa), en su franja de aviso: es
    // «algo que hay que mirar», y en esta aplicación eso va con su señal.
    avisos: producto.motivo ? [producto.motivo] : [],
    acciones: (producto.acciones || []).map((una) => ({ ...una, sencillo: true })),
  };
}

// ------------------------------------------------------- el libro del almacén (T09)

/**
 * El libro del almacén: lo que entró por albarán, en qué envase y de dónde salió lo que se ha echado.
 *
 * **Esto no es la cesta.** «Lo que tengo en el almacén» (arriba) contesta a «¿me queda producto?» con lo
 * comprado menos lo echado, y sigue igual que siempre. Este bloque contesta a lo que pide una inspección
 * y lo que pide el contrato del CRM: de qué lote salió cada cosa, qué entró de verdad con el albarán y
 * qué se perdió o se contó distinto. El servidor de todo esto ya estaba hecho y verificado
 * (`routers/almacen_api.py`); lo que faltaba era la puerta.
 *
 * Las cinco decisiones que sostienen este bloque:
 *
 *  1. **Aquí no se cuenta nada.** Ni una resta, ni un total: los números los calcula el servidor y llegan
 *     ya contados, con su etiqueta. Lo único que se hace aquí es preparar filas y pasar textos.
 *  2. **Un dato que no se sabe no es un cero.** Un envase sin cantidad o sin unidad sale con la frase del
 *     servidor («No se puede saber lo que queda») y su motivo. Y ponerlo a cero sería afirmar que no
 *     queda nada, con el agricultor yendo a comprar por nada.
 *  3. **Lo comprado que no ha entrado se dice aparte** y no se le suma: un almacén vacío con facturas
 *     apuntadas no es producto perdido, es mercancía que todavía no ha llegado.
 *  4. **Lo que se apunta sin cobertura se queda en el móvil con su clave de reenvío**, que es lo que
 *     impide que el mismo albarán entre dos veces cuando se manda solo (`mandarPendientes` reenvía el
 *     mismo cuerpo, y el servidor reconoce la clave).
 *  5. **Ni una frase escrita aquí.** Hasta los rótulos de las filas salen de `textos.py`, y las frases
 *     que llevan un número o un nombre dentro se montan en este fichero (nunca dentro de un componente).
 */

/** El estado de las pantallas del libro: lo que se ha cargado y lo que se está haciendo. */
function estadoDelLibro() {
  if (!estado.libro) {
    estado.libro = {
      // Lo que ha contestado el servidor, tal cual. `existencias` es la respuesta entera (con los
      // artículos, sus envases, lo que queda y lo comprado sin entrar).
      existencias: null,
      recepciones: [],
      movimientos: [],
      cargado: false,
      cargando: false,
      error: "",
      // La ficha de un albarán abierta, y si se está preguntando el motivo para anularlo.
      recepcion: null,
      anulando: false,
      // Lo que se está apuntando: un albarán, un movimiento a mano, una salida o un enganche.
      albaran: null,
      movimiento: null,
      salida: null,
      enganche: null,
      guardando: false,
      aviso: "",
    };
  }
  return estado.libro;
}

/** Los textos del libro del almacén, tal y como los sirve `/api/interfaz` (dentro del bloque del almacén). */
function textosDelLibro() {
  return {
    cesta: t("cesta", {}),
    acciones: t("acciones", {}),
    facturas: t("facturas", {}),
  };
}

/**
 * Una clave de reenvío nueva para un apunte del almacén.
 *
 * **Se pide una vez, al abrir el formulario, y no al guardar.** No es un detalle: si se pidiera al
 * guardar, dos pulsaciones del mismo botón mandarían dos claves distintas y el mismo albarán entraría
 * dos veces en el almacén. Con la clave del formulario, el reenvío —el de la cola del móvil, o el de un
 * dedo que pulsa dos veces— se reconoce y se contesta lo que ya había.
 */
function claveDeReenvio(prefijo) {
  return `${prefijo}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

/**
 * Un número con su unidad, o la frase que dice que no se sabe. **Nunca un cero.**
 *
 * Es la decisión de la casa escrita en un solo sitio: lo que el servidor manda como «no lo sé» (`null`)
 * se dice con palabras, no se rellena con un cero que parecería un dato.
 */
function quedaDeUnSaldo(saldo, unidad) {
  return saldo === null || saldo === undefined
    ? t("cesta.libro_no_se_sabe_lo_que_queda", "")
    : numeroConUnidad(saldo, unidad);
}

/** Cómo se llama cada clase de cosa que se guarda (el nombre lo pone el servidor, no este fichero). */
function etiquetaDeCategoria(categoria) {
  const etiquetas = {
    fitosanitario: t("cesta.libro_categoria_fitosanitario", ""),
    abono: t("cesta.libro_categoria_abono", ""),
    semilla: t("cesta.libro_categoria_semilla", ""),
    otros: t("cesta.libro_categoria_otros", ""),
  };
  return etiquetas[categoria] || "";
}

/** Cómo se llama cada cosa que puede pasar en el almacén: entró, salió, se perdió o se contó distinto. */
function etiquetaDeTipoDeMovimiento(tipo) {
  const etiquetas = {
    entrada: t("cesta.libro_entrada", ""),
    salida: t("cesta.libro_salida", ""),
    merma: t("cesta.libro_merma", ""),
    ajuste: t("cesta.libro_ajuste", ""),
  };
  return etiquetas[tipo] || "";
}

/** De dónde viene un movimiento: de un albarán, de un apunte del cuaderno, de una factura o a mano. */
function deDondeVieneUnMovimiento(movimiento) {
  const origenes = {
    recepcion: t("cesta.libro_de_un_albaran", ""),
    tratamiento: t("cesta.libro_de_un_apunte", ""),
    fertilizacion: t("cesta.libro_de_un_apunte", ""),
    factura: t("cesta.libro_de_una_factura", ""),
    manual: t("cesta.libro_a_mano", ""),
  };
  return origenes[movimiento.origen_tipo] || "";
}

/** Cómo se llama un albarán: por su número, y si no lo trae se dice que no lo trae (no se inventa). */
function tituloDeUnAlbaran(recepcion) {
  return recepcion.numero_albaran
    ? rellena(t("cesta.libro_albaran_numero", ""), { numero: recepcion.numero_albaran })
    : t("cesta.libro_albaran_sin_numero", "");
}

/** La fecha de algo, o «sin fecha»: un movimiento sin fecha no es el más antiguo, es uno que no se sabe. */
function fechaOSinFecha(fecha) {
  return fecha ? formateaFecha(fecha) : t("cesta.libro_sin_fecha", "");
}

/**
 * Un movimiento del libro, contado en una línea.
 *
 * El texto de cada movimiento se monta aquí, con valores y no con frases: dentro de un componente, una
 * frase compuesta es una frase escrita a mano (y la caza la prueba de la jerga).
 */
function textoDeUnMovimiento(movimiento) {
  return [
    fechaOSinFecha(movimiento.fecha),
    etiquetaDeTipoDeMovimiento(movimiento.tipo),
    numeroConUnidad(movimiento.cantidad, movimiento.unidad),
    movimiento.motivo || "",
  ]
    .filter(Boolean)
    .join(" · ");
}

/** Un albarán en la lista de «lo que ha llegado». */
function renglonDeUnAlbaran(recepcion) {
  const lineas = (recepcion.lineas || []).length;
  // Los dos avisos que puede llevar un albarán: que no ha metido nada (está anulado) y que no se ha
  // podido comprobar si ya estaba (no trae número). Se dicen los dos, porque los dos importan.
  const avisos = [];
  if (recepcion.anulada) avisos.push(t("cesta.libro_sin_entradas", ""));
  if (!recepcion.numero_albaran) avisos.push(t("cesta.libro_albaran_pista", ""));
  return {
    id: recepcion.id,
    titulo: tituloDeUnAlbaran(recepcion),
    cuando: fechaOSinFecha(recepcion.fecha),
    proveedor: recepcion.proveedor || "",
    detalle: conCuenta(t("cesta", {}), "libro_cuantas_lineas", lineas),
    anulado: recepcion.anulada
      ? recepcion.motivo_anulacion
        ? rellena(t("cesta.libro_anulado_con_motivo", ""), { motivo: recepcion.motivo_anulacion })
        : t("cesta.libro_anulado", "")
      : "",
    aviso: avisos.filter(Boolean).join(" "),
  };
}

/**
 * Un envase (un lote): lo que queda, cuándo caduca y **su desglose**.
 *
 * Las tres cosas que se dicen en vez de esconderse, y las tres vienen decididas del servidor:
 * un saldo que no se sabe (`null`) se dice con palabras, una caducidad que no se ha mirado no se cuenta
 * como vigente, y un envase sin número es un envase sin número (y se explica por qué importa).
 */
function fichaDeUnLote(lote, acciones = []) {
  const avisos = [];
  if (lote.motivo) avisos.push(lote.motivo);
  if (lote.fecha_caducidad === null || lote.fecha_caducidad === undefined) {
    avisos.push(t("cesta.libro_sin_caducidad_pista", ""));
  } else if (lote.caducado === true) {
    avisos.push(t("cesta.libro_caducado_pista", ""));
  }
  const filas = [];
  if (lote.presentacion) filas.push({ etiqueta: t("cesta.libro_envase", ""), valor: lote.presentacion });
  if (lote.ubicacion) filas.push({ etiqueta: t("cesta.libro_donde_esta", ""), valor: lote.ubicacion });
  return {
    lote_id: lote.lote_id,
    titulo: lote.numero_lote
      ? rellena(t("cesta.libro_lote_numero", ""), { numero: lote.numero_lote })
      : t("cesta.libro_sin_numero_de_lote", ""),
    pista: lote.numero_lote ? "" : t("cesta.libro_sin_numero_de_lote_pista", ""),
    caducidad: lote.fecha_caducidad
      ? formateaFecha(lote.fecha_caducidad)
      : t("cesta.libro_sin_caducidad", ""),
    // Tres estados y tres palabras: caducado, en fecha y «no se sabe cuándo caduca». El color solo no
    // informa (regla de la casa), así que cada uno lleva su texto.
    estado:
      lote.caducado === true
        ? { texto: t("cesta.libro_caducado", ""), tipo: "mirar" }
        : lote.caducado === false
          ? { texto: t("cesta.libro_en_plazo", ""), tipo: "bien" }
          : { texto: t("cesta.libro_sin_caducidad", ""), tipo: "falta" },
    queda: quedaDeUnSaldo(lote.saldo, lote.unidad),
    avisos: avisos.filter(Boolean),
    filas,
    // El desglose del envase: sus movimientos, uno debajo de otro. Cada uno dice si cuenta o no y por
    // qué, porque un movimiento anulado sigue en el libro pero no entra en la cuenta.
    movimientos: (lote.movimientos_del_lote || []).map((movimiento) => ({
      texto: textoDeUnMovimiento(movimiento),
      no_cuenta: movimiento.cuenta ? "" : movimiento.no_cuenta_porque || "",
    })),
    acciones,
  };
}

/** Un artículo del almacén con sus envases y sus tres botones (una entrada, una merma y un ajuste). */
function fichaDeUnArticuloDelAlmacen(articulo) {
  const filas = [];
  // **Las cuatro cuentas solo se enseñan cuando suman todo lo que hay.** Si el servidor dice que hay
  // movimientos sin la cantidad, o sin la unidad, o unidades que no se pueden comparar, esas sumas son
  // **solo de una parte**: un «Entró 0,00» parecería que no entró nada cuando lo que pasa es que hay una
  // entrada de la que no se sabe cuánto. En ese caso se callan las cuentas y se enseña el motivo (que ya
  // viene del servidor), que es la regla de siempre: un dato que no se sabe no se pone.
  const sePuedeSumar =
    (articulo.movimientos_sin_cantidad || 0) === 0 &&
    (articulo.movimientos_sin_unidad || 0) === 0 &&
    (articulo.unidades_que_no_cuadran || []).length === 0 &&
    Boolean(articulo.unidad);
  if (articulo.movimientos && sePuedeSumar) {
    filas.push({
      etiqueta: t("cesta.libro_entradas", ""),
      valor: numeroConUnidad(articulo.entradas, articulo.unidad),
    });
    if (articulo.salidas) {
      filas.push({
        etiqueta: t("cesta.libro_salidas", ""),
        valor: numeroConUnidad(articulo.salidas, articulo.unidad),
      });
    }
    if (articulo.mermas) {
      filas.push({
        etiqueta: t("cesta.libro_mermas", ""),
        valor: numeroConUnidad(articulo.mermas, articulo.unidad),
      });
    }
    if (articulo.ajustes) {
      filas.push({
        etiqueta: t("cesta.libro_ajustes", ""),
        valor: numeroConUnidad(articulo.ajustes, articulo.unidad),
      });
    }
  }
  const paraApuntar = (tipo, texto) => ({
    etiqueta: texto,
    accion: "movimiento-nuevo",
    datos: { tipo, articulo: articulo.articulo_id },
    clase: "boton-claro",
  });
  return {
    nombre: articulo.nombre,
    categoria: etiquetaDeCategoria(articulo.categoria),
    queda: quedaDeUnSaldo(articulo.saldo, articulo.unidad),
    motivo: articulo.motivo || "",
    filas,
    lotes: (articulo.lotes || []).map((lote) => fichaDeUnLote(lote)),
    acciones: [
      paraApuntar("entrada", t("cesta.libro_nueva_entrada", "")),
      paraApuntar("merma", t("cesta.libro_nueva_merma", "")),
      paraApuntar("ajuste", t("cesta.libro_nuevo_ajuste", "")),
    ],
  };
}

/** Un movimiento del libro, en la lista de «lo que ha pasado en el almacén». */
function renglonDeUnMovimiento(movimiento) {
  const lote = movimiento.numero_lote
    ? rellena(t("cesta.libro_lote_numero", ""), { numero: movimiento.numero_lote })
    : "";
  return {
    titulo: [etiquetaDeTipoDeMovimiento(movimiento.tipo), movimiento.articulo || ""]
      .filter(Boolean)
      .join(" · "),
    cuando: fechaOSinFecha(movimiento.fecha),
    detalle: [
      numeroConUnidad(movimiento.cantidad, movimiento.unidad),
      lote,
      deDondeVieneUnMovimiento(movimiento),
    ]
      .filter(Boolean)
      .join(" · "),
    motivo: movimiento.motivo || "",
    no_cuenta: movimiento.cuenta ? "" : movimiento.no_cuenta_porque || "",
  };
}

/**
 * Lo comprado por factura que **todavía no ha entrado** en el almacén.
 *
 * Existe por un motivo de sentido común: un agricultor que viene de la versión anterior tiene sus
 * facturas apuntadas y ningún albarán, así que su almacén sale vacío. **Eso no es que el programa le haya
 * perdido el producto**: es que las facturas no meten mercancía, la mete el albarán. Sin este aviso, el
 * silencio parecería una pérdida.
 */
function loCompradoSinEntrar(existencias) {
  const filas = (existencias || {}).comprado_sin_entrar || [];
  return {
    hay: filas.length > 0,
    texto:
      filas.length === 1
        ? t("cesta.libro_compras_sin_albaran_una", "")
        : t("cesta.libro_compras_sin_albaran", ""),
    filas: filas.map((fila) => ({
      detalle: [fila.nombre, conCuenta(t("cesta", {}), "libro_cuantas_lineas", fila.lineas)]
        .filter(Boolean)
        .join(" · "),
    })),
  };
}

/** Los botones del pie del libro y de sus pantallas: volver al libro. */
function volverAlLibro() {
  return [
    {
      etiqueta: t("cesta.libro_volver_al_libro", ""),
      accion: "libro-ver",
      clase: "boton-claro",
    },
  ];
}

/**
 * Pide lo que hay en el almacén, lo que ha llegado y lo que ha pasado.
 *
 * Se piden **las tres cosas juntas** porque el libro es las tres: sin lo que ha llegado, el agricultor no
 * puede saber si la mercancía que espera está dentro; sin el libro, no puede saber de dónde sale lo que
 * falta.
 */
async function recargarElLibro() {
  const suyo = estadoDelLibro();
  let problema = "";
  const apuntarProblema = (fallo) => {
    if (!problema) problema = (fallo && fallo.message) || mensaje("no_se_pudo");
    return null;
  };
  const [existencias, recepciones, movimientos] = await Promise.all([
    apiJson("/api/almacen/existencias").catch(apuntarProblema),
    apiJson("/api/almacen/recepciones").catch(() => apuntarProblema()),
    apiJson("/api/almacen/movimientos").catch(() => apuntarProblema()),
  ]);
  suyo.existencias = existencias;
  suyo.recepciones = Array.isArray(recepciones) ? recepciones : [];
  suyo.movimientos = Array.isArray(movimientos) ? movimientos : [];
  suyo.cargado = Boolean(existencias);
  suyo.error = problema;
  return suyo;
}

/**
 * Abre el libro del almacén: se pinta enseguida diciendo que está buscando, y se vuelve a pintar con lo
 * que contesta el servidor.
 *
 * Se pinta **antes** de pedir nada a propósito: con mala cobertura, una pantalla en blanco durante cinco
 * segundos parece que el programa se ha roto.
 */
async function abrirElLibroDelAlmacen() {
  const suyo = estadoDelLibro();
  suyo.error = "";
  suyo.aviso = "";
  suyo.cargando = true;
  pantallaLibroDelAlmacen();
  await recargarElLibro();
  suyo.cargando = false;
  pantallaLibroDelAlmacen();
}

/** El libro del almacén, ya en React (ver `docs/REACT.md`). */
function pantallaLibroDelAlmacen() {
  const suyo = estadoDelLibro();
  const existencias = (suyo.existencias || {}).articulos || [];
  montar(() =>
    pantallaDelLibroDelAlmacen({
      textos: textosDelLibro(),
      albaranes: (suyo.recepciones || []).map(renglonDeUnAlbaran),
      articulos: existencias.map(fichaDeUnArticuloDelAlmacen),
      movimientos: (suyo.movimientos || []).map(renglonDeUnMovimiento),
      compras: loCompradoSinEntrar(suyo.existencias),
      // Las dos cuentas, en singular o en plural: «Tienes 1 albaranes apuntados» es lo primero que hace
      // desconfiar de un programa (y el singular lo elige `conCuenta`, con las dos formas del servidor).
      resumen_albaranes: suyo.recepciones.length
        ? conCuenta(t("cesta", {}), "libro_cuantos_albaranes", suyo.recepciones.length)
        : "",
      resumen_articulos: existencias.length
        ? conCuenta(t("cesta", {}), "libro_cuantos_articulos", existencias.length)
        : "",
      error: suyo.error || "",
      cargando: suyo.cargando,
      acciones: [{ etiqueta: t("acciones.volver", ""), accion: "ir-inicio", clase: "boton-claro" }],
    }),
  );
}

// ---------------------------------------------------------------------------------------------
// Apuntar un albarán
// ---------------------------------------------------------------------------------------------

/** Una línea del albarán, vacía: es con lo que se empieza y con lo que se añade otra. */
function lineaDeAlbaranVacia() {
  return {
    articulo: "",
    nombre: "",
    cantidad: "",
    unidad: "",
    numero_lote: "",
    fecha_caducidad: "",
    presentacion: "",
    contenido_por_envase: "",
    ubicacion: "",
  };
}

/**
 * Lo que se puede elegir en «¿qué ha llegado?»: lo que ya está dado de alta en el almacén, los productos
 * y los abonos de la finca, y —lo primero— escribir el nombre tal y como sale en el papel.
 *
 * Las cuatro formas valen porque las cuatro pasan de verdad, y el orden importa: lo que el agricultor
 * elige de su lista es lo que hace que el almacén hable de lo mismo que el resto del cuaderno.
 */
function opcionesDeArticuloDelAlbaran() {
  const opciones = [{ valor: "", texto: t("cesta.libro_linea_libre", "") }];
  const articulos = ((estadoDelLibro().existencias || {}).articulos || []).slice();
  for (const articulo of articulos) {
    opciones.push({ valor: `articulo:${articulo.articulo_id}`, texto: articulo.nombre });
  }
  for (const producto of estado.productos || []) {
    opciones.push({ valor: `producto:${producto.id}`, texto: producto.nombre_comercial });
  }
  for (const abono of estado.abonos || []) {
    opciones.push({ valor: `abono:${abono.id}`, texto: abono.nombre });
  }
  return opciones;
}

/** En qué se puede medir lo que llega: el catálogo del servidor, no un campo libre. */
function unidadesParaElAlmacen() {
  return (t("unidades_producto", []) || []).map((unidad) => ({ valor: unidad, texto: unidad }));
}

/** Abre el formulario de un albarán nuevo, con su clave de reenvío y su primera línea. */
function abrirElAlbaranNuevo() {
  const suyo = estadoDelLibro();
  suyo.error = "";
  suyo.aviso = "";
  suyo.albaran = {
    clave: claveDeReenvio("albaran"),
    fecha: hoyISO(),
    proveedor: "",
    numero_albaran: "",
    notas: "",
    lineas: [lineaDeAlbaranVacia()],
  };
  pantallaNuevoAlbaran();
}

/** El albarán que se está apuntando, ya en React. */
function pantallaNuevoAlbaran() {
  const suyo = estadoDelLibro();
  const albaran = suyo.albaran || { lineas: [] };
  montar(() =>
    pantallaDeNuevoAlbaran({
      textos: textosDelLibro(),
      borrador: {
        ...albaran,
        lineas: (albaran.lineas || []).map((linea, indice) => ({
          ...linea,
          titulo: rellena(t("cesta.libro_linea_titulo", ""), { numero: indice + 1 }),
        })),
      },
      opciones: opcionesDeArticuloDelAlbaran(),
      unidades: unidadesParaElAlmacen(),
      guardando: Boolean(suyo.guardando),
      error: suyo.error || "",
    }),
  );
}

/** Lee lo que hay escrito en el formulario del albarán, campo a campo y por su `id`. */
function recogeElAlbaran() {
  const suyo = estadoDelLibro();
  const albaran = suyo.albaran;
  const valor = (id) => {
    const campo = document.getElementById(id);
    return campo ? String(campo.value || "").trim() : "";
  };
  albaran.fecha = valor("albaran-fecha");
  albaran.proveedor = valor("albaran-proveedor");
  albaran.numero_albaran = valor("albaran-numero");
  albaran.notas = valor("albaran-notas");
  albaran.lineas = (albaran.lineas || []).map((linea, indice) => ({
    articulo: valor(`albaran-${indice}-articulo`),
    nombre: valor(`albaran-${indice}-nombre`),
    cantidad: valor(`albaran-${indice}-cantidad`),
    unidad: valor(`albaran-${indice}-unidad`),
    numero_lote: valor(`albaran-${indice}-lote`),
    fecha_caducidad: valor(`albaran-${indice}-caducidad`),
    presentacion: valor(`albaran-${indice}-envase`),
    contenido_por_envase: valor(`albaran-${indice}-contenido`),
    ubicacion: valor(`albaran-${indice}-donde`),
  }));
  return albaran;
}

/**
 * La línea del albarán en la forma que acepta el servidor.
 *
 * **La cantidad vacía se manda como que no se sabe** (`null`), no como un cero: un albarán sin la
 * cantidad legible se apunta igual —lo que llegó, llegó— y lo que se dice es que no se sabe cuánto.
 */
function lineaDelAlbaranParaElServidor(linea) {
  const [tipo, identificador] = String(linea.articulo || "").split(":");
  const datos = {
    descripcion: null,
    // Vacío es «no se sabe cuánto venía» y «no se sabe en qué se mide»: la línea se apunta igual.
    cantidad: linea.cantidad ? aNumero(linea.cantidad) : null,
    unidad_de_la_cantidad: linea.unidad || null,
    numero_lote: linea.numero_lote || null,
    fecha_caducidad: linea.fecha_caducidad || null,
    presentacion: linea.presentacion || null,
    contenido_por_envase: linea.contenido_por_envase ? aNumero(linea.contenido_por_envase) : null,
    ubicacion: linea.ubicacion || null,
  };
  if (tipo === "articulo") datos.articulo_id = Number(identificador);
  else if (tipo === "producto") datos.producto_id = Number(identificador);
  else if (tipo === "abono") datos.fertilizante_id = Number(identificador);
  else datos.nombre = linea.nombre || null;
  return datos;
}

/**
 * Guarda el albarán: lo manda al servidor y, si no hay cobertura, lo deja apuntado en el móvil.
 *
 * **Los tres finales del proyecto, aquí:**
 *
 *  1. **Se guarda**: se dice, y con lo que eso significa para el agricultor (la mercancía ya está dentro).
 *  2. **Falta un dato y se dice cuál**: se comprueba lo imprescindible **antes** de mandar nada —un
 *     albarán sin ninguna línea, o una línea que no dice qué es— y se dice con la frase del servidor. Se
 *     comprueba aquí y no allí por un motivo del campo: sin cobertura, un albarán que se sabe que va a
 *     ser rechazado no debe acabar en la cola del móvil.
 *  3. **No se ha podido comprobar**: si el papel no trae número, el servidor contesta que no ha podido
 *     comprobar si ya estaba, y eso se enseña tal cual. Reenviar el mismo albarán **no lo duplica**:
 *     viaja con la clave de reenvío que se pidió al abrir el formulario.
 */
async function guardarElAlbaran() {
  const suyo = estadoDelLibro();
  const albaran = recogeElAlbaran();
  const conAlgo = (albaran.lineas || []).filter((linea) => linea.articulo || linea.nombre);
  if (!conAlgo.length) {
    suyo.error = mensaje("AL1_una_recepcion_sin_lineas");
    return pantallaNuevoAlbaran();
  }
  if ((albaran.lineas || []).some((linea) => !linea.articulo && !linea.nombre)) {
    suyo.error = mensaje("AL2_la_linea_no_dice_que_es");
    return pantallaNuevoAlbaran();
  }

  const datos = {
    fecha: albaran.fecha || null,
    proveedor: albaran.proveedor || null,
    numero_albaran: albaran.numero_albaran || null,
    notas: albaran.notas || null,
    clave_de_reenvio: albaran.clave,
    lineas: conAlgo.map(lineaDelAlbaranParaElServidor),
  };

  suyo.error = "";
  suyo.guardando = true;
  pantallaNuevoAlbaran();
  // `guardarComoUltimo: false`: un albarán no es «lo mismo que la última vez» (eso es un tratamiento o
  // un abono), y guardarlo ahí haría que el atajo de la pantalla de inicio ofreciera repetir un albarán.
  const resultado = await enviarOApuntar("/api/almacen/recepciones", datos, "recepcion", false);
  suyo.guardando = false;

  if (resultado.error) {
    suyo.error = resultado.error;
    return pantallaNuevoAlbaran();
  }
  if (resultado.encolado) return confirmarElAlbaranEncolado({ numero_albaran: datos.numero_albaran });

  suyo.albaran = null;
  await recargarElLibro();
  return confirmarElAlbaranGuardado(resultado.datos || {});
}

/**
 * Lo que se dice cuando el albarán se ha quedado apuntado en el móvil (sin cobertura).
 *
 * Y un aviso que solo se puede dar aquí: si el papel **no trae número**, cuando se apunte de verdad no se
 * podrá comprobar si ya estaba (el servidor lo contesta con `AL5`). Sin cobertura ese aviso no llega
 * todavía, así que se dice ahora: es la misma verdad, dicha antes.
 */
function confirmarElAlbaranEncolado(albaran = {}) {
  const avisos = albaran.numero_albaran
    ? []
    : [{ texto: t("cesta.libro_no_se_pudo_comprobar", "") }];
  montar(() =>
    confirmacion({
      pregunta: t("cesta.libro_encolado", ""),
      pista: mensaje("sin_cobertura"),
      avisos,
      acciones: [
        { etiqueta: t("cesta.libro_ver_el_libro", ""), accion: "libro-ver", clase: "boton-principal" },
        { etiqueta: t("acciones.volver", ""), accion: "ir-inicio", clase: "boton-claro", sencillo: true },
      ],
    }),
  );
}

/**
 * Lo que se dice cuando el albarán está apuntado.
 *
 * Dos casos, y el primero es el que importa: si el servidor lo ha reconocido como **el mismo albarán que
 * ya estaba** (`ya_estaba`), se dice con todas las letras que no se ha contado dos veces y se le da la
 * salida que hay —anular el que sobra—. Y los avisos del servidor (la caducidad que no cuadra con la que
 * había, la unidad de otra familia, que no se ha podido comprobar si ya estaba) se enseñan enteros.
 */
function confirmarElAlbaranGuardado(cuerpo) {
  const avisos = (cuerpo.avisos || []).map((texto) => ({ texto }));
  if (cuerpo.ya_estaba) {
    return montar(() =>
      confirmacion({
        pregunta: t("cesta.libro_ya_estaba", ""),
        pista: t("cesta.libro_ya_estaba_explica", ""),
        avisos,
        acciones: [
          { etiqueta: t("cesta.libro_ver_el_libro", ""), accion: "libro-ver", clase: "boton-principal" },
          { etiqueta: t("acciones.volver", ""), accion: "ir-inicio", clase: "boton-claro", sencillo: true },
        ],
      }),
    );
  }
  return montar(() =>
    confirmacion({
      pregunta: t("cesta.libro_guardado", ""),
      pista: t("cesta.libro_guardado_pista", ""),
      avisos,
      acciones: [
        { etiqueta: t("cesta.libro_ver_el_libro", ""), accion: "libro-ver", clase: "boton-principal" },
        { etiqueta: t("acciones.volver", ""), accion: "ir-inicio", clase: "boton-claro", sencillo: true },
      ],
    }),
  );
}

// ---------------------------------------------------------------------------------------------
// La ficha de un albarán
// ---------------------------------------------------------------------------------------------

/**
 * Abre un albarán ya apuntado: se pide por su puerta (que es la misma que usa su dirección) y se enseña.
 *
 * Los tres finales: se abre, «eso no está en tu cuaderno» (404) o «no lo he podido comprobar» (sin
 * cobertura). Confundir los dos últimos es lo que este proyecto no hace: no tener cobertura en el campo
 * no es que el albarán no exista.
 */
async function abrirLaRecepcion(id) {
  const suyo = estadoDelLibro();
  suyo.error = "";
  suyo.aviso = "";
  suyo.anulando = false;
  let respuesta = null;
  try {
    respuesta = await api(`/api/almacen/recepciones/${id}`);
  } catch (fallo) {
    respuesta = null;
  }
  if (!respuesta) {
    if (!navigator.onLine) return pantallaDeUnaDireccionQueNoSePuedeComprobar();
    avisarDelError(mensaje("no_se_pudo"));
    return;
  }
  if (respuesta.status === 404) return pantallaDeDireccionQueNoLlevaANingunaParte();
  if (!respuesta.ok) {
    avisarDelError(mensaje("no_se_pudo"));
    return;
  }
  const suya = await respuesta.json();
  suyo.recepcion = suya;
  // La lista de lo que ha llegado y lo que hay en el almacén pueden ser viejos (se acaba de apuntar algo
  // desde otro sitio): se refrescan de fondo. **Y al llegar se vuelve a pintar la ficha**, porque el
  // envase y el sitio donde se guardó salen de las existencias y, sin esto, la misma ficha enseñaría
  // menos al abrirse por su dirección que al abrirse desde el libro —eso se vio en la captura de la
  // ficha abierta por `#/almacen/recepcion/4`—. Solo se repinta si se sigue en ella: si el agricultor se
  // ha ido a otra pantalla, no se le cambia lo que está mirando.
  recargarElLibro()
    .then(() => {
      const sigue = suyo.recepcion && Number(suyo.recepcion.id) === Number(suya.id);
      if (sigue && estado.pantalla === "recepcion") pantallaRecepcion();
    })
    .catch(() => {});
  pantallaRecepcion();
}

/** Los datos de una línea casada entre el albarán y la factura, dichos con sus nombres. */
function renglonDeUnaLineaCasada(casada, recepcion, factura) {
  const delAlbaran =
    (recepcion.lineas || []).find(
      (linea) => Number(linea.id) === Number(casada.linea_de_recepcion_id),
    ) || {};
  const deLaFactura =
    (factura.lineas || []).find(
      (linea) => Number(linea.id) === Number(casada.linea_de_factura_id),
    ) || {};
  return {
    texto: [
      delAlbaran.articulo || delAlbaran.descripcion || "",
      deLaFactura.descripcion || "",
      casada.como || "",
    ]
      .filter(Boolean)
      .join(" · "),
  };
}

/**
 * La ficha de un albarán, ya en React.
 *
 * El envase y el sitio donde se guardó **no vienen en la respuesta del albarán** (los guarda el lote, y
 * la línea del albarán no los devuelve): si el libro está cargado se buscan por el identificador del
 * lote, y si no están, esas filas no se pintan. Antes un hueco que un dato inventado.
 */
function pantallaRecepcion() {
  const suyo = estadoDelLibro();
  const recepcion = suyo.recepcion || {};
  const deLaRecepcion = (linea) => {
    const lotes = [];
    for (const articulo of (suyo.existencias || {}).articulos || []) {
      for (const lote of articulo.lotes || []) lotes.push(lote);
    }
    return lotes.find((lote) => Number(lote.lote_id) === Number(linea.lote_id)) || {};
  };
  const lineas = (recepcion.lineas || []).map((linea) => {
    const lote = deLaRecepcion(linea);
    return {
      que_es: linea.articulo || linea.descripcion || "",
      cantidad: numeroConUnidad(linea.cantidad, linea.unidad),
      lote: linea.numero_lote || t("cesta.libro_sin_numero_de_lote", ""),
      caducidad: linea.fecha_caducidad
        ? formateaFecha(linea.fecha_caducidad)
        : t("cesta.libro_sin_caducidad", ""),
      sin_numero: !linea.numero_lote,
      envase: lote.presentacion || "",
      donde: lote.ubicacion || "",
    };
  });
  const filas = [];
  if (recepcion.proveedor) {
    filas.push({ etiqueta: t("cesta.libro_de_quien", ""), valor: recepcion.proveedor });
  }
  filas.push({ etiqueta: t("cesta.libro_de_que_dia", ""), valor: fechaOSinFecha(recepcion.fecha) });
  if (recepcion.numero_albaran) {
    filas.push({
      etiqueta: t("cesta.libro_numero_de_albaran", ""),
      valor: recepcion.numero_albaran,
    });
  }
  filas.push({
    etiqueta: t("cesta.libro_cuanto_metio", ""),
    valor: recepcion.entradas
      ? conCuenta(t("cesta", {}), "libro_cuantas_entradas", recepcion.entradas)
      : t("cesta.libro_sin_entradas", ""),
  });
  montar(() =>
    pantallaDeRecepcion({
      textos: textosDelLibro(),
      recepcion: {
        id: recepcion.id,
        titulo: tituloDeUnAlbaran(recepcion),
        cuando: [fechaOSinFecha(recepcion.fecha), recepcion.proveedor || ""]
          .filter(Boolean)
          .join(" · "),
        anulado: recepcion.anulada
          ? recepcion.motivo_anulacion
            ? rellena(t("cesta.libro_anulado_con_motivo", ""), { motivo: recepcion.motivo_anulacion })
            : t("cesta.libro_anulado", "")
          : "",
        filas,
        lineas,
        entradas: recepcion.entradas
          ? conCuenta(t("cesta", {}), "libro_cuantas_entradas", recepcion.entradas)
          : "",
        sin_entradas: t("cesta.libro_sin_entradas", ""),
        notas: recepcion.notas || "",
        acciones: volverAlLibro(),
      },
      // El estado de la factura: enganchada o no. **La mercancía no se cuenta otra vez**: lo dice el
      // propio texto del servidor, que es lo que el agricultor necesita oír al ver dos papeles.
      factura: { hay: Boolean(recepcion.factura_id) },
      anulando: Boolean(suyo.anulando),
      error: suyo.aviso || suyo.error || "",
    }),
  );
}

/**
 * Anula el albarán que se está mirando, con su motivo.
 *
 * **Nada se borra**: el albarán se queda con lo que dijo el papel y sus entradas dejan de contar en el
 * almacén. Y el motivo es obligatorio, porque es lo único que explica dentro de dos años por qué ese
 * papel no cuenta: sin él, anular y equivocarse se parecen demasiado.
 */
async function anularElAlbaran(id) {
  const suyo = estadoDelLibro();
  const campo = document.getElementById("albaran-motivo-anulacion");
  const motivo = campo ? String(campo.value || "").trim() : "";
  if (!motivo) {
    suyo.error = mensaje("AL10_falta_el_motivo");
    return pantallaRecepcion();
  }
  const resultado = await mandarCambio(`/api/almacen/recepciones/${id}/anular`, "POST", { motivo });
  if (resultado.error) {
    suyo.error = resultado.error;
    return pantallaRecepcion();
  }
  suyo.recepcion = resultado.datos;
  suyo.anulando = false;
  suyo.aviso = t("cesta.libro_anulado_ok", "");
  await recargarElLibro();
  return pantallaRecepcion();
}

// ---------------------------------------------------------------------------------------------
// Una merma, un ajuste o una entrada sin papel
// ---------------------------------------------------------------------------------------------

/** Abre el formulario de un movimiento a mano, con el tipo que se haya elegido y su artículo. */
function abrirElMovimientoAMano(tipo, articuloId) {
  const suyo = estadoDelLibro();
  const titulos = {
    entrada: t("cesta.libro_entrada_titulo", ""),
    merma: t("cesta.libro_merma_titulo", ""),
    ajuste: t("cesta.libro_ajuste_titulo", ""),
  };
  const pistas = {
    entrada: t("cesta.libro_entrada_pista", ""),
    merma: t("cesta.libro_merma_pista", ""),
    ajuste: t("cesta.libro_ajuste_pista", ""),
  };
  suyo.error = "";
  suyo.aviso = "";
  suyo.movimiento = {
    tipo: titulos[tipo] ? tipo : "merma",
    titulo: titulos[tipo] || "",
    pista: pistas[tipo] || "",
    articulo_id: articuloId || "",
    numero_lote: "",
    fecha: hoyISO(),
    cantidad: "",
    unidad: "",
    motivo: "",
    clave: claveDeReenvio("movimiento"),
  };
  pantallaMovimientoDeAlmacen();
}

/** El formulario de un movimiento a mano, ya en React. */
function pantallaMovimientoDeAlmacen() {
  const suyo = estadoDelLibro();
  const articulos = ((suyo.existencias || {}).articulos || []).map((articulo) => ({
    valor: articulo.articulo_id,
    texto: articulo.nombre,
  }));
  montar(() =>
    pantallaDeMovimientoDeAlmacen({
      textos: textosDelLibro(),
      borrador: suyo.movimiento || {},
      articulos,
      unidades: unidadesParaElAlmacen(),
      guardando: Boolean(suyo.guardando),
      error: suyo.error || "",
    }),
  );
}

/** Lee lo que hay escrito en el formulario del movimiento, por el `id` de cada campo. */
function recogeElMovimiento() {
  const suyo = estadoDelLibro();
  const movimiento = suyo.movimiento;
  const valor = (id) => {
    const campo = document.getElementById(id);
    return campo ? String(campo.value || "").trim() : "";
  };
  movimiento.articulo_id = valor("movimiento-articulo");
  movimiento.numero_lote = valor("movimiento-numero-lote");
  movimiento.fecha = valor("movimiento-fecha");
  movimiento.cantidad = valor("movimiento-cantidad");
  movimiento.unidad = valor("movimiento-unidad");
  movimiento.motivo = valor("movimiento-motivo");
  return movimiento;
}

/**
 * Guarda un movimiento a mano: una merma, un ajuste o una entrada sin papel.
 *
 * **El motivo es obligatorio y se comprueba aquí primero**: en estas tres cosas no hay ningún documento
 * detrás, así que lo único que las explica es lo que escriba el agricultor. Y la cantidad con su unidad,
 * que es lo que permite restarla de lo que hay: sin unidad no se puede hacer la cuenta, y el programa lo
 * dice en vez de suponer litros.
 */
async function guardarElMovimiento() {
  const suyo = estadoDelLibro();
  const movimiento = recogeElMovimiento();
  if (!movimiento.motivo) {
    suyo.error = mensaje("AL10_falta_el_motivo");
    return pantallaMovimientoDeAlmacen();
  }
  const cantidad = movimiento.cantidad ? aNumero(movimiento.cantidad) : null;
  if (movimiento.tipo === "merma" && (cantidad === null || cantidad <= 0)) {
    suyo.error = mensaje("AL12_una_merma_necesita_la_cantidad");
    return pantallaMovimientoDeAlmacen();
  }
  if (movimiento.tipo === "ajuste" && (cantidad === null || cantidad === 0)) {
    suyo.error = mensaje("AL11_un_ajuste_necesita_la_diferencia");
    return pantallaMovimientoDeAlmacen();
  }
  if (cantidad !== null && !movimiento.unidad) {
    suyo.error = mensaje("AL13_falta_la_unidad");
    return pantallaMovimientoDeAlmacen();
  }

  const datos = {
    tipo: movimiento.tipo,
    // El artículo va con su identificador y **vacío va como vacío**: mandar un 0 haría que el servidor
    // buscara un artículo que no existe y contestara «eso no está en tu cuaderno», que no dice nada de lo
    // que falta de verdad.
    articulo_id: movimiento.articulo_id ? Number(movimiento.articulo_id) : null,
    numero_lote: movimiento.numero_lote || null,
    fecha: movimiento.fecha || null,
    cantidad,
    unidad: movimiento.unidad || null,
    motivo: movimiento.motivo,
    clave_de_reenvio: movimiento.clave,
  };
  suyo.error = "";
  suyo.guardando = true;
  pantallaMovimientoDeAlmacen();
  const resultado = await enviarOApuntar("/api/almacen/movimientos", datos, "movimiento", false);
  suyo.guardando = false;
  if (resultado.error) {
    suyo.error = resultado.error;
    return pantallaMovimientoDeAlmacen();
  }
  if (resultado.encolado) {
    return montar(() =>
      confirmacion({
        pregunta: t("cesta.libro_movimiento_guardado", ""),
        pista: mensaje("sin_cobertura"),
        acciones: [
          { etiqueta: t("cesta.libro_ver_el_libro", ""), accion: "libro-ver", clase: "boton-principal" },
        ],
      }),
    );
  }
  suyo.movimiento = null;
  await recargarElLibro();
  return montar(() =>
    confirmacion({
      pregunta: t("cesta.libro_movimiento_guardado", ""),
      pista: t("cesta.libro_movimiento_guardado_pista", ""),
      acciones: [
        { etiqueta: t("cesta.libro_ver_el_libro", ""), accion: "libro-ver", clase: "boton-principal" },
        { etiqueta: t("acciones.volver", ""), accion: "ir-inicio", clase: "boton-claro", sencillo: true },
      ],
    }),
  );
}

// ---------------------------------------------------------------------------------------------
// Sacar de un envase lo que se gastó en un apunte
// ---------------------------------------------------------------------------------------------

/** El apunte del que sale una salida del almacén (un tratamiento o un abono), o `null`. */
function apunteDeLaSalida(tipo, id) {
  const donde = tipo === "fertilizacion" ? estado.fertilizaciones : estado.tratamientos;
  return (donde || []).find((apunte) => Number(apunte.id) === Number(id)) || null;
}

/**
 * Los envases que pueden ser los de un producto: los del artículo que el apunte engancha.
 *
 * **Los tratamientos se enganchan por el identificador del producto** y los abonos **por el nombre**: la
 * respuesta de un abono no devuelve su `fertilizante_id` (está apuntado en
 * `docs/T09_PANTALLA_DEL_ALMACEN.md`), así que lo único que hay para casarlos es el nombre, comparado
 * como lo compara el servidor (sin tildes, sin mayúsculas y sin espacios de más). Si no casa ninguno, se
 * dice que de eso no hay nada en el almacén en vez de enseñar los envases de otro producto.
 */
function normalizaParaComparar(texto) {
  return String(texto || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .split(/\s+/)
    .filter(Boolean)
    .join(" ")
    .toUpperCase();
}

function articulosDeUnApunte(apunte) {
  const articulos = ((estadoDelLibro().existencias || {}).articulos) || [];
  if (!apunte) return [];
  if (apunte.producto_id) {
    return articulos.filter((articulo) => Number(articulo.producto_id) === Number(apunte.producto_id));
  }
  const buscado = normalizaParaComparar(apunte.fertilizante_nombre);
  if (!buscado) return [];
  return articulos.filter((articulo) => normalizaParaComparar(articulo.nombre) === buscado);
}

/**
 * Abre la pantalla de sacar de un envase, con los envases de ese producto.
 *
 * Se piden las existencias **cada vez**: lo que hay en el almacén cambia con cada albarán, y elegir un
 * envase de una lista vieja es restar de un lote que quizá ya no tiene nada.
 */
async function abrirLaSalidaDeUnLote(apunteTipo, apunteId) {
  const suyo = estadoDelLibro();
  suyo.error = "";
  suyo.aviso = "";
  suyo.cargando = true;
  suyo.salida = {
    apunte_tipo: apunteTipo,
    apunte_id: apunteId,
    clave: claveDeReenvio("salida"),
    pidiendo_cantidad: null,
    descuadre: "",
    lote_del_descuadre: null,
    resultado: null,
    avisos: [],
  };
  pantallaSacarDeUnLote();
  await recargarElLibro();
  suyo.cargando = false;
  pantallaSacarDeUnLote();
}

/** La pantalla de sacar de un envase, ya en React. */
function pantallaSacarDeUnLote() {
  const suyo = estadoDelLibro();
  const salida = suyo.salida || {};
  const apunte = apunteDeLaSalida(salida.apunte_tipo, salida.apunte_id) || {};
  const hectareas = apunte.superficie_tratada_ha || apunte.superficie_ha || null;
  const articulos = articulosDeUnApunte(apunte).map((articulo) => ({
    nombre: articulo.nombre,
    lotes: (articulo.lotes || []).map((lote) => fichaDeUnLote(lote)),
  }));
  montar(() =>
    pantallaDeSacarDeUnLote({
      textos: textosDelLibro(),
      apunte: {
        titulo: t("cesta.libro_salida_apunte", ""),
        detalle: [
          apunte.producto_nombre || apunte.fertilizante_nombre || "",
          fechaOSinFecha(apunte.fecha),
          dondeSeApunto(apunte),
          hectareas ? numeroConUnidad(hectareas, t("rotulos.hectareas_corto", "")) : "",
        ]
          .filter(Boolean)
          .join(" · "),
        acciones: volverAlLibro(),
      },
      articulos,
      pidiendo_cantidad: salida.pidiendo_cantidad,
      descuadre: salida.descuadre || "",
      lote_del_descuadre: salida.lote_del_descuadre,
      resultado: salida.resultado,
      avisos: salida.avisos || [],
      aviso: suyo.aviso || "",
      // El error de esta pantalla va **en la salida** y no en el libro: lo que ha dicho el servidor de una
      // salida («ese apunte solo tiene la dosis») no tiene nada que ver con lo que pueda decir el libro, y
      // mezclarlos haría que el aviso de una pantalla saliera en otra.
      error: salida.error || suyo.error || "",
      guardando: Boolean(suyo.guardando),
      cargando: Boolean(suyo.cargando),
    }),
  );
}

/** Lo que dice el apunte que se gastó, si lo dice: `null` es «solo trae lo que se echa por hectárea». */
function totalDelApunte(tipo, apunte) {
  if (!apunte) return null;
  const total = tipo === "fertilizacion" ? apunte.cantidad_total_kg : apunte.cantidad_total;
  return total === null || total === undefined ? null : total;
}

/**
 * Saca de un envase lo que se gastó en un apunte.
 *
 * **La cantidad la dice el apunte**, y por eso aquí no se teclea: el servidor la copia y devuelve las
 * dos cuentas —el total gastado y lo que va por hectárea, cada una con su nombre—. Multiplicar la dosis
 * por la superficie por nuestra cuenta es exactamente el error de diez veces que hay que evitar, así que
 * cuando el apunte solo trae la dosis **se pide el total**.
 *
 * Y si lo que sale deja el envase en negativo, el servidor lo avisa con los números: aquí no se apunta
 * nada a escondidas ni se impide registrar lo que de verdad pasó; se le dan al agricultor las dos salidas
 * (corregir la cantidad, o decir que la diferencia es de verdad).
 */
async function guardarLaSalida(loteId, { aceptarDescuadre = false } = {}) {
  const suyo = estadoDelLibro();
  const salida = suyo.salida;
  const apunte = apunteDeLaSalida(salida.apunte_tipo, salida.apunte_id) || {};
  const campo = document.getElementById("salida-cantidad");
  const escrita = campo ? String(campo.value || "").trim() : "";
  const cantidadEscrita = escrita ? aNumero(escrita) : null;
  const total = totalDelApunte(salida.apunte_tipo, apunte);

  // El apunte solo trae lo que se echa por hectárea: se pide el total, con el mensaje del servidor, que
  // dice por qué el número que hay no sirve para esto.
  if (total === null && cantidadEscrita === null) {
    salida.pidiendo_cantidad = Number(loteId);
    salida.error = mensaje("AL17_el_apunte_no_dice_el_total");
    return pantallaSacarDeUnLote();
  }
  salida.error = "";

  const datos = {
    apunte_tipo: salida.apunte_tipo,
    apunte_id: salida.apunte_id,
    lote_id: Number(loteId),
    clave_de_reenvio: salida.clave,
  };
  if (cantidadEscrita !== null) datos.cantidad = cantidadEscrita;
  // «La diferencia es de verdad»: lo que salió era más de lo que el libro dice que había, y el agricultor
  // dice que eso es lo que pasó. Se apunta **marcado**, no a escondidas (contrato: nunca se impide
  // registrar lo que de verdad ocurrió).
  if (aceptarDescuadre) datos.aceptar_descuadre = true;

  suyo.error = "";
  suyo.aviso = "";
  suyo.guardando = true;
  pantallaSacarDeUnLote();
  const resultado = await enviarOApuntar("/api/almacen/salidas", datos, "salida", false);
  suyo.guardando = false;

  if (resultado.encolado) {
    suyo.aviso = mensaje("sin_cobertura");
    return pantallaSacarDeUnLote();
  }
  if (resultado.error) {
    // Lo que sale deja el envase en negativo: no se apunta nada y se dan las dos salidas. Cualquier otro
    // «no» (un apunte anulado, un envase que no es de esta finca) se enseña tal cual.
    if (resultado.estado === 409) {
      salida.descuadre = resultado.error;
      salida.lote_del_descuadre = Number(loteId);
    } else {
      salida.error = resultado.error;
    }
    return pantallaSacarDeUnLote();
  }

  // Apuntado: las dos cuentas, cada una con su nombre. La unidad de lo que va por hectárea es la del
  // propio apunte (`unidad_dosis`), no una que se invente la pantalla.
  const cuerpo = resultado.datos || {};
  const dosis = cuerpo.dosis_por_hectarea;
  const superficie = cuerpo.superficie_ha;
  salida.resultado = {
    total: numeroConUnidad(cuerpo.cantidad_total_gastada, cuerpo.unidad_de_la_cantidad),
    filas: [
      dosis === null || dosis === undefined
        ? null
        : {
            etiqueta: t("cesta.libro_salida_por_hectarea", ""),
            valor: numeroConUnidad(dosis, apunte.unidad_dosis || ""),
          },
      superficie === null || superficie === undefined
        ? null
        : {
            etiqueta: t("cesta.libro_salida_hectareas", ""),
            valor: numeroConUnidad(superficie, t("rotulos.hectareas_corto", "")),
          },
    ].filter(Boolean),
    avisos: cuerpo.avisos || [],
    acciones: volverAlLibro(),
  };
  salida.avisos = cuerpo.avisos || [];
  await recargarElLibro();
  return pantallaSacarDeUnLote();
}

// ---------------------------------------------------------------------------------------------
// Enganchar la factura que llega después
// ---------------------------------------------------------------------------------------------

/** Las facturas que se pueden elegir: las que están guardadas y no anuladas. */
function facturasParaElegir() {
  return (estado.facturasLista || [])
    .filter((factura) => !factura.anulada)
    .map((factura) => ({
      id: factura.id,
      titulo: factura.numero_factura || factura.proveedor || "",
      proveedor: factura.numero_factura ? factura.proveedor || "" : "",
      cuando: fechaOSinFecha(factura.fecha),
      total: factura.total === null || factura.total === undefined ? "" : enEuros(factura.total),
    }));
}

/**
 * Abre «decir de qué factura es este albarán».
 *
 * **Esta pantalla no escribe nada hasta que el agricultor lo dice.** Elegir una factura solo pregunta al
 * servidor si esa factura puede ser la de este albarán: la propuesta se enseña con su porqué y sus líneas
 * casadas, y hasta que no se pulsa el botón de decir que sí no se manda ningún enganche. Es la misma
 * regla que en el dictado y en la lectura de facturas: una máquina propone, una persona confirma.
 */
function abrirElEngancheDeLaFactura(recepcionId) {
  const suyo = estadoDelLibro();
  suyo.error = "";
  suyo.aviso = "";
  suyo.enganche = {
    recepcion_id: Number(recepcionId),
    eleccion: null,
    comprobando: false,
    aviso: "",
    error: "",
  };
  pantallaEngancharLaFactura();
}

/** La pantalla de enganchar la factura, ya en React. */
function pantallaEngancharLaFactura() {
  const suyo = estadoDelLibro();
  const enganche = suyo.enganche || {};
  const recepcion = suyo.recepcion || {};
  montar(() =>
    pantallaDeEngancharLaFactura({
      textos: textosDelLibro(),
      albaran: {
        id: recepcion.id,
        titulo: tituloDeUnAlbaran(recepcion),
        detalle: [fechaOSinFecha(recepcion.fecha), recepcion.proveedor || ""]
          .filter(Boolean)
          .join(" · "),
        acciones: [
          {
            etiqueta: t("cesta.libro_volver_al_albaran", ""),
            accion: "albaran-abrir",
            datos: { id: recepcion.id },
            clase: "boton-claro",
          },
        ],
      },
      facturas: facturasParaElegir(),
      eleccion: enganche.eleccion,
      comprobando: Boolean(enganche.comprobando),
      aviso: enganche.aviso || "",
      error: enganche.error || "",
    }),
  );
}

/** Pregunta al servidor si esa factura puede ser la de este albarán. **No engancha nada.** */
async function proponerLaFactura(facturaId) {
  const suyo = estadoDelLibro();
  const enganche = suyo.enganche;
  const factura = (estado.facturasLista || []).find(
    (una) => Number(una.id) === Number(facturaId),
  ) || {};
  enganche.comprobando = true;
  enganche.error = "";
  enganche.aviso = "";
  pantallaEngancharLaFactura();

  let propuesta = null;
  try {
    propuesta = await apiJson(`/api/almacen/facturas/${facturaId}/posibles-recepciones`);
  } catch (fallo) {
    // No se ha podido preguntar (sin cobertura, o el servidor no contesta): se dice, y no se da por
    // bueno nada. «No lo he podido comprobar» no es «no».
    enganche.comprobando = false;
    enganche.aviso = t("cesta.libro_factura_sin_comprobar", "");
    return pantallaEngancharLaFactura();
  }
  const suya = (propuesta.propuestas || []).find(
    (una) => Number(una.recepcion_id) === Number(suyo.recepcion.id),
  );
  enganche.comprobando = false;
  enganche.eleccion = {
    factura_id: facturaId,
    titulo: [factura.numero_factura, factura.proveedor].filter(Boolean).join(" · "),
    propuesta: Boolean(suya),
    como: suya ? suya.como_se_propone || "" : "",
    lineas: suya
      ? (suya.lineas_casadas || []).map((casada) =>
          renglonDeUnaLineaCasada(casada, suyo.recepcion, factura),
        )
      : [],
    // Lo que hay que mandar si el agricultor dice que sí. Se guarda tal cual, sin interpretarlo.
    casadas: suya ? suya.lineas_casadas || [] : [],
  };
  return pantallaEngancharLaFactura();
}

/**
 * Engancha la factura al albarán, **solo cuando el agricultor lo dice**.
 *
 * Lo que se manda no lleva ni una cantidad: la mercancía entró una vez, el día que llegó el albarán, y la
 * factura solo dice de dónde salió y cuánto costó. Lo que sí viaja es qué línea del albarán es qué línea
 * de la factura, para el caso en que los dos papeles no cuadren del todo.
 */
async function engancharLaFacturaElegida(facturaId) {
  const suyo = estadoDelLibro();
  const enganche = suyo.enganche;
  const recepcion = suyo.recepcion || {};
  const eleccion = enganche.eleccion || {};
  const datos = {
    factura_id: Number(facturaId),
    lineas: (eleccion.casadas || []).map((casada) => ({
      linea_de_recepcion_id: casada.linea_de_recepcion_id,
      linea_de_factura_id: casada.linea_de_factura_id,
    })),
  };
  if (!navigator.onLine) {
    enganche.aviso = t("cesta.libro_factura_sin_comprobar", "");
    return pantallaEngancharLaFactura();
  }
  enganche.comprobando = true;
  enganche.error = "";
  pantallaEngancharLaFactura();
  const resultado = await mandarCambio(
    `/api/almacen/recepciones/${recepcion.id}/factura`,
    "POST",
    datos,
  );
  enganche.comprobando = false;
  if (resultado.error) {
    enganche.error = resultado.error;
    return pantallaEngancharLaFactura();
  }
  suyo.recepcion = resultado.datos;
  suyo.enganche = null;
  suyo.aviso = t("cesta.libro_factura_enganchada_ok", "");
  await recargarElLibro();
  return pantallaRecepcion();
}

// ------------------------------------------------------------- las facturas

/**
 * Las facturas de compra: subir una, que el programa la lea y que el agricultor la confirme.
 *
 * **El recorrido, que es lo que importa entender:** el agricultor hace una foto al papel (o sube
 * el PDF que le ha mandado el proveedor), el programa **lee lo que pone** y le enseña lo que ha
 * entendido —el proveedor, el NIF, la fecha, el número, los totales y cada línea con su producto,
 * su cantidad y su precio— para que lo corrija. Lo que se guarda es lo que él da por bueno.
 *
 * **Ese último paso no es un adorno.** Una foto hecha con el móvil siempre trae alguna errata (el
 * lector de letras de este ordenador, por ejemplo, solo tiene el idioma inglés y las palabras con
 * eñe salen cambiadas). Enseñar lo leído para que lo confirme es lo que hace que esto se pueda usar
 * sin jugarse un dato del cuaderno.
 */
function estadoDeLasFacturas() {
  if (!estado.facturas) {
    estado.facturas = {
      lista: [],
      cargada: false,
      leyendo: false,
      guardando: false,
      // Lo que ha entendido el programa, tal y como lo ha devuelto el servidor.
      interpretacion: null,
      // La factura que se está **corrigiendo**, si es que se está corrigiendo una (ronda 93). Cuando
      // está puesta, la pantalla de la interpretación no enseña lo que se acaba de leer sino lo que ya
      // está guardado, y guardar manda un `PUT` a esa factura en vez de crear una nueva. Es la misma
      // idea que `documentoEnEdicion` para los papeles y que `asistente.corregir` para los apuntes.
      corrigiendo: null,
      // El fichero elegido, guardado aquí **antes** de repintar: ver la nota de `leerFactura`.
      fichero: null,
      guardada: null,
      error: "",
    };
  }
  return estado.facturas;
}


/**
 * «Mis facturas»: la lista y la confirmación de guardada, ya en React (ver `docs/REACT.md`).
 *
 * Tres estados y tres caminos:
 *
 *  - **Se acaba de guardar una factura** (`facturas.guardada`): se dice y se ofrecen los dos sitios
 *    donde sigue viva: el almacén (los números de producto) y la lista de facturas.
 *  - **Hay una lectura pendiente de confirmar** (`facturas.interpretacion`): eso **no** está migrado
 *    todavía y se pinta con la pantalla de siempre. Es la pantalla donde el agricultor corrige lo que
 *    el programa ha leído de una foto, y se migrará aparte, con sus pruebas.
 *  - **La lista**: cada factura con su proveedor, su número, su total y cuántas líneas trae.
 */
function pantallaFacturas() {
  const f = (clave) => t(`facturas.${clave}`, "");
  const facturas = estadoDeLasFacturas();

  if (!facturas.guardada && facturas.interpretacion) {
    return pantallaInterpretacionDeLaFactura();
  }

  // Cada factura llega contada: el total ya escrito en euros (o «—» si no se dijo) y su línea de
  // detalle. Un total que no se sabe **no es un cero**: es un dato que falta, y se enseña como tal.
  //
  // Y desde la ronda 90, con el diseño de Stitch de esta pantalla, cada factura dice si tiene su papel:
  // **el dato estaba en el servidor desde la ronda 40 y no lo enseñaba nadie**, y el papel es justo lo
  // que se pide en una inspección. Los dos caminos (verlo y subirlo) también estaban en el servidor:
  // `GET/POST /api/facturas/{id}/fichero`.
  const suyas = (estado.facturasLista || []).map((factura) => ({
    id: factura.id,
    proveedor: factura.proveedor || f("sin_proveedor"),
    detalle: [factura.numero_factura, factura.fecha ? formateaFecha(factura.fecha) : ""]
      .filter(Boolean)
      .join(" · "),
    total: factura.total === null ? "—" : `${formateaNumero(factura.total, 2)} €`,
    // `lineas` viene siempre del servidor (`FacturaSalida.lineas`), pero se lee con red: una lista que
    // falte **no puede dejar la pantalla en blanco**, que es el fallo que ya apareció una vez con
    // `ResumenDelApunte` (ronda 92) y que en el móvil de David se ve como «no hay nada».
    lineas: String((factura.lineas || []).length),
    tiene_fichero: Boolean(factura.tiene_fichero),
    // **Y los datos en crudo, para la tabla del ordenador** (30/09/2026): la fecha y los números como son
    // (para poder ordenar por ellos) y el papel, que es lo primero que se pide en una inspección.
    fecha_iso: factura.fecha || "",
    fecha_escrita: factura.fecha ? formateaFecha(factura.fecha) : "",
    numero_factura: factura.numero_factura || "",
    base_imponible: factura.base_imponible,
    cuota_iva: factura.cuota_iva,
    total_numero: factura.total,
    papel: factura.tiene_fichero ? f("papel_guardado") : f("sin_fichero"),
    papel_corto: factura.tiene_fichero ? "" : f("papel_falta"),
    // **Y sus botones** (ronda 93): hoy solo BORRAR (ver `OTRAS_COSAS.factura`: corregir una factura es
    // la pantalla que revisa sus líneas, y ese camino todavía no se abre con lo guardado).
    acciones: botonesDeCorregirYBorrar("factura", factura.id),
  }));
  const lector = estado.lectorDeFacturas ? estado.lectorDeFacturas.lector : null;

  montar(() =>
    pantallaDeFacturas({
      textos: { facturas: t("facturas", {}), acciones: t("acciones", {}) },
      facturas: suyas,
      // **Y la tabla, para el ordenador** (30/09/2026): las facturas del año juntas, con sus números y si
      // tienen el papel guardado. Al pie, el total gastado.
      tabla: tablaDeFacturas(suyas),
      // Cuántas hay, en singular o en plural: lo decide el servidor con `con_cuenta` (ronda 84).
      resumen: suyas.length
        ? conCuenta(t("facturas", {}) || {}, "cuantas", suyas.length)
        : "",
      lector: lector ? lector.nota : "",
      error: facturas.error || "",
      guardada: facturas.guardada ? "si" : "",
    }),
  );
}

/**
 * La tabla de las facturas, para el ordenador.
 *
 * POR QUÉ. Las facturas son los papeles que demuestran lo que se compró: en el ordenador interesa verlas
 * juntas —fecha, proveedor, número, base, IVA, total— para cuadrar el año, y **si tienen guardado el
 * papel**, que es lo primero que se pide en una inspección. Al pie, el total del año.
 *
 * Un total que no se sabe **no es un cero**: se deja en blanco y no suma. Es la decisión de siempre («un
 * cero sería un dato inventado»), y aquí importa más que en ningún sitio, porque el pie es una cuenta.
 */
function tablaDeFacturas(facturas) {
  const col = (clave) => t(`tabla.${clave}`, "");
  const f = (clave) => t(`facturas.${clave}`, "");
  const ordenadas = ordenarFichas(facturas, elOrdenDeLaTabla("facturas"), "id");
  const columnas = columnasDeLaTabla("facturas", [
    { texto: col("fecha"), campo: "fecha_iso", clase: "tabla-numero" },
    { texto: col("proveedor"), campo: "proveedor" },
    { texto: col("numero_factura"), campo: "numero_factura" },
    { texto: col("base"), campo: "base_imponible", clase: "tabla-numero" },
    { texto: col("iva"), campo: "cuota_iva", clase: "tabla-numero" },
    { texto: col("total"), campo: "total_numero", clase: "tabla-numero" },
    { texto: col("papel"), campo: "tiene_fichero" },
    { texto: col("acciones") },
  ]);

  const filas = ordenadas.map((factura) => ({
    celdas: [
      { texto: factura.fecha_escrita, clase: "tabla-numero" },
      { texto: factura.proveedor },
      { texto: factura.numero_factura },
      { texto: enEuros(factura.base_imponible), clase: "tabla-numero" },
      { texto: enEuros(factura.cuota_iva), clase: "tabla-numero" },
      { texto: enEuros(factura.total_numero), clase: "tabla-numero" },
      {
        // El papel: si está, se dice; si no, se dice **con su etiqueta corta**, porque es lo que hay que
        // arreglar. La frase larga («Esta factura no tiene ni la foto ni el fichero.») se queda en la ficha
        // del móvil: en una celda de la tabla ocuparía cinco renglones.
        texto: factura.tiene_fichero ? f("papel_guardado") : "",
        estado: factura.tiene_fichero ? null : { texto: factura.papel_corto, tipo: "mirar" },
      },
    ],
    acciones: factura.acciones || [],
  }));

  // Si una factura carece de una cifra, la suma de las demás NO es el total del año.
  // Una cifra desconocida queda como tal tanto en el pie como en la franja de números.
  const sumaCompleta = (campo) => {
    if (ordenadas.some((factura) => factura[campo] === null || factura[campo] === undefined ||
      factura[campo] === "" || !Number.isFinite(Number(factura[campo])))) return null;
    return ordenadas.reduce((suma, factura) => suma + Number(factura[campo]), 0);
  };
  const base = sumaCompleta("base_imponible");
  const iva = sumaCompleta("cuota_iva");
  const total = sumaCompleta("total_numero");
  const sinPapel = ordenadas.filter((factura) => !factura.tiene_fichero).length;
  const cifra = (valor) => valor === null ? "—" : enEuros(valor);
  return {
    clave: "facturas",
    etiqueta: col("facturas_etiqueta"),
    columnas,
    filas,
    resumen: total === null
      ? conCuenta(t("tabla", {}), "resumen_facturas_sin_total", ordenadas.length)
      : resumenDeLaTabla("resumen_facturas", ordenadas.length, {
          total: formateaNumero(total, 2),
        }),
    indicadores: [
      { etiqueta: f("numero_de_facturas"), valor: String(ordenadas.length) },
      { etiqueta: col("base"), valor: cifra(base) },
      { etiqueta: col("iva"), valor: cifra(iva) },
      { etiqueta: col("total"), valor: cifra(total) },
      { etiqueta: f("sin_papel_numero"), valor: String(sinPapel) },
    ],
  };
}

/** Un importe con su euro, o vacío si no se sabe (un cero sería un dato inventado). */
function enEuros(valor) {
  return valor === null || valor === undefined ? "" : `${formateaNumero(valor, 2)} €`;
}

/**
 * Sube la foto (o el fichero) de una factura que ya está apuntada.
 *
 * **Esto faltaba entero**: el camino estaba en el servidor desde la ronda 40 (`POST
 * /api/facturas/{id}/fichero`) y el texto del botón también («SUBIR LA FOTO DEL PAPEL»), pero ninguna
 * pantalla lo pedía, así que una factura escrita a mano se quedaba para siempre sin su papel. Lo pidió el
 * diseño de Stitch de la pantalla de facturas (ronda 90), que enseña cada factura con su papel al lado.
 *
 * El campo del fichero se lee **por su `id`** (`factura-papel-<id>`), que es como lee esta aplicación todo
 * lo que se escribe: el manejador de clics es uno solo y vive aquí.
 */
async function subirElPapelDeLaFactura(id) {
  const facturas = estadoDeLasFacturas();
  const entrada = document.getElementById(`factura-papel-${id}`);
  if (!entrada || !entrada.files || !entrada.files.length) {
    facturas.error = f("que_fichero");
    pantallaFacturas();
    return;
  }
  // Sin cobertura no se puede subir un fichero de un tirón: se dice claro, en vez de dejar al agricultor
  // esperando delante de algo que no avanza. Es la misma decisión que en los papeles de la documentación.
  if (!navigator.onLine) {
    facturas.error = aviso("no_se_pudo");
    pantallaFacturas();
    return;
  }
  facturas.error = null;
  const cuerpo = new FormData();
  cuerpo.append("fichero", entrada.files[0]);
  try {
    // Con `fetch` y no con `api()`: `api()` pone la cabecera de JSON, y con un fichero la pone el
    // navegador sola (con su `boundary`). Poner las dos rompe el envío sin decir por qué.
    const respuesta = await fetch(`/api/facturas/${id}/fichero`, {
      method: "POST",
      headers: { Authorization: `Bearer ${estado.token}` },
      body: cuerpo,
    });
    if (!respuesta.ok) {
      const detalle = await respuesta.json().catch(() => null);
      throw new Error(avisoDelServidor(detalle) || mensaje("no_se_pudo"));
    }
    // La lista se vuelve a pedir: la factura que se acaba de subir tiene que salir ya con su papel.
    await cargarDatos().catch(() => {});
  } catch (error) {
    facturas.error = error.message;
  }
  pantallaFacturas();
}

/** Descarga la foto (o el fichero) de una factura. */
async function verElPapelDeLaFactura(id) {
  const respuesta = await api(`/api/facturas/${id}/fichero`);
  if (!respuesta.ok) {
    const detalle = await respuesta.json().catch(() => null);
    avisarDelError(avisoDelServidor(detalle) || mensaje("no_se_pudo"));
    return;
  }
  const blob = await respuesta.blob();
  const enlace = document.createElement("a");
  enlace.href = URL.createObjectURL(blob);
  enlace.download = `factura-${id}`;
  enlace.click();
  URL.revokeObjectURL(enlace.href);
}
/**
 * «Añadir una factura»: la pantalla, ya en React.
 *
 * El campo del fichero conserva su `id` (`factura-fichero`), que es como `leerFactura()` coge la
 * foto o el PDF. Mientras se está leyendo, la pantalla lo dice y el botón no se puede volver a
 * pulsar: sin eso, el agricultor puede mandar la misma factura dos veces.
 */
function pantallaNuevaFactura() {
  const facturas = estadoDeLasFacturas();

  montar(() =>
    pantallaDeNuevaFactura({
      textos: { facturas: t("facturas", {}), acciones: t("acciones", {}) },
      leyendo: Boolean(facturas.leyendo),
      error: facturas.error || "",
    }),
  );
}
/**
 * La pantalla de la interpretación: lo que el programa ha entendido, todo editable.
 *
 * Es la pantalla más importante de esta función. Si esto fuera un «ya está guardado», el programa
 * estaría metiendo en el cuaderno lo que ha adivinado de una foto, y eso es justo lo que no se
 * puede hacer.
 */
/**
 * Lo que el programa ha leído de una factura, ya en React (ver `docs/REACT.md`).
 *
 * **Es la pantalla que hace que leer una factura se pueda usar**: lo leído es una propuesta y el
 * agricultor la confirma. Todo lo que se prepara aquí es lo que el componente no puede saber: de
 * dónde sale la lectura, los avisos (con el de «esta misma factura ya la has subido» delante), los
 * ocho campos de la cabecera con su etiqueta y su pista, y las líneas con **sus opciones de
 * producto**, que salen de los productos que el agricultor tiene en la cesta.
 *
 * **Y sirve para dos cosas desde la ronda 93**: para confirmar lo que se acaba de leer de una foto y
 * para **corregir una factura que ya está guardada**. Lo segundo no es una pantalla nueva: es la misma
 * pregunta («¿esto es lo que dice el papel?») con los datos que ya están en el cuaderno, y con el botón
 * de guardar mandando un `PUT` en vez de crear otra. Lo que cambia cuando se está corrigiendo son tres
 * cosas, y las tres las dice `facturas.corrigiendo`: el título (no se ha leído nada), el botón de
 * volver (a la lista de facturas, no a «añadir una factura») y la etiqueta de guardar.
 */
/**
 * Una factura que ya está guardada, contada como lo que se lee de un papel.
 *
 * POR QUÉ HACE FALTA ESTO. La pantalla que confirma una lectura recorre `interpretacion`, que es lo que
 * devolvió el lector. Una factura guardada tiene los mismos datos con **otros nombres** (`total` es
 * `total`, pero el producto de una línea es `producto_id` y no `producto_sugerido_id`, y la cuenta de la
 * línea se llama `cuadra`) y en la lista de facturas viene `tiene_fichero` en vez del fichero. Traducirlo
 * aquí, en un solo sitio, es lo que permite usar la misma pantalla sin que el componente sepa de dónde
 * vienen los datos.
 *
 * **Y LO QUE LA PANTALLA NO PREGUNTA VIAJA IGUAL.** Tres datos de una factura no tienen campo en ninguna
 * pantalla: las `notas` de la cabecera, el `lote` y el `numero_registro` de cada línea y el abono al que
 * está enganchada una línea (`fertilizante_id`). Si no viajaran, **corregir un número borraría esos tres
 * datos sin decir nada**, que es exactamente el fallo que ya apareció dos veces en este programa (la
 * forma de una tierra que se perdió al corregirla y los nueve números del boletín de un análisis). Por
 * eso se copian aquí y `recogeLaInterpretacion()` los vuelve a mandar tal cual.
 */
function facturaComoInterpretacion(factura) {
  return {
    proveedor: factura.proveedor || "",
    proveedor_nif: factura.proveedor_nif || "",
    numero_factura: factura.numero_factura || "",
    fecha: factura.fecha || hoyISO(),
    base_imponible: factura.base_imponible,
    cuota_iva: factura.cuota_iva,
    tipo_iva_pct: factura.tipo_iva_pct,
    total: factura.total,
    // Lo que ninguna pantalla pregunta y no se puede perder (ver arriba).
    notas: factura.notas || null,
    // Cómo entró la factura en el cuaderno (de un PDF, de una foto, a mano): la pantalla lo dice, y es
    // un dato que se enseñó al guardarla. Aquí no se inventa nada: se repite lo que ya estaba.
    como_se_leyo: factura.leida_por || "a mano",
    idioma_del_lector: "",
    // Sin avisos y sin «ya estaba»: los avisos son de una lectura, y aquí no se ha leído nada. Poner
    // los de la última lectura sería repetir un aviso que ya se atendió (o que ya no es verdad).
    avisos: [],
    ya_estaba: null,
    lineas: (factura.lineas || []).map((linea) => ({
      descripcion: linea.descripcion || "",
      cantidad: linea.cantidad,
      unidad: linea.unidad || "",
      precio_unitario: linea.precio_unitario,
      importe: linea.importe,
      // Los tres que ninguna pantalla pregunta (ver arriba): se guardan para volver a mandarlos.
      numero_registro: linea.numero_registro || "",
      lote: linea.lote || null,
      fertilizante_id: linea.fertilizante_id === undefined ? null : linea.fertilizante_id,
      // Lo que ya se sabía al guardarla: si la cuenta cuadraba y a qué producto está enganchada. No es
      // una sugerencia (eso es de una lectura), así que no se escribe ninguna frase de sugerencia.
      cuadra: linea.cuadra,
      producto_sugerido_id: linea.producto_id,
      producto_sugerido: "",
      como_se_sugiere: "",
    })),
  };
}

function pantallaInterpretacionDeLaFactura() {
  const f = (clave) => t(`facturas.${clave}`, "");
  const facturas = estadoDeLasFacturas();
  const leida = facturas.interpretacion;
  const texto = (dato) => (dato === null || dato === undefined ? "" : String(dato));

  // Cómo se leyó. Se dice porque explica por qué puede haber erratas en las palabras: el lector de
  // letras de este ordenador solo tiene el idioma inglés.
  const comoSeLeyo = {
    pdf: f("leida_pdf"),
    foto: f("leida_foto"),
    escaneo: f("leida_escaneo"),
    texto: f("leida_pdf"),
    "a mano": f("leida_mano"),
  }[leida.como_se_leyo] || "";

  const avisos = [...(leida.avisos || [])];
  if (leida.ya_estaba) {
    avisos.unshift(rellena(f("ya_estaba"), { numero: leida.numero_factura || "?" }));
  }

  const cabecera = [
    {
      id: "factura-proveedor",
      etiqueta: f("campo_proveedor"),
      pista: f("campo_proveedor_pista"),
      valor: texto(leida.proveedor),
    },
    { id: "factura-proveedor-nif", etiqueta: f("campo_nif"), valor: texto(leida.proveedor_nif) },
    { id: "factura-numero", etiqueta: f("campo_numero"), valor: texto(leida.numero_factura) },
    { id: "factura-fecha", etiqueta: f("campo_fecha"), valor: texto(leida.fecha), tipo: "date" },
    { id: "factura-base", etiqueta: f("campo_base"), valor: texto(leida.base_imponible) },
    { id: "factura-iva", etiqueta: f("campo_iva"), valor: texto(leida.cuota_iva) },
    { id: "factura-tipo-iva", etiqueta: f("campo_tipo_iva"), valor: texto(leida.tipo_iva_pct) },
    { id: "factura-total", etiqueta: f("campo_total"), valor: texto(leida.total) },
  ];

  const lineas = (leida.lineas || []).map((linea) => {
    const elegido = linea.producto_sugerido_id || (linea.crear_producto ? "nuevo" : "");
    const opciones = [
      { valor: "", texto: f("linea_sin_producto"), elegido: elegido === "" },
      { valor: "nuevo", texto: f("linea_crear_producto"), elegido: elegido === "nuevo" },
    ];
    for (const producto of estado.productos || []) {
      opciones.push({
        valor: String(producto.id),
        texto: producto.nombre_comercial,
        elegido: Number(elegido) === producto.id,
      });
    }
    return {
      descripcion: texto(linea.descripcion),
      cantidad: texto(linea.cantidad),
      unidad: texto(linea.unidad),
      precio: texto(linea.precio_unitario),
      importe: texto(linea.importe),
      opciones,
      no_cuadra: linea.cuadra === false,
      sugerida: linea.producto_sugerido
        ? rellena(f("linea_sugerida"), {
            producto: linea.producto_sugerido,
            como: linea.como_se_sugiere,
          })
        : "",
      registro: linea.numero_registro ? `${f("linea_registro")}: ${linea.numero_registro}` : "",
    };
  });

  montar(() =>
    pantallaDeInterpretacionDeLaFactura({
      textos: { facturas: t("facturas", {}), acciones: t("acciones", {}) },
      leida: {
        // La frase se monta aquí, con su rótulo: son dos textos del servidor unidos.
        de_donde: comoSeLeyo ? `${f("de_donde_sale_la_lectura")}: ${comoSeLeyo}` : "",
        avisos,
        cabecera,
        lineas,
      },
      error: facturas.error || "",
      guardando: Boolean(facturas.guardando),
      // Si lo que se enseña es lo que se acaba de leer o **lo que ya está guardado** (ronda 93). El
      // componente cambia tres cosas con esto (título, pista y botón de volver) y ninguna más: los campos
      // y las líneas se pintan igual, que es justo lo que se quiere.
      corrigiendo: Boolean(facturas.corrigiendo),
    }),
  );
}
/** Sube el fichero y enseña lo que el programa ha entendido. **No guarda nada.** */
async function leerFactura() {
  const f = (clave) => t(`facturas.${clave}`, "");
  const facturas = estadoDeLasFacturas();
  const entrada = document.getElementById("factura-fichero");
  if (!entrada || !entrada.files || entrada.files.length === 0) {
    facturas.error = f("que_fichero");
    return pantallaNuevaFactura();
  }
  // El fichero se guarda en el estado **antes** de repintar: pintar la pantalla cambia la casilla
  // del fichero por una nueva y vacía. Es el mismo detalle que con el cuaderno de la Junta.
  facturas.fichero = entrada.files[0];
  if (!navigator.onLine) {
    facturas.error = f("sin_conexion");
    return pantallaNuevaFactura();
  }
  facturas.error = "";
  facturas.leyendo = true;
  pantallaNuevaFactura();
  const cuerpo = new FormData();
  cuerpo.append("fichero", facturas.fichero);
  try {
    const respuesta = await fetch("/api/facturas/leer", {
      method: "POST",
      headers: { Authorization: `Bearer ${estado.token}` },
      body: cuerpo,
    });
    const detalle = await respuesta.json().catch(() => null);
    if (!respuesta.ok) throw new Error((detalle && detalle.detail) || f("no_se_pudo"));
    facturas.interpretacion = detalle;
    // Las líneas se editan en la pantalla; se copian aquí para poder recogerlas al guardar.
    facturas.interpretacion.lineas = detalle.lineas || [];
  } catch (error) {
    facturas.error = error.message || f("no_se_pudo");
  }
  facturas.leyendo = false;
  if (facturas.interpretacion) return pantallaInterpretacionDeLaFactura();
  pantallaNuevaFactura();
}

/** Empieza una factura en blanco, para quien la apunta a mano o no quiere leer la foto. */
function facturaAMano() {
  const facturas = estadoDeLasFacturas();
  facturas.error = "";
  facturas.interpretacion = {
    proveedor: "",
    proveedor_nif: "",
    numero_factura: "",
    fecha: hoyISO(),
    base_imponible: null,
    cuota_iva: null,
    tipo_iva_pct: null,
    total: null,
    como_se_leyo: "a mano",
    idioma_del_lector: "",
    avisos: [],
    ya_estaba: null,
    lineas: [
      {
        descripcion: "",
        cantidad: null,
        unidad: "",
        precio_unitario: null,
        importe: null,
        numero_registro: "",
        cuadra: null,
        producto_sugerido_id: null,
        producto_sugerido: "",
        como_se_sugiere: "",
      },
    ],
  };
  pantallaInterpretacionDeLaFactura();
}

/** Recoge lo que hay en la pantalla: es lo que se guarda, palabra por palabra. */
function recogeLaInterpretacion() {
  const numero = (id) => {
    const nodo = document.getElementById(id);
    if (!nodo) return null;
    const limpio = String(nodo.value || "").trim().replace(",", ".");
    if (limpio === "") return null;
    const valor = Number(limpio);
    return Number.isFinite(valor) ? valor : null;
  };
  const texto = (id) => {
    const nodo = document.getElementById(id);
    return nodo ? String(nodo.value || "").trim() : "";
  };
  // Las líneas se recorren **por su número**, no buscando elementos en la pantalla: los campos se
  // llaman `factura-<número>-<campo>` y así se leen con `getElementById`, que es lo que usa todo el
  // programa (y lo que sabe hacer el DOM de mentira de los tests, que no tiene `querySelectorAll`).
  const lectura = estadoDeLasFacturas().interpretacion || {};
  const cuantas = (lectura.lineas || []).length;
  const lineas = [];
  for (let indice = 0; indice < cuantas; indice += 1) {
    const descripcion = texto(`factura-${indice}-descripcion`);
    if (!descripcion) continue;
    const elegido = texto(`factura-${indice}-producto`);
    // Lo que la pantalla **no pregunta** de esa línea y hay que devolver tal cual (ver
    // `facturaComoInterpretacion`): el número de registro que venía en el papel, el lote y el abono al
    // que está enganchada. Se cogen **por el número de la línea** y eso vale porque esta pantalla ni
    // añade ni quita líneas (los textos de «AÑADIR OTRA LÍNEA» y «QUITAR ESTA LÍNEA» están escritos y sin
    // puerta). El día que se puedan añadir o quitar, esto tiene que atarse a la línea y no al número.
    const suya = (lectura.lineas || [])[indice] || {};
    lineas.push({
      descripcion,
      cantidad: numero(`factura-${indice}-cantidad`),
      unidad: texto(`factura-${indice}-unidad`) || null,
      precio_unitario: numero(`factura-${indice}-precio`),
      importe: numero(`factura-${indice}-importe`),
      producto_id: elegido && elegido !== "nuevo" ? Number(elegido) : null,
      numero_registro: suya.numero_registro || null,
      lote: suya.lote || null,
      fertilizante_id: suya.fertilizante_id === undefined ? null : suya.fertilizante_id,
      // «CREARLO COMO PRODUCTO NUEVO»: se crea el producto con los datos de la factura. Es lo que
      // hace que traer una factura sirva para algo más que para guardar el papel.
      crear_producto: elegido === "nuevo",
    });
  }
  return {
    fecha: texto("factura-fecha") || null,
    proveedor: texto("factura-proveedor") || null,
    proveedor_nif: texto("factura-proveedor-nif") || null,
    numero_factura: texto("factura-numero") || null,
    base_imponible: numero("factura-base"),
    cuota_iva: numero("factura-iva"),
    tipo_iva_pct: numero("factura-tipo-iva"),
    total: numero("factura-total"),
    // Las notas tampoco se preguntan en esta pantalla, y son un dato del agricultor: viajan tal cual.
    notas: lectura.notas || null,
    leida_por: lectura.como_se_leyo || "a mano",
    lineas,
  };
}

async function guardarFactura() {
  const f = (clave) => t(`facturas.${clave}`, "");
  const facturas = estadoDeLasFacturas();
  const datos = recogeLaInterpretacion();
  if (!datos.lineas.length) {
    facturas.error = f("lineas_pista");
    return pantallaInterpretacionDeLaFactura();
  }
  // **Lo que se está haciendo se decide aquí** (ronda 93): si esta pantalla se abrió para corregir una
  // factura que ya está guardada, esto es un `PUT` a esa factura; si no, es un alta. Es la diferencia
  // entre arreglar la factura que ya existe (con su mismo identificador, que es lo que hace que lo que
  // se apuntó contra ella siga apuntando bien) y meter una segunda factura que contaría dos veces.
  const corrigiendo = facturas.corrigiendo;
  facturas.error = "";
  facturas.guardando = true;
  pantallaInterpretacionDeLaFactura();
  let respuesta;
  try {
    if (corrigiendo) {
      // Al corregir, los datos van en **JSON** y no en un formulario: la corrección no manda fichero
      // (el justificante no se toca, y para cambiarlo está su propia puerta), y el camino de `PUT` del
      // servidor recibe un cuerpo JSON. Mandarlo como formulario daría un 422 sin explicar nada.
      respuesta = await fetch(`/api/facturas/${corrigiendo.id}`, {
        method: "PUT",
        headers: { Authorization: `Bearer ${estado.token}`, "Content-Type": "application/json" },
        body: JSON.stringify(datos),
      });
    } else {
      const cuerpo = new FormData();
      cuerpo.append("datos", JSON.stringify(datos));
      // El fichero va con la factura: es el justificante, y es lo que hay que poder enseñar.
      if (facturas.fichero) cuerpo.append("fichero", facturas.fichero);
      respuesta = await fetch("/api/facturas", {
        method: "POST",
        headers: { Authorization: `Bearer ${estado.token}` },
        body: cuerpo,
      });
    }
    const detalle = await respuesta.json().catch(() => null);
    if (!respuesta.ok) throw new Error((detalle && detalle.detail) || f("no_se_pudo"));
    if (corrigiendo) {
      // La pantalla de «Factura guardada» **no vale aquí**: dice «ya cuenta para saber cuánto producto
      // tienes comprado», y al corregir no se ha añadido nada; se ha arreglado lo que había. Se dice lo
      // que ha pasado, que es lo mismo que se dice al corregir un apunte o una tierra.
      facturas.corrigiendo = null;
      facturas.interpretacion = null;
      facturas.guardando = false;
      await cargarDatos().catch(() => {});
      return pantallaFacturaCorregida();
    }
    facturas.guardada = detalle;
    facturas.interpretacion = null;
    facturas.fichero = null;
    await cargarDatos().catch(() => {});
  } catch (error) {
    facturas.error = error.message || f("no_se_pudo");
  }
  facturas.guardando = false;
  pantallaFacturas();
}

/**
 * La pantalla que sale después de corregir una factura.
 *
 * Se dice **«corregido»** y no «guardado»: al corregir no se ha añadido ninguna factura, y decirle
 * «Factura guardada» a quien acaba de arreglar una le haría pensar que tiene dos (y volvería a mirar la
 * lista para comprobar cuál sobra). Debajo se dice lo que queda en el cuaderno —lo de antes, apuntado—,
 * que es la mitad tranquilizadora de corregir en un cuaderno de campo. Los dos botones son la lista de
 * facturas y la vuelta al inicio.
 */
function pantallaFacturaCorregida() {
  const cb = (clave) => t(`corregir.${clave}`, "");
  montar(() =>
    confirmacion({
      titulo: cb("hecho_titulo"),
      pista: cb("hecho"),
      ayuda: { titulo: cb("rastro_titulo"), texto: cb("borrar_queda_rastro") },
      acciones: [
        {
          etiqueta: t("facturas.titulo", ""),
          accion: "facturas-abrir",
          clase: "boton-principal",
          sencillo: true,
        },
        { etiqueta: accion("volver"), accion: "ir-inicio", clase: "boton-claro", sencillo: true },
      ],
    }),
  );
}

/**
 * Qué hay sembrado en cada parcela este año, y qué hubo los años anteriores.
 *
 * Son las pestañas «Características DGC» e «Historial Cultivos» de la app oficial. Y esto
 * existía a medias de la peor manera posible: el cuaderno **ya le decía al agricultor** «a El
 * Prado le falta decir qué cultivo tiene este año», y no había ninguna forma de contestarle.
 * `ParcelaCultivo` estaba en la base de datos desde las primeras rondas, con su endpoint, y no
 * lo usaba ninguna pantalla.
 *
 * Lo que se arregla con esto:
 *
 * 1. El agricultor puede decirlo (y cambiarlo, y ver lo de otros años).
 * 2. El «Cultivo» de cada tratamiento y cada labor **se rellena solo**, que es lo que la app
 *    oficial llama un campo calculado: ya lo has dicho una vez, no hay que repetirlo.
 * 3. El aviso de «en esa fecha no había cultivo en esta parcela» puede funcionar, porque ya hay
 *    dato del que tirar.
 */
function pantallaCultivos() {
  const c = (clave) => t(`cultivos.${clave}`, "");
  const datos = estado.cultivos || {};
  const parcelas = datos.parcelas || [];

  // Las tierras se preparan aquí: los datos y cómo se enseña cada cosa son cosa de `app.js`.
  const preparadas = parcelas.map((parcela) => {
    const actual = parcela.actual;
    const filas = [];
    if (actual) {
      filas.push({
        etiqueta: c("tiene"),
        valor: `${actual.especie}${actual.variedad ? ` · ${actual.variedad}` : ""}`,
      });
      if (actual.fecha_inicio) filas.push({ etiqueta: c("cuando"), valor: formateaFecha(actual.fecha_inicio) });
      if (actual.fecha_fin) filas.push({ etiqueta: c("hasta"), valor: formateaFecha(actual.fecha_fin) });
    }
    return {
      parcela_id: parcela.parcela_id,
      alias: parcela.alias,
      // Si no se sabe la superficie, **no se enseña un cero ni una unidad suelta**: se dice solo lo que sí
      // se sabe (el sistema). `formateaNumero(null)` devuelve vacío, así que sin esta comprobación la línea
      // salía como « ha · Secano», que es un hueco disfrazado de dato (A14, 05/10/2026).
      detalle: [
        parcela.superficie_ha === null || parcela.superficie_ha === undefined
          ? ""
          : `${formateaNumero(parcela.superficie_ha, 2)} ${t("rotulos.hectareas_corto", "")}`,
        parcela.sistema ? etiquetaDeValor("sistemas", parcela.sistema) : "",
      ]
        .filter(Boolean)
        .join(" · "),
      tiene_cultivo: Boolean(actual),
      // La etiqueta de estado de cada tierra (diseño de Stitch de esta pantalla, ronda 90): con más de
      // cincuenta tierras, lo que se viene a buscar aquí es **a cuáles les falta decirlo**, y eso no se
      // saca leyendo la ficha de cada una. Las que están al día van en verde y las que no, en ámbar.
      estado: {
        texto: c(actual ? "al_dia" : "falta_rellenar"),
        tipo: actual ? "bien" : "falta",
      },
      filas,
      anteriores: (parcela.anteriores || [])
        .slice(0, 4)
        .map((cultivo) => `${cultivo.anio || "?"}: ${cultivo.especie}`)
        .join(" · "),
      repite: Boolean(parcela.repite_el_del_ano_pasado),
      // **Lo mismo, en crudo, para la tabla del ordenador** (30/09/2026): la misma lista que las tarjetas,
      // mirada de otra forma. Es la tabla que faltaba: con 64 tierras, en el ordenador se veían tres
      // tarjetas por pantalla.
      // **El hueco se queda hueco** (A14, 05/10/2026). Aquí ponía `Number(parcela.superficie_ha) || 0`, que
      // es exactamente lo que A7 arregló en la tabla de tierras (`app.js`: `parcela.superficie_ha ===
      // undefined ? null : …`) y que en esta pantalla se había quedado sin arreglar: la tierra sin
      // hectáreas salía con un **cero** en la columna, y `formateaNumero(null)` ya sabe pintar el vacío.
      superficie_ha: parcela.superficie_ha === undefined ? null : parcela.superficie_ha,
      especie: actual ? actual.especie || "" : "",
      variedad: actual ? actual.variedad || "" : "",
      // El botón de la fila: el mismo que el de la tarjeta, con su etiqueta corta cuando ya hay cultivo.
      acciones: [
        {
          etiqueta: actual ? t("tabla.cambiarlo", "") : t("tabla.decirlo", ""),
          accion: "cultivo-decir",
          datos: { id: parcela.parcela_id },
          clase: "boton-claro",
        },
      ],
    };
  });

  // **El filtro de las que faltan** (30/09/2026). El aviso de arriba dice a cuántas les falta decir qué
  // tienen; con 64 tierras, lo que hace falta es poder ver **esas y solo esas**, para irlas diciendo una
  // detrás de otra sin buscarlas en la lista. Se filtra la lista entera (tarjetas y tabla): el filtro es de la
  // pantalla, no de una de las dos formas.
  const filtrando = Boolean(estado.soloLasQueFaltan);
  const mostradas = filtrando ? preparadas.filter((parcela) => !parcela.tiene_cultivo) : preparadas;
  const cuantasFaltan = preparadas.filter((parcela) => !parcela.tiene_cultivo).length;

  // Esta pantalla ya está en React (ver `docs/REACT.md`). Se monta con `montar()`, que pide el
  // elemento dentro de un `try`: si los ficheros de React de `vendor/` no han llegado, enseña el
  // aviso de emergencia en vez de dejar la pantalla en blanco.
  montar(() =>
    pantallaDeCultivos({
      textos: {
        cultivos: t("cultivos", {}),
        maestros: t("maestros", {}),
        acciones: t("acciones", {}),
      },
      parcelas: mostradas,
      // **La tabla, para el ordenador**: la misma lista que las tarjetas, con sus columnas ordenables.
      tabla: tablaDeLosCultivos(mostradas, filtrando, preparadas.length),
      // El aviso de arriba: cuántas faltan y **el botón que enseña solo esas** (o el de volver a verlas
      // todas, que tiene que estar siempre a mano: un filtro del que no se puede salir es una lista de
      // tierras que ha desaparecido).
      aviso: {
        texto: datos.resumen || "",
        boton:
          cuantasFaltan && !filtrando
            ? {
                etiqueta: c("ver_las_que_faltan"),
                accion: "cultivo-solo-las-que-faltan",
                clase: "boton-claro",
              }
            : filtrando
              ? {
                  etiqueta: c("verlas_todas"),
                  accion: "cultivo-ver-todas",
                  clase: "boton-claro",
                }
              : null,
      },
      error: estado.errorCultivos,
    }),
  );
}

/**
 * La tabla de lo que hay sembrado este año, para el ordenador (30/09/2026).
 *
 * POR QUÉ. Es la lista más larga del programa después de las tierras (una fila por tierra) y se había
 * quedado sin tabla: en el ordenador se veían **tres tarjetas enormes** por pantalla. Se vio en la revisión
 * de la interfaz del 30/09/2026, mirando la aplicación con las 64 tierras de verdad.
 *
 * Las columnas son las que hacen falta para contestar a la pregunta con la que se entra aquí —**¿a cuáles
 * les falta decir qué tienen?**—: la tierra, sus hectáreas, lo que hay este año, lo de años anteriores y,
 * en su etiqueta, si está al día o le falta. El pie dice cuántas hay y cuántas están dichas.
 */
function tablaDeLosCultivos(parcelas, filtrando = false, total = 0) {
  const col = (clave) => t(`tabla.${clave}`, "");
  const c = (clave) => t(`cultivos.${clave}`, "");
  const ordenadas = ordenarFichas(parcelas, elOrdenDeLaTabla("cultivos"), "parcela_id");
  const columnas = columnasDeLaTabla("cultivos", [
    { texto: col("tierra"), campo: "alias" },
    { texto: col("hectareas"), campo: "superficie_ha", clase: "tabla-numero" },
    { texto: col("este_ano"), campo: "especie" },
    // **La alerta de rotación, en su propia columna** (30/09/2026): así lo pone el diseño de escritorio de
    // esta pantalla, y tiene razón — con 64 tierras el aviso se busca recorriendo la lista de arriba abajo, y
    // como letra pequeña debajo del cultivo no se ve.
    { texto: col("rotacion") },
    { texto: col("otros_anos"), campo: "anteriores" },
    { texto: col("estado") },
    { texto: col("acciones") },
  ]);

  const filas = ordenadas.map((parcela) => ({
    celdas: [
      { texto: parcela.alias },
      {
        texto: `${formateaNumero(parcela.superficie_ha, 2)} ${t("rotulos.hectareas_corto", "")}`,
        clase: "tabla-numero",
      },
      {
        texto: parcela.especie ? [parcela.especie, parcela.variedad].filter(Boolean).join(" · ") : "",
      },
      {
        texto: "",
        // El aviso de que repite el cultivo del año pasado, con palabras y en ámbar: el color solo no informa.
        // La frase entera (que explica por qué importa) se queda en la tarjeta del móvil.
        estado: parcela.repite ? { texto: col("repite_el_ano_pasado"), tipo: "mirar" } : null,
      },
      { texto: parcela.anteriores },
      {
        texto: "",
        // El estado va **con palabras** además del color: «Al día» o «Falta rellenar», que es lo que se
        // viene a buscar en esta pantalla.
        estado: parcela.estado,
      },
    ],
    acciones: parcela.acciones || [],
  }));

  const dichas = ordenadas.filter((parcela) => parcela.tiene_cultivo).length;
  // Con el filtro puesto, el pie dice cuántas se están viendo de cuántas: un filtro sin decirlo deja al
  // agricultor creyendo que ha perdido tierras (lo mismo que hace la tabla de tierras con su buscador).
  const resumen = filtrando
    ? rellena(col("resumen_cultivos_filtrado"), { cuantas: ordenadas.length, total })
    : [
        resumenDeLaTabla("resumen_cultivos", ordenadas.length, {}),
        rellena(conCuenta(t("tabla", {}), "resumen_cultivos_dichas", dichas), {}),
      ].join(" · ");

  return {
    clave: "cultivos",
    etiqueta: col("cultivos_etiqueta"),
    columnas,
    filas,
    resumen,
  };
}

/**
 * El formulario para decir qué hay sembrado en una parcela.
 *
 * `escrito` son los valores que el agricultor ya había teclado. Se pasan cuando la pantalla se
 * vuelve a pintar por un aviso, para no borrarle lo que había escrito: perder lo tecleado es la
 * forma más rápida de que alguien abandone un formulario.
 */
/**
 * «Qué hay sembrado en esta tierra»: el formulario, ya en React (ver `docs/REACT.md`).
 *
 * `escrito` son los valores que el agricultor ya había teclado. Se pasan cuando la pantalla se vuelve
 * a pintar por un aviso del servidor, **para no borrarle lo que había escrito**: perder lo tecleado es
 * la forma más rápida de que alguien abandone un formulario. Los cinco campos conservan su `id` y los
 * lee `guardarCultivo()`, aquí debajo.
 */
function pantallaDecirCultivo(parcelaId, escrito = {}) {
  const datos = estado.cultivos || {};
  const parcela = (datos.parcelas || []).find((p) => String(p.parcela_id) === String(parcelaId));
  if (!parcela) {
    pantallaCultivos();
    return;
  }
  estado.cultivoParcela = parcelaId;
  const actual = parcela.actual || {};
  // El sistema que sale elegido: el que acaba de elegir, y si no, el que ya estaba declarado en el
  // cultivo o en la tierra. **Y si no lo dice nadie, ninguno** (A10): aquí ponía `|| "secano"`, así que
  // el desplegable salía con «Secano» marcado y guardar sin tocarlo declaraba de secano la tierra.
  const sistema = escrito.sistema !== undefined ? escrito.sistema : actual.sistema || parcela.sistema || null;
  // Lo que se enseña: lo que acaba de escribir, y si no, lo que ya estaba declarado.
  const valor = (campo, porDefecto = "") =>
    escrito[campo] !== undefined ? escrito[campo] : porDefecto;

  montar(() =>
    pantallaDeDecirCultivo({
      textos: {
        cultivos: t("cultivos", {}),
        acciones: t("acciones", {}),
        // El rótulo del botón de guardar cuando se está cambiando lo que ya estaba dicho
        // («GUARDAR LOS CAMBIOS»): viene de `corregir`, que es donde vive esa frase en toda la
        // aplicación, en vez de escribirla otra vez aquí.
        corregir: t("corregir", {}),
      },
      parcela: {
        id: parcela.parcela_id,
        detalle: `${parcela.alias} · ${formateaNumero(parcela.superficie_ha, 2)} ${t(
          "rotulos.hectareas_corto",
          "",
        )}`,
      },
      valores: {
        especie: valor("especie", actual.especie || ""),
        variedad: valor("variedad", actual.variedad || ""),
        desde: valor("desde", actual.fecha_inicio || ""),
        hasta: valor("hasta", actual.fecha_fin || ""),
      },
      sistemas: (datos.sistemas || []).map((opcion) => ({
        valor: opcion.valor,
        texto: opcion.texto,
        // Tres respuestas y la de «no lo sé» marcada cuando no se sabe (A10). El valor de esa opción es
        // `"nulo"`, que `valorDeEleccion` convierte en `null` al guardar.
        elegido: opcion.valor === "nulo" ? !sistema : opcion.valor === sistema,
      })),
      // **Si esta tierra ya tiene dicho qué hay sembrado este año** (ronda 93): entonces esta pantalla no
      // está diciéndolo, está **cambiándolo**, y eso cambia la etiqueta de arriba, el rótulo del botón de
      // guardar y el botón de quitar. El dato lo dice el servidor (`actual`), no se adivina.
      ya_dicho: Boolean(parcela.actual),
      error: estado.errorCultivos || "",
    }),
  );
}
async function guardarCultivo(parcelaId) {
  const c = (clave) => t(`cultivos.${clave}`, "");
  const escrito = {
    especie: valorDe("cultivo-especie").trim(),
    variedad: valorDe("cultivo-variedad").trim(),
    // `|| null`: sin sistema elegido se manda «no lo sé» y no una cadena vacía, que el servidor
    // guardaría como un sistema que no existe (A10).
    sistema: valorDeEleccion(valorDe("cultivo-sistema")) || null,
    desde: valorDe("cultivo-desde"),
    hasta: valorDe("cultivo-hasta"),
  };
  if (!escrito.especie) {
    estado.errorCultivos = c("la_especie_pista");
    pantallaDecirCultivo(parcelaId, escrito);
    return;
  }
  // Si esta tierra ya tenía dicho qué hay sembrado este año, esto **no es un alta: es un cambio**, y el
  // final tiene que decirlo así. Se mira antes de guardar (después puede que ya no esté en la lista).
  const estabaDicho = Boolean(
    ((estado.cultivos || {}).parcelas || []).find(
      (p) => String(p.parcela_id) === String(parcelaId),
    )?.actual,
  );
  try {
    await apiJson(`/api/parcelas/${parcelaId}/cultivos`, {
      // **POST y no PUT, y es a propósito**: el servidor corrige en el sitio cuando esa tierra ya tiene
      // cultivo declarado ese año (`asignar_cultivo` lo dice: «una parcela tiene un cultivo por campaña»),
      // así que una sola puerta sirve para decir y para cambiar. Aquí **no se crea un segundo cultivo**.
      method: "POST",
      body: JSON.stringify({
        campana_id: (estado.cultivos || {}).campana_id,
        especie: escrito.especie,
        variedad: escrito.variedad || null,
        sistema: escrito.sistema,
        fecha_inicio: escrito.desde || null,
        fecha_fin: escrito.hasta || null,
      }),
    });
  } catch (error) {
    estado.errorCultivos = error.message;
    pantallaDecirCultivo(parcelaId, escrito);
    return;
  }
  estado.errorCultivos = c("guardado");
  await cargarDatos().catch(() => {});
  if (estabaDicho) {
    // **«Corregido» y no «Apuntado»**: decirle «apuntado» a quien acaba de cambiar lo que ya había dicho
    // le haría pensar que tiene dos cultivos en la misma tierra (y el cuaderno solo admite uno por año).
    pantallaCosaCorregida("cultivos", t("cultivos.titulo", ""));
    return;
  }
  pantallaCultivos();
}

/**
 * QUITAR EL CULTIVO DE ESTE AÑO: primero se pregunta, y la pregunta lleva lo que va a desaparecer.
 *
 * POR QUÉ EXISTE ESTA PANTALLA. El camino está en el servidor desde la ronda 92
 * (`DELETE /api/parcelas/{id}/cultivos/{campana_id}`) y **ninguna pantalla lo pedía**: al agricultor que
 * se equivocaba de tierra al decir el cultivo solo le quedaba escribir otro encima, que es dejar un dato
 * falso en el cuaderno. Quitar no es lo mismo que cambiar: la tierra vuelve a salir como una a la que
 * **le falta decirlo**, que es la verdad cuando está en barbecho o cuando el cultivo era de otra tierra.
 *
 * Se pregunta antes por el mismo motivo que al borrar un apunte: es la única acción de esta pantalla que
 * quita algo, y un toque de más pasa (se toca con guantes y con sol). Y la pregunta ofrece **la otra
 * salida**, que casi siempre es la buena: cambiar el cultivo en vez de quitarlo.
 */
function preguntarSiQuitarElCultivo(parcelaId) {
  const parcela = ((estado.cultivos || {}).parcelas || []).find(
    (p) => String(p.parcela_id) === String(parcelaId),
  );
  if (!parcela || !parcela.actual) {
    // Ya no tiene nada dicho (o la lista es vieja): se recarga y se vuelve a la lista, que es donde se ve
    // de verdad en qué estado está cada tierra. Preguntar por quitar algo que ya no está no tiene sentido.
    pantallaCultivos();
    return;
  }
  const cb = (clave) => t(`corregir.${clave}`, "");
  const c = (clave) => t(`cultivos.${clave}`, "");
  const actual = parcela.actual;
  const cuando =
    actual.fecha_inicio || actual.fecha_fin
      ? `${actual.fecha_inicio ? formateaFecha(actual.fecha_inicio) : "?"} — ${
          actual.fecha_fin ? formateaFecha(actual.fecha_fin) : "?"
        }`
      : "";

  montar(() =>
    confirmacion({
      pregunta: cb("pregunta_borrar"),
      pista: cb("borrar_pista"),
      contenido: resumenDelApunte({
        titulo: cb("lo_que_desaparece"),
        // **Pares, no objetos** (ver la nota de `preguntarSiBorrarAlgo`): con objetos, la pantalla se
        // queda en blanco en un navegador de verdad y las pruebas no lo ven.
        filas: [
          [c("la_especie"), actual.especie || ""],
          [t("corregir.que_es_tierra", ""), parcela.alias || ""],
          ...(actual.variedad ? [[c("variedad"), actual.variedad]] : []),
          ...(cuando ? [[c("desde_cuando"), cuando]] : []),
        ],
      }),
      avisos: [{ texto: c("quitar_pista") }, { texto: cb("borrar_queda_rastro") }],
      acciones: [
        {
          etiqueta: cb("boton_borrar_si"),
          accion: "cultivo-quitar-si",
          datos: { id: parcelaId },
          clase: "boton-peligro",
          sencillo: true,
        },
        {
          etiqueta: cb("boton_mejor_corregirlo"),
          accion: "cultivo-decir",
          datos: { id: parcelaId },
          clase: "boton-claro",
          sencillo: true,
        },
        { etiqueta: accion("volver"), accion: "cultivo-ver-todos", clase: "boton-claro", sencillo: true },
      ],
    }),
  );
}

/** El quitado, ya decidido: se manda al servidor y se dice qué ha pasado. */
async function quitarElCultivo(parcelaId) {
  const campanaId = (estado.cultivos || {}).campana_id;
  try {
    await apiJson(`/api/parcelas/${parcelaId}/cultivos/${campanaId}`, { method: "DELETE" });
  } catch (error) {
    estado.errorCultivos = error.message;
    pantallaCultivos();
    return;
  }
  estado.errorCultivos = "";
  await cargarDatos().catch(() => {});
  const c = (clave) => t(`cultivos.${clave}`, "");
  montar(() =>
    confirmacion({
      titulo: c("quitado_titulo"),
      pista: c("quitado"),
      ayuda: { titulo: t("corregir.rastro_titulo", ""), texto: t("corregir.borrar_queda_rastro", "") },
      acciones: [
        { etiqueta: c("titulo"), accion: "cultivo-ver-todos", clase: "boton-principal", sencillo: true },
        { etiqueta: accion("volver"), accion: "ir-inicio", clase: "boton-claro", sencillo: true },
      ],
    }),
  );
}

/**
 * Las unidades homogéneas de cultivo: parcelas que se llevan igual y se apuntan de una vez.
 *
 * **Esto faltaba igual que las otras dos veces**, y era el apartado «UHC» de la app oficial.
 * `GrupoParcelas` estaba en la base de datos con tres endpoints —listar, crear a mano y
 * «calcular» automático— y **ninguna pantalla los llamaba**: `grupo_id` no aparecía ni una vez
 * en todo el JavaScript. Así que el trabajo que ahorra esto no lo ahorraba nadie.
 *
 * Y lo que ahorra es lo que dice el documento oficial: *«son agrupaciones de las DGC de la
 * explotación que tienen un mismo cultivo y un mismo sistema de explotación. Tienen como fin
 * facilitar la cumplimentación del Cuaderno»*. Con seis parcelas de cebada, un tratamiento es
 * **un apunte**, no seis.
 */
function pantallaGrupos() {
  const g = (clave) => t(`grupos.${clave}`, "");
  const grupos = estado.grupos || [];
  const parcelas = estado.parcelas || [];
  const dichas = estado.cultivos || {};
  const faltanCultivos = (dichas.parcelas || []).filter((p) => p.falta_decirlo).length;

  // Cada grupo se prepara aquí: las cuentas y los nombres de sus parcelas son cosa de estos datos.
  const preparados = grupos.map((grupo) => {
    const suyas = (grupo.parcela_ids || [])
      .map((id) => parcelas.find((p) => p.id === id))
      .filter(Boolean);
    return {
      nombre: grupo.nombre,
      detalle:
        `${suyas.length} ${t("rotulos.parcelas_corto", "")} · ${formateaNumero(
          grupo.superficie_total_ha,
          2,
        )} ${t("rotulos.hectareas_corto", "")}` + (grupo.cultivo ? ` · ${grupo.cultivo}` : ""),
      parcelas: suyas.map((p) => p.alias).join(" · "),
      // Las tierras del grupo, una por una y **con sus hectáreas** (diseño de Stitch de esta pantalla, ronda
      // 90): antes eran una línea con los nombres separados por puntos, y con seis tierras no se sabía cuál
      // era cuál ni cuánto tenía cada una. Aquí se numeran (el número lo pone el CSS), así que el nombre y
      // las hectáreas son lo único que viene de los datos.
      tierras: suyas.map((p) => ({
        nombre: p.alias,
        hectareas: `${formateaNumero(p.superficie_ha, 2)} ${t("rotulos.hectareas_corto", "")}`,
      })),
      automatico: Boolean(grupo.creado_automaticamente),
      // Los dos botones del grupo (ronda 92): corregir su nombre y borrarlo.
      acciones: botonesDeCorregirYBorrar("grupo", grupo.id),
    };
  });

  // Esta pantalla ya está en React (ver `docs/REACT.md`). Se monta con `montar()`, que pide el
  // elemento dentro de un `try`: si los ficheros de React de `vendor/` no han llegado, enseña el
  // aviso de emergencia en vez de dejar la pantalla en blanco.
  montar(() =>
    pantallaDeGrupos({
      textos: {
        grupos: t("grupos", {}),
        cultivos: t("cultivos", {}),
        maestros: t("maestros", {}),
        acciones: t("acciones", {}),
      },
      grupos: preparados,
      faltanCultivos,
      error: estado.errorGrupos,
    }),
  );
}

async function calcularGrupos() {
  const g = (clave) => t(`grupos.${clave}`, "");
  try {
    const datos = await apiJson("/api/grupos/calcular", { method: "POST" });
    if (datos.grupos_creados > 0) {
      estado.errorGrupos = rellena(g("creados"), { cuantos: datos.grupos_creados });
    } else {
      // Un botón que no hace nada y no dice por qué es peor que no tenerlo. Se cuenta lo que
      // ha impedido juntarlas, que es lo que el agricultor puede arreglar.
      const no = datos.no_se_pudieron || {};
      const partes = [];
      if ((no.sin_cultivo || []).length) {
        partes.push(g("por_sin_cultivo"));
      }
      if ((no.sin_forma || []).length) {
        partes.push(g("por_sin_forma"));
      }
      if (partes.length === 0) {
        partes.push(g("no_hay_nada_que_juntar"));
      }
      estado.errorGrupos = partes.join(" ");
    }
  } catch (error) {
    estado.errorGrupos = error.message;
    pantallaGrupos();
    return;
  }
  await cargarDatos().catch(() => {});
  pantallaGrupos();
}

/**
 * El dibujo del trozo: la forma que trae el SIGPAC.
 *
 * El SIGPAC devuelve la forma de cada recinto desde la ronda 10 y hasta la 20 **no se veía en
 * ninguna parte**: se guardaba en la base de datos y ahí se quedaba. Ver la forma es lo que hace
 * que el agricultor reconozca su parcela de un vistazo, y es lo que le permite comprobar que la
 * que ha traído el programa es la suya y no la del vecino.
 *
 * **Si no hay forma, no se dibuja nada.** Una parcela apuntada a mano no tiene geometría, y un
 * cuadro inventado parecería su parcela. Lo que llega del servidor es la línea que se pinta
 * (`dibujo`), no el WKT: son unos cientos de caracteres en vez de un texto largo, que en el móvil
 * se nota.
 *
 * **Esto ya no se monta aquí.** La pantalla que lo enseñaba —«Mis cosas», la lista de parcelas— se
 * pasó a React en la ronda 32, y el dibujo vive ahora en `react/componentes.js`
 * (`DibujoDeLaParcela`), donde se dibuja con sus etiquetas de verdad en vez de metiendo un texto de
 * HTML dentro de otro. Se ha quitado de aquí para no tener dos versiones del mismo dibujo: lo único
 * que hace `app.js` es pasarle a la pantalla la línea que trae cada parcela (`dibujo`).
 */

/**
 * La pantalla que sale después de **corregir** algo que no es un apunte del cuaderno: un análisis, una
 * venta o un plan de abono.
 *
 * Los tres tienen su propia pantalla de «guardado» (`pantallaAnaliticaGuardado`, `pantallaVentaGuardada`,
 * `pantallaPlanGuardado`) y las tres dicen «se ha guardado…», que al corregir sería mentira: no se ha
 * añadido nada, se ha cambiado lo que había. Así que hay una sola pantalla para los tres, la misma que
 * sale al corregir un apunte o una tierra, y su primer botón lleva a ver lo que se acaba de arreglar.
 */
function pantallaCosaCorregida(irA, etiquetaVer) {
  const cb = (clave) => t(`corregir.${clave}`, "");
  montar(() =>
    confirmacion({
      titulo: cb("hecho_titulo"),
      pista: cb("hecho"),
      ayuda: { titulo: cb("rastro_titulo"), texto: cb("borrar_queda_rastro") },
      acciones: [
        {
          etiqueta: etiquetaVer,
          accion: "inicio",
          datos: { ir: irA },
          clase: "boton-principal",
          sencillo: true,
        },
        { etiqueta: accion("volver"), accion: "ir-inicio", clase: "boton-claro", sencillo: true },
      ],
    }),
  );
}

/**
 * «Los años de mi cuaderno»: la lista de los años, ya en React.
 *
 * POR QUÉ ES UNA PANTALLA NUEVA Y NO UN TROZO DE OTRA. Hasta la ronda 93 la campaña la creaba el programa
 * al darse de alta la cuenta y **no había ninguna pantalla que la enseñara**: el agricultor no podía
 * arreglar un año mal escrito ni empezar el año siguiente. Y de la campaña cuelga el año entero del
 * cuaderno, así que las dos cosas son de las que no se pueden dejar sin salida.
 *
 * Lo que se prepara aquí es lo que el componente no puede saber: el año ya escrito, sus fechas ya
 * formateadas, **si es el que se está llevando** (el más nuevo: `estado.campana`) y **cuánto tiene dentro
 * cada uno**, que es lo que explica por qué un año no se puede quitar. Ese número lo cuenta el servidor
 * (`cuantas_cosas`); si no lo ha contado (`null`), no se dice nada —ni un cero— y el botón de borrar se
 * deja a mano, que es lo honesto: el servidor contestará con la cuenta de verdad.
 */
function pantallaCampanas() {
  const c = (clave) => t(`campanas.${clave}`, "");
  const suyas = (estado.campanas || []).map((campana) => {
    const contadas = campana.cuantas_cosas;
    const sabido = contadas !== null && contadas !== undefined;
    const sePuedeQuitar = !sabido || contadas === 0;
    const acciones = botonesDeCorregirYBorrar("campana", campana.id);
    if (!sePuedeQuitar) {
      // **El botón se apaga, y al lado se dice por qué** (diseño de Stitch de esta pantalla): un año con
      // cosas dentro no se puede quitar, y ofrecer un botón que va a fallar sin decir nada hasta que se
      // pulse es la forma de que el agricultor crea que el programa está roto.
      for (const una of acciones) {
        if (una.accion === "cosa-borrar") una.deshabilitado = true;
      }
    }
    return {
      id: campana.id,
      anio: String(campana.anio || ""),
      // Los números en crudo, para la tabla del ordenador: la fecha sin escribir (para poder ordenar por
      // ella) y cuántos **apuntes** tiene dentro (para ordenar por lo lleno que está el año).
      anio_numero: Number(campana.anio) || 0,
      desde_iso: campana.fecha_inicio || "",
      hasta_iso: campana.fecha_fin || "",
      cuantas_cosas: sabido ? contadas : null,
      // **Los apuntes del cuaderno** (30/09/2026): lo que el agricultor cuenta. El total (`cuantas_cosas`)
      // sigue mandando en dos cosas: si el año se puede quitar o no, y nada más.
      apuntes: sabido && campana.apuntes !== null && campana.apuntes !== undefined
        ? Number(campana.apuntes) || 0
        : null,
      desde: campana.fecha_inicio ? formateaFecha(campana.fecha_inicio) : "",
      hasta: campana.fecha_fin ? formateaFecha(campana.fecha_fin) : "",
      es_la_que_llevo: Boolean(estado.campana) && estado.campana.id === campana.id,
      estado: campana.cerrada ? c("cerrado") : c("abierto"),
      cerrada: Boolean(campana.cerrada),
      dentro: sabido ? dentroDeUnAno(campana) : "",
      se_puede_quitar: sePuedeQuitar,
      acciones,
    };
  });

  montar(() =>
    pantallaDeCampanas({
      textos: { campanas: t("campanas", {}), acciones: t("acciones", {}), corregir: t("corregir", {}) },
      campanas: suyas,
      // **Y la tabla, para el ordenador** (30/09/2026): los años de un vistazo, con lo que tiene cada uno
      // dentro. Es la misma lista que las fichas, mirada de otra forma.
      tabla: tablaDeLosAnos(suyas),
      error: estado.errorCampanas || "",
    }),
  );
}

/**
 * Qué tiene dentro un año, **dicho por lo que es** (30/09/2026).
 *
 * POR QUÉ, CON EL FALLO QUE LO TRAJO. La pantalla de los años decía «Tiene 54 cosas apuntadas dentro» del
 * 2026 y «mi cuaderno», del mismo año, decía «0 apuntes en el cuaderno». Las dos eran verdad —las 54 eran
 * las tierras con su cultivo dicho, que también cuelgan del año— y el agricultor no podía entenderlo: parece
 * que una de las dos miente. Se vio en la revisión de la interfaz del 30/09/2026, mirando la aplicación con
 * sus 64 tierras de verdad.
 *
 * Así que aquí se junta, en este orden y en una sola línea: **los apuntes** (tratamientos, abonos y labores,
 * que es exactamente lo que cuenta el cuaderno), **las tierras con su cultivo dicho** y **las demás cosas**
 * (análisis, ventas, planes, facturas, papeles y la firma). Las frases y sus números los pone el servidor
 * (`textos.CAMPANAS`), y el total sigue siendo el que decide si el año se puede quitar.
 *
 * **Si el servidor no manda el desglose** (una respuesta vieja, o `null` porque no lo ha contado), se cae al
 * texto de siempre («Tiene N cosas apuntadas dentro»): nunca se enseña un cero que no se sabe.
 */
function dentroDeUnAno(campana) {
  const frases = t("campanas", {});
  const total = Number(campana.cuantas_cosas) || 0;
  if (!total) return t("campanas.vacio", "");
  const apuntes = campana.apuntes;
  if (apuntes === null || apuntes === undefined) {
    return conCuenta(frases, "dentro", total);
  }
  const partes = [conCuenta(frases, "apuntes", Number(apuntes) || 0)];
  const cultivos = Number(campana.tierras_con_cultivo) || 0;
  const otras = Number(campana.otras_cosas) || 0;
  if (cultivos) partes.push(conCuenta(frases, "cultivo_dicho", cultivos));
  if (otras) partes.push(conCuenta(frases, "otras_cosas", otras));
  return partes.join(" · ");
}

/**
 * La tabla de los años del cuaderno, para el ordenador.
 *
 * POR QUÉ. Un agricultor con tres o cuatro años quiere verlos **juntos**: cuál tiene más cosas dentro, cuál
 * está cerrado y cuáles se pueden quitar. En el móvil cada año va en su ficha (con su etiqueta y su aviso);
 * en el ordenador, la tabla los pone uno debajo de otro y se pueden ordenar por año o por lo llenos que
 * estén.
 */
function tablaDeLosAnos(campanas) {
  const col = (clave) => t(`tabla.${clave}`, "");
  const c = (clave) => t(`campanas.${clave}`, "");
  const ordenadas = ordenarFichas(campanas, elOrdenDeLaTabla("anos"), "id");
  const columnas = columnasDeLaTabla("anos", [
    { texto: col("ano"), campo: "anio_numero", clase: "tabla-numero" },
    { texto: col("empieza"), campo: "desde_iso", clase: "tabla-numero" },
    { texto: col("termina"), campo: "hasta_iso", clase: "tabla-numero" },
    // Se ordena por **los apuntes**, que es lo que enseña la celda (el total sigue mandando en si el año se
    // puede quitar, que no es una columna).
    { texto: col("dentro"), campo: "apuntes" },
    { texto: col("estado") },
    { texto: col("acciones") },
  ]);

  const filas = ordenadas.map((campana) => ({
    celdas: [
      { texto: campana.anio, clase: "tabla-numero" },
      { texto: campana.desde, clase: "tabla-numero" },
      { texto: campana.hasta, clase: "tabla-numero" },
      {
        texto: campana.dentro,
        // Si no se puede quitar, se dice **en la misma celda y antes de que lo intente**: es lo que explica
        // por qué su botón de borrar sale apagado. Va con la etiqueta **corta** («Hay cosas dentro»): la
        // frase entera ocupaba dos renglones dentro de la celda y ponía la fila alta (el mismo fallo que
        // «Falta decirlo» en las tierras y «Cuadra» en el almacén). Y la frase entera sigue leyéndose en la
        // ficha del año y en la pantalla que pregunta antes de borrar.
        estado: campana.se_puede_quitar ? null : { texto: c("no_se_puede_quitar_corto"), tipo: "mirar" },
      },
      {
        // El estado del año, con las dos palabras que se usan en su ficha. El año que se está llevando se
        // dice además en su etiqueta, como en la ficha (es lo que se viene a ver aquí).
        texto: campana.estado,
        estado: campana.es_la_que_llevo ? { texto: c("el_que_llevo"), tipo: "mirar" } : null,
      },
    ],
    acciones: campana.acciones || [],
  }));

  return {
    clave: "anos",
    etiqueta: col("anos_etiqueta"),
    columnas,
    filas,
    resumen: resumenDeLaTabla("resumen_anos", ordenadas.length, {}),
  };
}

/**
 * El año nuevo, con lo que el agricultor va a querer poner puesto.
 *
 * POR QUÉ SE RELLENA SOLO. Un año del cuaderno es un año, y el que va a empezar es **el siguiente al
 * último que tiene**: eso se sabe, así que se pone. Las fechas salen del año natural (1 de enero a 31 de
 * diciembre) y **se pueden cambiar**: muchas cosechas empiezan en septiembre, y la pista de la pantalla lo
 * dice. Rellenarlo no es inventar un dato: es lo que el agricultor iba a escribir, y lo cambia si no.
 */
function borradorDeUnaCampanaNueva() {
  const suyos = estado.campanas || [];
  const ultimo = suyos.reduce((mayor, una) => Math.max(mayor, Number(una.anio) || 0), 0);
  const anio = ultimo ? ultimo + 1 : Number((estado.campana && estado.campana.anio) || 0) || new Date().getFullYear();
  return {
    anio: String(anio),
    fecha_inicio: `${anio}-01-01`,
    fecha_fin: `${anio}-12-31`,
    // `bool:false` y no `false`: es como viaja un «sí o no» en la pantalla (ver `opcionesDe`).
    cerrada: "bool:false",
  };
}

/** Lo que se manda a la API con lo que hay en el asistente de un año. */
function cargaCampana() {
  const b = estado.asistente.borrador;
  return {
    anio: aNumero(b.anio),
    fecha_inicio: b.fecha_inicio || null,
    fecha_fin: b.fecha_fin || null,
    // El «sí o no» vuelve a ser verdadero o falso: es lo que espera la API.
    cerrada: valorDeEleccion(String(b.cerrada)) === true,
  };
}

/**
 * «Año guardado»: lo que sale después de empezar un año nuevo.
 *
 * Es propia y no la de los maestros porque el primer botón de aquella lleva a «MIS PARCELAS, PRODUCTOS Y
 * MÁQUINAS», y quien acaba de empezar un año lo que quiere es **ver sus años** (o volver al cuaderno).
 */
function pantallaCampanaGuardada() {
  const c = (clave) => t(`campanas.${clave}`, "");
  montar(() =>
    confirmacion({
      titulo: c("guardado"),
      pista: c("anadir_pista"),
      acciones: [
        { etiqueta: c("titulo"), accion: "inicio", datos: { ir: "campanas" }, clase: "boton-principal", sencillo: true },
        { etiqueta: accion("volver"), accion: "ir-inicio", clase: "boton-claro", sencillo: true },
      ],
    }),
  );
}

function pantallaMaestroGuardado(tipo, corregido = false) {
  // La misma pantalla sirve para «se ha guardado» y para «se ha corregido» (ronda 92): lo dice quien
  // llama, que es el único que sabe si lo que se acaba de hacer ha cambiado una fila o ha creado una.
  // Decirle «guardado» a quien acaba de corregir el nombre de una tierra le haría pensar que tiene dos.
  if (corregido) {
    const cb = (clave) => t(`corregir.${clave}`, "");
    montar(() =>
      confirmacion({
        titulo: cb("hecho_titulo"),
        pista: cb("hecho"),
        ayuda: { titulo: cb("rastro_titulo"), texto: cb("borrar_queda_rastro") },
        acciones: [
          { etiqueta: t("maestros.titulo", ""), accion: "mis-cosas", clase: "boton", sencillo: true },
          { etiqueta: accion("volver"), accion: "ir-inicio", clase: "boton-claro", sencillo: true },
        ],
      }),
    );
    return;
  }
  montar(() =>
    confirmacion({
      titulo: t("maestros.guardado", ""),
      ayuda: {
        titulo: t("maestros.donde_se_usa", ""),
        texto: t(`maestros.${tipo}_se_usa`, ""),
      },
      // Esta confirmación no lleva la frase de «se ha guardado»: el título ya lo dice, y los dos botones
      // llevan a ver lo que se ha dado de alta.
      acciones: [
        { etiqueta: t("maestros.titulo", ""), accion: "mis-cosas", clase: "boton", sencillo: true },
        { etiqueta: accion("volver"), accion: "ir-inicio", clase: "boton-claro", sencillo: true },
      ],
    }),
  );
}

// El aviso que desbloquea al agricultor nuevo (el que no tiene ninguna parcela) ya no se
// monta aquí: vive en `react/pantallas/inicio.js`, en `BloqueAntesDeEmpezar`, porque forma
// parte de la pantalla de inicio. Sigue saliendo solo cuando no hay parcelas, con el mismo
// texto del servidor y el mismo botón (`data-accion="anadir-maestro"`, `data-tipo="parcela"`).
// No se ha duplicado a propósito: dos versiones del mismo aviso acabarían diciendo cosas
// distintas.

// ------------------------------------------------------------------ el dictado

/**
 * «Dímelo con la voz»: la pantalla, ya en React (ver `docs/REACT.md`).
 *
 * Lo único que hay que preparar aquí es si este navegador sabe escuchar: eso lo sabe `window`, no
 * un componente puro. El campo de escribir sigue teniendo su `id` (`dictado-texto`) y lo lee
 * `entenderDictado()` de aquí abajo, que es quien manda el texto al servidor.
 */
function pantallaDictado() {
  const puedeHablar =
    typeof window !== "undefined" &&
    Boolean(window.SpeechRecognition || window.webkitSpeechRecognition);

  // `montar()` pide el elemento dentro de un `try`: si los ficheros de React de `vendor/` no han
  // llegado, enseña el aviso de emergencia en vez de dejar la pantalla en blanco.
  montar(() =>
    pantallaDeDictado({
      textos: { dictado: t("dictado", {}), acciones: t("acciones", {}) },
      escrito: estado.dictadoTexto || "",
      puedeHablar,
      error: estado.errorDictado || "",
    }),
  );
}

/**
 * Abre el dictado **por su dirección** (`#/dictado`).
 *
 * Es la pantalla a la que se va a dictar (tiene su botón en la de inicio), así que tiene dirección propia:
 * volver a ella la reconstruye entera.
 *
 * **`estado.dictadoTexto` no se vacía aquí, y es a propósito**: volver con «atrás» desde el borrador al
 * dictado —o recargar— tiene que dejar escrito lo que el agricultor ya había contado; borrarlo al ir hacia
 * atrás sería perder su trabajo. Quien empieza un dictado **nuevo** es el botón de la pantalla de inicio,
 * que sí lo vacía.
 */
function abrirElDictado() {
  estado.errorDictado = "";
  pantallaDictado();
}

/**
 * Abre la revisión de lo dictado **por su dirección** (`#/borrador`).
 *
 * **Si no hay nada dictado no se inventa una revisión**: se lleva al dictado, que es donde nace el borrador
 * y donde el agricultor puede hacer algo. El borrador que se está revisando vive en la memoria de la sesión
 * —el servidor devuelve una propuesta y **no guarda nada** (`AGENTS.md` §3.8)—, así que una dirección que
 * enseñara una revisión de nada estaría mintiendo con una pantalla en blanco.
 */
function abrirElBorrador() {
  if (!estado.borradorPendiente) return abrirElDictado();
  return pantallaBorrador(estado.borradorPendiente);
}

/**
 * Escucha con lo que trae el propio móvil.
 *
 * Decisión: se usa el reconocimiento de voz del navegador y no un servicio de pago.
 * Así no hay claves, no hay coste, no se manda la voz a ningún sitio que no sea el que
 * el agricultor ya usa, y donde no esté disponible **se puede escribir igual**: el
 * dictado es un atajo, nunca un requisito.
 */
function hablar() {
  const Reconocimiento = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!Reconocimiento) return;
  const area = document.getElementById("dictado-texto");

  let reconocimiento;
  try {
    reconocimiento = new Reconocimiento();
  } catch (error) {
    estado.errorDictado = t("dictado.no_se_puede", "");
    pantallaDictado();
    return;
  }
  reconocimiento.lang = "es-ES";
  reconocimiento.continuous = false;
  reconocimiento.interimResults = true;

  reconocimiento.onresult = (evento) => {
    let texto = "";
    for (const resultado of evento.results) texto += resultado[0].transcript;
    estado.dictadoTexto = texto;
    if (area) area.value = texto;
  };
  reconocimiento.onerror = () => {
    estado.errorDictado = t("dictado.no_se_puede", "");
    pantallaDictado();
  };

  try {
    reconocimiento.start();
  } catch (error) {
    estado.errorDictado = t("dictado.no_se_puede", "");
    pantallaDictado();
  }
}

async function entenderDictado() {
  const area = document.getElementById("dictado-texto");
  const texto = ((area && area.value) || estado.dictadoTexto || "").trim();
  estado.errorDictado = "";

  if (texto.length < 3) {
    estado.errorDictado = t("dictado.no_he_oido", "");
    pantallaDictado();
    return;
  }
  estado.dictadoTexto = texto;

  let borrador;
  try {
    borrador = await apiJson("/api/borradores/desde-texto", {
      method: "POST",
      body: JSON.stringify({ texto }),
    });
  } catch (error) {
    estado.errorDictado = error.message;
    pantallaDictado();
    return;
  }
  pantallaBorrador(borrador);
}

/**
 * La tarjeta de revisión: lo que se ha entendido, en pantalla editable.
 *
 * Esto es lo que en el documento se llama "Generative UI": la respuesta no es un texto
 * de chat que hay que leer y creerse, es el formulario a medio rellenar que el
 * agricultor revisa y confirma. Y lo que no se ha entendido se pregunta, en vez de
 * rellenarse con algo parecido.
 */
/**
 * La revisión de lo dictado, ya en React (ver `docs/REACT.md`).
 *
 * Lo que se prepara aquí y por qué: `estado.borradorPendiente` se guarda **antes** de pintar,
 * porque los botones de esta pantalla («apuntarlo» y «corregirlo a mano») abren el asistente con
 * lo que se ha entendido, y ese estado es lo que leen. Todo lo demás (el título, la introducción,
 * lo que falta y el aviso de que no se ha entendido nada) viene ya con el borrador, del servidor.
 */
function pantallaBorrador(borrador) {
  estado.borradorPendiente = borrador;

  // `montar()` pide el elemento dentro de un `try`: si los ficheros de React de `vendor/` no han
  // llegado, enseña el aviso de emergencia en vez de dejar la pantalla en blanco.
  montar(() =>
    pantallaDeBorrador({
      textos: { maestros: t("maestros", {}), dictado: t("dictado", {}) },
      borrador,
      // **Lo que ha dicho, tal cual** (diseño de Stitch de esta pantalla, ronda 90). Es lo que él contó
      // —dictado o escrito— y va arriba, para poder compararlo con lo que el programa ha entendido: si ha
      // oído mal una palabra, el agricultor es el único que puede darse cuenta. Vive en memoria desde que
      // se envió, así que no hay que pedirlo otra vez al servidor.
      dicho: estado.dictadoTexto || "",
    }),
  );
}

/** Abre el asistente de siempre, con lo que se ha entendido ya puesto. */
function abrirDesdeBorrador(irAlFinal) {
  const borrador = estado.borradorPendiente;
  if (!borrador) {
    pantallaInicio();
    return;
  }
  const pasos =
    borrador.tipo === "tratamiento"
      ? pasosTratamiento()
      : borrador.tipo === "fertilizacion"
        ? pasosAbonar()
        : pasosLabor(borrador.tipo);

  abrirAsistente(borrador.tipo, pasos);
  estado.asistente.borrador = { ...borrador.datos };
  if (irAlFinal) estado.asistente.indice = pasos.length - 1;
  pintarAsistente();
}

// ------------------------------------------------------------------ la firma

/**
 * «Firmar el cuaderno»: la pantalla, ya en React (ver `docs/REACT.md`).
 *
 * Se le pasan cuatro cosas y ninguna más: los textos, **cómo se llama el fichero** que hay que
 * descargar y firmar (el agricultor tiene que reconocerlo en su carpeta de descargas), el aviso de
 * que se acaba de firmar y el error. El campo del fichero sigue teniendo su `id`
 * (`firma-fichero`) y lo lee `subirFirma()`, aquí abajo.
 */
function pantallaFirmar() {
  const datos = estado.firmaEstado || {};

  // El estado de la firma, en su línea y con su aviso (diseño de Stitch de esta pantalla, ronda 90): la
  // pantalla solo enseñaba los tres pasos, y **el estado no se veía en ninguna parte** —ni que ya esté
  // firmado, ni que la firma se haya quedado vieja porque después se cambió algo—. Ese mensaje lo compone
  // el servidor (`/api/firmas/estado`), así que aquí solo se pasa.
  //
  // Y el aviso de que en esta instalación no se puede firmar (porque hace falta el certificado), que
  // tampoco se veía: el texto llevaba escrito desde siempre y no lo leía ninguna pantalla.
  const estadoDeLaFirma = datos.mensaje || "";
  const avisos = [datos.puede_firmar === false ? t("firma.no_puede_firmar", "") : ""].filter(Boolean);

  // `montar()` pide el elemento dentro de un `try`: si los ficheros de React de `vendor/` no han
  // llegado, enseña el aviso de emergencia en vez de dejar la pantalla en blanco.
  montar(() =>
    pantallaDeFirmar({
      textos: { firma: t("firma", {}), acciones: t("acciones", {}) },
      nombreDelFichero: datos.nombre_del_fichero || "",
      estado: estadoDeLaFirma,
      avisos,
      firmado: estado.firmaLista
        ? estado.firmaMensaje || t("firma.firmado_ok", "")
        : "",
      error: estado.errorFirma || "",
    }),
  );
}

async function descargarFicheroAFirmar() {
  try {
    // **El año que se está mirando** (06/10/2026). Sin esto había dos problemas a la vez: la pantalla
    // enseñaba el fichero y el estado de **la campaña más nueva** (la ruta, sin año, coge esa), y al
    // guardar la firma se apuntaba contra **el año que se estaba mirando** —así que la firma podía
    // quedar guardada contra un fichero que no era el que se había firmado—. Ahora las dos cosas piden
    // el mismo año.
    const respuesta = await api(conLaCampana("/api/firmas/fichero"));
    if (!respuesta.ok) throw new Error(mensaje("no_se_pudo"));
    const blob = await respuesta.blob();
    const nombre = (estado.firmaEstado && estado.firmaEstado.nombre_del_fichero) || "cuaderno.txt";
    const enlace = document.createElement("a");
    enlace.href = URL.createObjectURL(blob);
    enlace.download = nombre;
    document.body.appendChild(enlace);
    enlace.click();
    enlace.remove();
    estado.errorFirma = "";
  } catch (error) {
    estado.errorFirma = error.message;
    pantallaFirmar();
    return;
  }
  estado.errorFirma = t("firma.fichero_listo", "");
  pantallaFirmar();
}

/** Convierte el fichero que ha elegido el agricultor en el texto que espera la API. */
function aBase64(archivo) {
  return new Promise((resolver, rechazar) => {
    const lector = new FileReader();
    lector.onload = () => {
      const resultado = String(lector.result || "");
      // readAsDataURL devuelve "data:...;base64,XXXX": lo de delante no nos vale.
      resolver(resultado.includes(",") ? resultado.split(",")[1] : resultado);
    };
    lector.onerror = () => rechazar(new Error("no se ha podido leer el fichero"));
    lector.readAsDataURL(archivo);
  });
}

async function subirFirma() {
  estado.errorFirma = "";
  const datos = estado.firmaEstado || {};
  const entrada = document.getElementById("firma-fichero");
  const archivo = entrada && entrada.files ? entrada.files[0] : null;
  if (!archivo) {
    estado.errorFirma = t("firma.subir", "");
    pantallaFirmar();
    return;
  }

  let contenido;
  try {
    contenido = await aBase64(archivo);
  } catch (error) {
    estado.errorFirma = error.message;
    pantallaFirmar();
    return;
  }

  try {
    // Lo que devuelve el servidor trae **si la firma se ha podido comprobar**. Hay que
    // enseñarlo: si no se pudo comprobar, el agricultor tiene que saber que su cuaderno está
    // guardado pero que la firma no se ha podido mirar. Callarlo sería dejarle creer que está
    // todo comprobado cuando no lo está.
    const guardada = await apiJson("/api/firmas", {
      method: "POST",
      body: JSON.stringify({
        entidad: "cuaderno",
        campana_id: estado.campana ? estado.campana.id : null,
        huella: datos.huella,
        nombre_del_fichero: archivo.name,
        contenido,
      }),
    });
    estado.firmaMensaje = guardada.verificada_criptograficamente
      ? t("firma.firma_comprobada", "")
      : t("firma.firma_sin_comprobar", "").replace(
          "{motivo}",
          guardada.nota_verificacion || ""
        );
  } catch (error) {
    estado.errorFirma = error.message;
    pantallaFirmar();
    return;
  }

  estado.firmaLista = true;
  await cargarDatos().catch(() => {});
  pantallaFirmar();
}

// ------------------------------------------------------ el plan de abono

/**
 * «El plan de abono del año»: la pantalla, ya en React (ver `docs/REACT.md`).
 *
 * Lo que se prepara aquí es todo lo que hay que contar o formatear: el título del plan con su
 * cultivo, la línea de la parcela con su superficie, si se ha pasado con el fertilizante (que lo dice
 * el servidor con `se_ha_pasado`) y las tres filas de N, P y K con sus números ya escritos en
 * castellano. **La fila de un nutriente del que no hay dato no se pinta**: un «—» donde no hay nada
 * que decir es un hueco con un rótulo delante.
 */
function pantallaPlanes() {
  const p = (clave) => t(`plan.${clave}`, "");
  const planes = (estado.planes || []).map((plan) => {
    const parcela = estado.parcelas.find((x) => x.id === Number(plan.parcela_id));
    const filas = [
      ["N", plan.necesidad_n, plan.aplicado_n, plan.queda_n],
      ["P", plan.necesidad_p, plan.aplicado_p, plan.queda_p],
      ["K", plan.necesidad_k, plan.aplicado_k, plan.queda_k],
    ]
      .filter(([, previsto]) => previsto !== null && previsto !== undefined)
      .map(([nombre, previsto, aplicado, queda]) => ({
        nombre,
        // Lo previsto, lo aplicado y lo que queda, **cada uno con su nombre en la cabecera** (ronda 85).
        // El tercer número salía sin rótulo —la cabecera solo nombraba dos— y quien lo leía tenía que
        // adivinar de qué era. Cuando se ha pasado, en el tercer sitio no va un número sino la palabra
        // «Pasado», que ya existía en los textos y no la usaba nadie: un dato sin nombre no se puede leer,
        // y el aviso de arriba lo dice en rojo pero no sustituye al rótulo.
        texto: `${formateaNumero(previsto, 1)} · ${formateaNumero(aplicado, 1)} · ${
          queda < 0 ? p("tabla_pasado") : formateaNumero(queda, 1)
        }`,
      }));

    return {
      titulo: rellena(p("plan_de"), { cultivo: plan.cultivo }),
      detalle: [
        parcela ? parcela.alias : "",
        `${formateaNumero(plan.superficie_ha, 2)} ${t("rotulos.hectareas_corto", "")}`,
        p("kilos_por_hectarea"),
      ]
        .filter(Boolean)
        .join(" · "),
      // La cabecera de la tabla se arma aquí, y no en el componente, porque son textos del servidor
      // unidos: dentro de un componente, una frase compuesta es una frase escrita a mano. **Los tres
      // rótulos**, y no dos: en la tabla hay tres números (ronda 85).
      cabecera: [p("tabla_previsto"), p("tabla_aplicado"), p("tabla_queda")].join(" · "),
      precedente: plan.cultivo_precedente
        ? `${p("precedente")}: ${plan.cultivo_precedente}`
        : "",
      herramienta:
        plan.herramienta === null || plan.herramienta === undefined
          ? ""
          : `${p("herramienta_pregunta")}: ${plan.herramienta ? accion("si") : accion("no")}`,
      mensaje: plan.mensaje,
      se_ha_pasado: Boolean(plan.se_ha_pasado),
      // El veredicto del plan, en una etiqueta (diseño de Stitch de esta pantalla, ronda 90): «En regla» si
      // no se ha pasado de lo previsto y «Alerta: exceso» si sí. Es la primera pregunta que se hace al
      // abrir esta pantalla —«¿voy bien?»— y antes había que leerse la tabla entera para contestarla.
      estado: {
        texto: p(plan.se_ha_pasado ? "alerta_exceso" : "en_regla"),
        tipo: plan.se_ha_pasado ? "mirar" : "bien",
      },
      filas,
      // **Y sus dos botones** (ronda 93). De un plan se puede cambiar lo previsto —es una previsión, no
      // un apunte: si a mitad de campaña cambia el precio del abono, el plan se ajusta— y se puede
      // borrar si se hizo para la tierra que no era. Lo que no se toca nunca son los apuntes de abono.
      acciones: botonesDeCorregirYBorrar("plan", plan.id),
      analisis: plan.analisis
        ? {
            titulo: `${nombreDeAnalisis(plan.analisis)} · ${formateaFecha(
              plan.analisis.fecha_toma_muestra,
            )}`,
            numeros: (plan.analisis.parametros_con_nombre || []).map((n) => [n.etiqueta, n.texto]),
          }
        : null,
    };
  });

  // `montar()` pide el elemento dentro de un `try`: si los ficheros de React de `vendor/` no han
  // llegado, enseña el aviso de emergencia en vez de dejar la pantalla en blanco.
  montar(() =>
    pantallaDePlanes({
      textos: { plan: t("plan", {}), acciones: t("acciones", {}) },
      planes,
      // **Cuándo es obligatorio el plan**, que el servidor manda desde la ronda 60 y **no lo enseñaba
      // nadie**: `plan.obligatorio` existía en el vocabulario y el componente no lo leía. Es lo que
      // contesta a «¿esto me hace falta?», y va arriba, en su aviso, como en el diseño de Stitch.
      obligatorio: p("obligatorio"),
    }),
  );
}

/**
 * Elegir el análisis en el que se apoya el plan.
 *
 * Solo se ofrecen los de la parcela elegida, y solo los de tierra o de planta: los de
 * agua y cosecha no dicen nada de lo que hay que abonar. Es opcional, porque hay
 * agricultores que no tienen análisis y hacen el plan igual.
 */
/**
 * El análisis del que sale el plan de abono, ya en React: la lista de los análisis de esa tierra y, si
 * hay uno elegido, **sus números** debajo (que es lo que hace que el plan se pueda mirar antes de
 * guardarlo). Se montan dos piezas seguidas, con `html`.
 */
function montarAnalisisParaElPlan() {
  const b = estado.asistente.borrador;
  const deLaParcela = (estado.analiticas || []).filter(
    (a) =>
      Number(a.parcela_id) === Number(b.parcela_id) && (a.tipo === "suelo" || a.tipo === "cultivo"),
  );

  if (deLaParcela.length === 0) {
    return listaParaElegir({
      aviso: {
        texto: t("analitica.sin_analisis_de_la_parcela", ""),
        boton: {
          etiqueta: t("analitica.anadir", ""),
          accion: "analisis-nuevo",
          clase: "boton-claro",
          // Sencillo (sin icono y sin flecha), como estaba: este botón abre el alta de un análisis, no
          // saca de la pantalla.
          sencillo: true,
        },
      },
    });
  }

  const lista = listaParaElegir({
    bloques: [
      {
        botones: deLaParcela.map((a) => ({
          etiqueta: nombreDeAnalisis(a),
          pista: formateaFecha(a.fecha_toma_muestra),
          icono: "🧪",
          accion: "elegir",
          datos: { campo: "analitica_id", valor: a.id },
          clase: Number(b.analitica_id) === a.id ? "boton-elegido" : "boton-claro",
        })),
      },
    ],
  });

  const elegido = deLaParcela.find((a) => Number(a.id) === Number(b.analitica_id));
  if (!elegido) return lista;

  const numeros = filasDeLosNumerosDelAnalisis(elegido);
  return html`
    ${lista}
    ${
      numeros.length === 0
        ? listaParaElegir({ bloques: [{ pista: t("analitica.sin_numeros", "") }] })
        : resumenDelApunte({ filas: numeros })
    }
  `;
}


function pasosPlanAbonado() {
  const et = (clave) => t(`etiquetas.${clave}.pregunta`, "");
  const pi = (clave) => t(`etiquetas.${clave}.pista`, "");
  return [
    {
      titulo: et("comun.parcela_id"),
      pista: pi("comun.parcela_id"),
      montar: montarParcelas,
      recoger: exigeSitio,
    },
    {
      // El análisis del que sale el plan. Va justo después de la parcela porque es de la
      // parcela de donde tiene que ser: un análisis de tierra solo vale para su trozo.
      titulo: et("analitica.elegir_para_el_plan"),
      pista: pi("analitica.elegir_para_el_plan"),
      opcional: true,
      montar: montarAnalisisParaElPlan,
    },
    {
      titulo: et("plan.cultivo"),
      pista: pi("plan.cultivo"),
      montar: () => montarCamposMaestro(["plan.cultivo"]),
      recoger: recogeCamposMaestro(["plan.cultivo"]),
    },
    {
      // Los tres números del cultivo van en una sola pantalla porque son una sola idea:
      // lo que el cultivo se va a llevar. Y son opcionales.
      titulo: et("plan.necesidades"),
      pista: pi("plan.necesidades"),
      opcional: true,
      montar: () =>
        montarCamposMaestro(["plan.necesidad_n", "plan.necesidad_p", "plan.necesidad_k"]),
      recoger: recogeCamposMaestro([
        "plan.necesidad_n",
        "plan.necesidad_p",
        "plan.necesidad_k",
      ]),
    },
    {
      titulo: et("plan.produccion_esperada_kg_ha"),
      pista: pi("plan.produccion_esperada_kg_ha"),
      opcional: true,
      montar: () =>
        montarCamposMaestro(["plan.produccion_esperada_kg_ha", "plan.aportes_suelo_agua"]),
      recoger: recogeCamposMaestro([
        "plan.produccion_esperada_kg_ha",
        "plan.aportes_suelo_agua",
      ]),
    },
    {
      titulo: et("plan.notas"),
      pista: pi("plan.notas"),
      opcional: true,
      montar: () => montarCamposMaestro(["plan.notas"]),
      recoger: recogeCamposMaestro(["plan.notas"]),
    },
    {
      // Con qué se hizo el plan. El anexo II lo pide y no se preguntaba. Va al final y es
      // opcional: quien lo haya hecho de cabeza tiene que poder apuntarlo igual.
      titulo: et("plan.herramienta"),
      pista: pi("plan.herramienta"),
      opcional: true,
      montar: () => montarCamposMaestro(["plan.herramienta"]),
      recoger: recogeCamposMaestro(["plan.herramienta"]),
    },
    {
      titulo: t("etiquetas.tratamiento.resumen.pregunta", ""),
      pista: t("etiquetas.tratamiento.resumen.pista", ""),
      montar: () => resumenDelApunte({ filas: filasDelResumenPlan(), pista: t("plan.kilos_por_hectarea", "") }),
    },
  ];
}

/**
 * Las filas del resumen del plan de abono, ya preparadas.
 *
 * **Lo que NO hace esto:** pintar. Devuelve las filas —y solo las que tienen dato— para la pieza
 * `resumen_del_apunte.js`, que es la misma que usa el resumen de echar producto: al final los cuatro
 * resúmenes del asistente (tratamiento, plan, venta y análisis) son la misma cosa, una lista de
 * etiqueta y valor para repasar antes de apuntar.
 */
function filasDelResumenPlan() {
  const b = estado.asistente.borrador;
  const parcela = estado.parcelas.find((p) => p.id === Number(b.parcela_id));
  return [
    [t("etiquetas.comun.parcela_id.pregunta", ""), parcela ? parcela.alias : ""],
    [t("etiquetas.plan.cultivo.pregunta", ""), b.cultivo || ""],
    [
      t("etiquetas.comun.superficie_ha.pregunta", ""),
      formateaNumero(aNumero(b.superficie_ha) || (parcela ? parcela.superficie_ha : 0), 2),
    ],
    ["N", b.necesidad_n ? formateaNumero(aNumero(b.necesidad_n), 1) : ""],
    ["P", b.necesidad_p ? formateaNumero(aNumero(b.necesidad_p), 1) : ""],
    ["K", b.necesidad_k ? formateaNumero(aNumero(b.necesidad_k), 1) : ""],
  ].filter(([, valor]) => valor !== "");
}

function cargaPlan() {
  const b = estado.asistente.borrador;
  const parcela = estado.parcelas.find((p) => p.id === Number(b.parcela_id));
  return {
    campana_id: estado.campana.id,
    parcela_id: Number(b.parcela_id) || null,
    // El grupo y el reparto previsto (ronda 93): el asistente no los pregunta —el reparto lo arma el
    // plan al guardarlo— pero **si no se devolvieran, corregir los kilos previstos de un plan borraría
    // el reparto** («qué abono, cuánto y en qué momento»), que es la mitad del plan.
    grupo_id: b.grupo_id ?? null,
    detalle: Array.isArray(b.detalle) ? b.detalle : [],
    cultivo: (b.cultivo || "").trim(),
    superficie_ha: aNumero(b.superficie_ha) ?? (parcela ? parcela.superficie_ha : 0),
    produccion_esperada_kg_ha: aNumero(b.produccion_esperada_kg_ha),
    necesidad_n: aNumero(b.necesidad_n),
    necesidad_p: aNumero(b.necesidad_p),
    necesidad_k: aNumero(b.necesidad_k),
    aportes_suelo_agua: aNumero(b.aportes_suelo_agua),
    notas: b.notas || null,
    herramienta: b.herramienta === undefined ? null : b.herramienta,
    analitica_id: Number(b.analitica_id) || null,
  };
}

function pantallaPlanGuardado() {
  const p = (clave) => t(`plan.${clave}`, "");
  montar(() =>
    confirmacion({
      titulo: p("guardado_titulo"),
      pista: p("guardado"),
      ayuda: { titulo: p("se_usa"), texto: p("apunta_abonos") },
      acciones: accionesDeConfirmacion({
        etiqueta: p("ver"),
        accion: "plan-ver",
        clase: "boton",
        sencillo: true,
      }),
    }),
  );
}

// ------------------------------------------ lo que se vende

/**
 * Lo que sale de la finca.
 *
 * La app oficial lo tiene en «Otras Actividades: Cosecha Comercializada», y el contenido
 * mínimo del CUE la llama «Cosecha comercializada y/o venta directa». Aquí se llama «lo que
 * he vendido», que es como lo dice el agricultor, y la ruta es `/api/ventas` a propósito:
 * ya existe un `/api/cosecha` para «he cogido la cosecha», y dos cosas distintas llamadas
 * «cosecha» en el mismo programa serían una trampa.
 *
 * Lo que de verdad sirve de esta sección no es el apunte: es que **cuadre con lo cosechado**.
 * Lo normal cuando alguien vende más de lo que ha apuntado es que se haya olvidado de
 * apuntar la cosecha.
 */

/**
 * «Lo que he vendido»: la cosecha comercializada, una de las secciones que pide la Junta.
 *
 * Esta pantalla ya está en React (ver `docs/REACT.md`). Desde el T12 (03/10/2026) se prepara aquí **la
 * tabla** que pide el contrato (§4, S12) —sus columnas con el rótulo del servidor, cada celda ya escrita y
 * el pie del conjunto filtrado— y el componente solo la coloca. La antigua lista de filas con nombre
 * (`filasDeLaVenta`) se retiró con ella: era la otra forma de enseñar lo mismo, y dos listas que enseñan lo
 * mismo acaban diciendo cosas distintas.
 */
/**
 * Los kilos de las ventas de la finca, **sumando solo las que traen su peso** (A14, 05/10/2026).
 *
 * Devuelve la suma y cuántas ventas no lo traen, por el mismo motivo que en el pie de las tierras: una
 * venta sin kilos sumaba cero en silencio y el total de la pantalla parecía el de todas las entregas
 * cuando era el de las que traen su peso. Quien lo enseña tiene que poder decir cuántas faltan.
 */
function kilosDeLasVentas() {
  return sumandoLoQueSeSabe(estado.ventas, (venta) => venta.kilos);
}

function pantallaVentas() {
  const v = (clave) => t(`venta.${clave}`, "");
  const suya = estado.ventasTabla || { columnas: [], filas: [], totales: {} };
  // `estado.ordenDeLaTabla` se crea con el resto del estado y puede no estar en una sesión vieja: se
  // prueba antes de tocarlo, que es lo que hace que esta pantalla no se quede en blanco por eso.
  const orden = (estado.ordenDeLaTabla || {}).ventas || { campo: "", sentido: -1 };
  // **Una sola vez**, y no tres: la suma de kilos y las ventas que no lo traen se cuentan aquí y se usan
  // en el pie (A14, 05/10/2026).
  const losKilos = kilosDeLasVentas();

  // **La tabla se prepara aquí y el componente solo la coloca** (es la regla de la pieza `Tabla`): las
  // columnas con su rótulo —que viene del servidor—, cada fila con sus celdas ya escritas, y **una
  // celda menos que columnas**: la última («Acciones») la pinta la pieza, y escribir una celda de más
  // dejaría los botones en una columna sin cabecera.
  const tabla = {
    clave: "ventas",
    etiqueta: v("titulo"),
    columnas: (suya.columnas || []).map((columna) => ({
      texto: columna.texto,
      campo: columna.ordenable ? columna.clave : "",
      ordenada: orden.campo === columna.clave,
      descendente: orden.campo === columna.clave && orden.sentido < 0,
      orden: rellena(t("tabla.ordenar_por", ""), { columna: columna.texto }),
    })),
    filas: (suya.filas || []).map((fila) => ({
      // **La fila entera, tal y como la sirve el servidor**, y encima las celdas y las acciones: la tabla
      // del ordenador usa `celdas` (la pieza pinta la última columna, la de los botones) y **la tarjeta del
      // móvil usa los campos de la fila** (`cliente`, `cantidad`, `importe`…). Copiar solo las celdas dejaba
      // las tarjetas del móvil **vacías** —el nombre, la cantidad y todo el dinero en blanco— y eso no lo ve
      // ningún test de los de mentira: lo cazó la comprobación del navegador, que mira lo que se dibuja.
      ...fila,
      celdas: (suya.columnas || [])
        .slice(0, -1)
        .map((columna) => ({
          texto: fila[columna.clave] || "",
          // El estado va con su palabra y, cuando está vencida, con su explicación debajo: el color
          // nunca informa solo (guía de la interfaz, apartado 3).
          pista: columna.clave === "estado" && fila.estado_vencida ? v("estado_vencida_pista") : "",
          clase: columna.clave === "importe" || columna.clave === "cobrado" || columna.clave === "pendiente" ? "tabla-numero" : "",
        })),
      // **Las acciones de cada entrega**, que es lo que completa el recorrido de negocio: poner el
      // importe (A08), facturarla, cobrarla y apuntar una devolución o un ajuste. Y corregirla o
      // borrarla, que ya estaba.
      acciones: [
        !fila.importe_conocido
          ? { etiqueta: v("poner_importe"), accion: "venta-importe", datos: { id: fila.id }, sencillo: true }
          : null,
        fila.facturada
          ? null
          : { etiqueta: v("facturar_esto"), accion: "ventas-facturar", datos: { id: fila.id }, sencillo: true },
        { etiqueta: v("ajuste_poner"), accion: "venta-ajuste", datos: { id: fila.id }, sencillo: true },
        ...botonesDeCorregirYBorrar("venta", fila.id),
      ].filter(Boolean),
    })),
    resumen: suya.pie || "",
    // El pie va en los dos sitios a propósito y con **el mismo texto**: en la línea destacada de arriba
    // (que es lo que se lee de un vistazo) y en el pie de la tabla del ordenador, que es donde el contrato
    // lo pide («pie con filtrados/total»). Los dos salen del servidor, así que no pueden decir cosas
    // distintas.
    pie: suya.pie || "",
    avisos: suya.avisos || [],
    // El panel de al lado no se usa en esta pantalla: la tabla ocupa todo el ancho (ocho columnas más
    // los botones no caben al lado de una ficha).
    panel: null,
  };

  const cuantas = (suya.totales || {}).entregas || 0;
  montar(() =>
    pantallaDeVentas({
      textos: { venta: t("venta", {}), acciones: t("acciones", {}) },
      tabla,
      filtros: estado.filtroVentas || {},
      // El resumen de cuántas hay, con singular y plural del servidor: «1 entregas» se lee fatal y es
      // lo primero que hace desconfiar de un programa.
      resumen: cuantas
        ? [
            `${cuantas === 1 ? v("cuantas_una") : rellena(v("cuantas"), { cuantas })} · ` +
              `${formateaNumero(losKilos.suma, 0)} ${t("rotulos.kilos_corto", "")}`,
            // Y lo que no trae kilos, dicho aparte (A14, 05/10/2026): si no, el total de arriba parece el
            // de todas las entregas cuando es el de las que traen su peso.
            losKilos.sin_decir
              ? conCuenta(t("tabla", {}), "ventas_sin_kilos", losKilos.sin_decir)
              : "",
          ]
            .filter(Boolean)
            .join(" · ")
        : "",
      // Y lo que se acaba de hacer, si se viene de guardar algo del dinero: se dice una vez y se olvida.
      aviso: estado.avisoVentas || "",
    }),
  );
  estado.avisoVentas = "";
}

/**
 * Vuelve a pedir la tabla de lo que se vende con el filtro puesto y la repinta.
 *
 * **El filtrado y las sumas los hace el servidor**, y no es por comodidad: el contrato pide que el pie
 * sea «el agregado del conjunto filtrado» y no la suma de lo que se ve. Además, si el navegador sumara
 * importes, los sumaría en coma flotante, que es justo lo que este ticket no puede permitir.
 */
async function recargarLaTablaDeVentas() {
  const filtro = estado.filtroVentas || {};
  const partes = [];
  if (filtro.q) partes.push(`q=${encodeURIComponent(filtro.q)}`);
  if (filtro.solo) partes.push(`solo=${encodeURIComponent(filtro.solo)}`);
  if (filtro.orden) partes.push(`orden=${encodeURIComponent(filtro.orden)}`);
  if (filtro.sentido) partes.push(`sentido=${encodeURIComponent(filtro.sentido)}`);
  try {
    estado.ventasTabla = await apiJson(`/api/ventas/tabla${partes.length ? `?${partes.join("&")}` : ""}`);
    estado.errorVentas = "";
  } catch (fallo) {
    // Si el servidor no contesta, se dice y **no se vacía la tabla**: una tabla vacía cuando falló la
    // consulta es la mentira más cara de esta pantalla («¿y mis ventas?»).
    estado.errorVentas = mensajeDeFallo(fallo);
  }
  pantallaVentas();
}

/** Un entrega de la tabla, por su identificador, para las pantallas que trabajan sobre una. */
function unaEntregaDeLaTabla(id) {
  return ((estado.ventasTabla || {}).filas || []).find((fila) => Number(fila.id) === Number(id)) || null;
}

/**
 * El mensaje de un fallo, en palabras del agricultor.
 *
 * Lo que contesta el servidor viene ya escrito para él (`avisoDelServidor` lo saca de la respuesta), y
 * si no hay nada que sacar se dice lo de siempre. Existe para no repetir el `catch` en las nueve
 * pantallas del dinero y, sobre todo, para que **un fallo no deje la pantalla en blanco**: se dice y se
 * sigue.
 */
function mensajeDeFallo(fallo) {
  const suyo = fallo && fallo.message ? String(fallo.message) : "";
  return suyo && suyo !== "sin permiso" ? suyo : mensaje("no_se_pudo");
}

/**
 * Corrige una entrega ya apuntada (el `PUT` entero) y vuelve a la lista.
 *
 * **Se manda la entrega entera y no solo el importe**, y es a propósito: el `PUT` es el mismo para el
 * alta y para la corrección, así que lo que no viaja se queda en blanco en el servidor. Mandar solo el
 * importe le borraría a la entrega su producto, sus kilos y su albarán —que es el fallo que el propio
 * proyecto ya documentó al añadir los campos de la máquina (`AGENTS.md`, «un campo que existe y una
 * puerta que lo rechaza»)—.
 */
async function guardarVenta(datos, aviso) {
  const entrega = estado.entregaDelImporte;
  if (!entrega) return pantallaVentas();
  try {
    await apiJson(`/api/ventas/${entrega.id}`, {
      method: "PUT",
      body: JSON.stringify(datos),
    });
    estado.entregaDelImporte = null;
    estado.errorVentas = "";
    estado.avisoVentas = aviso || "";
    await cargarDatos().catch(() => {});
    return pantallaVentas();
  } catch (fallo) {
    estado.errorVentas = mensajeDeFallo(fallo);
    return pantallaImporteDeUnaEntrega(entrega.id);
  }
}

/** Cómo se llama una entrega en el encabezado de una pantalla: «Trigo blando · 10/07/2026». */
function tituloDeUnaEntrega(fila) {
  if (!fila) return "";
  return [fila.producto, fila.fecha, fila.cantidad].filter(Boolean).join(" · ");
}

/**
 * Poner el importe de una entrega (T12): la puerta del caso A08.
 *
 * **Pide la entrega entera al servidor** (`GET /api/ventas/{id}`) y no se fía de la fila de la tabla:
 * la fila solo trae lo que se enseña, y el `PUT` es el mismo para el alta y para la corrección —o sea
 * que hay que mandar **todos** los campos—, así que corregir el importe con media entrega le borraría
 * el producto, los kilos y el albarán. Es el fallo que este proyecto ya documentó dos veces.
 */
async function pantallaImporteDeUnaEntrega(id) {
  const v = (clave) => t(`venta.${clave}`, "");
  try {
    const entrega = await apiJson(`/api/ventas/${id}`);
    estado.entregaDelImporte = entrega;
    estado.errorVentas = "";
  } catch (fallo) {
    estado.errorVentas = mensajeDeFallo(fallo);
    return pantallaVentas();
  }
  const entrega = estado.entregaDelImporte;
  // Las fichas de cliente, para poder enlazar la entrega con una (revisión del T12). Se piden aquí, antes
  // de pintar: la pantalla se pinta **una sola vez** y con la lista, no primero sin ella.
  const contactos = await conLosContactos();
  montar(() =>
    pantallaDeImporte({
      textos: { venta: t("venta", {}), acciones: t("acciones", {}) },
      entrega: {
        id: entrega.id,
        // Lo que se enseña para saber de qué entrega se habla: su producto, su fecha y sus kilos. La fecha
        // se escribe aquí (formato de aquí) porque el `GET` la devuelve en su forma de dato.
        producto: entrega.producto,
        titulo: tituloDeUnaEntrega({
          producto: entrega.producto,
          fecha: formateaFecha(entrega.fecha),
          cantidad: entrega.texto_cantidad,
        }),
        texto_cantidad: entrega.texto_cantidad,
        texto_importe_total: entrega.texto_importe_total,
      },
      borrador: {
        importe: entrega.importe || "",
        precio_unitario: entrega.precio_unitario || "",
        vencimiento: entrega.vencimiento || "",
        // El enlace con la ficha, tal y como está: si ya estaba enlazada, se enseña elegido en vez de
        // aparecer en blanco y quitarse sola al guardar.
        contacto_id: entrega.contacto_id ? String(entrega.contacto_id) : "",
        cosecha_id: entrega.cosecha_id ? String(entrega.cosecha_id) : "",
      },
      // Las cosechas apuntadas, para poder decir de cuál salió esta entrega. La primera opción es «sin
      // decirla»: **no se elige la más parecida** por el agricultor.
      cosechas: opcionesDeCosechasApuntadas(),
      contactos,
      error: estado.errorVentas || "",
    }),
  );
}

/**
 * Guarda el importe de una entrega: es un `PUT` de la entrega entera, con lo que ya había.
 *
 * El importe y el precio viajan **como texto decimal** (contrato §2) y vacío es «no se sabe» y no
 * cero: es lo que hace que una entrega sin precio siga sin precio (A08) en vez de convertirse en un
 * ingreso de cero euros. Y la cantidad no es dinero: viaja como número, como siempre en este programa.
 */
async function guardarElImporteDeUnaEntrega() {
  const v = (clave) => t(`venta.${clave}`, "");
  const entrega = estado.entregaDelImporte;
  if (!entrega) return pantallaVentas();
  const leer = (id) => {
    const campo = document.getElementById(id);
    return campo ? String(campo.value || "").trim() : "";
  };
  const datos = {
    campana_id: entrega.campana_id,
    tipo: entrega.tipo,
    fecha: entrega.fecha,
    fecha_fin: entrega.fecha_fin || null,
    producto: entrega.producto,
    variedad: entrega.variedad || null,
    cantidad: entrega.cantidad,
    unidad: entrega.unidad,
    lote: entrega.lote || null,
    comprador: entrega.comprador || null,
    numero_albaran: entrega.numero_albaran || null,
    parcela_id: entrega.parcela_id,
    grupo_id: entrega.grupo_id,
    observaciones: entrega.observaciones,
    importe: leer("venta-importe") || null,
    precio_unitario: leer("venta-precio") || null,
    vencimiento: leer("venta-vencimiento") || null,
    // **Con qué ficha de cliente queda enlazada** (revisión del T12): la columna existía y ninguna
    // pantalla la preguntaba. Vacío es «sin enlazar», y entonces se manda `null` en vez de un cero, que
    // sería el identificador de una ficha que no existe.
    contacto_id: leer("venta-contacto") ? Number(leer("venta-contacto")) : null,
    // De qué cosecha salió (el «lote cosechado» del contrato). Vacío es «no lo he dicho», y entonces la
    // entrega se queda como estaba: **no se le pone la cosecha más parecida**.
    cosecha_id: leer("venta-cosecha") ? Number(leer("venta-cosecha")) : null,
  };
  return guardarVenta(datos, v("importe_guardado"));
}

/** Apuntar una devolución o un ajuste de peso, humedad o calidad (T12). */
async function pantallaAjusteDeUnaEntrega(id) {
  const v = (clave) => t(`venta.${clave}`, "");
  try {
    const entrega = await apiJson(`/api/ventas/${id}`);
    estado.entregaDelAjuste = entrega;
    estado.errorVentas = "";
  } catch (fallo) {
    estado.errorVentas = mensajeDeFallo(fallo);
    return pantallaVentas();
  }
  const entrega = estado.entregaDelAjuste;
  // El borrador sobrevive al repintado (es lo de siempre en este programa): lo que el agricultor ha
  // escrito no se pierde cuando la pantalla se vuelve a montar para enseñar un aviso.
  if (!estado.borradorAjuste || Number(estado.borradorAjuste.venta) !== Number(entrega.id)) {
    estado.borradorAjuste = {
      venta: entrega.id,
      tipo: "",
      origen: "",
      cantidad: "",
      importe: "",
      motivo: "",
      evidencia_descripcion: "",
      clave: claveDeReenvio("ajuste"),
    };
  }
  montar(() =>
    pantallaDeAjuste({
      textos: { venta: t("venta", {}), acciones: t("acciones", {}) },
      entrega: {
        id: entrega.id,
        producto: entrega.producto,
        // El importe **con los ajustes ya aplicados**: es contra lo que se está apuntando uno nuevo, y verlo
        // evita apuntar dos veces la misma devolución.
        texto_importe_total: entrega.texto_importe_total,
        titulo: tituloDeUnaEntrega({
          producto: entrega.producto,
          fecha: formateaFecha(entrega.fecha),
          cantidad: entrega.texto_cantidad,
        }),
      },
      borrador: estado.borradorAjuste,
      tipos: t("tipos_de_ajuste", []) || [],
      origenes: t("origenes_de_un_ajuste", []) || [],
      ajustes: entrega.ajustes || [],
      error: estado.errorVentas || "",
    }),
  );
}

/** Guarda el ajuste: primero recoge lo escrito, que es lo que el agricultor no quiere perder. */
async function guardarElAjuste() {
  const leer = (id) => {
    const campo = document.getElementById(id);
    return campo ? String(campo.value || "").trim() : "";
  };
  const borrador = estado.borradorAjuste;
  borrador.cantidad = leer("ajuste-cantidad");
  borrador.importe = leer("ajuste-importe");
  borrador.motivo = leer("ajuste-motivo");
  borrador.evidencia_descripcion = leer("ajuste-evidencia");
  try {
    await apiJson(`/api/ventas/${borrador.venta}/ajustes`, {
      method: "POST",
      body: JSON.stringify({
        tipo: borrador.tipo,
        origen: borrador.origen,
        cantidad: borrador.cantidad || null,
        importe: borrador.importe || null,
        motivo: borrador.motivo,
        evidencia_descripcion: borrador.evidencia_descripcion || null,
        // La clave de reenvío: si el móvil reintenta el mismo apunte (sin cobertura, un toque doble),
        // el servidor devuelve el que ya había en vez de apuntar dos devoluciones de lo mismo.
        clave_de_reenvio: borrador.clave,
      }),
    });
    estado.borradorAjuste = null;
    estado.entregaDelAjuste = null;
    estado.errorVentas = "";
    estado.avisoVentas = t("venta.ajuste_guardado", "");
    await cargarDatos().catch(() => {});
    return pantallaVentas();
  } catch (fallo) {
    estado.errorVentas = mensajeDeFallo(fallo);
    return pantallaAjusteDeUnaEntrega(borrador.venta);
  }
}

/** Quita un ajuste del importe, ya decidido, y no borra el papel que traía. */
async function quitarUnAjuste(idDeLaVenta, idDelAjuste) {
  const v = (clave) => t(`venta.${clave}`, "");
  try {
    await apiJson(`/api/ventas/${idDeLaVenta}/ajustes/${idDelAjuste}/anular`, {
      method: "POST",
      body: JSON.stringify({ motivo: v("ajuste_motivo_al_quitar") }),
    });
    estado.errorVentas = "";
    estado.avisoVentas = v("ajuste_anulado");
    await cargarDatos().catch(() => {});
    return pantallaAjusteDeUnaEntrega(idDeLaVenta);
  } catch (fallo) {
    estado.errorVentas = mensajeDeFallo(fallo);
    return pantallaAjusteDeUnaEntrega(idDeLaVenta);
  }
}

/** La lista de las facturas nuestras (T12). */
function pantallaFacturasEmitidas() {
  const f = (clave) => t(`factura_emitida.${clave}`, "");
  const facturas = estado.facturasEmitidas || [];
  const pendientes = facturas.filter((factura) => factura.pendiente && factura.pendiente !== "0.00");
  montar(() =>
    pantallaDeFacturasEmitidas({
      textos: { factura_emitida: t("factura_emitida", {}), venta: t("venta", {}), acciones: t("acciones", {}), cobro: t("cobro", {}) },
      facturas,
      resumen: facturas.length
        ? pendientes.length
          ? rellena(f(pendientes.length === 1 ? "cuantas_pendientes_una" : "cuantas_pendientes"), {
              cuantas: pendientes.length,
            })
          : f("cuantas_cobradas")
        : "",
      aviso: estado.avisoVentas || "",
      error: estado.errorVentas || "",
    }),
  );
  estado.avisoVentas = "";
}

/**
 * Juntar entregas en una factura.
 *
 * Se abre desde la lista y desde el botón de una entrega concreta (`ventas-facturar`), y en ese caso
 * esa entrega **viene ya marcada**: es lo que convierte «quiero facturar esto» en un solo toque.
 */
async function pantallaFacturarEntregas(idMarcada = null) {
  const f = (clave) => t(`factura_emitida.${clave}`, "");
  const v = (clave) => t(`venta.${clave}`, "");
  const filas = (estado.ventasTabla || {}).filas || [];
  const marcadas = new Set((estado.entregasAFacturar || []).map(Number));
  if (idMarcada) {
    // Marcar la que se ha pulsado, o desmarcarla si ya estaba: es el mismo botón para las dos cosas.
    if (marcadas.has(Number(idMarcada))) marcadas.delete(Number(idMarcada));
    else marcadas.add(Number(idMarcada));
  }
  estado.entregasAFacturar = [...marcadas];
  // Las fichas de cliente, para poder decir a qué ficha va la factura (revisión del T12).
  const contactos = await conLosContactos();
  const entregas = filas.map((fila) => ({
    id: fila.id,
    // Lo que se enseña en la lista de marcar: producto, fecha y cantidad, con el rótulo del servidor.
    titulo: tituloDeUnaEntrega(fila),
    fecha: fila.fecha,
    fecha_valor: fila.fecha_valor,
    producto: fila.producto,
    cliente: fila.cliente,
    importe: fila.importe_valor,
    // Lo que vale la entrega, ya escrito, para poder enseñarlo al lado de la casilla: marcar una entrega
    // sin ver por cuánto es marcar a ciegas.
    texto_importe: fila.importe,
    facturada: fila.facturada,
    factura_numero: fila.factura_numero,
    aviso_facturada: fila.aviso_facturada || "",
    elegida: marcadas.has(Number(fila.id)),
  }));
  const elegidas = entregas.filter((entrega) => entrega.elegida);
  montar(() =>
    pantallaDeFacturarEntregas({
      textos: {
        factura_emitida: t("factura_emitida", {}),
        venta: t("venta", {}),
        acciones: t("acciones", {}),
        cobro: t("cobro", {}),
      },
      entregas,
      borrador: {
        numero: estado.borradorFactura ? estado.borradorFactura.numero : "",
        fecha: (estado.borradorFactura && estado.borradorFactura.fecha) || hoyISO(),
        vencimiento: estado.borradorFactura ? estado.borradorFactura.vencimiento : "",
        cliente: estado.borradorFactura ? estado.borradorFactura.cliente : clienteDeLasEntregas(elegidas),
        // La ficha de cliente con la que queda enlazada la factura (revisión del T12).
        contacto_id: estado.borradorFactura ? estado.borradorFactura.contacto_id || "" : "",
        notas: estado.borradorFactura ? estado.borradorFactura.notas : "",
      },
      cliente: clienteDeLasEntregas(elegidas),
      contactos,
      error: estado.errorVentas || "",
    }),
  );
}

/** El cliente que se propone: el de la primera entrega marcada. No se inventa si no hay ninguna. */
function clienteDeLasEntregas(entregas) {
  const conCliente = (entregas || []).find((entrega) => entrega.cliente);
  return conCliente ? conCliente.cliente : "";
}

/** Crea la factura con las entregas marcadas. */
async function guardarLaFacturaEmitida() {
  const leer = (id) => {
    const campo = document.getElementById(id);
    return campo ? String(campo.value || "").trim() : "";
  };
  estado.borradorFactura = {
    numero: leer("factura-emitida-numero"),
    fecha: leer("factura-emitida-fecha"),
    vencimiento: leer("factura-emitida-vencimiento"),
    cliente: leer("factura-emitida-cliente"),
    // La ficha de cliente con la que va la factura (revisión del T12): se guarda en el borrador para que
    // un fallo al guardar no la pierda, igual que el número o la fecha.
    contacto_id: leer("factura-emitida-contacto"),
    notas: leer("factura-emitida-notas"),
  };
  const entregas = estado.entregasAFacturar || [];
  if (!entregas.length) {
    // Se comprueba aquí y no en el servidor por un motivo del campo: sin cobertura, una petición que se
    // sabe que va a ser rechazada no debe acabar en la cola del móvil.
    estado.errorVentas = t("mensajes.D10_no_hay_nada_que_facturar", "");
    return pantallaFacturarEntregas();
  }
  try {
    const factura = await apiJson("/api/facturas-emitidas", {
      method: "POST",
      body: JSON.stringify({
        fecha: estado.borradorFactura.fecha || hoyISO(),
        vencimiento: estado.borradorFactura.vencimiento || null,
        numero: estado.borradorFactura.numero || null,
        cliente: estado.borradorFactura.cliente || null,
        // Vacío es «sin enlazar con ninguna ficha» y se manda `null`: un cero sería el identificador de
        // una ficha que no existe.
        contacto_id: estado.borradorFactura.contacto_id
          ? Number(estado.borradorFactura.contacto_id)
          : null,
        notas: estado.borradorFactura.notas || null,
        entregas,
        clave_de_reenvio: estado.claveDeLaFactura || (estado.claveDeLaFactura = claveDeReenvio("factura")),
      }),
    });
    estado.borradorFactura = null;
    estado.claveDeLaFactura = null;
    estado.entregasAFacturar = [];
    estado.facturaEmitida = factura;
    estado.errorVentas = "";
    await recargarLasCuentasDeLasVentas();
    return pantallaUnaFacturaEmitida(factura.id);
  } catch (fallo) {
    estado.errorVentas = mensajeDeFallo(fallo);
    return pantallaFacturarEntregas();
  }
}

/** La ficha de una factura nuestra: lo que va dentro, lo que te han pagado y lo que queda. */
async function pantallaUnaFacturaEmitida(id) {
  try {
    estado.facturaEmitida = await apiJson(`/api/facturas-emitidas/${id}`);
    estado.errorVentas = "";
  } catch (fallo) {
    estado.errorVentas = mensajeDeFallo(fallo);
  }
  const factura = estado.facturaEmitida;
  if (!factura) return pantallaFacturasEmitidas();
  montar(() =>
    pantallaDeUnaFacturaEmitida({
      textos: {
        factura_emitida: t("factura_emitida", {}),
        venta: t("venta", {}),
        acciones: t("acciones", {}),
        cobro: t("cobro", {}),
      },
      factura,
      error: estado.errorVentas || "",
    }),
  );
}

/** La lista de lo que me han pagado (T12). */
function pantallaCobros() {
  const c = (clave) => t(`cobro.${clave}`, "");
  const cobros = estado.cobros || [];
  const sinAsignar = cobros.filter((cobro) => !cobro.factura_emitida_id);
  montar(() =>
    pantallaDeCobros({
      textos: { cobro: t("cobro", {}), acciones: t("acciones", {}) },
      cobros,
      sin_asignar: sinAsignar,
      resumen: cobros.length ? rellena(c(cobros.length === 1 ? "cuantos_uno" : "cuantos"), { cuantas: cobros.length }) : "",
      error: estado.errorVentas || "",
    }),
  );
}

/** Apuntar un cobro. Puede ser una parte de lo que se debe (caso A06) y puede no saberse de qué es. */
async function pantallaCobroNuevo(idDeFactura = null) {
  const c = (clave) => t(`cobro.${clave}`, "");
  estado.borradorCobro = estado.borradorCobro || {
    fecha: hoyISO(),
    importe: "",
    cliente: "",
    contacto_id: "",
    factura_emitida_id: idDeFactura || "",
    forma: "transferencia",
    referencia: "",
    notas: "",
    // **La clave de reenvío del cobro** (revisión del T12). Se apuntaba en el borrador pero **nadie la
    // escribía nunca**, así que el `POST /api/cobros` salía sin ella y un reintento del móvil —el mismo
    // cobro mandado dos veces al volver la cobertura— apuntaba el dinero dos veces. Lo cazó la prueba que
    // pulsa los botones del dinero y mira lo que llega al servidor; las pruebas de la API no lo veían
    // porque ellas mandan la clave a mano. Se guarda en el borrador para que un segundo intento de guardar
    // el mismo formulario mande la misma y el servidor devuelva el cobro que ya había (contrato §2, A12).
    clave: claveDeReenvio("cobro"),
  };
  if (idDeFactura) {
    estado.borradorCobro.factura_emitida_id = idDeFactura;
    const suya = (estado.facturasEmitidas || []).find((factura) => Number(factura.id) === Number(idDeFactura));
    if (suya && suya.cliente) estado.borradorCobro.cliente = suya.cliente;
    // Y la ficha de la factura, si la tiene: el que paga suele ser el mismo al que se le facturó, y
    // elegirlo otra vez a mano es pedir dos veces el mismo dato. Se propone, no se impone: el `<select>`
    // lo enseña elegido y se puede cambiar.
    if (suya && suya.contacto_id) estado.borradorCobro.contacto_id = String(suya.contacto_id);
  }
  const contactos = await conLosContactos();
  return montar(() =>
    pantallaDeCobroNuevo({
      textos: { cobro: t("cobro", {}), acciones: t("acciones", {}) },
      borrador: estado.borradorCobro,
      facturas: estado.facturasEmitidas || [],
      contactos,
      error: estado.errorVentas || "",
    }),
  );
}

/** Guarda el cobro. **No crea ninguna factura**, y eso es la mitad del caso A06. */
async function guardarElCobro() {
  const leer = (id) => {
    const campo = document.getElementById(id);
    return campo ? String(campo.value || "").trim() : "";
  };
  const borrador = estado.borradorCobro;
  borrador.fecha = leer("cobro-fecha");
  borrador.importe = leer("cobro-importe");
  borrador.cliente = leer("cobro-cliente");
  borrador.factura_emitida_id = leer("cobro-factura");
  borrador.forma = leer("cobro-forma") || "transferencia";
  borrador.referencia = leer("cobro-referencia");
  borrador.notas = leer("cobro-notas");
  // La ficha de contacto de quien ha pagado (revisión del T12).
  borrador.contacto_id = leer("cobro-contacto");
  try {
    const respuesta = await apiJson("/api/cobros", {
      method: "POST",
      body: JSON.stringify({
        fecha: borrador.fecha || hoyISO(),
        importe: borrador.importe || null,
        factura_emitida_id: borrador.factura_emitida_id ? Number(borrador.factura_emitida_id) : null,
        cliente: borrador.cliente || null,
        // Vacío es «sin enlazar con ninguna ficha» y viaja como `null`, no como cero. Se lee del
        // formulario aquí mismo (y se ha guardado en el borrador, para no perderlo si falla el envío).
        contacto_id: leer("cobro-contacto") ? Number(leer("cobro-contacto")) : null,
        forma: borrador.forma,
        referencia: borrador.referencia || null,
        notas: borrador.notas || null,
        clave_de_reenvio: borrador.clave,
      }),
    });
    // Lo que ha pasado con la factura, con las palabras del servidor: el número exacto de lo que queda
    // por cobrar. Es lo que el agricultor necesita leer después de apuntar un pago parcial.
    estado.avisoVentas = await avisoDeLaRespuestaDelCobro(respuesta);
    estado.rechazadoVentas = respuesta.ya_estaba ? t("cobro.ya_estaba", "") : "";
    estado.borradorCobro = null;
    estado.errorVentas = "";
    await recargarLasCuentasDeLasVentas();
    if (respuesta.factura) return pantallaUnaFacturaEmitida(respuesta.factura.id);
    return pantallaCobros();
  } catch (fallo) {
    estado.errorVentas = mensajeDeFallo(fallo);
    return pantallaCobroNuevo();
  }
}

/** Los avisos de una respuesta de cobro, uno por línea, tal y como los escribió el servidor. */
async function avisoDeLaRespuestaDelCobro(respuesta) {
  return (respuesta.avisos || []).join(" ");
}

/** Conciliar un cobro con una factura, o deshacer la asignación (el dinero sigue apuntado). */
async function conciliarUnCobro(id, idDeFactura) {
  try {
    const respuesta = await apiJson(`/api/cobros/${id}/conciliar`, {
      method: "POST",
      body: JSON.stringify({ factura_emitida_id: idDeFactura ? Number(idDeFactura) : null }),
    });
    estado.avisoVentas = (respuesta.avisos || []).join(" ");
    estado.errorVentas = "";
    await recargarLasCuentasDeLasVentas();
    if (idDeFactura) return pantallaUnaFacturaEmitida(idDeFactura);
    return pantallaCobros();
  } catch (fallo) {
    estado.errorVentas = mensajeDeFallo(fallo);
    return pantallaCobros();
  }
}

/** Vuelve a pedir lo que ha cambiado el dinero: la tabla de entregas, las facturas y los cobros. */
async function recargarLasCuentasDeLasVentas() {
  await recargarLaTablaDeVentas();
  try {
    estado.facturasEmitidas = await apiJson("/api/facturas-emitidas");
    estado.cobros = await apiJson("/api/cobros");
  } catch (fallo) {
    estado.errorVentas = mensajeDeFallo(fallo);
  }
}

/**
 * Quitar un cobro, ya decidido: la factura vuelve a deber lo que debía.
 *
 * **No se borra la fila**: queda anulada con su motivo y deja de contar en las sumas, que es la regla del
 * cuaderno. Y el motivo va escrito en `textos.py` —el mismo que usa el resto de la aplicación cuando el
 * agricultor se equivoca— porque aquí no hay ningún sitio donde escribirlo a mano: la pantalla que
 * pregunta ya ha dicho qué va a pasar y cuál es la salida.
 */
async function quitarUnCobro(id) {
  const c = (clave) => t(`cobro.${clave}`, "");
  try {
    await apiJson(`/api/cobros/${id}/anular`, {
      method: "POST",
      body: JSON.stringify({ motivo: c("motivo_al_quitar") }),
    });
    estado.errorVentas = "";
    estado.avisoVentas = c("anulado");
    await recargarLasCuentasDeLasVentas();
  } catch (fallo) {
    estado.errorVentas = mensajeDeFallo(fallo);
  }
  return pantallaCobros();
}

/** Anular un cobro desde la pantalla de la factura: se vuelve a la factura, no a la lista. */
async function quitarUnCobroDeUnaFactura(id, idDeFactura) {
  await quitarUnCobro(id);
  return pantallaUnaFacturaEmitida(idDeFactura);
}

/**
 * Elegir a qué factura va un cobro, cuando hay más de una con algo pendiente.
 *
 * Se monta con la pieza de la confirmación (una pregunta grande y sus caminos debajo): es una decisión
 * con varias salidas y ninguna es «guardar». **Si solo hay una factura pendiente no se pregunta**: se
 * va directo, porque preguntar cuando solo hay una respuesta posible es hacer perder el tiempo.
 */
function pantallaElegirFacturaParaElCobro(idDelCobro, pendientes) {
  const c = (clave) => t(`cobro.${clave}`, "");
  montar(() =>
    confirmacion({
      pregunta: c("conciliar_titulo"),
      pista: c("conciliar_elegir"),
      acciones: [
        ...pendientes.map((factura) => ({
          etiqueta: `${factura.titulo} · ${c("pendiente")}: ${factura.texto_pendiente}`,
          accion: "cobro-conciliar-con",
          datos: { cobro: idDelCobro, factura: factura.id },
        })),
        { etiqueta: accion("volver"), accion: "cobros-ver", clase: "boton-claro", sencillo: true },
      ],
    }),
  );
}

/**
 * Quitar un ajuste del importe: primero se pregunta, y no se toca nada hasta que se contesta.
 *
 * Es la misma forma que el resto de la aplicación (la pieza de la confirmación): una pregunta grande con
 * lo que va a pasar debajo y la salida de «mejor no». Y **el papel que traía no se borra del disco**:
 * sigue siendo el justificante de lo que se apuntó, y el programa tiene que poder enseñarlo aunque el
 * ajuste ya no cuente.
 */
function preguntarSiQuitarElAjuste(idDeLaVenta, idDelAjuste) {
  const cb = (clave) => t(`corregir.${clave}`, "");
  const v = (clave) => t(`venta.${clave}`, "");
  montar(() =>
    confirmacion({
      pregunta: cb("pregunta_borrar"),
      pista: v("ajuste_quitar_pista"),
      acciones: [
        {
          etiqueta: cb("boton_borrar_si"),
          accion: "ajuste-anular-si",
          datos: { venta: idDeLaVenta, id: idDelAjuste },
          clase: "boton-peligro",
          sencillo: true,
        },
        {
          etiqueta: accion("volver"),
          accion: "venta-ajuste",
          datos: { id: idDeLaVenta },
          clase: "boton-claro",
          sencillo: true,
        },
      ],
    }),
  );
}

/** La pregunta de quitar un cobro, con lo que pasa al quitarlo dicho antes de hacerlo. */
function preguntarSiQuitarElCobro(id) {
  const c = (clave) => t(`cobro.${clave}`, "");
  const cb = (clave) => t(`corregir.${clave}`, "");
  montar(() =>
    confirmacion({
      pregunta: c("anular_titulo"),
      pista: c("anular_explica"),
      acciones: [
        {
          etiqueta: cb("boton_borrar_si"),
          accion: "cobro-anular-si",
          datos: { id },
          clase: "boton-peligro",
          sencillo: true,
        },
        { etiqueta: accion("volver"), accion: "cobros-ver", clase: "boton-claro", sencillo: true },
      ],
    }),
  );
}

/** La pregunta de quitar una factura nuestra: sus entregas vuelven a quedar sin facturar. */
function preguntarSiQuitarLaFactura(id) {
  const f = (clave) => t(`factura_emitida.${clave}`, "");
  const cb = (clave) => t(`corregir.${clave}`, "");
  montar(() =>
    confirmacion({
      pregunta: f("anular_titulo"),
      pista: f("anular_explica"),
      acciones: [
        {
          etiqueta: cb("boton_borrar_si"),
          accion: "factura-emitida-anular-si",
          datos: { id },
          clase: "boton-peligro",
          sencillo: true,
        },
        {
          etiqueta: accion("volver"),
          accion: "factura-emitida-abrir",
          datos: { id },
          clase: "boton-claro",
          sencillo: true,
        },
      ],
    }),
  );
}

/** Anular una factura nuestra, ya decidido. Sus entregas vuelven a estar libres para facturarlas. */
async function quitarLaFacturaEmitida(id) {
  const f = (clave) => t(`factura_emitida.${clave}`, "");
  try {
    await apiJson(`/api/facturas-emitidas/${id}/anular`, {
      method: "POST",
      body: JSON.stringify({ motivo: f("motivo_al_quitar") }),
    });
    estado.errorVentas = "";
    estado.avisoVentas = f("anulada");
    estado.facturaEmitida = null;
    await cargarDatos().catch(() => {});
    return pantallaFacturasEmitidas();
  } catch (fallo) {
    estado.errorVentas = mensajeDeFallo(fallo);
    return pantallaUnaFacturaEmitida(id);
  }
}

/**
 * La línea de detalle de una venta: cantidad, tipo, comprador, lote, albarán y dónde.
 *
 * **Sigue existiendo, y a propósito**: es como se enseña una venta en el bloque de «mi cuaderno», que
 * enseña cuatro de un tirón y con cada dato con su nombre no cabría. En la pantalla de las ventas —donde se
 * va a mirar una venta concreta— van las filas con su nombre (ver `filasDeLaVenta`).
 */
function detallesDeLaVenta(venta) {
  return [
    venta.texto_cantidad,
    venta.etiqueta_tipo,
    venta.comprador || t("venta.sin_comprador", ""),
    venta.lote ? `${t("venta.tabla_lote", "")} ${venta.lote}` : "",
    venta.numero_albaran ? `${t("venta.tabla_albaran", "")} ${venta.numero_albaran}` : "",
    venta.donde,
  ]
    .filter(Boolean)
    .join(" · ");
}

function pasosVenta() {
  const et = (clave) => t(`etiquetas.${clave}.pregunta`, "");
  const pi = (clave) => t(`etiquetas.${clave}.pista`, "");
  return [
    {
      titulo: et("venta.tipo"),
      pista: pi("venta.tipo"),
      // Se pinta con los campos de maestro y no con `pintaOpciones` porque aquí el valor
      // («comercializada») no es lo que se lee: lo que se lee es la frase larga. Con
      // `pintaOpciones` el botón diría «comercializada», que es jerga.
      montar: () => montarCamposMaestro(["venta.tipo"]),
      recoger: () => {
        const b = estado.asistente.borrador;
        if (!b.tipo) b.tipo = "comercializada";
        return null;
      },
    },
    {
      titulo: et("venta.producto"),
      pista: pi("venta.producto"),
      montar: () => montarCamposMaestro(["venta.producto", "venta.variedad"]),
      recoger: recogeCamposMaestro(["venta.producto", "venta.variedad"]),
    },
    {
      // Cuánto y en qué se mide van juntos: son una sola idea, y separarlos obligaría a
      // pasar dos pantallas para escribir «42 toneladas».
      titulo: et("venta.cantidad"),
      pista: pi("venta.cantidad"),
      montar: () => montarCamposMaestro(["venta.cantidad", "venta.unidad"]),
      recoger: recogeCamposMaestro(["venta.cantidad", "venta.unidad"]),
    },
    {
      titulo: et("venta.fecha"),
      pista: pi("venta.fecha"),
      montar: () => montarFecha("fecha", "venta.fecha"),
      recoger: () => {
        const elemento = document.getElementById("fecha");
        if (elemento) estado.asistente.borrador.fecha = elemento.value;
        return null;
      },
    },
    {
      // La norma llama a la fecha «fecha (intervalo de tiempo)»: una partida puede salir en
      // varios viajes. Por eso hay un último día, y es opcional.
      titulo: et("venta.fecha_fin"),
      pista: pi("venta.fecha_fin"),
      opcional: true,
      montar: () => html`${camposDelMaestro({ bloques: bloquesDelMaestro(["venta.lote"]) })}${elementoDeFecha("fecha_fin", "venta.fecha_fin")}`,
      recoger: () => {
        recogeCamposMaestro(["venta.lote"])();
        const elemento = document.getElementById("fecha_fin");
        if (elemento) estado.asistente.borrador.fecha_fin = elemento.value;
        return null;
      },
    },
    {
      titulo: et("venta.de_donde"),
      pista: pi("venta.de_donde"),
      opcional: true,
      // La lista de tierras es la misma pieza que la del asistente de echar producto: aquí solo se
      // pregunta, sin la salida de «no es en una parcela» (una venta sale de una tierra o de un grupo).
      // El paso es opcional porque se puede estar vendiendo de otro año.
      montar: () =>
        estado.parcelas.length
          ? listaParaElegir({ bloques: [bloqueDeParcelas(), bloqueDeGrupos()].filter(Boolean) })
          : listaParaElegir({ aviso: { texto: aviso("no_hay_parcelas") } }),
    },
    {
      titulo: et("venta.comprador"),
      pista: pi("venta.comprador"),
      opcional: true,
      montar: () => montarCamposMaestro(["venta.comprador", "venta.numero_albaran"]),
      recoger: recogeCamposMaestro(["venta.comprador", "venta.numero_albaran"]),
    },
    {
      titulo: et("venta.observaciones"),
      pista: pi("venta.observaciones"),
      opcional: true,
      montar: () => montarCamposMaestro(["venta.observaciones"]),
      recoger: recogeCamposMaestro(["venta.observaciones"]),
    },
    {
      titulo: t("etiquetas.tratamiento.resumen.pregunta", ""),
      pista: t("etiquetas.tratamiento.resumen.pista", ""),
      montar: () => resumenDelApunte({ filas: filasDelResumenVenta() }),
    },
  ];
}

/** Las filas del resumen de la venta, ya preparadas (ver `filasDelResumenPlan`). */
function filasDelResumenVenta() {
  const b = estado.asistente.borrador;
  const parcela = estado.parcelas.find((p) => p.id === Number(b.parcela_id));
  const unidad = (t("unidades_venta", []) || []).find((u) => u.valor === (b.unidad || "kg"));
  return [
    [t("etiquetas.venta.tipo.pregunta", ""), etiquetaDeValor("tipos_venta", b.tipo || "comercializada")],
    [t("etiquetas.venta.producto.pregunta", ""), b.producto || ""],
    [t("etiquetas.venta.variedad.pregunta", ""), b.variedad || ""],
    [
      t("etiquetas.venta.cantidad.pregunta", ""),
      b.cantidad
        ? `${formateaNumero(aNumero(b.cantidad), 2)} ${unidad ? unidad.corto : ""}`.trim()
        : "",
    ],
    [
      t("etiquetas.venta.fecha.pregunta", ""),
      b.fecha
        ? `${formateaFecha(b.fecha)}${
            b.fecha_fin ? ` — ${formateaFecha(b.fecha_fin)}` : ` (${t("venta.un_viaje", "")})`
          }`
        : "",
    ],
    [t("etiquetas.venta.lote.pregunta", ""), b.lote || ""],
    [t("etiquetas.venta.comprador.pregunta", ""), b.comprador || ""],
    [t("etiquetas.venta.numero_albaran.pregunta", ""), b.numero_albaran || ""],
    // **El dinero no se pregunta en el asistente pero sí se enseña aquí** (T12), y no es un adorno: el
    // asistente no pregunta el importe (se apunta después, desde la pantalla de la entrega), pero al
    // **corregir** una venta sus datos van y vuelven dentro de este borrador, y el resumen es donde el
    // agricultor comprueba, antes de guardar, que no se ha perdido lo que ya estaba. Los rótulos salen del
    // vocabulario de la pantalla de las ventas (`textos.VENTA`), que es donde viven.
    [t("venta.importe", ""), b.importe || ""],
    [t("venta.precio_unitario", ""), b.precio_unitario || ""],
    [t("venta.vencimiento", ""), b.vencimiento ? formateaFecha(b.vencimiento) : ""],
    [t("venta.de_que_cosecha", ""), nombreDeLaCosecha(b.cosecha_id)],
    [t("etiquetas.venta.de_donde.pregunta", ""), parcela ? parcela.alias : ""],
  ].filter(([, valor]) => valor);
}

/** Cómo se llama una cosecha apuntada: «Trigo blando · 10/07/2026». Vacío si no se sabe cuál es. */
function nombreDeLaCosecha(cosechaId) {
  if (!cosechaId) return "";
  const labor = (estado.labores || []).find((una) => Number(una.id) === Number(cosechaId));
  if (!labor) return "";
  const producto = (labor.detalles || {}).producto || "";
  return `${producto} · ${formateaFecha(labor.fecha)}`.replace(/^ · /, "");
}

/**
 * Las cosechas que se pueden elegir como «lote del que salió esta entrega» (T12).
 *
 * Son **las cosechas apuntadas** (las labores de tipo cosecha), que es el «lote cosechado» que el
 * contrato manda separar de la entrega: no hay una tabla nueva para él porque ya existe. Se ofrece la
 * primera la opción de no decirla: **no se elige la más parecida** por el agricultor.
 */
function opcionesDeCosechasApuntadas() {
  const opciones = [{ valor: "", texto: t("venta.sin_cosecha_apuntada", "") }];
  for (const labor of estado.labores || []) {
    if (labor.tipo !== "cosecha") continue;
    opciones.push({ valor: String(labor.id), texto: nombreDeLaCosecha(labor.id) });
  }
  return opciones;
}

/**
 * Las fichas de cliente que se pueden enlazar con una entrega, una factura o un cobro (T12).
 *
 * **Por qué existe esto** (revisión del T12): las tres columnas `contacto_id` estaban en el modelo, el
 * servidor las validaba… y **ninguna pantalla las preguntaba**, así que el enlace con la ficha —que es
 * como el informe promete contestar «¿cuánto me debe la cooperativa?» **sin comparar nombres a ojo**— no
 * se podía hacer desde ningún sitio. Es el fallo que este proyecto ya ha pagado varias veces: un campo en
 * el modelo sin puerta que lo pregunte.
 *
 * Los nombres son los del contacto, tal cual, y la primera opción es **no enlazar**: no se elige el que
 * se parezca al nombre escrito a mano.
 */
function opcionesDeContactos() {
  const opciones = [{ valor: "", texto: t("venta.sin_contacto", "") }];
  for (const contacto of estadoDeLosContactos().lista || []) {
    opciones.push({ valor: String(contacto.id), texto: contacto.nombre });
  }
  return opciones;
}

/**
 * Se asegura de tener las fichas de contacto cargadas antes de pintar una pantalla del dinero.
 *
 * Se piden **una sola vez** (`cargados`): lo que se gana es que las pantallas del dinero tengan la lista
 * también cuando se entra directamente por su dirección. Y si no hay cobertura, la lista se queda vacía y
 * la pantalla se pinta igual: sin contactos se puede apuntar el dinero, que es lo que no puede esperar.
 */
async function conLosContactos() {
  const suyo = estadoDeLosContactos();
  if (!suyo.cargados) await recargarLosContactos();
  return opcionesDeContactos();
}

function cargaVenta() {
  const b = estado.asistente.borrador;
  return {
    campana_id: estado.campana.id,
    tipo: b.tipo || "comercializada",
    fecha: b.fecha || hoyISO(),
    fecha_fin: b.fecha_fin || null,
    producto: (b.producto || "").trim(),
    variedad: b.variedad || null,
    cantidad: aNumero(b.cantidad),
    unidad: b.unidad || "kg",
    lote: b.lote || null,
    comprador: b.comprador || null,
    numero_albaran: b.numero_albaran || null,
    parcela_id: Number(b.parcela_id) || null,
    // El grupo, cuando la venta salió de varias tierras a la vez (ronda 93): el asistente no lo
    // pregunta, pero si no se devolviera, corregir una venta la dejaría sin decir de dónde salió.
    grupo_id: b.grupo_id ?? null,
    observaciones: b.observaciones || null,
    // El dinero de la entrega (T12). Los dos importes viajan **como texto decimal** y vacío es «no se
    // sabe»: es lo que hace que una venta sin precio se apunte igual y siga sin precio (A08) en vez de
    // convertirse en un ingreso de cero euros.
    importe: b.importe || null,
    precio_unitario: b.precio_unitario || null,
    vencimiento: b.vencimiento || null,
    cosecha_id: b.cosecha_id ? Number(b.cosecha_id) : null,
    // La clave de reenvío: si el móvil reintenta la misma entrega al volver la cobertura, el servidor
    // devuelve la que ya había en vez de apuntar otra (contrato §2, caso A12). Se guarda en el borrador
    // para que un segundo intento de guardar la misma entrega —el mismo formulario, el mismo agricultor—
    // mande la misma clave y no le salga la venta dos veces.
    clave_de_reenvio: b.clave_de_reenvio || (b.clave_de_reenvio = claveDeReenvio("venta")),
  };
}

function pantallaVentaGuardada() {
  const v = (clave) => t(`venta.${clave}`, "");
  montar(() =>
    confirmacion({
      titulo: v("guardado_titulo"),
      pista: v("guardado"),
      ayuda: { titulo: v("se_usa"), texto: v("aprovecha") },
      acciones: accionesDeConfirmacion({
        etiqueta: v("ver"),
        accion: "ventas-ver",
        clase: "boton",
        sencillo: true,
      }),
    }),
  );
}

// ----------------------------------- las medidas preventivas de la explotación

/**
 * Lo que el agricultor hace sin echar producto.
 *
 * La app oficial lo tiene en «Explotación: Medidas Preventivas», y es la parte no química
 * de la gestión integrada de plagas. Se declara **una vez** y vale para todo el año.
 *
 * Decisión de interfaz: las diez preguntas se pintan **las diez juntas**, en una sola
 * pantalla, y no una por pantalla como en el asistente. El motivo es que aquí no se está
 * apuntando lo que ha pasado: se está contestando un cuestionario del que ya se sabe la
 * respuesta, y hacer pasar al agricultor por diez pantallas para marcar tres casillas es
 * justo lo que la guía de interfaz prohíbe.
 *
 * Lo que hace que esta sección sirva de algo: al apuntar un producto, lo declarado aquí
 * **ya sale marcado** (ver `pintaMedidasDelTratamiento`). Sin eso, sería un formulario que
 * se rellena una vez y no se vuelve a mirar.
 */
function medidasDeLaFinca() {
  const datos = estado.medidas || { medidas: [] };
  return datos.medidas || [];
}

/** Los códigos que la finca dice aplicar. Es lo que se marca por defecto en un apunte. */
function medidasAplicadasDeLaFinca() {
  return medidasDeLaFinca()
    .filter((medida) => medida.aplicada)
    .map((medida) => medida.codigo);
}

/** La copia de trabajo de la pantalla: se toca aquí y se guarda al pulsar GUARDAR. */
function borradorDeMedidas() {
  if (!estado.medidasBorrador) {
    const observaciones = {};
    for (const medida of medidasDeLaFinca()) {
      if (medida.observaciones) observaciones[medida.codigo] = medida.observaciones;
    }
    estado.medidasBorrador = { aplicadas: medidasAplicadasDeLaFinca(), observaciones };
  }
  return estado.medidasBorrador;
}

function nombreDeMedida(codigo) {
  const medida = medidasDeLaFinca().find((m) => m.codigo === codigo);
  if (medida) return medida.etiqueta;
  const delCatalogo = (t("medidas_preventivas", []) || []).find((m) => m.codigo === codigo);
  return delCatalogo ? delCatalogo.etiqueta : codigo;
}


/**
 * Recoge lo que el agricultor haya escrito en las notas, antes de repintar.
 *
 * Hace falta de verdad: al marcar o desmarcar una medida la pantalla se vuelve a pintar, y
 * sin esto se perdería lo que estuviera escrito en las demás casillas. Se recogen todas
 * las notas, no solo la de la medida que se acaba de tocar.
 */
function recogeNotasDeMedidas() {
  const borrador = borradorDeMedidas();
  for (const medida of medidasDeLaFinca()) {
    const elemento = document.getElementById(`nota-${medida.codigo}`);
    if (elemento) borrador.observaciones[medida.codigo] = elemento.value;
  }
  return borrador;
}

/**
 * «Las medidas preventivas»: las diez que la ley pide haber probado antes de echar producto.
 *
 * Esta pantalla ya está en React (ver `docs/REACT.md`). Los diez botones llevan su `data-codigo` y las
 * notas su `id` (`nota-<código>`), y los sigue leyendo `app.js`: el manejador de clics es uno solo y
 * vive aquí. Al marcar o desmarcar, `recogeNotasDeMedidas()` recoge lo escrito **antes** de repintar,
 * así que no se pierde ninguna nota.
 */
function pantallaMedidas() {
  const borrador = borradorDeMedidas();
  const medidas = medidasDeLaFinca().map((medida) => ({
    codigo: medida.codigo,
    pregunta: medida.pregunta,
    marcada: borrador.aplicadas.includes(medida.codigo),
    nota: borrador.observaciones[medida.codigo] || "",
  }));

  // `montar()` pide el elemento dentro de un `try`: si los ficheros de React de `vendor/` no han
  // llegado, enseña el aviso de emergencia en vez de dejar la pantalla en blanco.
  montar(() =>
    pantallaDeMedidas({
      textos: { medidas: t("medidas", {}), acciones: t("acciones", {}) },
      medidas,
      // Si hay declaración, se ofrece **quitarla** (ronda 93). El dato lo dice el servidor
      // (`declarada`): sin él, la pantalla ofrecería quitar algo que no está declarado.
      hay_declaracion: Boolean((estado.medidas || {}).declarada),
    }),
  );
}

async function guardarMedidas() {
  const borrador = recogeNotasDeMedidas();
  // **`PUT`, no `POST`, y esto era un fallo de verdad** (ronda 93). La pantalla mandaba un `POST` con el
  // ayudante de siempre (`enviarOApuntar`) y el servidor **solo acepta `PUT` en `/api/medidas`**
  // (su ruta está escrita así a propósito: no se crea un apunte más, se **sustituye la declaración
  // entera**). Un `POST` contesta **405**, así que guardar las medidas decía «No se ha podido» y el
  // agricultor no podía declarar lo que hace en su finca. No lo cazó ninguna prueba porque la copia de la
  // API que usan los tests contesta por la ruta y no por el método: se ha visto probando la aplicación
  // contra un servidor de verdad, que es justo para lo que está esa comprobación.
  //
  // No pasa por la cola de sin cobertura a propósito: esto no es un apunte del día, es una declaración
  // que se hace en casa, y lo que se manda **sustituye** lo que había (mandarla dos veces no puede dejar
  // la declaración a medias).
  estado.errorMedidas = "";
  try {
    const respuesta = await api("/api/medidas", {
      method: "PUT",
      body: JSON.stringify({
        aplicadas: borrador.aplicadas,
        observaciones: borrador.observaciones,
      }),
    });
    const detalle = await respuesta.json().catch(() => null);
    if (!respuesta.ok) {
      avisarDelError(avisoDelServidor(detalle) || mensaje("no_se_pudo"));
      return;
    }
    estado.medidas = detalle;
  } catch (error) {
    avisarDelError(error.message || mensaje("no_se_pudo"));
    return;
  }
  estado.medidasBorrador = null;
  await cargarDatos().catch(() => {});
  pantallaMedidasGuardadas();
}

/**
 * QUITAR LA DECLARACIÓN de las medidas preventivas: la finca vuelve a estar **sin declarar**.
 *
 * POR QUÉ NO ES LO MISMO QUE «NO HAGO NINGUNA». Son dos cosas distintas y hacían falta las dos (lo
 * explica el servidor, `DELETE /api/medidas`): «no hago ninguna» es **una respuesta** —el agricultor ha
 * mirado las diez preguntas y ha contestado—, y quitarla es **volver a dejarlo sin contestar**, como una
 * finca recién dada de alta, con el programa preguntando otra vez. Hasta esta ronda el camino existía en
 * el servidor y **ninguna pantalla lo pedía**, así que el agricultor que había contestado por error —o
 * que quería volver a empezar— solo podía marcar y desmarcar.
 *
 * Se pregunta antes, como todo lo que quita algo del cuaderno, y la pregunta ofrece la otra salida
 * (volver y cambiar lo que hay marcado), que es lo que casi siempre se quiere.
 */
function preguntarSiQuitarLasMedidas() {
  const cb = (clave) => t(`corregir.${clave}`, "");
  const m = (clave) => t(`medidas.${clave}`, "");
  const datos = estado.medidas || {};
  montar(() =>
    confirmacion({
      pregunta: cb("pregunta_borrar"),
      pista: m("quitar_pista"),
      contenido: resumenDelApunte({
        titulo: cb("lo_que_desaparece"),
        // **Pares, no objetos** (ver la nota de `preguntarSiBorrarAlgo`): con objetos, la pantalla se queda
        // en blanco en un navegador de verdad y las pruebas no lo ven.
        filas: [[m("titulo"), datos.mensaje || ""]],
      }),
      avisos: [{ texto: m("quitar_explica") }, { texto: cb("borrar_queda_rastro") }],
      acciones: [
        {
          etiqueta: cb("boton_borrar_si"),
          accion: "medidas-quitar-si",
          clase: "boton-peligro",
          sencillo: true,
        },
        {
          etiqueta: cb("boton_mejor_corregirlo"),
          accion: "medidas-ver",
          clase: "boton-claro",
          sencillo: true,
        },
        { etiqueta: accion("volver"), accion: "inicio", datos: { ir: "mi_cuaderno" }, clase: "boton-claro", sencillo: true },
      ],
    }),
  );
}

/** El quitado, ya decidido: se manda al servidor y se dice qué ha pasado. */
async function quitarLasMedidas() {
  const m = (clave) => t(`medidas.${clave}`, "");
  try {
    const respuesta = await api("/api/medidas", { method: "DELETE" });
    const detalle = await respuesta.json().catch(() => null);
    if (!respuesta.ok) {
      avisarDelError(avisoDelServidor(detalle) || mensaje("no_se_pudo"));
      return;
    }
    estado.medidas = detalle;
  } catch (error) {
    avisarDelError(error.message || mensaje("no_se_pudo"));
    return;
  }
  estado.medidasBorrador = null;
  await cargarDatos().catch(() => {});
  montar(() =>
    confirmacion({
      titulo: m("quitado_titulo"),
      pista: m("quitado"),
      ayuda: { titulo: t("corregir.rastro_titulo", ""), texto: t("corregir.borrar_queda_rastro", "") },
      acciones: [
        {
          etiqueta: m("titulo"),
          accion: "medidas-ver",
          clase: "boton-principal",
          sencillo: true,
        },
        { etiqueta: accion("volver"), accion: "inicio", datos: { ir: "mi_cuaderno" }, clase: "boton-claro", sencillo: true },
      ],
    }),
  );
}

function pantallaMedidasGuardadas() {
  const m = (clave) => t(`medidas.${clave}`, "");
  const datos = estado.medidas || {};
  montar(() =>
    confirmacion({
      titulo: m("guardado_titulo"),
      pista: m("guardado"),
      ayuda: { titulo: m("se_usa"), texto: m("aprovecha") },
      // El servidor contesta con su propio mensaje (cuántas medidas se han guardado): se enseña tal cual.
      avisos: datos.mensaje ? [{ texto: datos.mensaje }] : [],
      acciones: accionesDeConfirmacion({
        etiqueta: m("ver"),
        accion: "medidas-ver",
        clase: "boton",
        sencillo: true,
      }),
    }),
  );
}

/**
 * Las medidas dentro del asistente de un tratamiento.
 *
 * Decisión: aquí NO se piden las diez desde cero. Lo que el agricultor declaró que hace en
 * su finca **ya viene marcado**, y él solo quita lo que esta vez no hiciera. Es la
 * diferencia entre una pregunta que se contesta en dos segundos y diez casillas que hay
 * que volver a marcar cada vez.
 */
/**
 * Las medidas preventivas del apunte, ya en React.
 *
 * Son las diez preguntas del catálogo de la finca, cada una con su casilla (✅ marcada, ⬜ sin marcar): lo
 * que se hizo **esa vez**, que no es lo mismo que lo que se hace siempre. Se marca y se desmarca
 * pulsando, así que **no hay nada que recoger del DOM**: lo que se apunta vive en el borrador.
 *
 * Si la finca todavía no ha declarado nada, se le dice **y se le da el botón** para hacerlo una vez para
 * todo el año, que es lo que evita tener que marcar diez casillas en cada apunte.
 */
function montarMedidasDelTratamiento() {
  const b = estado.asistente.borrador;
  if (!Array.isArray(b.medidas)) b.medidas = medidasAplicadasDeLaFinca();
  const sinDeclarar = !estado.medidas || !estado.medidas.declarada;

  return html`
    ${listaParaElegir({
      bloques: [
        {
          pista: t("medidas.pista_en_el_tratamiento", ""),
          botones: medidasDeLaFinca().map((medida) => {
            const marcada = b.medidas.includes(medida.codigo);
            return {
              etiqueta: medida.pregunta,
              // El ✅ y el ⬜ son lo que se ve de un vistazo: sin ellos, marcar diez casillas es leer diez
              // frases cada vez.
              icono: marcada ? "✅" : "⬜",
              accion: "medidas-marcar-apunte",
              datos: { codigo: medida.codigo },
              clase: marcada ? "boton-elegido" : "boton-claro",
            };
          }),
        },
      ],
    })}
    ${
      sinDeclarar
        ? listaParaElegir({
            aviso: {
              texto: t("medidas.sin_declarar", ""),
              boton: {
                etiqueta: t("medidas.hacer", ""),
                accion: "medidas-ver",
                clase: "boton-claro",
                sencillo: true,
              },
            },
          })
        : null
    }
  `;
}


// ------------------------------------------------ los análisis de laboratorio

/**
 * Los análisis que ha hecho el agricultor: tierra, agua, planta, cosecha y residuos.
 *
 * La app oficial los llama «Analíticas» y están en Otras Actividades. Aquí se llaman
 * análisis, que es como se dice en el pueblo, y tienen dos usos:
 *
 * 1. **Guardar el papel.** El boletín del laboratorio se sube en PDF o en foto y no se
 *    pierde en un cajón.
 * 2. **Aprovecharlo.** Los números se guardan con su clave, así que el plan de abono los
 *    puede leer y enseñar. Un análisis que solo se puede mirar no sirve para nada.
 *
 * Decisión sobre los números: **solo se pintan los que trae el boletín de esa clase de
 * análisis**, y se piden al servidor (`parametros_analitica`). Con un formulario fijo de
 * veinte casillas, el agricultor tendría que adivinar cuáles rellenar.
 */
function nombreDeAnalisis(analisis) {
  const a = analisis || {};
  const que = a.etiqueta_tipo || etiquetaDeValor("tipos_analitica", a.tipo);
  const donde = a.donde ? ` ${rellena(t("analitica.de_la_parcela", ""), { parcela: a.donde })}` : "";
  return `${rellena(t("analitica.de", ""), { que })}${donde}`;
}


/**
 * Los datos de la ficha de un análisis, ya en texto y listos para el componente de React.
 *
 * No devuelve HTML: devuelve filas de etiqueta y valor. Quien pinta es el componente
 * (`react/pantallas/analiticas.js`), y aquí solo se traducen las tres cosas que el componente no
 * puede saber: los textos con huecos rellenos (`Análisis de {que}`), las fechas en el formato de
 * aquí y qué filas tienen dato (una fila vacía, con su etiqueta y nada al lado, parece un error).
 */
function datosDeLaFichaDeAnalisis(analisis) {
  const lineas = [
    [t("analitica.sitio", ""), analisis.donde],
    [t("analitica.cogida", "").replace("{fecha}", ""), formateaFecha(analisis.fecha_toma_muestra)],
    [
      t("analitica.resultado", "").replace("{fecha}", ""),
      analisis.fecha_resultado ? formateaFecha(analisis.fecha_resultado) : "",
    ],
    [t("analitica.quien", ""), analisis.laboratorio || ""],
    [t("analitica.informe_numero", ""), analisis.numero_informe || ""],
  ].filter(([, valor]) => valor);

  return {
    id: analisis.id,
    titulo: nombreDeAnalisis(analisis),
    filas: lineas.map(([etiqueta, valor]) => [etiqueta, String(valor)]),
    // **La edad del boletín, en su etiqueta** (diseño de Stitch de esta pantalla, ronda 90): «De este
    // año (2026)» o «Hace 2 años (2024)». Es lo que dice, de un vistazo, si el boletín sirve para el plan
    // de este año o es de hace tres campañas; antes era una línea de texto debajo de la ficha que había
    // que leer. El año se pega detrás, entre paréntesis, y sale de la fecha de la muestra.
    estado: (() => {
      const anio = String(analisis.fecha_toma_muestra || "").slice(0, 4);
      const texto = analisis.anios
        ? rellena(t("analitica.hace_anios", ""), { anios: analisis.anios })
        : t("analitica.de_este_anio", "");
      return {
        texto: anio ? `${texto} (${anio})` : texto,
        tipo: analisis.anios ? "mirar" : "bien",
      };
    })(),
    numeros: (analisis.parametros_con_nombre || []).map((n) => [n.etiqueta, n.texto]),
    // La línea del papel se arma aquí y no en el componente porque lleva el nombre del fichero
    // entre paréntesis pegado a la frase del servidor, y eso es texto, no dibujo.
    linea_informe: analisis.fichero_nombre
      ? `${t("analitica.informe_ya_esta", "")} (${analisis.fichero_nombre})`
      : t("analitica.sin_informe", ""),
    tiene_informe: Boolean(analisis.fichero_nombre),
    // **Y sus dos botones** (ronda 93): un número copiado mal del boletín se arregla aquí —y ese número
    // es el que después lee el plan de abono—, y un análisis apuntado por error se puede quitar.
    acciones: botonesDeCorregirYBorrar("analitica", analisis.id),
  };
}

/**
 * «Los análisis»: la pantalla completa, ya en React (ver `docs/REACT.md`).
 *
 * Lo que se prepara aquí, y por qué: los textos del servidor con sus huecos rellenos (`Análisis de
 * {que}`, `de {parcela}`, `Hace {anios} años`) y las fechas en el formato de aquí. El componente no
 * sabe nada de eso: recibe filas de etiqueta y valor y las pinta.
 */
function pantallaAnaliticas() {
  const analisis = (estado.analiticas || []).map((uno) => datosDeLaFichaDeAnalisis(uno));

  // `montar()` pide el elemento dentro de un `try`: si los ficheros de React de `vendor/` no han
  // llegado, enseña el aviso de emergencia en vez de dejar la pantalla en blanco.
  montar(() =>
    pantallaDeAnaliticas({
      textos: { analitica: t("analitica", {}), acciones: t("acciones", {}) },
      analisis,
    }),
  );
}

/**
 * De dónde salió la muestra.
 *
 * Decisión: la lista de parcelas va primero y la salida —nave, balsa o lote— va debajo,
 * igual que en los tratamientos. Nueve de cada diez análisis son de una parcela, y hacer
 * pasar a todo el mundo por una pregunta que casi nunca aplica marea para nada.
 */
/**
 * El sitio de la muestra, ya en React: la tierra, la nave o el lote, y de qué partida era.
 *
 * **Este paso pide tres cosas a la vez**, y por eso se montan tres piezas seguidas: la lista de tierras
 * (o el aviso de que no hay ninguna), la lista de naves con su pregunta, y el campo del lote. Se
 * componen con `html`, que es lo que evita tener que inventar una pieza nueva para cada mezcla.
 */
function montarSitioDeLaMuestra() {
  const b = estado.asistente.borrador;

  const tierras = b.parcela_id
    ? null
    : estado.parcelas.length
      ? listaParaElegir({ bloques: [bloqueDeParcelas()] })
      : listaParaElegir({
          aviso: {
            texto: aviso("no_hay_parcelas"),
            boton: {
              etiqueta: t("maestros.anadir_primera_parcela", ""),
              icono: "📍",
              accion: "anadir-maestro",
              datos: { tipo: "parcela" },
              clase: "boton-principal",
            },
          },
        });

  const elegida = estado.parcelas.find((p) => p.id === Number(b.parcela_id));
  return html`
    ${tierras}
    ${
      elegida
        ? listaParaElegir({
            bloques: [
              // La frase compuesta («De dónde salió: El Prado») se monta aquí, que es quien conoce los
              // dos textos.
              { pista: `${t("analitica.sitio", "")}: ${elegida.alias}` },
            ],
          })
        : null
    }
    ${listaParaElegir({
      bloques: [
        // Las naves y balsas, para el agua o un lote guardado. Solo se ofrecen si las hay: si no, el
        // agricultor ve un hueco vacío que no puede rellenar.
        {
          titulo: t("etiquetas.analitica.no_es_parcela.pregunta", ""),
          pista: t("etiquetas.analitica.no_es_parcela.pista", ""),
          botones: (estado.instalaciones || []).map((instalacion) => ({
            etiqueta: instalacion.alias,
            pista: etiquetaDeValor("tipos_instalacion", instalacion.tipo),
            icono: "🏠",
            accion: "elegir",
            datos: { campo: "instalacion_id", valor: instalacion.id },
            clase:
              Number(b.instalacion_id) === instalacion.id ? "boton-elegido" : "boton-claro",
          })),
        },
      ],
    })}
    ${camposDelMaestro({ bloques: bloquesDelMaestro(["analitica.lote"]) })}
  `;
}

/** Los números de un análisis, como filas de etiqueta y valor (para la pieza del resumen). */
function filasDeLosNumerosDelAnalisis(analisis) {
  return (analisis.parametros_con_nombre || []).map((n) => [n.etiqueta, n.texto]);
}



/**
 * Los datos propios de cada práctica de labor, ya en React.
 *
 * Lo que se pregunta **cambia según la práctica**: mantener la cubierta pide sus fechas y sus anchuras,
 * pastorear pide de quién era el ganado, y podar o desbrozar piden dónde quedaron los restos. Una
 * práctica que no tenga preguntas propias **lo dice**, en vez de dejar la pantalla en blanco: es la
 * diferencia entre «aquí no hay nada que contestar» y «se ha roto algo».
 */
function montarDatosPropiosDeLaLabor(camposCubierta, camposRestos) {
  const elegido = estado.asistente.borrador.tipo;
  let claves = null;
  if (elegido === "cubierta") claves = camposCubierta;
  else if (elegido === "pastoreo") claves = ["labor.animales_terceros", "labor.animales_propios"];
  else if (elegido === "poda" || elegido === "desbroce") {
    claves = camposRestos.filter((campo) => campo.includes(elegido));
  }
  if (!claves || claves.length === 0) {
    return listaParaElegir({
      bloques: [{ pista: t("etiquetas.labor.datos_propios.sin_preguntas", "") }],
    });
  }
  return camposDelMaestro({ bloques: bloquesDelMaestro(claves) });
}

/**
 * Los números del boletín, ya en React.
 *
 * **Solo se piden los que trae el boletín de esa clase de análisis**, y salen del catálogo del servidor
 * (`parametros_analitica`): con un formulario fijo de veinte casillas, el agricultor tendría que adivinar
 * cuáles rellenar. Cada número lleva su unidad **dentro de la etiqueta**, porque es parte de la pregunta
 * («¿Cuánta materia orgánica? %»), y el `id` de cada casilla es `param-<clave>`, que es como lo lee
 * `recogeParametros()`. Ese `id` no se puede cambiar.
 */
function montarParametros() {
  const b = estado.asistente.borrador;
  const catalogo = t(`parametros_analitica.${b.tipo}`, []) || [];
  const puestos = b.parametros || {};

  if (catalogo.length === 0) {
    // Esta clase de análisis no trae números: se dice, en vez de dejar la pantalla en blanco.
    return listaParaElegir({ bloques: [{ pista: t("analitica.sin_numeros", "") }] });
  }

  return camposDelMaestro({
    bloques: catalogo.map((parametro) => {
      const valor = puestos[parametro.clave];
      return {
        tipo: "numero",
        id: `param-${parametro.clave}`,
        etiqueta: parametro.pregunta,
        valor: valor === undefined || valor === null ? "" : valor,
        unidad: parametro.unidad || "",
      };
    }),
  });
}

function recogeParametros() {
  const b = estado.asistente.borrador;
  const catalogo = t(`parametros_analitica.${b.tipo}`, []) || [];
  const puestos = {};
  for (const parametro of catalogo) {
    const elemento = document.getElementById(`param-${parametro.clave}`);
    // **Si el campo no está, se queda lo que ya había** (ronda 93). Al corregir un análisis los números
    // vienen puestos del boletín, y este paso no siempre se ha pintado (o el campo de ese número no
    // está): sustituyendo el diccionario entero, corregir la fecha de un análisis **le borraba los nueve
    // números**, que son los que después lee el plan de abono. Lo que sí se vacía —cuando cambia la clase
    // de análisis— se vacía en el paso de la clase, que es el único sitio donde se sabe que ha cambiado.
    if (!elemento) continue;
    // Lo que diga el campo manda, **aunque esté vacío**: si el agricultor borra un número, se borra.
    puestos[parametro.clave] = (elemento.value || "").trim();
  }
  b.parametros = { ...(b.parametros || {}), ...puestos };
  return null;
}

/** Las filas del resumen del análisis, ya preparadas: los datos y sus números (ver `filasDelResumenPlan`). */
function filasDelResumenAnalitica() {
  const b = estado.asistente.borrador;
  const catalogo = t(`parametros_analitica.${b.tipo}`, []) || [];
  const numeros = catalogo
    .filter((parametro) => {
      const valor = (b.parametros || {})[parametro.clave];
      return valor !== undefined && valor !== null && String(valor).trim() !== "";
    })
    .map((parametro) => [
      parametro.etiqueta || parametro.pregunta,
      `${formateaNumero(aNumero((b.parametros || {})[parametro.clave]), 2)}${
        parametro.unidad ? ` ${parametro.unidad}` : ""
      }`,
    ]);

  return [
    [t("etiquetas.analitica.tipo.pregunta", ""), etiquetaDeValor("tipos_analitica", b.tipo)],
    [t("analitica.sitio", ""), b.lote || ""],
    [t("etiquetas.analitica.fecha_toma_muestra.pregunta", ""), formateaFecha(b.fecha_toma_muestra)],
    [t("analitica.quien", ""), b.laboratorio || ""],
    ...numeros,
  ].filter(([, valor]) => valor);
}

function pasosAnalitica() {
  const et = (clave) => t(`etiquetas.${clave}.pregunta`, "");
  const pi = (clave) => t(`etiquetas.${clave}.pista`, "");
  return [
    {
      titulo: et("analitica.tipo"),
      pista: pi("analitica.tipo"),
      montar: () =>
        montarOpciones(
          "tipo",
          (t("tipos_analitica", []) || []).map((x) => x.valor),
          "analitica.tipo",
        ),
      recoger: () => {
        const b = estado.asistente.borrador;
        if (!b.tipo) return `${et("analitica.tipo")} — ${pi("analitica.tipo")}`;
        // La clase de análisis cambia qué números hay que preguntar, así que al elegirla se limpian los
        // que hubiera de la clase anterior: si no, quedarían números de tierra en un análisis de agua.
        //
        // **Pero solo si la clase ha cambiado** (ronda 93). Al **corregir** un análisis, este paso pasa
        // por aquí con la clase que ya tenía y **los números vienen puestos del boletín**: vaciarlos
        // siempre los borraba, así que corregir la fecha de un análisis le quitaba los nueve números —
        // que son justo los que después lee el plan de abono—. Lo cazó la prueba de «corregir un análisis
        // manda también sus números del boletín».
        if (String(b.tipo) !== String(estado.asistente.tipoOriginal || "")) {
          b.parametros = {};
          estado.asistente.tipoOriginal = b.tipo;
        }
        return null;
      },
    },
    {
      titulo: et("analitica.sitio"),
      pista: pi("analitica.sitio"),
      opcional: true,
      montar: montarSitioDeLaMuestra,
      recoger: () => {
        const b = estado.asistente.borrador;
        const deParcela = (t("analitica_de_parcela", []) || []).includes(b.tipo);
        if (deParcela && !b.parcela_id && !b.instalacion_id) {
          return `${et("analitica.sitio")} — ${pi("analitica.sitio")}`;
        }
        return null;
      },
    },
    {
      titulo: et("analitica.fecha_toma_muestra"),
      pista: pi("analitica.fecha_toma_muestra"),
      montar: () => montarFecha("fecha_toma_muestra", "analitica.fecha_toma_muestra"),
      recoger: () => {
        const elemento = document.getElementById("fecha_toma_muestra");
        if (elemento) estado.asistente.borrador.fecha_toma_muestra = elemento.value;
        return null;
      },
    },
    {
      titulo: et("analitica.parametros"),
      pista: pi("analitica.parametros"),
      opcional: true,
      montar: montarParametros,
      recoger: recogeParametros,
    },
    {
      titulo: et("analitica.laboratorio"),
      pista: pi("analitica.laboratorio"),
      opcional: true,
      montar: () => montarCamposMaestro(["analitica.laboratorio", "analitica.numero_informe"]),
      recoger: recogeCamposMaestro(["analitica.laboratorio", "analitica.numero_informe"]),
    },
    {
      titulo: et("analitica.fecha_resultado"),
      pista: pi("analitica.fecha_resultado"),
      opcional: true,
      montar: () =>
        montarCamposMaestro([
          "analitica.fecha_resultado",
          "analitica.sustancia_detectada",
          "analitica.observaciones",
        ]),
      recoger: recogeCamposMaestro([
        "analitica.fecha_resultado",
        "analitica.sustancia_detectada",
        "analitica.observaciones",
      ]),
    },
    {
      titulo: t("etiquetas.tratamiento.resumen.pregunta", ""),
      pista: t("etiquetas.tratamiento.resumen.pista", ""),
      montar: () => resumenDelApunte({ filas: filasDelResumenAnalitica() }),
    },
  ];
}

function cargaAnalitica() {
  const b = estado.asistente.borrador;
  const catalogo = t(`parametros_analitica.${b.tipo}`, []) || [];
  const parametros = catalogo
    .filter((parametro) => {
      const valor = (b.parametros || {})[parametro.clave];
      return valor !== undefined && valor !== null && String(valor).trim() !== "";
    })
    .map((parametro) => ({
      clave: parametro.clave,
      valor: String((b.parametros || {})[parametro.clave]).replace(",", "."),
    }));
  const parcela = estado.parcelas.find((p) => p.id === Number(b.parcela_id));
  return {
    campana_id: estado.campana.id,
    tipo: b.tipo,
    fecha_toma_muestra: b.fecha_toma_muestra || hoyISO(),
    fecha_resultado: b.fecha_resultado || null,
    parcela_id: Number(b.parcela_id) || null,
    instalacion_id: Number(b.instalacion_id) || null,
    lote: b.lote || null,
    laboratorio: b.laboratorio || null,
    nif_laboratorio: b.nif_laboratorio || null,
    numero_informe: b.numero_informe || null,
    tipo_analisis: b.tipo_analisis || null,
    sustancia_detectada: b.sustancia_detectada || null,
    parametros,
    observaciones: b.observaciones || null,
    _donde: parcela ? parcela.alias : b.lote || "",
  };
}

function pantallaAnaliticaGuardado(datos) {
  const guardado = datos || {};
  const a = (clave) => t(`analitica.${clave}`, "");
  montar(() =>
    confirmacion({
      titulo: a("guardado_titulo"),
      pista: a("guardado"),
      ayuda: { titulo: a("se_usa"), texto: a("aprovecha") },
      // El boletín se puede subir justo después de apuntarlo, que es cuando el agricultor lo tiene en la
      // mano. El `id` del campo es el de siempre (`informe-<id>`): `app.js` lo lee por ahí.
      archivo: {
        titulo: a("subir_ahora"),
        pista: a("subir_ahora_pista"),
        id: `informe-${guardado.id}`,
      },
      acciones: [
        {
          etiqueta: a("subir_informe"),
          accion: "analisis-informe-subir-ahora",
          datos: { id: guardado.id },
          clase: "boton",
          sencillo: true,
        },
        { etiqueta: a("ver"), accion: "analisis-ver", clase: "boton-claro", sencillo: true },
        { etiqueta: accion("volver"), accion: "ir-inicio", clase: "boton-claro", sencillo: true },
      ],
    }),
  );
}

/**
 * Sube el boletín del laboratorio.
 *
 * Va con `fetch` a mano y no con `enviarOApuntar` porque un fichero no se puede guardar
 * en la cola del móvil como si fuera un apunte de texto: la cola guarda JSON. Si no hay
 * cobertura, se dice claro en vez de apuntar algo que después no se podría mandar.
 */
async function subirInformeDeAnalisis(id, idDelCampo) {
  const entrada = document.getElementById(idDelCampo || `informe-${id}`);
  if (!entrada || !entrada.files || entrada.files.length === 0) {
    avisarDelError(t("analitica.el_informe", ""));
    return;
  }
  if (!navigator.onLine) {
    avisarDelError(aviso("no_se_pudo"));
    return;
  }
  const cuerpo = new FormData();
  cuerpo.append("fichero", entrada.files[0]);

  try {
    const respuesta = await fetch(`/api/analiticas/${id}/informe`, {
      method: "POST",
      headers: { Authorization: `Bearer ${estado.token}` },
      body: cuerpo,
    });
    if (!respuesta.ok) {
      const detalle = await respuesta.json().catch(() => null);
      throw new Error((detalle && detalle.detail) || mensaje("no_se_pudo"));
    }
  } catch (error) {
    avisarDelError(error.message);
    return;
  }
  await cargarDatos().catch(() => {});
  pantallaAnaliticas();
}

async function descargarInformeDeAnalisis(id) {
  const respuesta = await api(`/api/analiticas/${id}/informe`);
  if (!respuesta.ok) {
    const detalle = await respuesta.json().catch(() => null);
    avisarDelError((detalle && detalle.detail) || mensaje("no_se_pudo"));
    return;
  }
  const blob = await respuesta.blob();
  const enlace = document.createElement("a");
  enlace.href = URL.createObjectURL(blob);
  enlace.download = `analisis-${id}`;
  enlace.click();
  URL.revokeObjectURL(enlace.href);
}

// ---------------------------------------------------------------------------
// Las tierras en el mapa y en la tabla, y lo que ha sido una tierra (T06, 03/10/2026)
// ---------------------------------------------------------------------------
//
// **Qué es este bloque.** Todo lo que hace falta para las dos pantallas nuevas de T06: la vista de
// las 64 tierras con su tabla, sus filtros y su mapa (contrato §2.1), y la ficha de una tierra con sus
// versiones, la comparación de dos años y el ensayo de una importación (lo que T05 dejó pedido).
//
// **Las tres decisiones que se ven en el código, y por qué:**
//
//  1. **La vista se pide al abrir la pantalla, no al arrancar.** Son 64 tierras con sus anillos de
//     coordenadas: en el campo, que es cuando peor va la cobertura, nadie tiene por qué cargar con eso
//     para apuntar un tratamiento. Se guarda en `estado.t06.vista` y no se vuelve a pedir mientras la
//     pantalla esté abierta (salvo que se fuerce).
//  2. **El mapa no se abre en un sitio cualquiera.** La caja que se mira sale de la caja de la finca,
//     que la calcula el servidor **con las formas que de verdad hay** (`/api/parcelas/vista` →
//     `mapa.caja`, `null` cuando no hay ninguna). Y al acercarse, la caja se **queda dentro** de la de
//     la finca: así es imposible que el mapa salte a otra provincia, ni por un error de cuentas.
//  3. **Previsualizar y apuntar son dos caminos separados** (`ensayarTraerLoDeOtroAnio` y
//     `apuntarElLote`): el ensayo manda el lote a `/api/versiones/previsualizar`, que no escribe, y el
//     único sitio que manda algo a `/api/versiones/aplicar` es el botón de apuntarlo. Es la forma de
//     que «mirar cien veces no cambie nada» no dependa de que alguien se acuerde.

/** El tamaño de la imagen del mapa que se pide. Los mismos números que usa la pantalla del SIGPAC. */
const T06_ANCHO = 900;
const T06_ALTO = 600;
// El lado mínimo de la caja, en grados, para no pedirle al servicio una imagen que no puede dar.
// Es el mismo número que usa el servidor (`mapa.LADO_MINIMO_GRADOS`, unos 90 metros).
const T06_LADO_MINIMO = 0.0008;
// Y el lado **máximo**: el servicio oficial no da una caja de más de medio grado (unos 55 km). Es el
// mismo número que el servidor (`mapa.LADO_MAXIMO_GRADOS`), y aquí hace falta para no pedir una caja
// que el propio programa rechaza (revisión de T06, D7).
const T06_LADO_MAXIMO = 0.5;
// Cuánto se deja alrededor de una tierra al enfocarla: un trozo que ocupa el 70 % de la imagen se ve
// con su linde alrededor, que es como el agricultor reconoce dónde está.
const T06_MARGEN_AL_ENFOCAR = 1.4;

/** El estado de las dos pantallas de T06, creado la primera vez que hace falta. */
function elEstadoDeT06() {
  if (!estado.t06) {
    estado.t06 = {
      vista: null,
      filtro: { q: "", cultivo: "", municipio: "", revision: "", pac: "" },
      grupo: "",
      marcadas: [],
      elegida: null,
      // Las tierras que comparten el trozo que se está mirando (ver `elegirUnaTierra`).
      mismoRecinto: [],
      // El mapa: qué capa se ve debajo, si se ven las rayas de las tierras y por dónde se mira.
      capa: "foto",
      ver_mis_tierras: true,
      centro: null,
      zoom: 1,
      capas: {},
      capa_avisos_no_esta: "",
      leyenda_mis_tierras: "",
      si_no_llega_una_imagen: "",
      fallo: "",
      // La ficha de una tierra con sus versiones.
      versionParcela: null,
      versiones: [],
      compararAntes: null,
      compararDespues: null,
      comparacion: null,
      ensayo: null,
      ensayando: false,
      error: "",
    };
  }
  return estado.t06;
}

/**
 * Los textos de la vista de las tierras.
 *
 * **Se piden a `/api/interfaz` y, si no están, a la propia vista.** El orden importa y tiene su
 * motivo: la ficha de una tierra con sus versiones se puede abrir **directamente por su dirección**
 * (`#/tierras/2/versiones`) sin haber pasado por la pantalla del mapa, y entonces no hay ninguna vista
 * descargada de la que sacar las palabras. Los de `/api/interfaz` sí están guardados en el móvil, así
 * que la ficha tiene sus textos hasta **sin cobertura**; los de la vista quedan como respaldo.
 */
function losTextosDeT06() {
  const deLaInterfaz = t("tierras", null);
  if (deLaInterfaz && Object.keys(deLaInterfaz).length) return deLaInterfaz;
  return (elEstadoDeT06().vista || {}).textos || {};
}

/** Los textos de la ficha de una tierra, con el mismo cuidado y por el mismo motivo. */
function losTextosDeLasVersiones() {
  const deLaInterfaz = t("versiones", null);
  if (deLaInterfaz && Object.keys(deLaInterfaz).length) return deLaInterfaz;
  return (elEstadoDeT06().vista || {}).textos_de_las_versiones || {};
}

/**
 * La caja de toda la finca, tal y como la ha calculado el servidor.
 *
 * `null` cuando **ninguna tierra tiene forma medida**: en ese caso no hay mapa que abrir, y la
 * pantalla lo dice. Lo que no se hace es poner un centro a ojo.
 */
function laCajaDeLaFinca() {
  const mapa = (elEstadoDeT06().vista || {}).mapa || {};
  return mapa.caja || null;
}

/** ¿Cabe toda la finca en **una** imagen del mapa? Lo dice el servidor, que sabe cuánto miden. */
function laVistaCabeEntera() {
  const mapa = (elEstadoDeT06().vista || {}).mapa || {};
  return mapa.se_puede_ensenar_entera !== false;
}

/** El rectángulo que envuelve una tierra, sacado de sus anillos de verdad. */
function laCajaDeUnaTierra(tierra) {
  const puntos = (tierra.anillos || []).flat();
  if (!puntos.length) return null;
  const longitudes = puntos.map(([longitud]) => longitud);
  const latitudes = puntos.map(([, latitud]) => latitud);
  return {
    oeste: Math.min(...longitudes),
    sur: Math.min(...latitudes),
    este: Math.max(...longitudes),
    norte: Math.max(...latitudes),
  };
}

/**
 * La caja que se está mirando: la de la finca, encogida alrededor de su centro según el zoom.
 *
 * **Se queda dentro de la caja de la finca**, y eso es lo que hace imposible que el mapa enseñe otra
 * provincia: al acercarse, el centro se desplaza lo justo para que el borde no se salga. Es una
 * decisión, no una casualidad: la pantalla no tiene ninguna forma de pedir coordenadas a mano.
 */
function laCajaQueSeMira() {
  const t06 = elEstadoDeT06();
  const finca = laCajaDeLaFinca();
  if (!finca) return null;
  // **La finca entera se devuelve tal cual la dio el servidor.** No es un atajo: recalcularla con
  // «centro ± mitad» mete un error de coma flotante (40,91 sale 40,910000000000004), y esa caja se
  // manda al servicio de mapas y se compara con la suya. Cuando no hay nada que encoger, se devuelve
  // el número que vino.
  if (!t06.centro && (Number(t06.zoom) || 1) >= 1 && laVistaCabeEntera()) return { ...finca };
  const anchoDeLaFinca = finca.este - finca.oeste;
  const altoDeLaFinca = finca.norte - finca.sur;
  const ladoDeLaFinca = Math.max(anchoDeLaFinca, altoDeLaFinca);
  // El zoom nunca pasa de 1 (toda la finca) ni baja de lo que el servicio de mapas acepta.
  //
  // **Y por arriba tiene otro tope que no es un capricho** (revisión de T06, D7): el servicio no da
  // una caja de más de medio grado, así que una finca repartida en más que eso **no se puede enseñar
  // entera**. En vez de pedir la imagen con una caja que el propio programa rechaza —y acabar
  // enseñando «puede ser la cobertura» delante de un fallo que no tiene que ver con la cobertura—, la
  // caja se queda en el máximo que se puede pedir, y la pantalla lo dice.
  const porArriba = T06_LADO_MAXIMO / ladoDeLaFinca;
  const minimo = ladoDeLaFinca > 0 ? Math.min(T06_LADO_MINIMO / ladoDeLaFinca, 1) : 1;
  const maximo = Math.min(1, porArriba);
  const factor = Math.min(Math.max(Number(t06.zoom) || 1, minimo), maximo);
  const ancho = anchoDeLaFinca * factor;
  const alto = altoDeLaFinca * factor;
  const centro = t06.centro || {
    lon: (finca.oeste + finca.este) / 2,
    lat: (finca.sur + finca.norte) / 2,
  };
  let oeste = centro.lon - ancho / 2;
  let sur = centro.lat - alto / 2;
  // **Y con la finca recortada, el centro no se mete dentro de la caja de la finca**: una tierra que
  // está fuera de la parte que se ve (una finca repartida en más de lo que cabe, o una coordenada mal
  // apuntada) tiene que poder centrarse igual. Si se metiera, el agricultor tocaría esa tierra en la
  // lista y el mapa no se movería a ningún sitio, sin decir por qué.
  if (ancho < anchoDeLaFinca) oeste = Math.min(Math.max(oeste, finca.oeste), finca.este - ancho);
  if (alto < altoDeLaFinca) sur = Math.min(Math.max(sur, finca.sur), finca.norte - alto);
  if (!laVistaCabeEntera()) {
    oeste = centro.lon - ancho / 2;
    sur = centro.lat - alto / 2;
  }
  return { oeste, sur, este: oeste + ancho, norte: sur + alto };
}

/**
 * La dirección de la imagen del mapa para la caja que se está mirando.
 *
 * **La imagen la sirve el programa**, no el IGN: el navegador pide `/api/mapa/imagen` y es el servidor
 * el que habla con el servicio oficial. Así, si el servicio se cae, el agricultor ve un aviso en
 * castellano en vez de una imagen rota.
 */
function laDireccionDeLaImagen() {
  const t06 = elEstadoDeT06();
  const caja = laCajaQueSeMira();
  if (!caja) return "";
  const parametros = new URLSearchParams({
    capa: t06.capa,
    oeste: String(caja.oeste),
    sur: String(caja.sur),
    este: String(caja.este),
    norte: String(caja.norte),
    ancho: String(T06_ANCHO),
    alto: String(T06_ALTO),
  });
  return `/api/mapa/imagen?${parametros.toString()}`;
}

/** Las líneas de la leyenda del mapa, **ya escritas**: la frase del servidor con el dato dentro. */
function laLeyendaDelMapa() {
  const t06 = elEstadoDeT06();
  const textos = losTextosDeT06();
  const capa = (t06.capas || {})[t06.capa];
  if (!capa) return [];
  return [
    rellena(textos.lo_da || "", { servicio: capa.servicio || "" }),
    capa.leyenda || "",
    rellena(textos.fecha_de_la_imagen || "", {
      cuando: capa.fecha_texto || textos.fecha_sin_saber || "",
    }),
    t06.leyenda_mis_tierras || "",
  ].filter(Boolean);
}

/** Las hectáreas de una tierra, ya en castellano, o vacío cuando no se saben. */
function lasHectareasONada(valor) {
  if (valor === null || valor === undefined || valor === "") return "";
  return `${formateaNumero(valor, 2)} ${t("rotulos.hectareas_corto", "")}`.trim();
}

/** Pide la vista de las tierras al servidor. Es lo único que se pide al abrir la pantalla. */
async function cargarLaVistaDeLasTierras() {
  const t06 = elEstadoDeT06();
  const vista = await apiJson("/api/parcelas/vista");
  t06.vista = vista;
  t06.error = "";
  // La leyenda de las capas (y lo que se dice de la capa de avisos) la sirve `/api/mapa/estado`. Si no
  // llega, la pantalla sigue funcionando: se queda sin leyenda, no sin mapa ni sin tabla.
  try {
    const estadoDelMapa = await apiJson("/api/mapa/estado");
    const textos = (vista.textos || {});
    t06.capas = estadoDelMapa.capas || {};
    t06.capa_avisos_no_esta = textos.capa_avisos_no_esta || "";
    t06.leyenda_mis_tierras = estadoDelMapa.leyenda_de_mis_tierras || "";
    t06.si_no_llega_una_imagen = estadoDelMapa.si_no_llega_una_imagen || "";
  } catch (fallo) {
    t06.capas = t06.capas || {};
  }
  return vista;
}

/**
 * Abre la pantalla de las tierras en el mapa y en la tabla.
 *
 * Si la vista no está descargada, se pide. Si no se puede (sin cobertura la primera vez), la pantalla
 * sale con su aviso y con el botón de volver: lo que no se hace es dejarla en blanco.
 */
async function abrirLasTierrasDelMapa() {
  const t06 = elEstadoDeT06();
  if (!t06.vista) {
    try {
      await cargarLaVistaDeLasTierras();
    } catch (fallo) {
      t06.error = fallo.message || "";
    }
  }
  return pantallaTierrasDelMapa();
}

/** La pantalla de las tierras, con todo lo que necesita ya preparado. */
function pantallaTierrasDelMapa() {
  const t06 = elEstadoDeT06();
  const vista = t06.vista || {};
  const textos = vista.textos || {};
  const tierras = (vista.tierras || []).map((tierra) => ({
    ...tierra,
    superficie_texto: lasHectareasONada(tierra.superficie_ha),
    forma_texto: tierra.tiene_forma ? textos.con_forma || "" : "",
    revision_texto: tierra.estado_revision_texto || "",
    // **El nombre repetido, dicho.** El recuento lo da el servidor; aquí solo se rellena la frase.
    nombre_repetido_texto:
      (tierra.cuantas_con_el_mismo_nombre || 0) > 1
        ? rellena(textos.nombre_repetido || "", {
            cuantas: tierra.cuantas_con_el_mismo_nombre,
          })
        : "",
    // **Y las hectáreas que el agricultor declara este año**, cuando la tierra no tiene dicha su
    // superficie. La columna «Hectáreas» es la superficie de la tierra —esa es la regla que usan a la
    // vez la fila, el pie y el filtro, y tiene que seguir siéndolo—, así que lo declarado no se mete
    // en la misma casilla como si fuera lo mismo: se enseña **debajo, con su nombre**. Sin esto, una
    // tierra traída del cuaderno de la Junta sin superficie enseñaba un hueco mientras su versión sí
    // tenía las hectáreas declaradas (revisión de T06, D1).
    hectareas_declaradas_texto: lasHectareasONada(tierra.area_declarada_ha)
      ? rellena(textos.hectareas_declaradas_pista || "", {
          hectareas: lasHectareasONada(tierra.area_declarada_ha),
        })
      : "",
  }));
  const hayForma = Boolean((vista.mapa || {}).hay_forma);
  // Y cuando el trozo que se mira lo comparten varias tierras, cuántas son. Se cuenta sobre la misma
  // lista que la tabla, así que la frase y las filas encendidas no pueden decir cosas distintas.
  const mismoRecinto = t06.mismoRecinto || [];
  return montar(() =>
    pantallaDeLasTierrasDeLaExplotacion({
      textos: { tierras: textos, mapa: t("mapa", {}), acciones: { volver: t("acciones.volver", "") } },
      vista: { ...vista, tierras },
      filtro: t06.filtro,
      grupo: t06.grupo,
      marcadas: t06.marcadas || [],
      elegida: t06.elegida,
      mismoRecinto,
      mapa: {
        capa: t06.capa,
        ver_mis_tierras: t06.ver_mis_tierras,
        capas: t06.capas || {},
        url: laDireccionDeLaImagen(),
        caja: laCajaQueSeMira(),
        ancho: T06_ANCHO,
        alto: T06_ALTO,
        tiene_forma: hayForma,
        fallo: t06.fallo,
        capa_avisos_no_esta: t06.capa_avisos_no_esta,
        leyenda: laLeyendaDelMapa(),
        recinto_compartido_texto:
          mismoRecinto.length > 1
            ? rellena(textos.recinto_compartido || "", { cuantas: mismoRecinto.length })
            : "",
        // Y cuando la finca entera no cabe en una imagen, se dice antes de que nadie lea un aviso de
        // cobertura que no es: arriba se ve solo una parte, y elegir una tierra pone el mapa en ella.
        no_caben_todas_texto: laVistaCabeEntera() ? "" : textos.no_caben_todas || "",
        alNoLlegarLaImagen: () => avisarDeQueLaImagenNoLlega(),
      },
      aviso: t06.error,
    }),
  );
}

/**
 * La imagen de una capa no ha llegado.
 *
 * **Qué se hace, y por qué es esto y no otra cosa** (contrato §2.1: «Si falla una imagen WMS, no
 * borrar los polígonos ni dejar una fotografía vieja sin fecha»):
 *
 *  · no se borra **ningún polígono**: las rayas de las tierras se siguen dibujando;
 *  · no se deja la foto vieja puesta: la imagen se quita y en su sitio va el aviso, porque una foto
 *    que no es la de esta caja (y sin fecha) es peor que no tener foto;
 *  · y se dice **qué puede hacer mientras tanto**: la lista funciona igual.
 *
 * El `if` del principio no es un adorno: sin él, cada repintado volvería a intentar la misma imagen
 * que ya falló y la pantalla se quedaría dando vueltas.
 */
function avisarDeQueLaImagenNoLlega() {
  const t06 = elEstadoDeT06();
  if (t06.fallo) return;
  t06.fallo = t06.si_no_llega_una_imagen || mensaje("sin_cobertura");
  return pantallaTierrasDelMapa();
}

/** Aplica a `estado.t06` lo que venga en una dirección, antes de pedir nada. */
function aplicarLaDireccionAT06(parametros = {}) {
  const t06 = elEstadoDeT06();
  t06.filtro = {
    q: parametros.q === undefined ? "" : String(parametros.q || ""),
    cultivo: parametros.cultivo ? String(parametros.cultivo) : "",
    municipio: parametros.municipio ? String(parametros.municipio) : "",
    revision: parametros.revision ? String(parametros.revision) : "",
    pac: parametros.pac ? String(parametros.pac) : "",
  };
  t06.grupo = parametros.grupo ? String(parametros.grupo) : "";
  t06.elegida = parametros.id ? Number(parametros.id) : null;
  t06.mismoRecinto = t06.elegida ? [t06.elegida] : [];
  t06.capa = parametros.capa ? String(parametros.capa) : "foto";
  // Las marcadas viajan con guiones («3-7-12») porque una dirección no lleva listas: es la misma
  // decisión de siempre, un dato sencillo y legible.
  t06.marcadas = parametros.marcadas
    ? String(parametros.marcadas)
        .split("-")
        .map((uno) => Number(uno))
        .filter((uno) => Number.isFinite(uno) && uno > 0)
    : [];
  return t06;
}

/** Pone un filtro y vuelve a pintar. Un valor vacío es «quitar ese filtro». */
function filtrarLasTierrasDeLaVista(campo, valor) {
  const t06 = elEstadoDeT06();
  if (!["cultivo", "municipio", "revision", "pac"].includes(campo)) return;
  t06.filtro[campo] = valor || "";
  return pantallaTierrasDelMapa();
}

/** Lee lo que el agricultor ha escrito en el buscador y filtra por ello. */
function buscarEnLasTierras() {
  const t06 = elEstadoDeT06();
  t06.filtro.q = valorDe("t06_buscar") || "";
  return pantallaTierrasDelMapa();
}

/** Quita todos los filtros de golpe: es la salida de «con esos filtros no hay ninguna tierra». */
function quitarLosFiltrosDeLasTierras() {
  const t06 = elEstadoDeT06();
  t06.filtro = { q: "", cultivo: "", municipio: "", revision: "", pac: "" };
  return pantallaTierrasDelMapa();
}

/** Cambia cómo se agrupa la lista. */
function agruparLasTierrasDeLaVista(valor) {
  elEstadoDeT06().grupo = valor || "";
  return pantallaTierrasDelMapa();
}

/**
 * Enfoca una tierra: se enciende su fila **y** su trozo en el mapa.
 *
 * Es la mitad del enlace que pide el contrato («al seleccionar un polígono se enfoca la fila y
 * viceversa»): la otra mitad es que el mapa lleva la misma acción en cada polígono, así que tocar el
 * trozo llama a esta misma función con el identificador de su tierra.
 *
 * Si la tierra **no tiene forma**, no se mueve el mapa: se enciende su fila y se dice con qué se
 * encuentra. Mover el mapa buscando una forma que no existe sería enseñar otro sitio.
 */
function elegirUnaTierra(id) {
  const t06 = elEstadoDeT06();
  const numero = Number(id);
  if (!Number.isFinite(numero)) return;
  t06.elegida = numero;
  const tierras = ((t06.vista || {}).tierras) || [];
  const tierra = tierras.find((una) => Number(una.id) === numero);
  // **El trozo que se está mirando puede ser el de varias tierras.** En los datos de verdad hay más
  // tierras que referencias distintas: el cuaderno de la Junta parte un mismo recinto en varias líneas
  // de cultivo, así que varias filas **son el mismo trozo de tierra** y comparten su forma. Al tocar el
  // trozo no se elige una fila al azar: se encienden todas las que son de ese recinto y se dice cuántas
  // son. La clave la da el servidor (`clave_recinto`), calculada con la referencia o, si no la hay, con
  // la huella de la forma: **una sola forma de decidirlo**.
  //
  // **Los números, medidos sobre su finca (explotación 1) y dichos con lo que son**: 64 tierras y
  // **51 referencias distintas**; una sola referencia la comparten **9 tierras** y otra 6. (En toda la
  // base son 65 y 52: hay una tierra más en otra explotación, y por eso se dice cuál es cuál — quien
  // vuelva a medir y le salga 52 sabrá que ha medido otra cosa, no que se haya equivocado.)
  const suya = tierra ? tierra.clave_recinto : null;
  t06.mismoRecinto = suya
    ? tierras.filter((una) => una.clave_recinto === suya).map((una) => Number(una.id))
    : [numero];
  if (t06.mismoRecinto.length < 2) t06.mismoRecinto = [numero];
  const caja = tierra ? laCajaDeUnaTierra(tierra) : null;
  const finca = laCajaDeLaFinca();
  if (caja && finca) {
    const anchoDeLaFinca = Math.max(finca.este - finca.oeste, 1e-9);
    const altoDeLaFinca = Math.max(finca.norte - finca.sur, 1e-9);
    const ancho = Math.max(caja.este - caja.oeste, T06_LADO_MINIMO);
    const alto = Math.max(caja.norte - caja.sur, T06_LADO_MINIMO);
    const factor = Math.max((ancho * T06_MARGEN_AL_ENFOCAR) / anchoDeLaFinca, (alto * T06_MARGEN_AL_ENFOCAR) / altoDeLaFinca);
    t06.zoom = Math.min(Math.max(factor, T06_LADO_MINIMO / Math.max(anchoDeLaFinca, altoDeLaFinca)), 1);
    t06.centro = { lon: (caja.oeste + caja.este) / 2, lat: (caja.sur + caja.norte) / 2 };
  }
  // Al mirar otra tierra, el aviso de la imagen que no llegó se limpia: la caja ha cambiado y merece
  // la pena volver a intentarlo.
  t06.fallo = "";
  return pantallaTierrasDelMapa();
}

/** Marca o desmarca una tierra (la selección múltiple que pide el contrato). */
function marcarUnaTierra(id) {
  const t06 = elEstadoDeT06();
  const numero = Number(id);
  if (!Number.isFinite(numero)) return;
  const ya = (t06.marcadas || []).some((una) => Number(una) === numero);
  t06.marcadas = ya
    ? t06.marcadas.filter((una) => Number(una) !== numero)
    : [...(t06.marcadas || []), numero];
  return pantallaTierrasDelMapa();
}

/** Marca **las que se están viendo**, que es lo que hace falta después de filtrar. */
function marcarTodasLasQueSeVen() {
  const t06 = elEstadoDeT06();
  const tierras = (((t06.vista || {}).tierras) || []).map((tierra) => ({
    ...tierra,
    superficie_texto: lasHectareasONada(tierra.superficie_ha),
  }));
  const seVen = filtrarLasTierras(tierras, t06.filtro);
  t06.marcadas = [...new Set([...(t06.marcadas || []), ...seVen.map((una) => Number(una.id))])];
  return pantallaTierrasDelMapa();
}

/** Quita la selección entera. */
function desmarcarTodasLasTierras() {
  elEstadoDeT06().marcadas = [];
  return pantallaTierrasDelMapa();
}

/** Cambia la capa que se ve debajo de los linderos (la foto, los linderos o lo declarado). */
function cambiarLaCapaDelMapa(capa) {
  const t06 = elEstadoDeT06();
  if (!Object.prototype.hasOwnProperty.call(t06.capas || {}, capa)) return;
  t06.capa = capa;
  t06.fallo = "";
  return pantallaTierrasDelMapa();
}

/** Enseña o quita las rayas de las tierras: el contrato pide que se puedan ocultar capas. */
function verOLosLinderosDeMisTierras() {
  const t06 = elEstadoDeT06();
  t06.ver_mis_tierras = !t06.ver_mis_tierras;
  return pantallaTierrasDelMapa();
}

/** Encaja toda la finca: es el botón con el que se vuelve después de haberse acercado a una tierra. */
function encajarTodaLaFinca() {
  const t06 = elEstadoDeT06();
  t06.zoom = 1;
  t06.centro = null;
  t06.fallo = "";
  return pantallaTierrasDelMapa();
}

/**
 * Acerca y aleja, **sin salirse nunca de la finca**.
 *
 * El zoom se dobla y se parte por dos, y el tope de alejarse es la finca entera (factor 1). El de
 * acercarse es el lado mínimo que acepta el servicio de mapas, para no pedir una imagen que no va a
 * llegar.
 */
function acercarOAlejarElMapa(veces) {
  const t06 = elEstadoDeT06();
  const finca = laCajaDeLaFinca();
  if (!finca) return pantallaTierrasDelMapa();
  const ladoDeLaFinca = Math.max(finca.este - finca.oeste, finca.norte - finca.sur, 1e-9);
  const minimo = Math.min(T06_LADO_MINIMO / ladoDeLaFinca, 1);
  t06.zoom = Math.min(Math.max((Number(t06.zoom) || 1) * veces, minimo), 1);
  t06.fallo = "";
  return pantallaTierrasDelMapa();
}

// --- Lo que ha sido una tierra: sus versiones, la comparación y el ensayo ---------------------

/**
 * Pide las versiones de una tierra y las deja en el estado, **sin tocar nada más**.
 *
 * Se separa de `abrirLasVersionesDeUnaTierra` por un motivo concreto: al apuntar un lote hay que
 * volver a leer las versiones para que se vea lo que se acaba de escribir, y eso **no** puede borrar
 * el ensayo que se está mirando (si lo borrara, el agricultor apuntaría algo y el aviso de «ya está
 * apuntado» desaparecería en el mismo instante).
 */
async function cargarLasVersionesDeUnaTierra(id) {
  const t06 = elEstadoDeT06();
  t06.versiones = (await apiJson(`/api/versiones?parcela_id=${encodeURIComponent(id)}`)) || [];
  const anios = aniosConVersiones(t06.versiones);
  t06.compararAntes = anios.length > 1 ? anios[1].anio : null;
  t06.compararDespues = anios.length ? anios[0].anio : null;
  return t06.versiones;
}

/**
 * Abre la ficha de una tierra con sus versiones.
 *
 * Se piden **las versiones de esa tierra** (`/api/versiones?parcela_id=…`), que es lo que hace que la
 * pantalla se reconstruya entera al recargar su dirección. El error se enseña en la pantalla, no se
 * traga: si el servidor no contesta, el agricultor tiene que saberlo.
 */
async function abrirLasVersionesDeUnaTierra(id) {
  const t06 = elEstadoDeT06();
  t06.versionParcela = Number(id);
  t06.error = "";
  // Abrir la ficha de una tierra de cero **sí** limpia lo que se estaba mirando: un ensayo o una
  // comparación de la tierra anterior encima de esta serían datos de otra parcela.
  t06.comparacion = null;
  t06.ensayo = null;
  t06.ensayando = false;
  try {
    await cargarLasVersionesDeUnaTierra(id);
  } catch (fallo) {
    t06.versiones = [];
    t06.error = fallo.message || "";
  }
  return pantallaVersionesDeUnaTierra();
}

/** Las versiones de una tierra, ordenadas del año más nuevo al más viejo y con sus datos escritos. */
function lasVersionesPreparadas() {
  const t06 = elEstadoDeT06();
  const textos = losTextosDeLasVersiones();
  return [...(t06.versiones || [])]
    .sort((una, otra) => (otra.anio || 0) - (una.anio || 0) || String(una.fuente).localeCompare(String(otra.fuente)))
    .map((version) => ({
      id: version.id,
      // El título lo monta `app.js`: es el año con la fuente, dos datos del servidor unidos aquí.
      titulo: [version.anio === null ? "" : String(version.anio), version.fuente_texto || ""]
        .filter(Boolean)
        .join(" · "),
      como_esta: version.como_esta || "",
      filas: [
        version.referencia
          ? { etiqueta: textos.referencia || "", valor: version.referencia }
          : {
              etiqueta: textos.referencia || "",
              valor: version.poligono_valido
                ? textos.sin_referencia_numeros || ""
                : textos.le_falta_el_recinto || "",
            },
        { etiqueta: textos.el_area_de_la_forma || "", valor: lasHectareasONada(version.area_geometria_ha) || textos.no_se_sabe || "" },
        { etiqueta: textos.el_area_del_sigpac || "", valor: lasHectareasONada(version.area_sigpac_ha) || textos.no_se_sabe || "" },
        { etiqueta: textos.el_area_declarada || "", valor: lasHectareasONada(version.area_declarada_ha) || textos.no_se_sabe || "" },
        { etiqueta: textos.cuando_se_miro || "", valor: version.fecha_consulta ? formateaFecha(version.fecha_consulta) : textos.sin_fecha_de_consulta || "" },
        { etiqueta: textos.como_esta || "", valor: version.estado_texto || "" },
      ].filter((fila) => fila.etiqueta),
      avisos: version.uso_sigpac ? [version.uso_sigpac] : [],
    }));
}

/** Los años que se pueden comparar: los que tienen versiones de esta tierra. */
function losAniosQueSePuedenComparar() {
  return aniosConVersiones(elEstadoDeT06().versiones).map((uno) => ({
    valor: uno.anio,
    texto: String(uno.anio),
  }));
}

/** La comparación de dos años, ya escrita para leerla. */
function laComparacionPreparada() {
  const t06 = elEstadoDeT06();
  const textos = losTextosDeLasVersiones();
  const comparacion = t06.comparacion;
  if (!comparacion) return null;
  return {
    resumen: comparacion.resumen || "",
    cuenta: [
      { etiqueta: textos.cuenta_iguales || "", valor: comparacion.iguales, clase: "bien" },
      { etiqueta: textos.cuenta_cambiados || "", valor: comparacion.cambiados, clase: "mirar" },
      { etiqueta: textos.cuenta_desaparecidos || "", valor: comparacion.desaparecidos, clase: "mirar" },
      { etiqueta: textos.cuenta_nuevos || "", valor: comparacion.nuevos, clase: "bien" },
    ],
    cambios: (comparacion.cambios || []).map((cambio) => ({
      estado_texto: cambio.estado_texto || "",
      clase: claseDelEstado(cambio.estado),
      titulo: [cambio.tierra || "", cambio.referencia || cambio.clave || ""].filter(Boolean).join(" · "),
      que_cambio: (cambio.que_cambio || []).length
        ? `${textos.que_cambio || ""}: ${cambio.que_cambio.join(", ")}`
        : textos.no_cambio_nada || "",
    })),
  };
}

/** El estilo con el que se dice cada estado de la comparación. Cuatro estados, cuatro clases. */
function claseDelEstado(estado) {
  if (estado === "igual") return "bien";
  if (estado === "nuevo") return "voluntario";
  return "mirar";
}

/** Los años y las fuentes de los que se puede traer algo, para ensayarlo antes. */
function loQueSePuedeTraer() {
  const t06 = elEstadoDeT06();
  const textos = losTextosDeLasVersiones();
  const elDeAhora = (estado.campana || {}).id;
  const vistos = new Set();
  const opciones = [];
  for (const version of t06.versiones || []) {
    if (!version.campana_id || version.campana_id === elDeAhora) continue;
    const clave = `${version.campana_id}-${version.fuente}`;
    if (vistos.has(clave)) continue;
    vistos.add(clave);
    opciones.push({
      fuente: version.fuente,
      campana: String(version.campana_id),
      pista: rellena(textos.traer_de_anio || "", {
        anio: version.anio === null ? "" : version.anio,
        fuente: version.fuente_texto || "",
      }),
    });
  }
  return opciones;
}

/** La pantalla de lo que ha sido una tierra. */
function pantallaVersionesDeUnaTierra() {
  const t06 = elEstadoDeT06();
  const textos = losTextosDeLasVersiones();
  const textosDeLasTierras = losTextosDeT06();
  const parcela = (estado.parcelas || []).find((una) => Number(una.id) === Number(t06.versionParcela));
  const anios = aniosConVersiones(t06.versiones);
  const puedeComparar = anios.length > 1;
  return montar(() =>
    pantallaDeLasVersionesDeUnaTierra({
      textos: {
        versiones: textos,
        mapa: t("mapa", {}),
        acciones: { volver: t("acciones.volver", "") },
      },
      tierra: {
        id: t06.versionParcela,
        titulo: parcela ? parcela.alias : "",
        abrir_en_el_mapa: textosDeLasTierras.abrir_en_el_mapa || "",
        filas: parcela
          ? [
              parcela.ref_sigpac
                ? { etiqueta: textos.referencia || "", valor: parcela.ref_sigpac }
                : null,
              parcela.municipio
                ? { etiqueta: textos.el_uso || "", valor: parcela.municipio }
                : null,
              {
                etiqueta: textos.el_area_declarada || "",
                valor: lasHectareasONada(parcela.superficie_ha) || textos.no_se_sabe || "",
              },
            ].filter(Boolean)
          : [],
      },
      versiones: lasVersionesPreparadas(),
      comparar: {
        puede: puedeComparar,
        sin_datos: textos.comparar_sin_datos || "",
        anios: losAniosQueSePuedenComparar(),
        antes: t06.compararAntes,
        despues: t06.compararDespues,
        comparacion: laComparacionPreparada(),
      },
      traer: loQueSePuedeTraer(),
      ensayo: elEnsayoPreparado(),
      aviso: t06.error,
    }),
  );
}

/** El resultado del ensayo, tal y como se lee: los cuatro números, el detalle y lo que no se pudo. */
function elEnsayoPreparado() {
  const t06 = elEstadoDeT06();
  const textos = losTextosDeLasVersiones();
  const plan = t06.ensayo;
  if (!plan) return null;
  return {
    titulo: plan.fuente_texto
      ? `${textos.recintos_que_trae || ""} · ${plan.fuente_texto}${plan.anio ? ` ${plan.anio}` : ""}`
      : textos.recintos_que_trae || "",
    filas: [
      { etiqueta: textos.recintos_que_trae || "", valor: plan.recintos_en_el_lote },
      { etiqueta: textos.cuenta_iguales || "", valor: plan.iguales },
      { etiqueta: textos.cuenta_cambiados || "", valor: plan.cambiados },
      { etiqueta: textos.cuenta_nuevos || "", valor: plan.nuevos },
      { etiqueta: textos.tierras_nuevas || "", valor: plan.tierras_nuevas },
      // **El recuento de recintos sin forma lleva su nombre**, y no la etiqueta de «No se sabe»:
      // no es un dato que no se sepa —de un recinto sin polígono se sabe todo lo demás—, es un
      // recuento. Lo cazó la revisión de T06 (D9), y en pantalla se leía «No se sabe: 3».
      { etiqueta: textos.recintos_sin_forma || "", valor: plan.sin_forma },
    ],
    detalle: (plan.detalle || []).map((recinto) => ({
      estado_texto: recinto.estado_texto || "",
      clase: claseDelEstado(recinto.estado),
      titulo: [recinto.tierra || "", recinto.referencia || recinto.clave || ""].filter(Boolean).join(" · "),
      que_cambio: (recinto.que_cambia || []).length
        ? `${textos.que_cambio || ""}: ${recinto.que_cambia.join(", ")}`
        : "",
    })),
    avisos: avisosDelEnsayo(plan, textos),
    // **Las dos frases que dicen si esto se ha apuntado o no.** Es lo que hace visible que ensayar no
    // escribe: mientras `aplicada` sea falso, la pantalla dice que no se ha apuntado nada.
    apuntado: plan.aplicada
      ? rellena(textos.apuntado_el_lote || "", {
          creadas: plan.versiones_creadas,
          actualizadas: plan.versiones_actualizadas,
          iguales: plan.iguales,
        })
      : "",
    sin_apuntar: plan.aplicada ? "" : textos.no_se_ha_apuntado || "",
    apuntando: t06.ensayando,
  };
}

/** Lo que el ensayo dice que no ha podido tener en cuenta: problemas, solapes y superficies. */
function avisosDelEnsayo(plan, textos) {
  const bloques = [];
  if ((plan.problemas || []).length) {
    bloques.push({ titulo: textos.lo_que_no_se_pudo || "", lineas: plan.problemas });
  }
  if ((plan.solapes || []).length) {
    bloques.push({
      titulo: textos.trozos_que_se_pisan || "",
      lineas: plan.solapes.map((solape) =>
        [solape.referencia_a || solape.clave_a, solape.referencia_b || solape.clave_b, solape.como_texto]
          .filter(Boolean)
          .join(" · "),
      ),
    });
  }
  if ((plan.diferencias_de_superficie || []).length) {
    bloques.push({
      titulo: textos.superficies_que_no_cuadran || "",
      lineas: plan.diferencias_de_superficie.map((diferencia) => diferencia.texto),
    });
  }
  return bloques;
}

/** Elige el año de «antes» o el de «después» de la comparación. */
function elegirUnAnioParaComparar(cual, anio) {
  const t06 = elEstadoDeT06();
  const numero = Number(anio);
  if (!Number.isFinite(numero)) return;
  if (cual === "antes") t06.compararAntes = numero;
  else t06.compararDespues = numero;
  t06.error = "";
  return pantallaVersionesDeUnaTierra();
}

/**
 * Compara los dos años elegidos. **No escribe nada**: solo lee (`/api/versiones/comparar`).
 */
async function compararDosAniosDeLaTierra() {
  const t06 = elEstadoDeT06();
  const textos = losTextosDeLasVersiones();
  const anios = aniosConVersiones(t06.versiones);
  const antes = anios.find((uno) => uno.anio === Number(t06.compararAntes));
  const despues = anios.find((uno) => uno.anio === Number(t06.compararDespues));
  if (!antes || !despues) {
    t06.error = textos.comparar_falta || "";
    return pantallaVersionesDeUnaTierra();
  }
  try {
    t06.comparacion = await apiJson(
      `/api/versiones/comparar?parcela_id=${encodeURIComponent(t06.versionParcela)}` +
        `&campana_antes=${encodeURIComponent(antes.campana_id)}` +
        `&campana_despues=${encodeURIComponent(despues.campana_id)}`,
    );
    t06.error = "";
  } catch (fallo) {
    t06.comparacion = null;
    t06.error = fallo.message || "";
  }
  return pantallaVersionesDeUnaTierra();
}

/**
 * **Ensaya** traer lo que esta tierra tenía en otro año. No escribe nada.
 *
 * Se manda a `/api/versiones/previsualizar`, que es la ruta que **solo lee**: el plan que devuelve es
 * el mismo objeto que devolvería aplicar, con `aplicada` en falso, así que lo que se enseña antes no
 * puede diferir de lo que pasaría después. El lote se arma con `loteDesdeLasVersiones`, que copia los
 * números de la referencia **tal y como vinieron** y no rellena ninguno.
 */
async function ensayarTraerLoDeOtroAnio(fuente, campana) {
  const t06 = elEstadoDeT06();
  const textos = losTextosDeLasVersiones();
  t06.ensayando = true;
  t06.error = "";
  try {
    const delAnio = (t06.versiones || []).filter((version) => String(version.campana_id) === String(campana));
    const lote = loteDesdeLasVersiones(delAnio, {
      campanaId: (estado.campana || {}).id,
      fuente,
    });
    t06.ensayo = await apiJson("/api/versiones/previsualizar", {
      method: "POST",
      body: JSON.stringify(lote),
    });
  } catch (fallo) {
    t06.ensayo = null;
    t06.error = fallo.message || textos.no_se_pudo || "";
  }
  t06.ensayando = false;
  return pantallaVersionesDeUnaTierra();
}

/**
 * Apunta lo que se había ensayado. **Es el único camino que escribe**, y solo existe en este botón.
 *
 * `/api/versiones/aplicar` es repetible: aplicarlo dos veces con el mismo lote no duplica nada (T05),
 * así que un doble toque no puede estropear el cuaderno.
 */
async function apuntarElLoteEnsayado() {
  const t06 = elEstadoDeT06();
  t06.ensayando = true;
  t06.error = "";
  try {
    const delAnio = (t06.versiones || []).filter(
      (version) => String(version.campana_id) === String(t06.ensayo && t06.ensayo.campana_id),
    );
    const lote = loteDesdeLasVersiones(
      delAnio.length ? delAnio : [],
      { campanaId: (estado.campana || {}).id, fuente: t06.ensayo ? t06.ensayo.fuente : "" },
    );
    t06.ensayo = await apiJson("/api/versiones/aplicar", {
      method: "POST",
      body: JSON.stringify(lote),
    });
    // Y las versiones se vuelven a leer: lo que se acaba de apuntar tiene que verse **sin borrar el
    // aviso de que se ha apuntado** (por eso se llama a `cargarLasVersionesDeUnaTierra` y no a
    // `abrirLasVersionesDeUnaTierra`, que limpia el ensayo).
    await cargarLasVersionesDeUnaTierra(t06.versionParcela);
  } catch (fallo) {
    t06.error = fallo.message || "";
  }
  t06.ensayando = false;
  return pantallaVersionesDeUnaTierra();
}

// ---------------------------------------------------------------------------------------------
// Las semillas, las etiquetas y las siembras (T10, 03/10/2026)
//
// Tres cosas que conviene entender de este bloque antes de tocar nada:
//
//  1. **La pantalla no calcula nada.** Lo que queda en el almacén, la cantidad total que sale del
//     almacén y lo que el programa ha calculado a partir de la dosis y las hectáreas **llegan
//     contados del servidor**, con su unidad. Aquí solo se preparan las filas que se leen.
//  2. **La dosis por hectárea y la cantidad total son dos cosas distintas** y se enseñan con dos
//     nombres distintos. Es lo que impide el error de diez veces (el caso A02 del contrato), y por eso
//     en las tarjetas van en dos filas separadas y en el formulario en dos campos separados.
//  3. **Lo que se lee de una foto es una propuesta.** Se enseña dentro del formulario y **no se manda
//     nada al servidor** hasta que el agricultor pulsa GUARDAR: la lectura, por sí sola, no crea
//     ninguna semilla.
// ---------------------------------------------------------------------------------------------

/** El estado de las semillas, creado la primera vez que hace falta (como el del almacén). */
function estadoDeLasSemillas() {
  if (!estado.semillas) {
    estado.semillas = {
      lista: [],
      siembras: [],
      articulos: [],
      cargando: false,
      guardando: false,
      error: "",
      aviso: "",
      // La ficha que se está escribiendo, la propuesta que se ha leído de una foto y el fichero que
      // el agricultor ha elegido. **El fichero vive aquí y no en el `<input>`**: pintar la pantalla
      // borra la casilla, y entonces la pantalla diría que no ha elegido nada (es una trampa que este
      // proyecto ya tiene pagada dos veces, con el cuaderno de la Junta y con las facturas).
      ficha: null,
      propuesta: null,
      fichero: null,
      corrigiendo: null,
      siembra: null,
      clave: "",
      pedirDescuadre: false,
    };
  }
  return estado.semillas;
}

/** Los textos: un solo bloque del servidor, que trae las palabras de las cuatro pantallas. */
function textosDeLasSemillas() {
  return { semillas: t("semillas", {}) };
}

/** Un número del servidor, con la coma de aquí, y la unidad al lado. `null` es «no se sabe». */
function conUnidad(cantidad, unidad) {
  if (cantidad === null || cantidad === undefined) return "";
  return `${formateaNumero(cantidad)}${unidad ? ` ${unidad}` : ""}`;
}

/**
 * Una semilla, en la forma que lee la tarjeta de la lista.
 *
 * **Lo que no se sabe se dice con palabras, nunca con un cero**: el poder germinativo y la pureza no
 * vienen en todas las etiquetas, y cuando no vienen se escribe «La etiqueta no lo dice». Lo mismo con
 * lo que queda: si el servidor dice que no se puede saber, se dice eso y su motivo.
 */
function tarjetaDeUnaSemilla(semilla) {
  const queda = semilla.queda || {};
  const s = (clave) => t(`semillas.${clave}`, "");
  const noLoDice = s("no_lo_dice");
  const filas = [];
  if (semilla.casa_comercial) {
    filas.push({ etiqueta: s("casa_comercial"), valor: semilla.casa_comercial });
  }
  if (semilla.numero_lote_proveedor) {
    filas.push({ etiqueta: s("numero_lote_proveedor"), valor: semilla.numero_lote_proveedor });
  }
  filas.push({
    etiqueta: s("dosis_recomendada"),
    valor: semilla.dosis_recomendada_por_ha === null
      ? noLoDice
      : conUnidad(semilla.dosis_recomendada_por_ha, semilla.unidad_dosis),
  });
  filas.push({
    etiqueta: s("poder_germinativo"),
    valor:
      semilla.poder_germinativo_pct === null
        ? noLoDice
        : `${formateaNumero(semilla.poder_germinativo_pct)} %`,
  });
  filas.push({
    etiqueta: s("pureza"),
    valor: semilla.pureza_pct === null ? noLoDice : `${formateaNumero(semilla.pureza_pct)} %`,
  });
  filas.push({
    etiqueta: s("tratada"),
    // **Tres respuestas y no dos**: el `null` del servidor es «no lo sé», y convertirlo en «no viene
    // tratada» sería afirmar algo que nadie ha mirado.
    valor: semilla.tratada === true ? s("tratada_si") : semilla.tratada === false ? s("tratada_no") : s("tratada_no_se"),
  });
  filas.push({
    etiqueta: s("fecha_caducidad"),
    valor: semilla.fecha_caducidad
      ? formateaFecha(semilla.fecha_caducidad)
      : noLoDice,
  });

  const avisos = [];
  if (semilla.queda && semilla.queda.saldo === null && queda.motivo) {
    avisos.push(queda.motivo);
  }
  const lineas = [
    queda.saldo === null || queda.saldo === undefined
      ? s("sin_saber_lo_que_queda")
      : `${t("cesta.queda", "")} ${conUnidad(queda.saldo, queda.unidad || semilla.unidad)}`.trim(),
  ];
  const rotulo = [semilla.especie, semilla.variedad].filter(Boolean).join(" · ");
  return { id: semilla.id, etiqueta: semilla.nombre, rotulo, lineas, filas, avisos };
}

/**
 * Una siembra, en la forma que lee la tarjeta: **las dos cifras, cada una con su nombre**.
 *
 * Y lo que el servidor diga de si ha descontado o no del almacén: una siembra que no ha restado nada
 * (porque no se sabe cuánto se sembró o de qué envase sale) lo dice ahí mismo, con su motivo. Sin
 * eso, el agricultor vería que la semilla que le queda no ha bajado y no sabría por qué.
 */
function tarjetaDeUnaSiembra(siembra) {
  const s = (clave) => t(`semillas.${clave}`, "");
  const filas = [
    {
      etiqueta: s("siembra_dosis"),
      valor: siembra.dosis_por_ha === null
        ? s("no_se_sabe")
        : conUnidad(siembra.dosis_por_ha, siembra.unidad_dosis),
    },
    {
      etiqueta: s("siembra_cantidad_total"),
      valor: siembra.cantidad_total === null
        ? s("no_se_sabe")
        : conUnidad(siembra.cantidad_total, siembra.unidad_cantidad),
    },
  ];
  if (siembra.superficie_ha !== null && siembra.superficie_ha !== undefined) {
    filas.push({ etiqueta: s("cuantas_hectareas"), valor: `${formateaNumero(siembra.superficie_ha)} ha` });
  }
  if (siembra.numero_lote) {
    filas.push({ etiqueta: s("siembra_envase"), valor: siembra.numero_lote });
  }
  const avisos = [];
  if (siembra.anulada) avisos.push(s("siembra_anulada"));
  else if (!siembra.descuenta && siembra.no_descuenta_porque) avisos.push(siembra.no_descuenta_porque);
  for (const aviso of siembra.avisos || []) avisos.push(aviso);
  return {
    id: siembra.id,
    etiqueta: siembra.tierra || "",
    rotulo: siembra.fecha ? formateaFecha(siembra.fecha) : "",
    lineas: [siembra.semilla || ""],
    filas,
    avisos,
  };
}

/** Pide las semillas y las siembras de golpe: las dos listas se miran juntas. */
async function recargarLasSemillas() {
  const suyo = estadoDeLasSemillas();
  let problema = "";
  const apuntarProblema = (fallo) => {
    if (!problema) problema = (fallo && fallo.message) || mensaje("no_se_pudo");
    return null;
  };
  const [semillas, siembras] = await Promise.all([
    apiJson("/api/semillas").catch(apuntarProblema),
    apiJson("/api/siembras").catch(() => apuntarProblema()),
  ]);
  suyo.lista = Array.isArray(semillas) ? semillas : [];
  suyo.siembras = Array.isArray(siembras) ? siembras : [];
  suyo.error = problema;
  return suyo;
}

/** Abre «mis semillas»: se pinta enseguida y se vuelve a pintar con lo que contesta el servidor. */
async function abrirLasSemillas() {
  const suyo = estadoDeLasSemillas();
  suyo.error = "";
  suyo.cargando = true;
  pantallaSemillas();
  await recargarLasSemillas();
  suyo.cargando = false;
  pantallaSemillas();
}

/** La lista de semillas, ya en React. */
function pantallaSemillas() {
  const suyo = estadoDeLasSemillas();
  montar(() =>
    pantallaDeLasSemillas({
      textos: textosDeLasSemillas(),
      tarjetas: suyo.lista.map(tarjetaDeUnaSemilla),
      // El singular y el plural con las dos formas del servidor: «Tienes 1 semillas» es lo primero
      // que hace desconfiar de un programa.
      resumen: suyo.lista.length
        ? conCuenta(t("semillas", {}), "cuantas", suyo.lista.length)
        : "",
      aviso: suyo.aviso || "",
      error: suyo.error || "",
      cargando: suyo.cargando,
    }),
  );
}

/** Abre «lo que he sembrado». */
async function abrirLasSiembras() {
  const suyo = estadoDeLasSemillas();
  suyo.error = "";
  suyo.cargando = true;
  // Al **entrar** en la lista se limpia lo que decía el servidor la última vez que se guardó: eso era
  // de aquel apunte, y dejarlo puesto encima de la lista volvería a contarlo como si fuera de ahora.
  suyo.aviso = "";
  suyo.calculado = null;
  suyo.avisos = [];
  pantallaSiembras();
  await recargarLasSemillas();
  suyo.cargando = false;
  pantallaSiembras();
}

/** La lista de lo que se ha sembrado, ya en React. */
function pantallaSiembras() {
  const suyo = estadoDeLasSemillas();
  montar(() =>
    pantallaDeLasSiembras({
      textos: textosDeLasSemillas(),
      tarjetas: suyo.siembras.map(tarjetaDeUnaSiembra),
      resumen: suyo.siembras.length
        ? conCuenta(t("semillas", {}), "cuantas_siembras", suyo.siembras.length)
        : "",
      // Sin ninguna semilla dada de alta no hay de dónde descontar: el aviso sale con su botón.
      puedeSembrar: suyo.lista.length > 0,
      aviso: suyo.aviso || "",
      // **Y la cuenta que ha hecho el servidor se lee aquí también.** Es lo que se acaba de guardar:
      // si el total lo ha calculado el programa a partir de la dosis y las hectáreas, el agricultor
      // tiene que leerlo para poder revisarlo, y el formulario ya no está delante.
      calculado: suyo.calculado || null,
      avisos: suyo.avisos || [],
      error: suyo.error || "",
      cargando: suyo.cargando,
    }),
  );
}

/** Los insumos del almacén que **todavía no tienen etiqueta de semilla**, para engancharla a uno. */
async function articulosSinEtiqueta() {
  const articulos = await apiJson("/api/almacen/articulos");
  const conEtiqueta = new Set(estadoDeLasSemillas().lista.map((una) => Number(una.articulo_id)));
  return (articulos || [])
    .filter((articulo) => !conEtiqueta.has(Number(articulo.id)))
    .map((articulo) => ({ valor: articulo.id, texto: articulo.nombre }));
}

/** Los campos de la ficha, con lo que ya estaba guardado. */
function borradorDeUnaSemilla(semilla) {
  return {
    nombre: semilla.nombre || "",
    unidad: semilla.unidad || "",
    especie: semilla.especie || "",
    variedad: semilla.variedad || "",
    casa_comercial: semilla.casa_comercial || "",
    proveedor: semilla.proveedor || "",
    numero_lote_proveedor: semilla.numero_lote_proveedor || "",
    dosis_recomendada_por_ha:
      semilla.dosis_recomendada_por_ha === null ? "" : String(semilla.dosis_recomendada_por_ha),
    unidad_dosis: semilla.unidad_dosis || "",
    fecha_envasado: semilla.fecha_envasado || "",
    fecha_caducidad: semilla.fecha_caducidad || "",
    poder_germinativo_pct:
      semilla.poder_germinativo_pct === null ? "" : String(semilla.poder_germinativo_pct),
    pureza_pct: semilla.pureza_pct === null ? "" : String(semilla.pureza_pct),
    // Tres estados, y el «no lo sé» es el que viene puesto cuando el servidor no lo sabe.
    tratada: semilla.tratada === true ? "si" : semilla.tratada === false ? "no" : "no_se",
  };
}

/** La ficha vacía, para dar de alta una semilla escribiéndola a mano. */
function fichaDeUnaSemillaVacia() {
  return {
    nombre: "",
    unidad: "",
    especie: "",
    variedad: "",
    casa_comercial: "",
    proveedor: "",
    numero_lote_proveedor: "",
    dosis_recomendada_por_ha: "",
    unidad_dosis: "",
    fecha_envasado: "",
    fecha_caducidad: "",
    poder_germinativo_pct: "",
    pureza_pct: "",
    tratada: "no_se",
  };
}

/** Abre la ficha vacía: para escribir a mano o para hacerle una foto a la etiqueta. */
async function abrirLaSemillaNueva() {
  const suyo = estadoDeLasSemillas();
  suyo.error = "";
  suyo.aviso = "";
  suyo.propuesta = null;
  suyo.fichero = null;
  suyo.corrigiendo = null;
  suyo.guardando = false;
  suyo.ficha = fichaDeUnaSemillaVacia();
  // Los insumos que ya están en el almacén y no tienen etiqueta: es lo que evita que una semilla que
  // ya entró por albarán acabe con dos fichas y el mismo nombre.
  suyo.articulos = await articulosSinEtiqueta().catch(() => []);
  pantallaNuevaSemilla();
}

/** Abre la ficha de una semilla que ya existe, para corregirla. */
function abrirLaSemilla(semillaId) {
  const suyo = estadoDeLasSemillas();
  const semilla = (suyo.lista || []).find((una) => Number(una.id) === Number(semillaId));
  if (!semilla) return pantallaDeDireccionQueNoLlevaANingunaParte();
  suyo.error = "";
  suyo.aviso = "";
  suyo.propuesta = null;
  suyo.fichero = null;
  suyo.guardando = false;
  suyo.corrigiendo = semilla;
  suyo.articulos = [];
  suyo.ficha = borradorDeUnaSemilla(semilla);
  pantallaNuevaSemilla();
}

/** La ficha de una semilla, ya en React (el alta y la corrección son la misma pantalla). */
function pantallaNuevaSemilla() {
  const suyo = estadoDeLasSemillas();
  montar(() =>
    pantallaDeUnaSemilla({
      textos: textosDeLasSemillas(),
      borrador: suyo.ficha || fichaDeUnaSemillaVacia(),
      propuesta: suyo.propuesta,
      articulos: suyo.articulos || [],
      unidades_dosis: (t("unidades_dosis_semilla", []) || []).map((unidad) => ({
        valor: unidad,
        texto: unidad,
      })),
      unidades_cantidad: (t("unidades_cantidad_semilla", []) || []).map((unidad) => ({
        valor: unidad,
        texto: unidad,
      })),
      // El identificador de la semilla que se está corrigiendo: es lo que hace salir el botón de
      // **sembrarla** (con una semilla que todavía no está guardada no se puede sembrar nada).
      semillaId: suyo.corrigiendo ? suyo.corrigiendo.id : "",
      corrigiendo: Boolean(suyo.corrigiendo),
      guardando: Boolean(suyo.guardando),
      error: suyo.error || "",
    }),
  );
}

/** Lee lo que hay escrito en la ficha, campo a campo y por su `id` (que no se puede cambiar). */
function recogeLaSemilla() {
  const valor = (id) => {
    const campo = document.getElementById(id);
    return campo ? String(campo.value || "").trim() : "";
  };
  const cual = valor("semilla-tratada");
  return {
    articulo: valor("semilla-articulo"),
    nombre: valor("semilla-nombre"),
    especie: valor("semilla-especie"),
    variedad: valor("semilla-variedad"),
    casa_comercial: valor("semilla-casa"),
    proveedor: valor("semilla-proveedor"),
    numero_lote_proveedor: valor("semilla-lote"),
    dosis_recomendada_por_ha: valor("semilla-dosis"),
    unidad_dosis: valor("semilla-unidad-dosis"),
    fecha_envasado: valor("semilla-envasado"),
    fecha_caducidad: valor("semilla-caducidad"),
    poder_germinativo_pct: valor("semilla-germinativo"),
    pureza_pct: valor("semilla-pureza"),
    // **Tres estados**: «no lo sé» viaja como `null` y no como un «no», que es lo que afirmaría que
    // nadie ha mirado la etiqueta cuando a lo mejor sí lo dice y no se ha visto.
    tratada: cual === "si" ? true : cual === "no" ? false : null,
  };
}

/** Un número del formulario, o `null`. **Un hueco no es un cero.** */
function numeroOMarco(texto) {
  const limpio = String(texto || "").trim();
  if (!limpio) return null;
  const numero = aNumero(limpio);
  return Number.isFinite(numero) ? numero : null;
}

/**
 * Guarda la semilla: **es la confirmación**.
 *
 * Lo que se ha leído de una foto llega aquí ya revisado por el agricultor, y hasta este botón no hay
 * ninguna semilla apuntada. Si la ficha es de una semilla que ya existe, se corrige con `PUT`.
 */
async function guardarLaSemilla() {
  const suyo = estadoDeLasSemillas();
  // **Un toque mientras ya se está guardando no manda otra petición.** El botón se deshabilita
  // (`disabled=${guardando}`) y eso corta el doble toque en un navegador, pero entre el primer toque y
  // el repintado cabe un segundo; esta línea lo cierra sin depender de lo que tarde React en pintar.
  if (suyo.guardando) return;
  const escrita = recogeLaSemilla();
  // **Y lo que ha escrito el agricultor se guarda en el estado antes de mandar nada.** La pantalla se
  // vuelve a pedir a React al guardar y al fallar: si el borrador no lleva lo escrito, **el formulario
  // se vacía** y el agricultor tiene que teclearlo todo otra vez para corregir. Lo encontró la prueba
  // que pulsa el botón y comprueba el cuerpo y la pantalla después del error.
  suyo.ficha = { ...(suyo.ficha || fichaDeUnaSemillaVacia()), ...escrita };
  if (!escrita.nombre) {
    suyo.error = mensaje("SM13_falta_el_nombre");
    return pantallaNuevaSemilla();
  }
  if (escrita.dosis_recomendada_por_ha && !escrita.unidad_dosis) {
    suyo.error = mensaje("SM14_falta_la_unidad_de_la_dosis");
    return pantallaNuevaSemilla();
  }
  const datos = {
    nombre: escrita.nombre,
    unidad: (suyo.ficha || {}).unidad || null,
    especie: escrita.especie || null,
    variedad: escrita.variedad || null,
    casa_comercial: escrita.casa_comercial || null,
    proveedor: escrita.proveedor || null,
    numero_lote_proveedor: escrita.numero_lote_proveedor || null,
    dosis_recomendada_por_ha: numeroOMarco(escrita.dosis_recomendada_por_ha),
    unidad_dosis: escrita.unidad_dosis || null,
    fecha_envasado: escrita.fecha_envasado || null,
    fecha_caducidad: escrita.fecha_caducidad || null,
    poder_germinativo_pct: numeroOMarco(escrita.poder_germinativo_pct),
    pureza_pct: numeroOMarco(escrita.pureza_pct),
    tratada: escrita.tratada,
    // **Cómo se rellenaron los datos**, que es lo que permite saber dentro de un año si un número lo
    // escribió una persona o lo leyó un programa.
    leida_de: suyo.propuesta ? suyo.propuesta.como_se_leyo || "" : "mano",
    idioma_del_lector: suyo.propuesta ? suyo.propuesta.idioma_del_lector || null : null,
  };
  if (!suyo.corrigiendo && escrita.articulo) {
    // Enganchar la etiqueta a un insumo que ya está en el almacén: sin esto, la semilla que ya entró
    // por albarán tendría dos fichas con el mismo nombre.
    datos.articulo_id = Number(escrita.articulo);
    delete datos.unidad;
  }

  suyo.error = "";
  suyo.guardando = true;
  pantallaNuevaSemilla();
  const ruta = suyo.corrigiendo ? `/api/semillas/${suyo.corrigiendo.id}` : "/api/semillas";
  const resultado = await mandarCambio(ruta, suyo.corrigiendo ? "PUT" : "POST", datos);
  suyo.guardando = false;
  if (resultado.error) {
    suyo.error = resultado.error;
    return pantallaNuevaSemilla();
  }
  const guardada = resultado.datos || {};
  // Si se ha hecho una foto, se guarda **con la semilla** después de confirmarla: el papel que
  // sostiene lo que se acaba de apuntar.
  if (suyo.fichero && guardada.id) {
    await mandarLaFotoDeLaEtiqueta(guardada.id, suyo.fichero);
  }
  suyo.ficha = null;
  suyo.propuesta = null;
  suyo.fichero = null;
  suyo.corrigiendo = null;
  suyo.aviso = t("semillas.guardada", "");
  await recargarLasSemillas();
  suyo.aviso = t("semillas.guardada", "");
  pantallaSemillas();
}

/** El fichero que ha elegido el agricultor, guardado **antes** de repintar (pintar borra la casilla). */
function elFicheroDeLaEtiqueta() {
  const suyo = estadoDeLasSemillas();
  const campo = document.getElementById("semilla-foto");
  if (campo && campo.files && campo.files.length) suyo.fichero = campo.files[0];
  return suyo.fichero;
}

/**
 * Manda un fichero por `POST` (multipart).
 *
 * Con `fetch` y no con `api()` a propósito: `api()` pone la cabecera de JSON, y en un fichero la pone
 * el navegador sola con su `boundary`. Poner las dos rompe el envío sin decir por qué.
 */
async function mandarElFichero(ruta, fichero) {
  const cuerpo = new FormData();
  cuerpo.append("fichero", fichero);
  const respuesta = await fetch(ruta, {
    method: "POST",
    headers: { Authorization: `Bearer ${estado.token}` },
    body: cuerpo,
  });
  const detalle = await respuesta.json().catch(() => null);
  if (!respuesta.ok) {
    throw new Error(avisoDelServidor(detalle) || mensaje("no_se_pudo"));
  }
  return detalle;
}

/**
 * Lee la etiqueta de una foto. **No guarda nada**: lo que devuelve es una propuesta, y los campos de
 * la ficha se rellenan con ella para que el agricultor la revise y la corrija.
 */
async function leerLaEtiquetaDeLaSemilla() {
  const suyo = estadoDeLasSemillas();
  const fichero = elFicheroDeLaEtiqueta();
  if (!fichero) {
    suyo.error = t("semillas.leer_etiqueta_pista", "");
    return pantallaNuevaSemilla();
  }
  if (!navigator.onLine) {
    // Sin cobertura no se puede leer una foto: se dice, en vez de dejar al agricultor esperando.
    suyo.error = mensaje("no_se_pudo");
    return pantallaNuevaSemilla();
  }
  suyo.error = "";
  suyo.guardando = true;
  pantallaNuevaSemilla();
  try {
    const leida = await mandarElFichero("/api/semillas/etiqueta", fichero);
    suyo.propuesta = laPropuestaEnPalabras(leida);
    suyo.ficha = { ...fichaDeUnaSemillaVacia(), ...(suyo.ficha || {}), ...borradorDeLaPropuesta(leida) };
  } catch (fallo) {
    suyo.error = fallo.message || mensaje("no_se_pudo");
  }
  suyo.guardando = false;
  pantallaNuevaSemilla();
}

/** Sube (o cambia) la foto de la etiqueta de una semilla que ya está guardada. */
async function mandarLaFotoDeLaEtiqueta(semillaId, fichero) {
  try {
    await mandarElFichero(`/api/semillas/${semillaId}/etiqueta`, fichero);
    return true;
  } catch (fallo) {
    estadoDeLasSemillas().error = fallo.message || mensaje("no_se_pudo");
    return false;
  }
}

async function subirLaFotoDeLaEtiqueta() {
  const suyo = estadoDeLasSemillas();
  const fichero = elFicheroDeLaEtiqueta();
  if (!fichero || !suyo.corrigiendo) {
    suyo.error = t("semillas.leer_etiqueta_pista", "");
    return pantallaNuevaSemilla();
  }
  suyo.error = "";
  suyo.guardando = true;
  pantallaNuevaSemilla();
  await mandarLaFotoDeLaEtiqueta(suyo.corrigiendo.id, fichero);
  suyo.guardando = false;
  suyo.fichero = null;
  suyo.aviso = t("semillas.foto_guardada", "");
  await recargarLasSemillas();
  pantallaSemillas();
}

/** Descarga la foto de la etiqueta de una semilla. */
async function verLaFotoDeLaEtiqueta(semillaId) {
  const respuesta = await api(`/api/semillas/${semillaId}/etiqueta`);
  if (!respuesta.ok) {
    const detalle = await respuesta.json().catch(() => null);
    avisarDelError(avisoDelServidor(detalle) || mensaje("no_se_pudo"));
    return;
  }
  const blob = await respuesta.blob();
  const enlace = document.createElement("a");
  enlace.href = URL.createObjectURL(blob);
  enlace.download = `etiqueta-semilla-${semillaId}`;
  enlace.click();
  URL.revokeObjectURL(enlace.href);
}

/**
 * Lo que se ha leído de la etiqueta, contado con las palabras del servidor.
 *
 * **Las frases compuestas se montan aquí y no en el componente** (`docs/REACT.md`): «Leído de la foto
 * de la etiqueta» y «He podido leer 6 datos» son textos del servidor unidos con datos del servidor, y
 * el componente solo los pinta.
 */
function laPropuestaEnPalabras(leida) {
  const s = (clave) => t(`semillas.${clave}`, "");
  const cuantos = (leida.campos_leidos || []).length;
  return {
    como_se_leyo: leida.como_se_leyo || "",
    como_se_leyo_texto: s(`leido_de_${leida.como_se_leyo || "mano"}`),
    resumen_campos: cuantos
      ? conCuenta(t("semillas", {}), "campos_leidos", cuantos)
      : "",
    idioma_texto: leida.idioma_del_lector
      ? rellena(s("idioma_de_la_lectura"), { idioma: leida.idioma_del_lector })
      : "",
    idioma_del_lector: leida.idioma_del_lector || "",
    campos_leidos: leida.campos_leidos || [],
    avisos: (leida.avisos || []).slice(),
    dudas: (leida.dudas || []).slice(),
    hay_lector: leida.hay_lector !== false,
    texto_crudo: leida.texto_crudo || "",
  };
}

/** Lo que se ha leído, en la forma que tienen los campos de la ficha. Lo que no se leyó, en blanco. */
function borradorDeLaPropuesta(leida) {
  const texto = (valor) => (valor === null || valor === undefined ? "" : String(valor));
  const nombre =
    leida.nombre ||
    // El nombre del artículo se propone con lo que dice el papel (la especie y la variedad): es un
    // dato leído, no uno inventado, y el agricultor lo puede cambiar antes de guardarlo.
    [leida.especie, leida.variedad].filter(Boolean).join(" ");
  return {
    nombre,
    especie: texto(leida.especie),
    variedad: texto(leida.variedad),
    casa_comercial: texto(leida.casa_comercial),
    proveedor: texto(leida.proveedor),
    numero_lote_proveedor: texto(leida.numero_lote_proveedor),
    dosis_recomendada_por_ha: texto(leida.dosis_recomendada_por_ha),
    unidad_dosis: texto(leida.unidad_dosis),
    fecha_envasado: texto(leida.fecha_envasado),
    fecha_caducidad: texto(leida.fecha_caducidad),
    poder_germinativo_pct: texto(leida.poder_germinativo_pct),
    pureza_pct: texto(leida.pureza_pct),
    tratada: leida.tratada === true ? "si" : leida.tratada === false ? "no" : "no_se",
  };
}

// ---------------------------------------------------------------------------------------------
// Sembrar una semilla
// ---------------------------------------------------------------------------------------------

/** Los envases de una semilla, para poder decir de cuál sale lo que se siembra. */
function envasesDeUnaSemilla(semilla) {
  return ((semilla || {}).envases || []).map((envase) => ({
    valor: envase.lote_id,
    texto: envase.numero_lote
      ? `${envase.numero_lote} (${envase.saldo === null || envase.saldo === undefined ? t("semillas.sin_saber_lo_que_queda", "") : conUnidad(envase.saldo, envase.unidad)})`
      : t("semillas.envase_sin_numero", ""),
  }));
}

function laSemillaDe(semillaId) {
  return (estadoDeLasSemillas().lista || []).find((una) => Number(una.id) === Number(semillaId)) || null;
}

/** Abre «sembrar esta semilla»: la semilla ya viene elegida y sus envases son los suyos. */
function abrirLaSiembraNueva(semillaId) {
  const suyo = estadoDeLasSemillas();
  const semilla = laSemillaDe(semillaId);
  // `pantallaDeDireccionQueNoLlevaANingunaParte` con la «A» de «A Ninguna»: el nombre se escribió mal
  // aquí y en `abrirLaSiembra`, y **eso era un `ReferenceError`** —la pantalla no se abría, la consola
  // del móvil se llenaba y el agricultor no veía nada—. Lo encontró la prueba que pulsa el botón de
  // verdad (`tests_js/semillas.test.js`); ninguna prueba que solo pinte la pantalla lo podía ver.
  if (!semilla) return pantallaDeDireccionQueNoLlevaANingunaParte();
  suyo.error = "";
  suyo.aviso = "";
  suyo.pedirDescuadre = false;
  suyo.corrigiendo = null;
  suyo.guardando = false;
  // La clave de reenvío se pide **al abrir el formulario** y no al guardar: si se pidiera al guardar,
  // dos pulsaciones del mismo botón (o el reenvío de la cola del móvil) llevarían claves distintas y
  // la semilla se descontaría dos veces del almacén.
  suyo.clave = claveDeReenvio("siembra");
  suyo.siembra = {
    semilla_id: semilla.id,
    parcela_id: "",
    lote_id: "",
    fecha: hoyISO(),
    superficie_ha: "",
    dosis_por_ha: "",
    unidad_dosis: semilla.unidad_dosis || "",
    cantidad_total: "",
    unidad_cantidad: semilla.unidad || "",
    notas: "",
    motivo_anulacion: "",
  };
  pantallaNuevaSiembra();
}

/** Abre una siembra que ya está apuntada, para corregirla o anularla. */
function abrirLaSiembra(siembraId) {
  const suyo = estadoDeLasSemillas();
  const siembra = (suyo.siembras || []).find((una) => Number(una.id) === Number(siembraId));
  // El nombre de la función, bien escrito (ver `abrirLaSiembraNueva`): aquí estaba igual de mal.
  if (!siembra) return pantallaDeDireccionQueNoLlevaANingunaParte();
  suyo.error = "";
  suyo.aviso = "";
  suyo.pedirDescuadre = false;
  suyo.guardando = false;
  suyo.clave = "";
  suyo.corrigiendo = siembra;
  suyo.siembra = {
    semilla_id: siembra.semilla_id,
    parcela_id: String(siembra.parcela_id),
    lote_id: siembra.lote_id === null ? "" : String(siembra.lote_id),
    fecha: siembra.fecha || "",
    superficie_ha: siembra.superficie_ha === null ? "" : String(siembra.superficie_ha),
    dosis_por_ha: siembra.dosis_por_ha === null ? "" : String(siembra.dosis_por_ha),
    unidad_dosis: siembra.unidad_dosis || "",
    cantidad_total: siembra.cantidad_total === null ? "" : String(siembra.cantidad_total),
    unidad_cantidad: siembra.unidad_cantidad || "",
    notas: siembra.notas || "",
    motivo_anulacion: "",
  };
  pantallaNuevaSiembra();
}

/**
 * Las unidades que se ofrecen para la dosis de una semilla: **las del servidor más la suya, si no está**.
 *
 * POR QUÉ ESTO NO ES UN ADORNO. La lista del servidor es corta (`kg/ha`, `g/ha`, `ud/ha`, `L/ha`) y una
 * etiqueta puede traer otra cosa —`millones/ha` de remolacha, `ud/m2`—: si el desplegable no tiene esa
 * opción, el navegador enseña la primera y **el agricultor guarda la siembra sin la unidad que tenía la
 * semilla**. Y una siembra sin unidad no descuenta del almacén. La unidad que ya consta se ofrece la
 * primera, tal cual está guardada: no se inventa ninguna.
 */
function unidadesDeDosisDeUnaSemilla(semilla) {
  const lista = (t("unidades_dosis_semilla", []) || []).map((unidad) => ({
    valor: unidad,
    texto: unidad,
  }));
  const suya = (semilla || {}).unidad_dosis;
  if (suya && !lista.some((unidad) => unidad.valor === suya)) {
    lista.unshift({ valor: suya, texto: suya });
  }
  return lista;
}

/** El formulario de una siembra, ya en React. */
function pantallaNuevaSiembra() {
  const suyo = estadoDeLasSemillas();
  const borrador = suyo.siembra || {};
  const semilla = laSemillaDe(borrador.semilla_id) || (suyo.corrigiendo ? { id: borrador.semilla_id } : null);
  montar(() =>
    pantallaDeUnaSiembra({
      textos: textosDeLasSemillas(),
      borrador,
      semilla: (semilla && semilla.nombre) || (suyo.corrigiendo ? suyo.corrigiendo.semilla : ""),
      tierras: (estado.parcelas || []).map((tierra) => ({
        valor: tierra.id,
        texto: `${tierra.alias}${tierra.superficie_ha ? ` · ${formateaNumero(tierra.superficie_ha)} ha` : ""}`,
      })),
      envases: envasesDeUnaSemilla(semilla),
      unidades_dosis: unidadesDeDosisDeUnaSemilla(semilla),
      unidades_cantidad: (t("unidades_cantidad_semilla", []) || []).map((unidad) => ({
        valor: unidad,
        texto: unidad,
      })),
      // Lo que el servidor ha calculado se dice con sus dos frases. Se enseña **después** de guardar o
      // al corregir, que es cuando el servidor ha contestado: antes no se calcula nada aquí.
      calculado: suyo.calculado || null,
      quedar: semilla && semilla.queda ? semilla.queda : null,
      corrigiendo: Boolean(suyo.corrigiendo),
      guardando: Boolean(suyo.guardando),
      error: suyo.error || "",
    }),
  );
}

/** Lee lo que hay escrito en el formulario de la siembra, campo a campo y por su `id`. */
function recogeLaSiembra() {
  const valor = (id) => {
    const campo = document.getElementById(id);
    return campo ? String(campo.value || "").trim() : "";
  };
  return {
    parcela_id: valor("siembra-tierra"),
    lote_id: valor("siembra-envase"),
    fecha: valor("siembra-fecha"),
    superficie_ha: valor("siembra-superficie"),
    dosis_por_ha: valor("siembra-dosis"),
    unidad_dosis: valor("siembra-unidad-dosis"),
    cantidad_total: valor("siembra-cantidad"),
    unidad_cantidad: valor("siembra-unidad-cantidad"),
    notas: valor("siembra-notas"),
    motivo_anulacion: valor("siembra-motivo"),
  };
}

/**
 * Guarda la siembra: **el apunte y el descuento del almacén, a la vez**.
 *
 * Un hueco se manda como «no se sabe» (`null`), nunca como un cero. Y el envase vacío también es
 * «no se sabe»: el servidor dirá que entonces no se descuenta nada y por qué, en vez de restarlo de un
 * saco cualquiera.
 */
async function guardarLaSiembra() {
  const suyo = estadoDeLasSemillas();
  // Un toque mientras ya se está guardando no manda otra petición (ver `guardarLaSemilla`).
  if (suyo.guardando) return;
  const escrita = recogeLaSiembra();
  // **Lo escrito se guarda en el estado antes de mandar nada**, para que el formulario no se vacíe al
  // repintarlo (al guardar y al fallar): sin esto, un error del servidor borraba las hectáreas, la
  // fecha y las dos cifras, y el agricultor tenía que teclearlas otra vez para corregir. Lo encontró la
  // prueba que pulsa el botón de guardar.
  suyo.siembra = { ...(suyo.siembra || {}), ...escrita };
  if (!escrita.parcela_id) {
    suyo.error = mensaje("SM22_falta_la_tierra");
    return pantallaNuevaSiembra();
  }
  const datos = {
    semilla_id: (suyo.siembra || {}).semilla_id,
    parcela_id: Number(escrita.parcela_id),
    lote_id: escrita.lote_id ? Number(escrita.lote_id) : null,
    fecha: escrita.fecha || null,
    superficie_ha: numeroOMarco(escrita.superficie_ha),
    dosis_por_ha: numeroOMarco(escrita.dosis_por_ha),
    unidad_dosis: escrita.unidad_dosis || null,
    cantidad_total: numeroOMarco(escrita.cantidad_total),
    unidad_cantidad: escrita.unidad_cantidad || null,
    notas: escrita.notas || null,
    aceptar_descuadre: Boolean(suyo.pedirDescuadre),
  };
  if (!suyo.corrigiendo) datos.clave_de_reenvio = suyo.clave;

  suyo.error = "";
  suyo.guardando = true;
  pantallaNuevaSiembra();
  const ruta = suyo.corrigiendo ? `/api/siembras/${suyo.corrigiendo.id}` : "/api/siembras";
  // **Apuntar se puede sin cobertura; corregir no.** Un apunte nuevo se queda en el móvil y se manda
  // solo (con su clave de reenvío, que es lo que impide que se descuente dos veces). Una corrección se
  // hace **en el momento**: la cola del móvil manda todo con `POST`, y un `POST` a la dirección de una
  // siembra no es una corrección, es un error del servidor que el agricultor no sabría entender.
  const resultado = suyo.corrigiendo
    ? await mandarCambio(ruta, "PUT", datos)
    : await enviarOApuntar(ruta, datos, "siembra", false);
  suyo.guardando = false;

  if (resultado.error) {
    suyo.error = resultado.error;
    // El envase se quedaría en negativo: se dice y se ofrece la salida que ya existe en el almacén
    // («sí, la diferencia es de verdad»), sin apuntar nada a escondidas.
    suyo.pedirDescuadre = resultado.estado === 409;
    return pintarLaSiembraConElAviso();
  }
  if (resultado.encolado) {
    suyo.aviso = conCuenta(t("aviso", {}), "pendientes", 1);
    await recargarLasSemillas();
    return pantallaSiembras();
  }
  suyo.calculado = loQueHaCalculadoElServidor(resultado.datos);
  // **Y los avisos del servidor se guardan para enseñarlos**, no se tiran: el aviso solo existe en la
  // respuesta de guardar (al volver a leer la siembra ya no viene), así que perderlo aquí es
  // perderlo del todo. Es lo mismo que hace la salida del almacén del T09 (`salida.avisos = …`).
  // Lo cazó la revisión del T10: el cuadro de «lo ha calculado el programa» se pintaba en el
  // formulario, que ya no vuelve a salir, y la cuenta no la leía nadie.
  suyo.avisos = (resultado.datos || {}).avisos || [];
  suyo.corrigiendo = null;
  suyo.siembra = null;
  suyo.pedirDescuadre = false;
  await recargarLasSemillas();
  suyo.aviso = t("semillas.siembra_guardada", "");
  pantallaSiembras();
}

/**
 * Las dos frases del número que ha calculado el programa.
 *
 * **Se montan aquí con los textos del servidor** (el aviso del servidor ya viene entero: esto es solo
 * para poder enseñarlo en su cuadro), y solo cuando el servidor dice que lo ha calculado él.
 */
function loQueHaCalculadoElServidor(datos) {
  const guardada = datos || {};
  if (!guardada.cantidad_total_calculada && !guardada.dosis_calculada) return null;
  const avisos = guardada.avisos || [];
  return {
    cantidad_total: Boolean(guardada.cantidad_total_calculada),
    dosis_por_ha: Boolean(guardada.dosis_calculada),
    // La cuenta entera la dice el servidor en su aviso (SM8 o SM10): aquí solo se enseña, y va
    // también la lista entera para que el agricultor la lea donde esté mirando (el formulario o la
    // lista de lo sembrado).
    total_en_palabras: guardada.cantidad_total_calculada ? avisos[0] || "" : "",
    dosis_en_palabras: guardada.dosis_calculada ? avisos[0] || "" : "",
    avisos,
  };
}

/** Vuelve a pintar el formulario con lo que ha dicho el servidor (y la salida, si la hay). */
function pintarLaSiembraConElAviso() {
  const suyo = estadoDeLasSemillas();
  const borrador = suyo.siembra || {};
  const semilla = laSemillaDe(borrador.semilla_id);
  montar(() =>
    pantallaDeUnaSiembra({
      textos: textosDeLasSemillas(),
      borrador,
      semilla: (semilla && semilla.nombre) || "",
      tierras: (estado.parcelas || []).map((tierra) => ({ valor: tierra.id, texto: tierra.alias })),
      envases: envasesDeUnaSemilla(semilla),
      unidades_dosis: unidadesDeDosisDeUnaSemilla(semilla),
      unidades_cantidad: (t("unidades_cantidad_semilla", []) || []).map((u) => ({ valor: u, texto: u })),
      calculado: null,
      quedar: semilla && semilla.queda ? semilla.queda : null,
      corrigiendo: Boolean(suyo.corrigiendo),
      guardando: false,
      error: suyo.error || "",
      descuadre: suyo.pedirDescuadre,
    }),
  );
}

/** Anula una siembra, con su motivo. Lo que había salido del almacén vuelve a contar. */
async function anularLaSiembra() {
  const suyo = estadoDeLasSemillas();
  // **Un toque mientras ya se está anulando no manda otra anulación.** Esto es lo que caza el doble
  // toque de verdad: en un navegador el botón se deshabilita mientras guarda, pero entre el primer
  // toque y el repintado cabe un segundo, y entonces entrarían dos peticiones. Con la primera en el
  // aire, la segunda no manda nada; y si aun así llegara dos veces al servidor, la segunda contesta
  // `409` («Esta siembra está anulada»), así que no hay dos anulaciones ni por un lado ni por otro.
  if (suyo.guardando) return;
  const escrita = recogeLaSiembra();
  // Y el motivo escrito se guarda antes de repintar: si el servidor dice que no, no se pierde lo que
  // el agricultor había explicado (ver `guardarLaSemilla`).
  suyo.siembra = { ...(suyo.siembra || {}), ...escrita };
  const motivo = escrita.motivo_anulacion.trim();
  if (motivo.length < 3) {
    suyo.error = mensaje("SM24_falta_el_motivo_para_anular");
    return pantallaNuevaSiembra();
  }
  suyo.error = "";
  suyo.guardando = true;
  pantallaNuevaSiembra();
  const resultado = await mandarCambio(
    `/api/siembras/${suyo.corrigiendo.id}/anular`,
    "POST",
    { motivo },
  );
  suyo.guardando = false;
  if (resultado.error) {
    suyo.error = resultado.error;
    return pantallaNuevaSiembra();
  }
  suyo.corrigiendo = null;
  suyo.siembra = null;
  await recargarLasSemillas();
  suyo.aviso = t("semillas.siembra_anulada", "");
  pantallaSiembras();
}

// ---------------------------------------------------------------------------------------------
// Las personas y las empresas (T11, 03/10/2026)
//
// Cuatro pantallas, y tres cosas que conviene entender antes de tocar esto:
//
//  1. **La pantalla no calcula nada.** Cuántos nombres escritos tiene una ficha, si dos nombres se
//     parecen y qué fichas se pueden apuntar lo dice el servidor. Aquí solo se preparan las filas y las
//     frases, con los textos del servidor.
//  2. **Lo que el agricultor escribió no se toca.** No hay ni una línea que mande el nombre de un papel
//     al servidor: el enlace dice de quién es un texto que ya está escrito, y nada más.
//  3. **Las frases compuestas se montan aquí**, no en los componentes (`docs/REACT.md`): el rótulo de un
//     nombre escrito (de qué papel es, su número y su fecha) y la frase de un aviso con datos dentro se
//     arman en este bloque con `t(...)` y `rellena(...)`.
// ---------------------------------------------------------------------------------------------

/** El estado de los contactos, creado la primera vez que hace falta. */
function estadoDeLosContactos() {
  if (!estado.contactos) {
    estado.contactos = {
      lista: [],
      papeles: [],
      // Si la lista se ha llegado a pedir al servidor. Lo miran las pantallas del dinero (T12), que
      // necesitan los contactos para su lista de enlazar y no tienen por qué volver a pedirlos.
      cargados: false,
      // La ficha que se está escribiendo y, si se está corrigiendo, la que había.
      ficha: null,
      corrigiendo: null,
      vivos: [],
      // La revisión de los nombres escritos: lo que ha contestado el servidor, tal cual.
      revisar: null,
      // Los nombres escritos sin dueño, para la pantalla de enlazar.
      escritos: [],
      buscado: "",
      buscadoEscritos: "",
      cargando: false,
      guardando: false,
      borrando: false,
      error: "",
      aviso: "",
      revisarApuntado: "",
      revisarDeshecho: "",
    };
  }
  return estado.contactos;
}

/** Los textos: un solo bloque del servidor, que trae las palabras de las cuatro pantallas. */
function textosDeLosContactos() {
  return { contactos: t("contactos", {}), acciones: t("acciones", {}) };
}

/** Cómo se llama un papel en pantalla. El nombre vive en `textos.py`, como todo. */
function elNombreDelPapel(papel) {
  return t(`contactos.papeles.${papel}`, "");
}

/** Los papeles de un contacto, ya en palabras. */
function losPapelesEnPalabras(papeles) {
  return (papeles || []).map(elNombreDelPapel).filter(Boolean).join(" · ");
}

/**
 * De qué papel es un nombre escrito: «Una factura · 2026/00123 · 12/03/2026».
 *
 * Se arma aquí y no en el componente porque **una frase compuesta no se monta en un componente**
 * (`docs/REACT.md`), y porque el rótulo lleva tres cosas de tres sitios distintos: la tabla de la que
 * sale (un texto del servidor), su número y su fecha.
 */
function elRotuloDeUnEscrito(escrito) {
  const trozos = [t(`contactos.tabla_${escrito.clave}`, "")];
  for (const trozo of escrito.referencia || []) trozos.push(String(trozo));
  if (escrito.fecha) trozos.push(formateaFecha(escrito.fecha));
  return trozos.filter(Boolean).join(" · ");
}

/** Un nombre escrito, en la forma que lee la tarjeta. */
function escritoEnTarjeta(escrito) {
  const c = (clave) => t(`contactos.${clave}`, "");
  const filas = [];
  if (escrito.nif) filas.push({ etiqueta: c("nif"), valor: escrito.nif });
  const avisos = [];
  if (escrito.anulada) avisos.push(c("esta_anulada"));
  if (escrito.texto_cambiado) {
    avisos.push(
      rellena(c("el_texto_ha_cambiado"), {
        ahora: escrito.texto,
        entonces: escrito.texto_de_entonces || "",
      }),
    );
  }
  return {
    claveTarjeta: `${escrito.tabla}-${escrito.campo}-${escrito.registro_id}`,
    tabla: escrito.tabla,
    campo: escrito.campo,
    registro_id: escrito.registro_id,
    texto: escrito.texto,
    rotulo: elRotuloDeUnEscrito(escrito),
    lineas: [],
    filas,
    avisos,
  };
}

/** Un contacto, en la forma que lee la tarjeta de la lista. */
function tarjetaDeUnContacto(contacto) {
  const c = (clave) => t(`contactos.${clave}`, "");
  const filas = [];
  if (contacto.nif) filas.push({ etiqueta: c("nif"), valor: contacto.nif });
  if (contacto.telefono) filas.push({ etiqueta: c("telefono"), valor: contacto.telefono });
  if (contacto.correo) filas.push({ etiqueta: c("correo"), valor: contacto.correo });
  filas.push({
    etiqueta: c("donde_aparece"),
    // **Un cero no se dice**: una ficha sin ningún papel enlazado no dice «0 papeles», dice que su
    // nombre todavía no está enlazado, que es lo que de verdad pasa (la ficha lo cuenta al abrirla).
    valor: contacto.enlaces
      ? conCuenta(t("contactos", {}), "cuantos_escritos", contacto.enlaces)
      : "",
  });
  return {
    id: contacto.id,
    etiqueta: contacto.nombre,
    rotulo: losPapelesEnPalabras(contacto.papeles),
    lineas: (contacto.nombres_escritos || []).slice(0, 3),
    filas: filas.filter((fila) => fila.valor),
    avisos: [],
  };
}

/** Pide los contactos y sus papeles. Los nombres escritos los pide la pantalla que los usa. */
async function recargarLosContactos() {
  const suyo = estadoDeLosContactos();
  let problema = "";
  const parametros = suyo.buscado ? `?q=${encodeURIComponent(suyo.buscado)}` : "";
  let lista = null;
  try {
    lista = await apiJson(`/api/contactos${parametros}`);
  } catch (fallo) {
    problema = (fallo && fallo.message) || mensaje("no_se_pudo");
  }
  suyo.lista = Array.isArray(lista) ? lista : [];
  suyo.cargados = true;
  // **Los papeles vienen de `/api/interfaz`, y no de una llamada propia**, por el mismo motivo que
  // todo lo demás: lo que se sirve ahí **se guarda en el móvil**, así que la ficha tiene sus botones
  // también sin cobertura. Una llamada aparte sería un hueco en el campo.
  suyo.papeles = (t("papeles_de_un_contacto", []) || []).map((papel) => ({
    valor: papel.valor,
    texto: papel.texto,
  }));
  suyo.error = problema;
  return suyo;
}

/** Abre «las personas y las empresas»: se pinta enseguida y se vuelve a pintar con lo del servidor. */
async function abrirLosContactos() {
  const suyo = estadoDeLosContactos();
  suyo.error = "";
  suyo.aviso = "";
  suyo.cargando = true;
  pantallaContactos();
  await recargarLosContactos();
  suyo.cargando = false;
  pantallaContactos();
}

/** La lista de contactos, ya en React. */
function pantallaContactos() {
  const suyo = estadoDeLosContactos();
  montar(() =>
    pantallaDeLosContactos({
      textos: textosDeLosContactos(),
      tarjetas: suyo.lista.map(tarjetaDeUnContacto),
      // El singular y el plural con las dos formas del servidor: «Tienes 1 fichas» es lo primero que
      // hace desconfiar de un programa.
      resumen: suyo.lista.length ? conCuenta(t("contactos", {}), "cuantas", suyo.lista.length) : "",
      buscado: suyo.buscado,
      aviso: suyo.aviso || "",
      error: suyo.error || "",
      cargando: suyo.cargando,
    }),
  );
}

/** Abre la ficha de un contacto (`id` vacío es «una ficha nueva»). */
async function abrirLaFichaDeUnContacto(id) {
  const suyo = estadoDeLosContactos();
  suyo.error = "";
  suyo.aviso = "";
  suyo.borrando = false;
  if (!suyo.papeles.length) await recargarLosContactos();
  if (!id) {
    suyo.corrigiendo = null;
    suyo.ficha = { papeles: [], es_empresa_texto: "no_se" };
    suyo.vivos = [];
    return pantallaFichaDeContacto();
  }
  suyo.cargando = true;
  pantallaFichaDeContacto();
  try {
    const ficha = await apiJson(`/api/contactos/${id}`);
    suyo.corrigiendo = ficha;
    suyo.ficha = {
      ...ficha,
      es_empresa_texto:
        ficha.es_empresa === true ? "si" : ficha.es_empresa === false ? "no" : "no_se",
    };
    suyo.vivos = (ficha.vivos || []).map((vivo) => ({
      id: vivo.id,
      origen: vivo.origen,
      escrito: vivo.escrito,
      rotulo: elRotuloDeUnEscrito(vivo.escrito),
      aviso: vivo.escrito.texto_cambiado
        ? rellena(t("contactos.el_texto_ha_cambiado", ""), {
            ahora: vivo.escrito.texto,
            entonces: vivo.escrito.texto_de_entonces || "",
          })
        : "",
    }));
  } catch (fallo) {
    suyo.error = (fallo && fallo.message) || mensaje("no_se_pudo");
    suyo.corrigiendo = null;
    suyo.ficha = null;
    suyo.vivos = [];
  }
  suyo.cargando = false;
  pantallaFichaDeContacto();
}

/** La ficha de un contacto, ya en React. */
function pantallaFichaDeContacto() {
  const suyo = estadoDeLosContactos();
  const ficha = suyo.ficha || {};
  // La frase con los papeles que dicen sus propios papeles se monta aquí (una frase compuesta no vive
  // en un componente), y solo cuando hay algo que decir.
  const segunLoEscrito = (ficha.papeles_segun_lo_escrito || []).length
    ? [t("contactos.papeles_que_dicen_sus_papeles", ""), losPapelesEnPalabras(ficha.papeles_segun_lo_escrito)]
        .filter(Boolean)
        .join(" ")
    : "";
  montar(() =>
    pantallaDeUnContacto({
      textos: textosDeLosContactos(),
      borrador: {
        ...ficha,
        papeles: ficha.papeles || [],
        papeles_segun_lo_escrito_texto: segunLoEscrito,
      },
      papeles: suyo.papeles,
      vivos: suyo.vivos,
      puedeDesenlazar: true,
      corrigiendo: Boolean(suyo.corrigiendo),
      borrando: suyo.borrando,
      guardando: suyo.guardando,
      error: suyo.error || "",
    }),
  );
}

/** Lo que hay escrito en el formulario, leído **por el `id` de cada campo**, como en toda la casa. */
function recogeLaFichaDeContacto() {
  const valor = (id) => {
    const campo = document.getElementById(id);
    return campo ? campo.value.trim() : "";
  };
  const empresa = document.getElementById("contacto-es-empresa");
  const cual = empresa ? empresa.value : "no_se";
  return {
    nombre: valor("contacto-nombre"),
    nif: valor("contacto-nif"),
    telefono: valor("contacto-telefono"),
    correo: valor("contacto-correo"),
    direccion: valor("contacto-direccion"),
    localidad: valor("contacto-localidad"),
    notas: valor("contacto-notas"),
    // **Tres respuestas y no dos**: «no lo sé» no es lo mismo que «es una persona».
    es_empresa: cual === "no_se" ? null : cual === "si",
    // Los papeles se marcan con botones, así que no están en ningún campo: se leen del estado.
    papeles: (estadoDeLosContactos().ficha || {}).papeles || [],
  };
}

/** Guarda la ficha, y si hay cobertura manda los cambios. */
async function guardarElContacto() {
  const suyo = estadoDeLosContactos();
  const datos = recogeLaFichaDeContacto();
  if (!datos.nombre) {
    suyo.error = mensaje("C7_un_contacto_necesita_nombre");
    return pantallaFichaDeContacto();
  }
  suyo.error = "";
  suyo.guardando = true;
  pantallaFichaDeContacto();
  const corrigiendo = suyo.corrigiendo;
  const resultado = await mandarCambio(
    corrigiendo ? `/api/contactos/${corrigiendo.id}` : "/api/contactos",
    corrigiendo ? "PUT" : "POST",
    datos,
  );
  suyo.guardando = false;
  if (resultado.error) {
    suyo.error = resultado.error;
    return pantallaFichaDeContacto();
  }
  suyo.corrigiendo = resultado.datos;
  suyo.ficha = resultado.datos;
  suyo.vivos = (resultado.datos.vivos || []).map((vivo) => ({
    id: vivo.id,
    origen: vivo.origen,
    escrito: vivo.escrito,
    rotulo: elRotuloDeUnEscrito(vivo.escrito),
    aviso: vivo.escrito.texto_cambiado
      ? rellena(t("contactos.el_texto_ha_cambiado", ""), {
          ahora: vivo.escrito.texto,
          entonces: vivo.escrito.texto_de_entonces || "",
        })
      : "",
  }));
  await recargarLosContactos();
  suyo.aviso = t("contactos.guardada", "");
  pantallaFichaDeContacto();
}

/** Borra la ficha (con su confirmación, que la pone la pantalla). */
async function borrarElContacto(id) {
  const suyo = estadoDeLosContactos();
  suyo.borrando = false;
  suyo.error = "";
  const resultado = await mandarCambio(`/api/contactos/${id}`, "DELETE", null);
  if (resultado.error) {
    suyo.error = resultado.error;
    return pantallaFichaDeContacto();
  }
  suyo.corrigiendo = null;
  suyo.ficha = null;
  suyo.vivos = [];
  await recargarLosContactos();
  suyo.aviso = t("contactos.borrada", "");
  pantallaContactos();
}

/**
 * Marca o desmarca **un** papel.
 *
 * El papel se apunta en el estado **antes** de repintar, y eso no es un detalle: los botones de los
 * papeles no son campos de un formulario (no se leen del DOM), así que si se repintara con lo que
 * había en el servidor, el papel recién marcado desaparecería de la pantalla hasta guardar. Es la
 * misma trampa que el fichero del cuaderno de la Junta, con otra ropa.
 */
async function marcarElPapel(papel, puesto) {
  const suyo = estadoDeLosContactos();
  const ficha = suyo.ficha || {};
  const suyos = new Set(ficha.papeles || []);
  if (puesto) suyos.add(papel);
  else suyos.delete(papel);
  suyo.ficha = { ...ficha, papeles: [...suyos] };
  suyo.aviso = "";
  // Y si ya existe, se manda en el momento: los papeles no son un campo de texto que se pueda dejar a
  // medias, y el agricultor espera que tocar un botón haga algo.
  if (suyo.corrigiendo) {
    try {
      const guardada = await apiJson(`/api/contactos/${suyo.corrigiendo.id}/papeles`, {
        method: "POST",
        body: JSON.stringify({ papel, puesto }),
      });
      suyo.corrigiendo = guardada;
      suyo.ficha = { ...suyo.ficha, papeles: guardada.papeles };
      await recargarLosContactos();
    } catch (fallo) {
      suyo.error = (fallo && fallo.message) || mensaje("no_se_pudo");
      suyo.ficha = { ...suyo.ficha, papeles: ficha.papeles || [] };
    }
  }
  pantallaFichaDeContacto();
}

/** Abre la lista de nombres escritos que todavía no son de nadie, para enlazarlos con esta ficha. */
async function abrirLosNombresEscritos() {
  const suyo = estadoDeLosContactos();
  suyo.error = "";
  suyo.aviso = "";
  suyo.cargando = true;
  pantallaNombresEscritos();
  // Se piden también las fichas: sin ninguna no hay dónde enlazar, y la pantalla lo dice con su botón.
  await recargarLosContactos();
  await recargarLosEscritosSinEnlazar();
  suyo.cargando = false;
  pantallaNombresEscritos();
}

/** Pide los nombres escritos sin enlazar (con el buscador si lo hay). */
async function recargarLosEscritosSinEnlazar() {
  const suyo = estadoDeLosContactos();
  const parametros = new URLSearchParams({ sin_enlazar: "true" });
  if (suyo.buscadoEscritos) parametros.set("q", suyo.buscadoEscritos);
  try {
    suyo.escritos = await apiJson(`/api/contactos/escritos?${parametros.toString()}`);
    suyo.error = "";
  } catch (fallo) {
    suyo.escritos = [];
    suyo.error = (fallo && fallo.message) || mensaje("no_se_pudo");
  }
  return suyo;
}

/** La lista de nombres escritos, ya en React. */
function pantallaNombresEscritos() {
  const suyo = estadoDeLosContactos();
  montar(() =>
    pantallaDeLosNombresEscritos({
      textos: textosDeLosContactos(),
      escritos: suyo.escritos.map(escritoEnTarjeta),
      resumen: suyo.escritos.length
        ? conCuenta(t("contactos", {}), "escritos_cuantos", suyo.escritos.length)
        : "",
      buscado: suyo.buscadoEscritos,
      // Si no hay ninguna ficha, no hay dónde enlazar: la pantalla lo dice y ofrece el botón.
      hayContacto: suyo.lista.length > 0,
      aviso: suyo.aviso || "",
      error: suyo.error || "",
      cargando: suyo.cargando,
    }),
  );
}

/** Enlaza un nombre escrito con la ficha que se está mirando. */
async function enlazarUnEscrito(elemento) {
  const suyo = estadoDeLosContactos();
  const id = suyo.corrigiendo && suyo.corrigiendo.id;
  if (!id) return;
  suyo.error = "";
  suyo.aviso = "";
  const resultado = await mandarCambio(`/api/contactos/${id}/enlaces`, "POST", {
    tabla: elemento.dataset.tabla,
    campo: elemento.dataset.campo,
    registro_id: Number(elemento.dataset.registro),
  });
  if (resultado.error) {
    suyo.error = resultado.error;
    return pantallaNombresEscritos();
  }
  suyo.corrigiendo = resultado.datos;
  suyo.ficha = { ...(suyo.ficha || {}), ...resultado.datos };
  suyo.vivos = (resultado.datos.vivos || []).map((vivo) => ({
    id: vivo.id,
    origen: vivo.origen,
    escrito: vivo.escrito,
    rotulo: elRotuloDeUnEscrito(vivo.escrito),
    aviso: "",
  }));
  await recargarLosContactos();
  suyo.aviso = t("contactos.enlazado", "");
  pantallaFichaDeContacto();
}

/** Quita el enlace. **El nombre escrito se queda donde estaba**, con sus letras. */
async function desenlazarUnEscrito(enlaceId) {
  const suyo = estadoDeLosContactos();
  const id = suyo.corrigiendo && suyo.corrigiendo.id;
  if (!id) return;
  suyo.error = "";
  const resultado = await mandarCambio(
    `/api/contactos/${id}/enlaces/${enlaceId}`,
    "DELETE",
    null,
  );
  if (resultado.error) {
    suyo.error = resultado.error;
    return pantallaFichaDeContacto();
  }
  suyo.corrigiendo = resultado.datos;
  suyo.ficha = { ...(suyo.ficha || {}), ...resultado.datos };
  suyo.vivos = (resultado.datos.vivos || []).map((vivo) => ({
    id: vivo.id,
    origen: vivo.origen,
    escrito: vivo.escrito,
    rotulo: elRotuloDeUnEscrito(vivo.escrito),
    aviso: "",
  }));
  await recargarLosContactos();
  suyo.aviso = t("contactos.enlace_quitado", "");
  pantallaFichaDeContacto();
}

/** Abre la revisión de los nombres que ya están escritos. */
async function abrirLaRevisionDeLosContactos() {
  const suyo = estadoDeLosContactos();
  suyo.error = "";
  suyo.aviso = "";
  suyo.revisarApuntado = "";
  suyo.revisarDeshecho = "";
  suyo.cargando = true;
  pantallaRevisionDeLosContactos();
  await recargarLaRevision();
  await recargarLosContactos();
  suyo.cargando = false;
  pantallaRevisionDeLosContactos();
}

/** Pide la propuesta: **mirarla no escribe nada** (lo hace el servidor por su cuenta). */
async function recargarLaRevision() {
  const suyo = estadoDeLosContactos();
  try {
    suyo.revisar = await apiJson("/api/contactos/migracion");
    suyo.error = "";
  } catch (fallo) {
    suyo.revisar = null;
    suyo.error = (fallo && fallo.message) || mensaje("no_se_pudo");
  }
  return suyo;
}

/** Una propuesta, con su motivo ya dicho en palabras por el servidor. */
function propuestaParaLaPantalla(propuesta) {
  let motivoTexto = "";
  if (propuesta.motivo === "mismo_nif") {
    motivoTexto = t("contactos.revision_motivo_mismo_nif", "");
  } else if (propuesta.motivo === "el_mismo_nombre") {
    motivoTexto = t("contactos.revision_motivo_el_mismo_nombre", "");
  } else if (propuesta.motivo === "se_parecen") {
    // **Los dos nombres que se parecen, con nombre y apellidos.** Enseñar solo el grupo entero haría
    // creer que todos se parecen con todos, y no es lo mismo.
    motivoTexto = rellena(t("contactos.revision_se_parecen_estos", ""), {
      uno: (propuesta.pareja || [])[0] || "",
      otro: (propuesta.pareja || [])[1] || "",
    });
  } else if (propuesta.motivo === "mismo_nif_nombres_distintos") {
    // **El caso que encontró la revisión independiente.** El NIF coincide pero los nombres no tienen
    // nada que ver: eso no es una prueba, es un papel mal escrito, y lo decide el agricultor.
    motivoTexto = t("contactos.revision_motivo_mismo_nif_nombres_distintos", "");
  } else {
    motivoTexto = t("contactos.revision_motivo_el_mismo_nombre_dos_nif", "");
  }
  const nifsTexto =
    propuesta.motivo === "el_mismo_nombre_dos_nif"
      ? rellena(t("contactos.revision_nifs_dos", ""), { nifs: (propuesta.nifs || []).join(", ") })
      : propuesta.motivo === "mismo_nif_nombres_distintos"
        ? rellena(t("contactos.revision_nif_compartido", ""), {
            nifs: (propuesta.nifs || []).join(", "),
          })
        : "";
  return {
    clave: propuesta.clave,
    nombre: propuesta.nombre,
    segura: propuesta.segura,
    motivo: propuesta.motivo,
    motivo_texto: motivoTexto,
    nifs_texto: nifsTexto,
    papeles_texto: propuesta.papeles && propuesta.papeles.length
      ? [t("contactos.papeles_que_tendria", ""), losPapelesEnPalabras(propuesta.papeles)].join(" ")
      : "",
    escritos: (propuesta.escritos || []).map(escritoEnTarjeta),
  };
}

/** La pantalla de la revisión, ya en React. */
function pantallaRevisionDeLosContactos() {
  const suyo = estadoDeLosContactos();
  const revisar = suyo.revisar || { resumen: {}, propuestas: [], ya_enlazados: 0, total_escritos: 0 };
  const todas = (revisar.propuestas || []).map(propuestaParaLaPantalla);
  const resumen = revisar.resumen || {};
  return montar(() =>
    pantallaDeLaRevisionDeLosNombres({
      textos: textosDeLosContactos(),
      // **La lista de las que se pueden apuntar y la de las que hay que mirar salen separadas de aquí**,
      // y esa separación es lo que hace que una prueba pueda comprobar que la primera no lleva ni una
      // dudosa. La pantalla no decide nada: solo pinta las dos.
      seguras: todas.filter((una) => una.segura),
      paraMirar: todas.filter((una) => !una.segura),
      resumenTexto: elResumenDeLaPropuesta(resumen),
      // El resumen de la frase necesita los dos números, así que se rellena a mano cuando hay más de
      // una (el singular ya lo trae puesto).
      hayYaEnlazados: Boolean(revisar.ya_enlazados),
      yaEnlazadosTexto: revisar.ya_enlazados
        ? rellena(t("contactos.revision_cuantos_ya", ""), { cuantos: revisar.ya_enlazados })
        : "",
      sePuedeDeshacer: Boolean(revisar.se_puede_deshacer),
      // **Los botones de apuntar se apagan mientras la petición está en el aire** (defecto 3 de la
      // revisión: el doble toque con guantes mandaba la misma confirmación dos veces). El servidor la
      // contesta ahora sin duplicar y devolviendo su resultado, pero el botón no debe invitar a eso.
      enviando: suyo.cargando,
      apuntado: suyo.revisarApuntado,
      deshecho: suyo.revisarDeshecho,
      aviso: suyo.aviso || "",
      error: suyo.error || "",
      cargando: suyo.cargando,
    }),
  );
}

/** **El resumen de la propuesta, con sus dos números** (fichas y nombres escritos). */
function elResumenDeLaPropuesta(resumen) {
  if (!resumen || !resumen.fichas) return "";
  const plantilla =
    resumen.fichas === 1
      ? t("contactos.revision_cuantas_una", "")
      : t("contactos.revision_cuantas", "");
  return rellena(plantilla, { cuantas: resumen.fichas, nombres: resumen.nombres });
}

/** Apunta una propuesta (o todas las seguras) por su clave. */
async function apuntarLaPropuesta(claves) {
  const suyo = estadoDeLosContactos();
  suyo.error = "";
  suyo.aviso = "";
  suyo.cargando = true;
  pantallaRevisionDeLosContactos();
  const resultado = await mandarCambio("/api/contactos/migracion/aplicar", "POST", { claves });
  suyo.cargando = false;
  if (resultado.error) {
    suyo.error = resultado.error;
    return pantallaRevisionDeLosContactos();
  }
  const datos = resultado.datos || {};
  suyo.revisarApuntado = datos.fichas
    ? rellena(
        datos.fichas === 1
          ? t("contactos.revision_apuntadas_uno", "")
          : t("contactos.revision_apuntadas", ""),
        { cuantas: datos.fichas, nombres: datos.enlaces },
      )
    : (datos.avisos || [])[0] || "";
  suyo.revisarDeshecho = "";
  await recargarLaRevision();
  await recargarLosContactos();
  pantallaRevisionDeLosContactos();
}

/** Deshace lo que apuntó la migración, respetando lo que el agricultor ya ha hecho suyo. */
async function deshacerLaMigracion() {
  const suyo = estadoDeLosContactos();
  suyo.error = "";
  suyo.aviso = "";
  suyo.cargando = true;
  pantallaRevisionDeLosContactos();
  const resultado = await mandarCambio("/api/contactos/migracion/deshacer", "POST", {});
  suyo.cargando = false;
  if (resultado.error) {
    suyo.error = resultado.error;
    return pantallaRevisionDeLosContactos();
  }
  const datos = resultado.datos || {};
  suyo.revisarDeshecho = rellena(t("contactos.revision_deshecho", ""), {
    fichas: datos.fichas,
    enlaces: datos.enlaces,
  });
  suyo.revisarApuntado = "";
  // **Y lo que no se ha quitado se dice**, con su motivo: volver atrás no puede llevarse una ficha que
  // el agricultor ya ha corregido, y callarlo haría creer que se ha deshecho todo.
  suyo.aviso = (datos.se_quedan || []).join(" ");
  await recargarLaRevision();
  await recargarLosContactos();
  pantallaRevisionDeLosContactos();
}

// ---------------------------------------------------------------------------
// La maquinaria de la finca (T14, E8, 03/10/2026)
// ---------------------------------------------------------------------------
//
// QUÉ HACE ESTA PARTE, Y QUÉ ES LO QUE NO HACE
//
// Es la parte de `app.js` de la pantalla S16: la lista de máquinas, la ficha de una, sus cinco
// obligaciones, sus inspecciones y sus averías. Y **aquí no se calcula ni una fecha**: lo que se enseña
// es lo que contestó el servidor, que a su vez copia lo que dice el papel. El porqué está escrito entero
// en `app/maquinaria.py`, y en el JavaScript se cumple en dos sitios que conviene no romper:
//
//   1. **Cuando la próxima fecha no está, se dice que falta el dato** (`sin_fecha_corto`) y se cuenta
//      cuántas obligaciones no la tienen (`faltan_por_saber`). Nunca se rellena con nada.
//   2. **El texto de cada estado sale del servidor** (`situacion_*`), y las fechas se meten en su hueco
//      con `rellena`. Así el vocabulario sigue viviendo en `textos.py` y el test de jerga lo revisa.
//
// LO QUE SE PREPARA AQUÍ Y POR QUÉ
//
// El componente de React es **puro**: recibe todo hecho. Lo que se prepara aquí es lo que no puede saber
// —los nombres de las columnas, los textos de cada estado, las fechas en formato español— para que la
// tabla del ordenador y las tarjetas del móvil **digan exactamente lo mismo** de la misma máquina: se
// preparan una vez, en `maquinasPreparadas`, y las dos lo leen de ahí.

/** El estado de la maquinaria, creado la primera vez que hace falta (como el del almacén). */
function estadoDeLaMaquinaria() {
  if (!estado.maquinaria) {
    estado.maquinaria = {
      // Lo que devolvió `GET /api/maquinaria`: las máquinas con su resumen, los equipos del cuaderno que
      // todavía no están en la lista y lo que el programa no sabe calcular.
      tabla: null,
      lista: [],
      equipos: [],
      queFalta: [],
      avisos: [],
      filtro: "",
      // La ficha abierta, ya preparada para el componente…
      maquina: null,
      // …y la misma ficha **en crudo**, que es lo que hace falta para corregir una inspección o una
      // avería: el formulario se rellena con los datos tal y como los devolvió el servidor, no con los
      // textos ya montados.
      maquinaCruda: null,
      // Lo que se está rellenando: la máquina, una inspección o una avería. Vive aquí y no dentro del
      // componente por lo de siempre: el componente se vuelve a montar entero cada vez, así que lo escrito
      // tiene que sobrevivir a un repintado (y un formulario que se vacía solo es un formulario que se
      // pierde).
      formulario: null,
      borrador: null,
      // La pregunta del motivo, cuando se va a anular una inspección o una avería.
      anulando: null,
      cargando: false,
      guardando: false,
      error: "",
      aviso: "",
    };
  }
  return estado.maquinaria;
}

/**
 * El formulario que se está rellenando, **reconstruido en cada pintado**.
 *
 * POR QUÉ SE GUARDA SOLO CUÁL ES Y NO EL FORMULARIO ENTERO. Porque los valores de las casillas viven en la
 * pantalla, y el formulario tiene que recogerlos **en el momento de pintar**: si se guardara el formulario
 * ya montado (como se hacía al principio), al elegir una opción se repintaría con los valores de cuando se
 * abrió, y lo que el agricultor había escrito se perdería —el mismo defecto que ya costó una ronda con el
 * fichero del cuaderno de la Junta—.
 */
function elFormularioDeLaMaquinaria(descriptor) {
  if (!descriptor) return null;
  if (descriptor.clase === "inspeccion") return formularioDeUnaInspeccion(descriptor);
  if (descriptor.clase === "averia") return formularioDeUnaAveria(descriptor);
  return formularioDeLaMaquina({ corrigiendo: Boolean(descriptor.corrigiendo) });
}

/** El vocabulario de estas pantallas: el de la maquinaria y los dos botones de corregir y borrar. */
function textosDeLaMaquinaria() {
  return {
    maquinaria: t("maquinaria", {}),
    acciones: t("acciones", {}),
    // Los dos botones de siempre, que en este programa se llaman igual en todas las fichas.
    corregir: t("corregir.boton", ""),
    borrar: t("corregir.borrar", ""),
  };
}

/** El texto de una de las listas cerradas que sirve el servidor (`clases_de_maquina`, etc.). */
function textoDeLaLista(nombre, valor, porDefecto = "") {
  const lista = t(nombre, []) || [];
  const uno = lista.find((opcion) => String(opcion.valor) === String(valor));
  return (uno && uno.texto) || porDefecto;
}

/** Las opciones de una de esas listas, con la que está elegida marcada. */
function opcionesDeLaLista(nombre, elegido) {
  return (t(nombre, []) || []).map((opcion) => ({
    valor: opcion.valor,
    texto: opcion.texto,
    elegido: String(opcion.valor) === String(elegido),
  }));
}

/**
 * El texto de lo que le pasa a una obligación, con su fecha metida en el hueco.
 *
 * **Es el único sitio donde se compone esa frase**, y por eso lo usan la ficha y la tabla: si se
 * compusiera dos veces, la lista y la ficha podrían decir cosas distintas de la misma máquina, que es la
 * peor forma de perder la confianza en un programa.
 */
function textoDeLaSituacion(obligacion) {
  const plantilla = t(`maquinaria.situacion_${obligacion.situacion}`, "");
  return rellena(plantilla, {
    fecha: obligacion.proxima_fecha ? formateaFecha(obligacion.proxima_fecha) : "",
  });
}

/**
 * La frase de la próxima revisión de una máquina: **la fecha que hay escrita, o que falta el dato**.
 *
 * Y cuando hay fecha pero además hay obligaciones sin fecha, se dice cuántas: sin esa cuenta, la tabla
 * enseñaría «ITV el 12/05/2027» y el agricultor creería que con eso está todo mirado.
 */
function textoDeLaProximaRevision(resumen, { corto = false } = {}) {
  const m = t("maquinaria", {});
  const revision = (resumen || {}).proxima_revision || {};
  const cuantas = revision.sin_fecha || 0;
  const lo_que_falta = cuantas ? conCuenta(m, "faltan_por_saber", cuantas) : "";
  if (!revision.fecha) {
    // Sin ninguna fecha escrita: se dice que falta el dato, y cuántas cosas son.
    return lo_que_falta || t("maquinaria.sin_fecha_corto", "");
  }
  const suyo = rellena(t("maquinaria.proxima_revision_texto", ""), {
    obligacion: textoDeLaLista("obligaciones_de_una_maquina", revision.tipo, revision.tipo || ""),
    fecha: formateaFecha(revision.fecha),
  });
  // En la tabla, la cuenta de lo que falta va **en su renglón** (ver `proxima_pista`): aquí se devuelve solo
  // la fecha, que es lo que no puede ensanchar la columna.
  if (corto) return suyo;
  return lo_que_falta ? `${suyo} · ${lo_que_falta}` : suyo;
}

/**
 * Lo que se dice de los papeles de una máquina, con las inspecciones que no traen ninguno.
 *
 * **En la tabla va en corto, y en una sola frase.** La celda no puede llevar «1 papel · 1 sin papel» (dos
 * frases seguidas ensanchan la columna y acaban sacando de la pantalla los botones de la fila, medido): lo
 * que importa en una celda es **si falta algún papel**, porque es lo único con lo que hay algo que hacer. El
 * detalle entero está en la ficha, donde sí hay sitio para contarlo.
 */
function textoDeLaDocumentacion(resumen, { corto = false } = {}) {
  const m = t("maquinaria", {});
  const papeles = (resumen || {}).documentacion || {};
  if (!papeles.inspecciones) return t("maquinaria.sin_inspecciones_corto", "");
  if (corto) {
    return papeles.sin_papel
      ? conCuenta(m, "sin_papel_apuntado", papeles.sin_papel)
      : conCuenta(m, "papeles", papeles.con_papel || 0);
  }
  const con_papel = conCuenta(m, "papeles", papeles.con_papel || 0);
  if (!papeles.sin_papel) return con_papel;
  return `${con_papel} · ${conCuenta(m, "sin_papel_apuntado", papeles.sin_papel)}`;
}

/**
 * La palabra que dice si una máquina tiene algo que mirar. Sin color, porque el color solo no informa.
 *
 * `corto` es para la celda de la tabla: «4 avisos» en vez de «4 cosas que mirar», que es lo mismo dicho de
 * la manera que cabe entre las nueve columnas.
 */
function textoDeLosAvisos(resumen, { corto = false } = {}) {
  const cuantos = (resumen || {}).avisos || 0;
  if (!cuantos) return null;
  const base = corto ? "avisos_corto" : "avisos";
  return { texto: conCuenta(t("maquinaria", {}), base, cuantos), tipo: "" };
}

/** La etiqueta corta del estado de una próxima revisión, para la columna de la tabla. */
function estadoDeLaRevision(revision) {
  const m = t("maquinaria", {});
  if (!revision || !revision.fecha) return null;
  // **La palabra sale de la situación que decide el servidor**, y no de una cuenta que se hiciera aquí:
  // el margen de «caduca pronto» es una sola decisión y vive en `app/maquinaria.py`. Si se calculara dos
  // veces, la lista y la ficha podrían decir cosas distintas de la misma máquina.
  const palabras = {
    vencida: m.vencida_corto,
    no_favorable: m.no_favorable_corto,
    proxima: m.al_caer_corto,
  };
  const texto = palabras[revision.situacion];
  return texto ? { texto, tipo: revision.situacion } : null;
}

/**
 * Cada máquina con sus textos ya montados: lo que leen **la tabla del ordenador y la tarjeta del móvil**.
 *
 * Se prepara una sola vez y de aquí beben las dos, por el motivo de siempre: dos sitios que componen la
 * misma frase acaban diciendo cosas distintas.
 *
 * Y los campos crudos (`horas_numero`, `proxima_orden`) van también, porque una tabla se ordena **por el
 * dato**, no por el texto ya escrito: ordenar «12/05/2027» como texto pondría delante una fecha de 2028.
 */
function maquinasPreparadas() {
  const suyo = estadoDeLaMaquinaria();
  const m = t("maquinaria", {});
  // **De dónde salen «Próxima revisión» y «Papeles», y por qué no de `maquinaria`.**
  // Esos dos rótulos están en los de la **tabla** (`textos.TABLA`), porque son los mismos dos datos
  // que enseña la tabla del ordenador: la tarjeta del móvil tiene que decir lo mismo y salir de la
  // misma fuente. Pidiéndolos a `maquinaria` salían como `undefined` en la tarjeta —«undefined: ITV el
  // 12/05/2026»—, que es lo que midió la revisión independiente del T14 (03/10/2026). Y con `t(..., "")`
  // lo peor que puede pasar es que el rótulo salga vacío, nunca la palabra «undefined».
  const col = (clave) => t(`tabla.${clave}`, "");
  return (suyo.lista || []).map((maquina) => {
    const resumen = maquina.resumen || {};
    const revision = resumen.proxima_revision || {};
    const avisos = (suyo.avisos || [])
      .filter((aviso) => Number(aviso.maquina_id) === Number(maquina.id))
      .map((aviso) => ({ texto: aviso.mensaje, urgente: Boolean(aviso.urgente) }));
    const sin_horas = maquina.horas === null || maquina.horas === undefined;
    const clase_texto = textoDeLaLista("clases_de_maquina", maquina.clase, m.sin_decir);
    const propiedad_texto = textoDeLaLista(
      "propiedades_de_una_maquina",
      maquina.propiedad,
      m.propiedad_no_se,
    );
    const disponibilidad_texto = textoDeLaLista(
      "disponibilidades_de_una_maquina",
      maquina.disponibilidad,
      m.disponibilidad_no_se,
    );
    const matricula_o_serie = maquina.matricula || maquina.numero_serie || m.sin_decir;
    return {
      ...maquina,
      clase_texto,
      propiedad_texto,
      disponibilidad_texto,
      matricula_o_serie,
      horas_texto: sin_horas ? "" : `${formateaNumero(maquina.horas, 0)} ${m.horas_corto || ""}`.trim(),
      horas_numero: sin_horas ? "" : maquina.horas,
      proxima_texto: textoDeLaProximaRevision(resumen, { corto: true }),
      // Para ordenar por la fecha de verdad, y para que lo que no tiene fecha se vaya al final.
      proxima_orden: revision.fecha || "",
      proxima_estado: estadoDeLaRevision(revision),
      // **Lo que falta por saber va como pista, en su renglón**, y no pegado a la fecha: con las nueve
      // columnas de la tabla, «ITV el 01/03/2029 · 4 más sin fecha» en una sola línea ensanchaba la columna
      // hasta sacar de la pantalla los botones de la fila (medido). En su renglón se lee igual y no ensancha.
      proxima_pista: revision.sin_fecha
        ? conCuenta(m, "faltan_por_saber", revision.sin_fecha)
        : "",
      papeles_texto: textoDeLaDocumentacion(resumen, { corto: true }),
      avisos_texto: textoDeLosAvisos(resumen, { corto: true }),
      detalle: [clase_texto, matricula_o_serie, propiedad_texto].join(" · "),
      proxima: `${col("proxima_revision")}: ${textoDeLaProximaRevision(resumen)}`,
      papeles: `${col("documentacion")}: ${textoDeLaDocumentacion(resumen)}`,
      disponibilidad: `${m.disponibilidad}: ${disponibilidad_texto}`,
      avisos,
    };
  });
}

/** Las máquinas que se están viendo: con el buscador puesto, solo las que casan. */
function maquinasFiltradas() {
  const suyo = estadoDeLaMaquinaria();
  const buscando = (suyo.filtro || "").trim().toLocaleLowerCase("es");
  if (!buscando) return suyo.lista;
  return suyo.lista.filter((maquina) =>
    [
      maquina.nombre,
      maquina.matricula,
      maquina.numero_serie,
      maquina.numero_roma,
      maquina.marca,
      maquina.modelo,
    ]
      .filter(Boolean)
      .some((texto) => String(texto).toLocaleLowerCase("es").includes(buscando)),
  );
}

/** La tabla de la maquinaria, con las ocho columnas del contrato y el pie del conjunto. */
function tablaDeLaMaquinaria() {
  const col = (clave) => t(`tabla.${clave}`, "");
  const m = t("maquinaria", {});
  const suyo = estadoDeLaMaquinaria();
  const preparadas = maquinasPreparadas();
  const casan = new Set(maquinasFiltradas().map((maquina) => maquina.id));
  const ordenadas = ordenarFichas(
    preparadas.filter((maquina) => casan.has(maquina.id)),
    elOrdenDeLaTabla("maquinaria"),
    "id",
  );
  const columnas = columnasDeLaTabla("maquinaria", [
    { texto: col("maquina"), campo: "nombre" },
    { texto: col("tipo_maquina"), campo: "clase_texto" },
    { texto: col("matricula_o_serie"), campo: "matricula_o_serie" },
    { texto: col("propiedad"), campo: "propiedad_texto" },
    { texto: col("horas"), campo: "horas_numero", clase: "tabla-numero" },
    { texto: col("proxima_revision"), campo: "proxima_orden", clase: "tabla-numero" },
    { texto: col("documentacion") },
    { texto: col("disponibilidad"), campo: "disponibilidad_texto" },
    { texto: col("acciones") },
  ]);

  const filas = ordenadas.map((maquina) => ({
    celdas: [
      { texto: maquina.nombre },
      { texto: maquina.clase_texto },
      { texto: maquina.matricula_o_serie },
      { texto: maquina.propiedad_texto },
      { texto: maquina.horas_texto || m.sin_decir, clase: "tabla-numero" },
      {
        texto: maquina.proxima_texto,
        clase: "tabla-numero",
        // **Lo que falta por saber, en su renglón** (no pegado a la fecha): la celda no puede ensancharse.
        pista: maquina.proxima_pista,
        // **El estado va con palabras**: «Vencida», «Desfavorable»… El color solo no informa (regla de la
        // casa), y en una tabla de nueve columnas es lo primero que se mira.
        estado: maquina.proxima_estado,
      },
      // La celda de los papeles lleva **una sola frase**: la que dice si falta alguno. El detalle (cuántos
      // hay y cuántos no traen papel) está en la ficha, donde sí hay sitio; repetirlo aquí en pequeño era
      // ruido en una celda que ya dice lo que importa.
      { texto: maquina.papeles_texto },
      { texto: maquina.disponibilidad_texto, estado: maquina.avisos_texto },
    ],
    acciones: [
      {
        // **En corto, «VER»**, como en las demás tablas: «VER ESTA MÁQUINA» ensancha la última columna
        // hasta empujar la tabla fuera de la pantalla (medido a 1440 px). La frase entera es la del botón de
        // la tarjeta del móvil, donde sí hay sitio.
        etiqueta: m.ver_corto,
        accion: "maquina-ver",
        datos: { id: maquina.id },
        clase: "boton-claro",
      },
    ],
  }));

  const total = preparadas.length;
  const cuantas = filas.length;
  const resumen = suyo.filtro
    ? rellena(t("tabla.resumen_maquinaria_filtrado", ""), { cuantas, total })
    : conCuenta(t("tabla", {}), "resumen_maquinaria", cuantas);
  return { clave: "maquinaria", etiqueta: col("maquinaria_etiqueta"), columnas, filas, resumen };
}

/**
 * El nombre del papel que demuestra una inspección, buscándolo entre los papeles guardados.
 *
 * La ficha decía solo «Con su papel»: **no decía cuál** ni dejaba verlo, y el papel es justo lo que se
 * enseña en una inspección (lo encontró la revisión del ticket). Es la misma lista que usa el formulario
 * para elegirlo (`papelesParaElegir`), así que lo que se elige al apuntar es lo que se lee después.
 */
function elPapelPorSuId(documento_id) {
  if (documento_id === null || documento_id === undefined) return "";
  const suyos = (estado.documentos || {}).documentos || [];
  const papel = suyos.find((uno) => Number(uno.id) === Number(documento_id));
  return (papel && papel.titulo) || t("maquinaria.papel_sin_nombre", "");
}

/**
 * La ficha de una máquina, ya preparada para el componente.
 *
 * De cada obligación se prepara **todo lo que enseña**: la aplicabilidad con sus tres respuestas, el
 * texto de su estado, la última inspección, el resultado, la próxima fecha (la del papel), su papel y la
 * fuente de la obligación. Y cuando falta la **clasificación técnica** se dice: es el dato del que depende
 * todo, y el programa lo pide en vez de deducirlo.
 */
function unaMaquinaPreparada(ficha) {
  const m = t("maquinaria", {});
  const maquina = (ficha || {}).maquina || {};
  const obligaciones = ((ficha || {}).obligaciones || []).map((obligacion) => ({
    tipo: obligacion.tipo,
    nombre: textoDeLaLista("obligaciones_de_una_maquina", obligacion.tipo, obligacion.tipo),
    que_es: t(`maquinaria.que_es_${obligacion.tipo}`, ""),
    situacion_texto: textoDeLaSituacion(obligacion),
    // Las tres respuestas, con la que está puesta marcada. Y la pregunta de **de dónde sale**, que es lo
    // primero que se pregunta en una inspección.
    opciones_aplicabilidad: {
      etiqueta: m.aplicabilidad,
      campo: "aplicabilidad",
      datos: { tipo: obligacion.tipo },
      opciones: opcionesDeLaLista("aplicabilidades_de_una_obligacion", obligacion.aplicabilidad),
    },
    opciones_origen: {
      etiqueta: m.de_donde_sale,
      pista: m.de_donde_sale_pista,
      campo: "origen",
      datos: { tipo: obligacion.tipo },
      opciones: opcionesDeLaLista(
        "origenes_de_una_aplicabilidad",
        obligacion.origen_de_la_aplicabilidad,
      ),
    },
    ultima_texto: obligacion.ultima_inspeccion
      ? rellena(t("maquinaria.ultima_inspeccion_texto", ""), {
          fecha: formateaFecha(obligacion.ultima_inspeccion.fecha),
        })
      : "",
    resultado_texto: textoDeLaLista(
      "resultados_de_una_inspeccion",
      obligacion.resultado,
      m.resultado_no_consta,
    ),
    proxima_texto: obligacion.proxima_fecha ? formateaFecha(obligacion.proxima_fecha) : "",
    // **Con su nombre, y con su identificador para poder abrirlo** (ver `elPapelPorSuId`).
    papel: obligacion.trae_papel ? elPapelPorSuId(obligacion.documento_id) : "",
    papel_id: obligacion.documento_id || null,
    fuente: obligacion.fuente || null,
    // **Lo que el programa pide en vez de deducir**: si no se sabe la clasificación técnica, no se puede
    // decir qué le toca, y la ficha lo dice con estas palabras.
    clasificacion_falta:
      !maquina.clasificacion_tecnica && obligacion.situacion === "no_se_si_toca",
  }));
  const sin_horas = maquina.horas === null || maquina.horas === undefined;
  return {
    maquina: {
      id: maquina.id,
      nombre: maquina.nombre,
      clase_texto: textoDeLaLista("clases_de_maquina", maquina.clase, m.sin_decir),
      clasificacion: maquina.clasificacion_tecnica || "",
      clasificacion_falta: !maquina.clasificacion_tecnica,
      matricula: maquina.matricula || "",
      numero_serie: maquina.numero_serie || "",
      numero_roma: maquina.numero_roma || "",
      marca: maquina.marca || "",
      modelo: maquina.modelo || "",
      anio_texto: maquina.anio ? String(maquina.anio) : "",
      // Los números **en crudo**, para el formulario de corregir: en una casilla de número no puede ir
      // «2.400 h» (ver `formularioDeLaMaquina`), y con el texto ya montado las horas se perderían al
      // guardar.
      anio_numero: maquina.anio ? String(maquina.anio) : "",
      horas_numero: sin_horas ? "" : maquina.horas,
      horas_texto: sin_horas ? "" : `${formateaNumero(maquina.horas, 0)} ${m.horas_corto || ""}`.trim(),
      propiedad_texto: textoDeLaLista("propiedades_de_una_maquina", maquina.propiedad, ""),
      disponibilidad_texto: textoDeLaLista(
        "disponibilidades_de_una_maquina",
        maquina.disponibilidad,
        "",
      ),
      es_el_equipo_del_cuaderno: Boolean(maquina.equipo_aplicacion_id),
      // **La clase, la propiedad y la disponibilidad, EN CRUDO**, por el mismo motivo que los números de
      // arriba: el formulario de corregir las necesita tal cual las guardó el servidor (`clase`, no
      // `clase_texto`). Faltaban, y eso hacía **dos** cosas mal a la vez (lo midió la revisión
      // independiente del T14, 03/10/2026): el formulario enseñaba las tres preguntas **sin marcar** —como
      // si nadie hubiera contestado— y al guardar mandaba `""` en las tres, así que el servidor contestaba
      // 422 y **corregir una máquina no se guardaba nunca**.
      clase: maquina.clase || "",
      propiedad: maquina.propiedad || "",
      disponibilidad: maquina.disponibilidad || "",
      // El identificador del equipo enlazado va también: **corregir una máquina no puede desenlazarla sin
      // que nadie lo diga**. El formulario no lo manda si no se toca esa pregunta, y sin este dato el
      // enlace se perdería al guardar (es el defecto de «una columna que no vuelve al formulario»).
      equipo_aplicacion_id: maquina.equipo_aplicacion_id ?? null,
      notas: maquina.notas || "",
      que_falta: (ficha || {}).que_falta || [],
    },
    avisos: ((ficha || {}).avisos || []).map((aviso) => ({
      texto: aviso.mensaje,
      urgente: Boolean(aviso.urgente),
      tipo: aviso.tipo,
    })),
    obligaciones,
    inspecciones: ((ficha || {}).inspecciones || []).map((inspeccion) => ({
      id: inspeccion.id,
      titulo: rellena(t("maquinaria.inspeccion_de", ""), {
        obligacion: textoDeLaLista("obligaciones_de_una_maquina", inspeccion.tipo, inspeccion.tipo),
      }),
      fecha_texto: rellena(t("maquinaria.ultima_inspeccion_texto", ""), {
        fecha: formateaFecha(inspeccion.fecha),
      }),
      resultado_texto: textoDeLaLista(
        "resultados_de_una_inspeccion",
        inspeccion.resultado,
        m.resultado_no_consta,
      ),
      proxima_texto: inspeccion.proxima_fecha
        ? `${m.proxima_fecha}: ${formateaFecha(inspeccion.proxima_fecha)}`
        : `${m.proxima_fecha}: ${m.sin_fecha_apuntada}`,
      // **El caso que el contrato pide que se diga**: una inspección sin documento se apunta igual y aquí
      // se dice que no lo trae, sin adornos. Y con documento, se dice **cuál es** y se puede abrir.
      papel_texto: inspeccion.trae_papel
        ? `${m.con_papel}: ${elPapelPorSuId(inspeccion.documento_id)}`
        : m.sin_papel_pista,
      papel_id: inspeccion.documento_id || null,
      anulado: Boolean(inspeccion.anulado),
      motivo_anulacion: inspeccion.motivo_anulacion || "",
    })),
    averias: ((ficha || {}).averias || []).map((averia) => ({
      id: averia.id,
      titulo: rellena(t("maquinaria.averia_de_texto", ""), { fecha: formateaFecha(averia.fecha) }),
      fecha_texto: averia.que_paso || "",
      resuelta_texto:
        averia.resuelta === true
          ? rellena(t("maquinaria.arreglada_texto", ""), {
              fecha: averia.fecha_resuelta ? formateaFecha(averia.fecha_resuelta) : m.sin_decir,
            })
          : averia.resuelta === false
            ? t("maquinaria.sigue_sin_arreglar", "")
            : t("maquinaria.no_se_si_arreglada", ""),
      notas: averia.notas || "",
      anulado: Boolean(averia.anulado),
    })),
  };
}

/** Abre «mi maquinaria»: se pinta enseguida y se vuelve a pintar con lo que contesta el servidor. */
async function abrirLaMaquinaria() {
  const suyo = estadoDeLaMaquinaria();
  suyo.error = "";
  suyo.aviso = "";
  suyo.formulario = null;
  suyo.borrador = null;
  suyo.anulando = null;
  suyo.maquina = null;
  suyo.cargando = true;
  pantallaMaquinaria();
  await recargarLaMaquinaria();
  suyo.cargando = false;
  pantallaMaquinaria();
}

/** Vuelve a pedir la lista y los avisos de todas las máquinas. */
async function recargarLaMaquinaria() {
  const suyo = estadoDeLaMaquinaria();
  let problema = "";
  const apuntar = (fallo) => {
    if (!problema) problema = (fallo && fallo.message) || mensaje("no_se_pudo");
    return null;
  };
  const [tabla, avisos] = await Promise.all([
    apiJson("/api/maquinaria").catch(apuntar),
    apiJson("/api/maquinaria/avisos").catch(() => apuntar()),
  ]);
  if (tabla) {
    suyo.tabla = tabla;
    suyo.lista = tabla.maquinas || [];
    suyo.equipos = tabla.equipos_sin_ficha || [];
    suyo.queFalta = tabla.que_falta || [];
  }
  suyo.avisos = Array.isArray(avisos) ? avisos : [];
  // **Y los mismos avisos, para el asistente**: es lo que hace que elegir la máquina de un trabajo avise de
  // lo mismo que enseña su ficha. Si no se refrescara, el agricultor que acaba de pasar una inspección
  // seguiría viendo el aviso viejo al apuntar el trabajo siguiente.
  estado.maquinariaAvisos = suyo.avisos;
  suyo.error = problema;
  return suyo;
}

/** La lista de la maquinaria, ya en React. */
function pantallaMaquinaria() {
  const suyo = estadoDeLaMaquinaria();
  const m = t("maquinaria", {});
  const preparadas = maquinasPreparadas();
  const casan = new Set(maquinasFiltradas().map((maquina) => maquina.id));
  const cuantas = preparadas.length;
  return montar(() =>
    pantallaDeLaMaquinaria({
      textos: textosDeLaMaquinaria(),
      // El singular y el plural con las dos formas del servidor: «Tienes 1 máquinas» es lo primero que hace
      // desconfiar de un programa.
      cuantas: cuantas ? conCuenta(m, "cuantas", cuantas) : "",
      filtro: suyo.filtro,
      tabla: tablaDeLaMaquinaria(),
      maquinas: preparadas.filter((maquina) => casan.has(maquina.id)),
      equipos: (suyo.equipos || []).map((equipo) => ({
        id: equipo.id,
        nombre: equipo.nombre,
        detalle: [
          equipo.tipo,
          equipo.numero_roma,
          equipo.fecha_proxima_iteaf ? formateaFecha(equipo.fecha_proxima_iteaf) : "",
        ]
          .filter(Boolean)
          .join(" · "),
      })),
      queFalta: suyo.queFalta || [],
      formulario: elFormularioDeLaMaquinaria(suyo.formulario),
      guardando: suyo.guardando,
      error: suyo.error || "",
      aviso: suyo.aviso || "",
    }),
  );
}

/**
 * Abre la ficha de una máquina.
 *
 * Se pide **a su puerta** (`GET /api/maquinaria/<id>`) y con los tres finales de siempre: se abre, «eso no
 * está en tu cuaderno» (404, que es lo que contesta el servidor también cuando la máquina es de otra
 * finca, para no contar si existe) o, sin cobertura, «no lo he podido comprobar».
 */
/** Abre la ficha de una máquina. */
async function abrirUnaMaquina(id) {
  const suyo = estadoDeLaMaquinaria();
  if (!id) return pantallaMaquinaria();
  suyo.error = "";
  suyo.aviso = "";
  suyo.formulario = null;
  suyo.borrador = null;
  suyo.anulando = null;
  let respuesta = null;
  try {
    respuesta = await api(`/api/maquinaria/${id}`);
  } catch (fallo) {
    respuesta = null;
  }
  if (!respuesta) {
    if (!navigator.onLine) return pantallaDeUnaDireccionQueNoSePuedeComprobar();
    avisarDelError(mensaje("no_se_pudo"));
    return;
  }
  if (respuesta.status === 404) return pantallaDeDireccionQueNoLlevaANingunaParte();
  if (!respuesta.ok) {
    avisarDelError(mensaje("no_se_pudo"));
    return;
  }
  suyo.maquinaCruda = await respuesta.json();
  suyo.maquina = unaMaquinaPreparada(suyo.maquinaCruda);
  // Y los avisos de todas las máquinas, que son los mismos que enseña la lista: se piden aquí para que la
  // ficha y la lista no puedan decir cosas distintas de la misma máquina.
  await recargarLaMaquinaria();
  pantallaUnaMaquina();
}

/** La ficha de una máquina, ya en React. */
function pantallaUnaMaquina() {
  const suyo = estadoDeLaMaquinaria();
  const ficha = suyo.maquina || {};
  return montar(() =>
    pantallaDeUnaMaquina({
      textos: textosDeLaMaquinaria(),
      maquina: ficha.maquina || null,
      avisos: ficha.avisos || [],
      obligaciones: ficha.obligaciones || [],
      inspecciones: ficha.inspecciones || [],
      averias: ficha.averias || [],
      formulario: elFormularioDeLaMaquinaria(suyo.formulario),
      anulando: suyo.anulando,
      guardando: suyo.guardando,
      error: suyo.error || "",
      aviso: suyo.aviso || "",
    }),
  );
}

/** Vuelve a pedir la ficha abierta, después de guardar algo en ella. */
async function recargarLaFichaDeLaMaquina() {
  const suyo = estadoDeLaMaquinaria();
  const id = (suyo.maquina || {}).maquina ? suyo.maquina.maquina.id : null;
  if (!id) return;
  try {
    suyo.maquinaCruda = await apiJson(`/api/maquinaria/${id}`);
    suyo.maquina = unaMaquinaPreparada(suyo.maquinaCruda);
  } catch (fallo) {
    suyo.error = mensajeDeFallo(fallo);
  }
}

/**
 * El formulario de una máquina (nueva o corregida).
 *
 * **El borrador de las opciones vive en `estado.maquinaria.borrador`**, no en el DOM: al elegir una opción
 * se repinta la pantalla, y lo que solo estuviera en una casilla se perdería (la trampa que ya costó una
 * ronda con el fichero del cuaderno de la Junta). Lo que se escribe con el teclado sí vive en su casilla,
 * con su `id`, que es lo único que `app.js` tiene para leerlo.
 */
function formularioDeLaMaquina({ corrigiendo = false } = {}) {
  const m = t("maquinaria", {});
  const suyo = estadoDeLaMaquinaria();
  const b = suyo.borrador || {};
  const maquina = (suyo.maquina || {}).maquina || {};
  const clasificacion = document.getElementById("maquina-clasificacion");
  const elegido = (clave) => (b[clave] !== undefined && b[clave] !== "" ? b[clave] : maquina[clave] || "");
  const escrito = (id, enLaFicha) =>
    loEscrito(id, corrigiendo ? String(maquina[enLaFicha] ?? "") : "");
  return {
    clase: "maquina",
    corrigiendo,
    titulo: corrigiendo ? m.form_corregir_titulo : m.form_nueva_titulo,
    pista: corrigiendo ? m.form_corregir_pista : m.form_nueva_pista,
    guardar: corrigiendo ? accion("guardar") : m.guardar,
    cancelar: t("corregir.volver_sin_guardar", ""),
    guardando: m.form_guardando,
    bloques: [
      {
        tipo: "texto",
        id: "maquina-nombre",
        etiqueta: m.nombre,
        pista: m.nombre_pista,
        valor: escrito("maquina-nombre", "nombre"),
      },
      {
        tipo: "opciones",
        campo: "clase",
        etiqueta: m.clase,
        pista: m.clase_pista,
        elegido: elegido("clase"),
        opciones: opcionesDeLaLista("clases_de_maquina", elegido("clase")),
      },
      {
        tipo: "opciones",
        campo: "propiedad",
        etiqueta: m.propiedad,
        elegido: elegido("propiedad"),
        opciones: opcionesDeLaLista("propiedades_de_una_maquina", elegido("propiedad")),
      },
      {
        tipo: "opciones",
        campo: "disponibilidad",
        etiqueta: m.disponibilidad,
        pista: m.disponibilidad_pista,
        elegido: elegido("disponibilidad"),
        opciones: opcionesDeLaLista("disponibilidades_de_una_maquina", elegido("disponibilidad")),
      },
      {
        tipo: "texto",
        id: "maquina-clasificacion",
        etiqueta: m.clasificacion,
        pista: m.clasificacion_pista,
        valor: escrito("maquina-clasificacion", "clasificacion"),
      },
      { tipo: "texto", id: "maquina-marca", etiqueta: m.marca, valor: escrito("maquina-marca", "marca") },
      { tipo: "texto", id: "maquina-modelo", etiqueta: m.modelo, valor: escrito("maquina-modelo", "modelo") },
      // **El número en crudo, no su texto ya montado**: en el campo de las horas no puede ir «2.400 h», que
      // es lo que se lee en la ficha. Si fuera eso, al corregir la máquina el número se perdería (no se
      // puede volver a leer) y las horas se quedarían en blanco sin que nadie lo dijera.
      { tipo: "numero", id: "maquina-anio", etiqueta: m.anio, valor: escrito("maquina-anio", "anio_numero") },
      {
        tipo: "texto",
        id: "maquina-matricula",
        etiqueta: m.matricula,
        pista: m.matricula_pista,
        valor: escrito("maquina-matricula", "matricula"),
      },
      {
        tipo: "texto",
        id: "maquina-numero-serie",
        etiqueta: m.numero_serie,
        pista: m.numero_serie_pista,
        valor: escrito("maquina-numero-serie", "numero_serie"),
      },
      {
        tipo: "texto",
        id: "maquina-numero-roma",
        etiqueta: m.numero_roma,
        pista: m.numero_roma_pista,
        valor: escrito("maquina-numero-roma", "numero_roma"),
      },
      {
        tipo: "numero",
        id: "maquina-horas",
        etiqueta: m.horas,
        pista: m.horas_pista,
        valor: escrito("maquina-horas", "horas_numero"),
      },
      {
        tipo: "opciones",
        campo: "equipo_aplicacion_id",
        etiqueta: m.es_el_equipo_del_cuaderno,
        pista: m.es_el_equipo_del_cuaderno_pista,
        elegido:
          b.equipo_aplicacion_id !== undefined
            ? b.equipo_aplicacion_id
            : maquina.equipo_aplicacion_id
              ? String(maquina.equipo_aplicacion_id)
              : "",
        opciones: [
          // **El equipo que ya estaba enlazado se enseña**, aunque ya no salga en la lista de «equipos sin
          // ficha» (porque ya está enlazado): sin él, el agricultor no vería cuál tenía y al guardar sin
          // tocar nada se quedaría sin enlace.
          ...(maquina.equipo_aplicacion_id
            ? [
                {
                  valor: String(maquina.equipo_aplicacion_id),
                  texto: m.el_equipo_que_ya_estaba,
                  elegido: true,
                },
              ]
            : []),
          ...equiposParaElegir(),
          { valor: "", texto: m.ningun_equipo },
        ],
      },
      {
        tipo: "area",
        id: "maquina-notas",
        etiqueta: m.campo_notas,
        pista: m.notas_pista,
        valor: escrito("maquina-notas", "notas"),
        filas: 3,
      },
    ],
  };
}

/** Los papeles guardados, para poder elegir cuál demuestra una inspección.
 *
 * **`estado.documentos` es la respuesta entera de `GET /api/documentos`, no la lista**: es un objeto
 * con `textos`, `carpetas`, `sugeridas` y, dentro, `documentos`. Aquí se hacía `.map` sobre el objeto,
 * así que la función **reventaba** (`TypeError: … .map is not a function`) y con ella el formulario de
 * apuntar una inspección: el agricultor pulsaba el botón y no pasaba nada. Lo encontró la revisión
 * independiente del T14 (03/10/2026) ejecutando la función de verdad. La lista está en
 * `.documentos`, como en el resto de la aplicación (`app.js:5678`, `:8629`).
 */
function papelesParaElegir() {
  return ((estado.documentos || {}).documentos || []).map((papel) => ({
    valor: String(papel.id),
    texto: papel.titulo || "",
    elegido: false,
  }));
}

/** Los equipos que están en el cuaderno y todavía no en la lista, para poder enlazarlos. */
function equiposParaElegir() {
  return (estadoDeLaMaquinaria().equipos || []).map((equipo) => ({
    valor: String(equipo.id),
    texto: equipo.nombre,
    elegido: false,
  }));
}

/** El formulario de una inspección, con sus campos y el tipo ya puesto. */
function formularioDeUnaInspeccion({ tipo = "iteaf", corrigiendo = null } = {}) {
  const m = t("maquinaria", {});
  const b = estadoDeLaMaquinaria().borrador || {};
  const puestos = corrigiendo || b;
  const papeles = papelesParaElegir();
  const mirando = () =>
    document.getElementById("inspeccion-fecha")
      ? document.getElementById("inspeccion-fecha").value
      : "";
  return {
    clase: "inspeccion",
    corrigiendo,
    titulo: m.form_inspeccion_titulo,
    pista: m.form_inspeccion_pista,
    guardar: m.apuntar_inspeccion,
    cancelar: t("corregir.volver_sin_guardar", ""),
    guardando: m.form_guardando,
    datos: { id: corrigiendo ? corrigiendo.id : "" },
    bloques: [
      {
        tipo: "opciones",
        campo: "tipo",
        etiqueta: m.campo_tipo_inspeccion,
        elegido: puestos.tipo || tipo,
        opciones: opcionesDeLaLista("obligaciones_de_una_maquina", puestos.tipo || tipo),
      },
      {
        tipo: "fecha",
        id: "inspeccion-fecha",
        etiqueta: m.campo_fecha,
        pista: m.campo_fecha_pista,
        valor: puestos.fecha || mirando() || hoyISO(),
      },
      {
        tipo: "opciones",
        campo: "resultado",
        etiqueta: m.resultado,
        elegido: puestos.resultado || "no_consta",
        opciones: opcionesDeLaLista("resultados_de_una_inspeccion", puestos.resultado || "no_consta"),
      },
      {
        tipo: "fecha",
        id: "inspeccion-proxima",
        etiqueta: m.campo_proxima_fecha,
        pista: m.campo_proxima_fecha_pista,
        valor: puestos.proxima_fecha || "",
      },
      {
        tipo: "opciones",
        campo: "documento_id",
        etiqueta: m.campo_documento,
        pista: papeles.length ? m.campo_documento_pista : m.sin_papeles_guardados,
        elegido: puestos.documento_id || "",
        opciones: [...papeles, { valor: "", texto: m.sin_papel }],
      },
      {
        tipo: "area",
        id: "inspeccion-notas",
        etiqueta: m.campo_notas,
        valor: puestos.notas || "",
        filas: 2,
      },
    ],
  };
}

/** El formulario de una avería. */
function formularioDeUnaAveria({ corrigiendo = null } = {}) {
  const m = t("maquinaria", {});
  const b = estadoDeLaMaquinaria().borrador || {};
  const puestos = corrigiendo || b;
  const resuelta = puestos.resuelta === true ? "true" : puestos.resuelta === false ? "false" : "";
  // Lo escrito se lee **de la pantalla antes de repintar** donde lo haya, y si no, del borrador o de lo
  // apuntado: es lo que impide que elegir «ya está arreglada» borre lo que se había escrito en «qué pasó».
  const puesto = (id, enElBorrador) => loEscrito(id, puestos[enElBorrador] || "");
  return {
    clase: "averia",
    corrigiendo,
    titulo: m.form_averia_titulo,
    pista: m.form_averia_pista,
    guardar: m.apuntar_averia,
    cancelar: t("corregir.volver_sin_guardar", ""),
    guardando: m.form_guardando,
    datos: { id: corrigiendo ? corrigiendo.id : "" },
    bloques: [
      {
        tipo: "fecha",
        id: "averia-fecha",
        etiqueta: m.campo_fecha_averia,
        valor: puesto("averia-fecha", "fecha") || hoyISO(),
      },
      {
        tipo: "area",
        id: "averia-que",
        etiqueta: m.campo_que_paso,
        pista: m.que_paso_pista,
        valor: puesto("averia-que", "que_paso"),
        filas: 2,
      },
      {
        tipo: "opciones",
        campo: "resuelta",
        etiqueta: m.resuelta,
        elegido: resuelta,
        opciones: [
          { valor: "true", texto: m.resuelta_si, elegido: resuelta === "true" },
          { valor: "false", texto: m.resuelta_no, elegido: resuelta === "false" },
          { valor: "", texto: m.resuelta_no_se, elegido: !resuelta },
        ],
      },
      {
        tipo: "fecha",
        id: "averia-fecha-resuelta",
        etiqueta: m.fecha_resuelta,
        valor: puesto("averia-fecha-resuelta", "fecha_resuelta"),
      },
      {
        tipo: "numero",
        id: "averia-horas",
        etiqueta: m.horas_de_la_averia,
        valor: puesto("averia-horas", "horas"),
      },
      {
        tipo: "area",
        id: "averia-notas",
        etiqueta: m.campo_notas,
        valor: puesto("averia-notas", "notas"),
        filas: 2,
      },
    ],
  };
}

/** El valor de una casilla del formulario, por su `id`. */
function valorDeLaCasilla(id) {
  const casilla = document.getElementById(id);
  return casilla ? String(casilla.value || "").trim() : "";
}

/**
 * Lo que hay escrito en una casilla, si esa casilla está en la pantalla.
 *
 * **Existe por la trampa que ya costó una ronda en este programa**: pintar la pantalla **borra la casilla**.
 * Al elegir una opción se repinta el formulario entero, y lo que solo viviera en un `<input>` se pierde: el
 * agricultor escribe la matrícula, toca «Es mía» y la matrícula desaparece. Por eso, al volver a preparar el
 * formulario, se mira **primero lo que hay escrito** y después lo que venía del cuaderno.
 */
function loEscrito(id, porDefecto = "") {
  const casilla = document.getElementById(id);
  if (!casilla) return porDefecto;
  const valor = String(casilla.value || "");
  return valor === "" ? porDefecto : valor;
}

/**
 * **El aviso al planificar un trabajo**: lo que hay que saber de la máquina que es ese equipo.
 *
 * El contrato lo pide con estas palabras («Avisos al planificar trabajo: que la máquina no esté disponible,
 * o que tenga una inspección vencida o a punto»), y el sitio donde de verdad hace falta es **donde se elige
 * con qué se hace el trabajo**: de nada sirve decirlo en la ficha de la máquina si el agricultor ya ha
 * enganchado el remolque. Por eso este aviso se enseña en el paso del asistente en el que se elige la
 * máquina, pegado a su nombre.
 *
 * **Se pasa de un equipo a su máquina por el enlace** (`equipo_aplicacion_id`), que es lo que permite que la
 * hoja 1.3 del cuaderno y la lista de maquinaria hablen de la misma máquina. Un equipo que no está enlazado
 * con ninguna máquina no tiene avisos de esta parte: los suyos siguen siendo la fecha de la ITEAF que ya se
 * enseñaba, y decir otra cosa sería inventarse una máquina.
 */
function avisoDeLaMaquinaDeUnEquipo(equipoId) {
  const suyos = (estado.maquinariaAvisos || []).filter(
    (aviso) => aviso.equipo_aplicacion_id !== null && Number(aviso.equipo_aplicacion_id) === Number(equipoId),
  );
  if (!suyos.length) return "";
  // **Uno solo, y el más urgente primero**: en una lista de máquinas para elegir, tres renglones de avisos
  // por botón no se leen. Lo demás está en su ficha, que es donde hay sitio para explicarlo.
  const suyo = suyos.find((aviso) => aviso.urgente) || suyos[0];
  return suyo.mensaje || "";
}

/** Recoge lo que el agricultor ha escrito en el formulario de una máquina. */
function recogeLaMaquina() {
  const suyo = estadoDeLaMaquinaria();
  const b = suyo.borrador || {};
  // **Si una pregunta no se ha tocado, se manda lo que ya había.** Al **corregir**, el borrador nace
  // vacío (`maquina-corregir` lo pone en `{}`), así que la clase, la propiedad y la disponibilidad salían
  // como `""` y el servidor contestaba 422 —««» no es una de las clases de máquina que se pueden
  // elegir»—: **corregir una máquina no se guardaba nunca**. Lo encontró la revisión independiente del
  // T14 (03/10/2026) ejecutando esta función de verdad. Al **dar de alta** una máquina nueva esto sigue
  // siendo `""` a propósito: las tres se preguntan y no nacen contestadas, que es lo que evita dar por
  // bueno lo que nadie ha dicho.
  const loQueYaEstaba = (clave) => b[clave] || ((suyo.maquina || {}).maquina || {})[clave] || "";
  const numero = (id) => {
    const texto = valorDeLaCasilla(id);
    if (texto === "") return null;
    const valor = Number(texto.replace(",", "."));
    return Number.isFinite(valor) ? valor : null;
  };
  const texto = (id) => valorDeLaCasilla(id) || null;
  return {
    nombre: valorDeLaCasilla("maquina-nombre"),
    clase: loQueYaEstaba("clase"),
    clasificacion_tecnica: texto("maquina-clasificacion"),
    matricula: texto("maquina-matricula"),
    numero_serie: texto("maquina-numero-serie"),
    numero_roma: texto("maquina-numero-roma"),
    marca: texto("maquina-marca"),
    modelo: texto("maquina-modelo"),
    anio: numero("maquina-anio"),
    propiedad: loQueYaEstaba("propiedad"),
    horas: numero("maquina-horas"),
    disponibilidad: loQueYaEstaba("disponibilidad"),
    equipo_aplicacion_id:
      b.equipo_aplicacion_id === undefined
        ? // No se ha tocado esa pregunta: **se queda como estaba**. Si no, corregir el nombre de una
          // máquina le quitaría el enlace con el equipo del cuaderno sin decir nada.
          (estadoDeLaMaquinaria().maquina || {}).maquina?.equipo_aplicacion_id ?? null
        : b.equipo_aplicacion_id
          ? Number(b.equipo_aplicacion_id)
          : null,
    notas: texto("maquina-notas"),
  };
}

/**
 * Guarda lo que se está rellenando: la máquina, una inspección o una avería.
 *
 * Los tres pasan por `mandarCambio`, que es lo que usa el programa para escribir. Y el error se enseña con
 * la frase del servidor, que es la que dice qué hacer.
 */
async function guardarLoDeLaMaquinaria() {
  const suyo = estadoDeLaMaquinaria();
  const formulario = suyo.formulario || {};
  const maquina = (suyo.maquina || {}).maquina || {};
  // **La clave de reenvío de este apunte, pedida una sola vez.**
  // Es lo que impide que dos toques del mismo botón —o un reintento cuando vuelve la cobertura— apunten
  // dos veces lo mismo. Se pide **la primera vez que se guarda** y se queda en el borrador, con el mismo
  // motivo que está escrito en `claveDeReenvio`: si se pidiera al guardar, cada pulsación mandaría una
  // clave distinta y el servidor no podría reconocer el reenvío. Faltaba en los tres formularios de la
  // maquinaria (lo encontró la revisión independiente del T14, 05/10/2026).
  const b = suyo.borrador || ((suyo.borrador = {}), suyo.borrador);
  const laClaveDeReenvio = () =>
    b.clave_de_reenvio || (b.clave_de_reenvio = claveDeReenvio("maquinaria"));
  let ruta = "/api/maquinaria";
  let metodo = "POST";
  let datos = {};

  if (formulario.clase === "maquina") {
    datos = { ...recogeLaMaquina(), clave_de_reenvio: laClaveDeReenvio() };
    if (formulario.corrigiendo && maquina.id) {
      ruta = `/api/maquinaria/${maquina.id}`;
      metodo = "PUT";
    }
  } else if (formulario.clase === "inspeccion") {
    const id = formulario.corrigiendo ? formulario.corrigiendo.id : null;
    datos = {
      tipo: b.tipo || "iteaf",
      fecha: valorDeLaCasilla("inspeccion-fecha"),
      resultado: b.resultado || "no_consta",
      proxima_fecha: valorDeLaCasilla("inspeccion-proxima") || null,
      documento_id: b.documento_id ? Number(b.documento_id) : null,
      notas: valorDeLaCasilla("inspeccion-notas") || null,
      clave_de_reenvio: laClaveDeReenvio(),
    };
    ruta = id
      ? `/api/maquinaria/${maquina.id}/inspecciones/${id}`
      : `/api/maquinaria/${maquina.id}/inspecciones`;
    metodo = id ? "PUT" : "POST";
  } else if (formulario.clase === "averia") {
    const id = formulario.corrigiendo ? formulario.corrigiendo.id : null;
    const dicho = (suyo.borrador || {}).resuelta;
    const horas = valorDeLaCasilla("averia-horas");
    datos = {
      fecha: valorDeLaCasilla("averia-fecha"),
      que_paso: valorDeLaCasilla("averia-que"),
      // **Tres respuestas, y la de «no lo sé» se manda como tal**: no se puede guardar sin contestar, que
      // es lo que impide dar por arreglada una máquina que no lo está.
      resuelta: dicho === "true" ? true : dicho === "false" ? false : null,
      fecha_resuelta: valorDeLaCasilla("averia-fecha-resuelta") || null,
      horas: horas ? Number(horas.replace(",", ".")) : null,
      notas: valorDeLaCasilla("averia-notas") || null,
      clave_de_reenvio: laClaveDeReenvio(),
    };
    ruta = id
      ? `/api/maquinaria/${maquina.id}/averias/${id}`
      : `/api/maquinaria/${maquina.id}/averias`;
    metodo = id ? "PUT" : "POST";
  }

  suyo.guardando = true;
  suyo.error = "";
  const resultado = await mandarCambio(ruta, metodo, datos);
  suyo.guardando = false;
  if (resultado.error) {
    suyo.error = resultado.error;
    return formulario.clase === "maquina" && !maquina.id ? pantallaMaquinaria() : pantallaUnaMaquina();
  }
  const eraNuevaMaquina = formulario.clase === "maquina" && !formulario.corrigiendo;
  suyo.formulario = null;
  suyo.borrador = null;
  suyo.aviso = eraNuevaMaquina ? t("maquinaria.guardado", "") : t("maquinaria.corregida", "");
  await recargarLaMaquinaria();
  if (eraNuevaMaquina) {
    // Al apuntar una máquina nueva se abre su ficha: es donde están las cinco obligaciones que hay que
    // contestar, y dejarla en la lista sin decirlo sería mandar al agricultor a buscarlo por su cuenta.
    await abrirUnaMaquina((resultado.datos || {}).id);
    return;
  }
  await recargarLaFichaDeLaMaquina();
  pantallaUnaMaquina();
}

// -------------------------------------------------------------------- eventos

document.addEventListener("click", async (evento) => {  const elemento = evento.target.closest("[data-accion]");
  if (!elemento) return;
  const nombre = elemento.dataset.accion;

  // **Al pulsar cualquier cosa del menú abierto, el menú se cierra** (07/10/2026). Lo encontró la
  // comprobación del armazón: al abrir «Mis cuentas» desde el panel, la pantalla se abría **detrás** del
  // panel y el agricultor no veía nada hasta cerrarlo a mano. Cerrar al navegar es lo que hace cualquier
  // menú, y así vale para los 21 renglones sin tener que acordarse en cada uno.
  if (estado.menuAbierto && elemento.closest("#marco .menu")) {
    estado.menuAbierto = false;
    estado.marcoPintado = "";
  }

  if (nombre === "ir-inicio") return irAInicio(null);
  if (nombre === "inicio") return irAInicio(elemento.dataset.ir);
  if (nombre === "trabajo") return abrirAsistente(elemento.dataset.tipo, pasosLabor(elemento.dataset.tipo));
  if (nombre === "anadir-maestro") {
    const tipo = elemento.dataset.tipo;
    // Al dar de alta una parcela se ofrece primero traerla del SIGPAC: es lo que ahorra
    // teclear ocho datos por cada una, y con cuarenta parcelas es la diferencia entre empezar
    // y abandonar. Se puede elegir no usarlo (`sigpac-no`), y entonces se pregunta a mano.
    if (tipo === "parcela" && (t("sigpac.traer", "") || "") !== "") {
      return pantallaTraerOApuntar();
    }
    return abrirAsistente(tipo, pasosDeMaestro(tipo));
  }
  if (nombre === "sigpac-si") return abrirAsistente("parcela-sigpac", pasosDeSigpac());
  if (nombre === "sigpac-no") return abrirAsistente("parcela", pasosDeMaestro("parcela"));
  // El mapa: elegir la tierra tocándola. Lo que hace el trabajo son los botones de mover y el
  // grande del centro; el toque directo en la imagen es un atajo para quien apunta bien.
  if (nombre === "mapa-abrir") return abrirElMapa();
  // El cuaderno de la Junta: leer el fichero que descarga el agricultor y traer sus tierras.
  if (nombre === "cuaderno-abrir") {
    estado.cuadernoCyl = null;
    return pantallaCuadernoDeLaJunta();
  }
  if (nombre === "cuaderno-volver") {
    estado.cuadernoCyl = null;
    return pantallaTraerOApuntar();
  }
  if (nombre === "cuaderno-leer") return leerElCuadernoDeLaJunta();
  if (nombre === "cuaderno-traer") return traerLasTierrasDelCuaderno();
  // Las facturas: subir una, leerla y confirmarla. La lectura **no** guarda nada: para eso está el
  // botón grande de la pantalla de la interpretación.
  if (nombre === "facturas-abrir") {
    estado.facturas = null;
    return pantallaFacturas();
  }
  if (nombre === "factura-nueva") {
    const facturas = estadoDeLasFacturas();
    facturas.interpretacion = null;
    facturas.fichero = null;
    facturas.error = "";
    // **Y se deja de corregir** (ronda 93): sin esto, entrar en «AÑADIR UNA FACTURA» después de haber
    // empezado a corregir una dejaría la factura en corrección puesta, y la factura nueva que se
    // escribiera se guardaría **encima de la que se estaba corrigiendo**. Es el mismo cuidado que con
    // `documentoEnEdicion` al abrir un papel en blanco.
    facturas.corrigiendo = null;
    return pantallaNuevaFactura();
  }
  if (nombre === "factura-leer") return leerFactura();
  if (nombre === "factura-mano") return facturaAMano();
  if (nombre === "factura-guardar") return guardarFactura();
  // El papel de una factura que ya está apuntada (ronda 90): verlo o subirlo. Los dos caminos estaban en
  // el servidor y ninguna pantalla los pedía, así que una factura escrita a mano se quedaba sin papel.
  if (nombre === "factura-papel-ver") return verElPapelDeLaFactura(Number(elemento.dataset.id));
  if (nombre === "factura-papel-subir") return subirElPapelDeLaFactura(Number(elemento.dataset.id));
  // El cuaderno de la Junta: sacarlo relleno con lo que hay apuntado.
  if (nombre === "cuaderno-sacar") return sacarElCuadernoDeLaJunta();
  if (nombre === "cuaderno-de-la-junta-abrir") return pantallaCuadernoDeLaJunta();
  // Mis datos: la portada del cuaderno de la Junta.
  if (nombre === "mis-datos-abrir") {
    estado.errorMisDatos = "";
    estado.misDatosGuardados = false;
    return pantallaMisDatos();
  }
  if (nombre === "mis-datos-guardar") return guardarMisDatos();
  // Los años del cuaderno (ronda 93): verlos, corregirlos, borrarlos y empezar uno nuevo. El alta y la
  // corrección van por el asistente (`campana-nueva` y `cosa-corregir`), como los maestros.
  if (nombre === "campanas-abrir") {
    estado.errorCampanas = "";
    return pantallaCampanas();
  }
  if (nombre === "campana-nueva") {
    abrirAsistente("campana", pasosDeMaestro("campana"));
    estado.asistente.borrador = borradorDeUnaCampanaNueva();
    // El año nuevo no se «apunta»: se **empieza**, y el título lo dice para que no parezca que se está
    // corrigiendo algo. Se pone con los títulos forzados, que es como el asistente admite un texto propio
    // de la pantalla de la que viene (lo mismo que hace el atajo de repetir).
    estado.asistente.tituloForzado = t("campanas.anadir", "");
    estado.asistente.pistaForzada = t("campanas.pista_anadir", "");
    return pintarAsistente();
  }
  // Quién entra en la finca y en qué finca se está trabajando (ronda 89). Las dos cosas son la misma
  // pregunta —quién apunta en este cuaderno y en cuál— y por eso viven en la misma pantalla.
  if (nombre === "quien-entra-abrir") return abrirQuienEntra();
  if (nombre === "finca-anadir") return anadirCuentaALaFinca();
  if (nombre === "finca-quitar") return quitarCuentaDeLaFinca(Number(elemento.dataset.persona));
  if (nombre === "finca-entrar") return entrarEnLaFinca(Number(elemento.dataset.id));
  // El mismo cambio de finca, desde la barra de arriba (T04): la barra usa `data-valor` como todos los
  // botones de elegir, y este es el único sitio donde se cambia de finca de verdad.
  if (nombre === "cambiar-finca") {
    return entrarEnLaFinca(Number(elemento.dataset.valor));
  }
  // **Cambiar de campaña no existe todavía**, y por eso este botón no cambia nada: lleva a la pantalla de
  // los años, que es donde de verdad se puede hacer algo con ellos (empezar un año nuevo, corregirlo,
  // borrarlo). El servidor no tiene ninguna forma de decir «trabaja en el año 2023»
  // (`/api/campanas/actual` devuelve siempre la más nueva), así que un botón que dijera «cambiar de
  // campaña» y no cambiara nada sería el peor de los dos mundos.
  if (nombre === "cambiar-campana") return pantallaCampanas();
  // Volver a intentar abrir la dirección cuando no se pudo comprobar por falta de cobertura (T04).
  if (nombre === "reintentar-direccion") return reintentarLaDireccion();
  // ---------------------------------------------------------------------------------------------
  // Las tierras en el mapa y en la tabla, y lo que ha sido una tierra (T06, 03/10/2026)
  //
  // Veinte acciones, todas con nombre literal (ninguna por variable): así el guardián de
  // `tests/test_los_botones_hacen_algo.py` puede comprobar una por una que el manejador las atiende.
  // Los filtros y las capas llevan su campo y su valor en `data-campo` / `data-valor` / `data-capa`.
  // ---------------------------------------------------------------------------------------------
  if (nombre === "t06-volver") return irAInicio("mis_cosas");
  if (nombre === "t06-filtrar") {
    return filtrarLasTierrasDeLaVista(elemento.dataset.campo, elemento.dataset.valor);
  }
  if (nombre === "t06-buscar") return buscarEnLasTierras();
  if (nombre === "t06-quitar-filtros") return quitarLosFiltrosDeLasTierras();
  if (nombre === "t06-agrupar") return agruparLasTierrasDeLaVista(elemento.dataset.valor);
  // **El enlace entre las dos vistas.** El nombre de una fila y cada trozo del mapa llevan la misma
  // acción y el mismo `data-id`: tocar cualquiera de los dos enfoca la tierra, y con ella su fila y su
  // trozo. Es la mitad del contrato («al seleccionar un polígono se enfoca la fila y viceversa»).
  if (nombre === "t06-elegir-fila") return elegirUnaTierra(elemento.dataset.id);
  if (nombre === "t06-marcar") return marcarUnaTierra(elemento.dataset.id);
  if (nombre === "t06-marcar-todas") return marcarTodasLasQueSeVen();
  if (nombre === "t06-desmarcar-todas") return desmarcarTodasLasTierras();
  if (nombre === "t06-capa") return cambiarLaCapaDelMapa(elemento.dataset.valor);
  if (nombre === "t06-ver-mis-tierras") return verOLosLinderosDeMisTierras();
  if (nombre === "t06-encajar") return encajarTodaLaFinca();
  if (nombre === "t06-acercar") return acercarOAlejarElMapa(0.5);
  if (nombre === "t06-alejar") return acercarOAlejarElMapa(2);
  if (nombre === "t06-versiones") return abrirLasVersionesDeUnaTierra(Number(elemento.dataset.id));
  if (nombre === "t06-abrir-en-el-mapa") {
    // Se abre el mapa de las tierras con esa tierra enfocada: es el otro sentido del enlace entre la
    // ficha y el mapa, y lo que hace que desde las versiones se pueda ver dónde está el trozo.
    elEstadoDeT06().elegida = Number(elemento.dataset.id);
    return abrirLasTierrasDelMapa().then(() => elegirUnaTierra(elemento.dataset.id));
  }
  if (nombre === "t06-comparar-antes") return elegirUnAnioParaComparar("antes", elemento.dataset.valor);
  if (nombre === "t06-comparar-despues") return elegirUnAnioParaComparar("despues", elemento.dataset.valor);
  if (nombre === "t06-comparar") return compararDosAniosDeLaTierra();
  // **Ensayar no escribe.** Este camino manda el lote a la ruta que solo lee.
  if (nombre === "t06-ensayar") {
    return ensayarTraerLoDeOtroAnio(elemento.dataset.fuente, elemento.dataset.campana);
  }
  // Y **este es el único sitio de la aplicación que manda algo a `/api/versiones/aplicar`**.
  if (nombre === "t06-apuntar-lote") return apuntarElLoteEnsayado();
  if (nombre === "mapa-volver") {
    estado.mapa = null;
    return pantallaTraerOApuntar();
  }
  if (nombre === "mapa-acercar") {
    const centro = elCentroDelMapa();
    centrarElMapa(centro.lon, centro.lat, estadoDelMapa().lado / 2);
    return pantallaMapa();
  }
  if (nombre === "mapa-alejar") {
    const centro = elCentroDelMapa();
    centrarElMapa(centro.lon, centro.lat, estadoDelMapa().lado * 2);
    return pantallaMapa();
  }
  if (nombre === "mapa-preguntar") {
    const centro = elCentroDelMapa();
    const pixel = aPixeles(centro.lon, centro.lat);
    return preguntarPorUnPunto(pixel.x, pixel.y);
  }
  if (nombre === "mapa-tocar") return preguntarPorUnPunto(evento.offsetX || 0, evento.offsetY || 0);
  if (nombre === "mapa-estoy-aqui") return irAEstoyAqui();
  if (nombre === "mapa-apuntar") return apuntarLaParcelaDelMapa();
  if (nombre === "mapa-no-es-esa") {
    const mapa = estadoDelMapa();
    mapa.elegido = null;
    mapa.error = null;
    return pantallaMapa();
  }
  // Elegir el pueblo de la lista oficial y buscar los trozos: las dos cosas que hacen que no haya
  // que saberse ningún código.
  if (nombre === "buscar-pueblo") return buscarElPueblo();
  if (nombre === "elegir-pueblo") {
    const b = recogeElSigpac();
    b.municipio = elemento.dataset.nombre;
    b.provincia = elemento.dataset.provincia;
    b.pueblos = [];
    estado.asistente.error = null;
    return pintarAsistente();
  }
  if (nombre === "buscar-trozos") return buscarLosTrozos();
  // El buscador de tierras del asistente (ronda 82): se lee lo escrito **por el `id` del campo**, que es
  // como se lee todo en esta aplicación, y se vuelve a pintar el paso con la lista ya filtrada. La
  // limpieza es el mismo camino con el filtro vacío.
  if (nombre === "buscar-tierra") return buscarLaTierra();
  if (nombre === "buscar-tierra-limpiar") return buscarLaTierra(true);
  // Los mismos dos botones en «mis cosas», con su propio buscador y su propia lista (ronda 87).
  if (nombre === "buscar-tierra-mis-cosas") return buscarLaTierra(false, "mis-cosas");
  if (nombre === "buscar-tierra-limpiar-mis-cosas") return buscarLaTierra(true, "mis-cosas");
  if (nombre === "marcar-trozo") return marcarElTrozo(elemento.dataset.referencia);
  if (nombre === "traer-marcados") return traerLosMarcados();
  if (nombre === "parcela-traida-seguir") return irAInicio("mis_cosas");
  if (nombre === "mis-cosas") return pantallaMisCosas();
  if (nombre === "papel-ver-todos") return pantallaDocumentos();
  // **La búsqueda global** (07/10/2026): el botón pregunta al servidor por lo que se ha escrito en el
  // cuadro y pinta los grupos. El manejador existe **a la vez que el botón**, y no antes: un botón que se
  // pinta y no hace nada es justo lo que el guardián de los botones persigue, y lo cazó.
  if (nombre === "buscar") return pantallaBuscar();
  if (nombre === "papel-nuevo") {
    // Guardar un papel **nuevo**: se olvida el que se estuviera corrigiendo (ronda 93). Sin esto, después
    // de corregir un papel y volver a la lista, el botón de guardar otro papel habría estado corrigiendo
    // el anterior con los campos vacíos. Es la misma trampa que `abrirAsistente()` limpia con `corregir`.
    estado.documentoEnEdicion = null;
    estado.errorDocumentos = "";
    return pantallaNuevoDocumento();
  }
  // Las carpetas que ya tiene, para tocarlas en vez de escribirlas (ronda 90, diseño de Stitch): el nombre
  // se escribe en el campo, que es lo que lee `guardarDocumento()` por su `id`.
  if (nombre === "papel-carpeta") {
    const campo = document.getElementById("papel-carpeta");
    if (campo) campo.value = elemento.dataset.nombre || "";
    return;
  }
  if (nombre === "papel-guardar") return guardarDocumento();
  if (nombre === "papel-subir") return subirFicheroDeDocumento(elemento.dataset.id);
  if (nombre === "papel-ver") return descargarDocumento(elemento.dataset.id);
  if (nombre === "papel-listado") return verListadoDePapeles();
  if (nombre === "cesta-ver") return pantallaCesta();
  // --- El libro del almacén (T09) ---
  // Todo el almacén que no es la cesta: el albarán que llega, lo que queda envase por envase, el libro de
  // movimientos y las dos cosas que se enganchan desde él (una salida de un apunte y la factura de un
  // albarán ya apuntado). Están todos juntos a propósito: se llega a ellos desde el libro y desde el
  // apunte del cuaderno, y así se ve de un vistazo que el manejador los atiende todos.
  if (nombre === "libro-ver") return abrirElLibroDelAlmacen();
  // ---------------------------------------------------------------------------------------------
  // Las semillas, las etiquetas y las siembras (T10, 03/10/2026)
  //
  // Todas las acciones con nombre literal (ninguna por variable): así el guardián de
  // `tests/test_los_botones_hacen_algo.py` puede comprobar una por una que el manejador las atiende.
  // ---------------------------------------------------------------------------------------------
  if (nombre === "semillas-ver") return abrirLasSemillas();
  if (nombre === "semilla-nueva") return abrirLaSemillaNueva();
  if (nombre === "semilla-abrir") return abrirLaSemilla(Number(elemento.dataset.id));
  // **Leer la etiqueta no guarda nada**: devuelve una propuesta y rellena los campos para que el
  // agricultor la revise. Por eso este botón no manda la ficha al servidor.
  if (nombre === "semilla-leer-foto") return leerLaEtiquetaDeLaSemilla();
  if (nombre === "semilla-subir-foto") return subirLaFotoDeLaEtiqueta();
  if (nombre === "semilla-ver-foto") {
    const suyo = estadoDeLasSemillas();
    const id = Number(elemento.dataset.id) || (suyo.corrigiendo && suyo.corrigiendo.id);
    if (!id) return pantallaNuevaSemilla();
    return verLaFotoDeLaEtiqueta(id);
  }
  if (nombre === "semilla-guardar") return guardarLaSemilla();
  if (nombre === "siembras-ver") return abrirLasSiembras();
  if (nombre === "siembra-nueva") return abrirLaSiembraNueva(Number(elemento.dataset.id));
  if (nombre === "siembra-abrir") return abrirLaSiembra(Number(elemento.dataset.id));
  if (nombre === "siembra-guardar") return guardarLaSiembra();
  // La salida del almacén cuando lo que sale deja el envase en negativo: el agricultor dice que la
  // diferencia es de verdad y se apunta. Es el mismo camino que en «sacar de un envase» (T09).
  if (nombre === "siembra-aceptar-descuadre") {
    estadoDeLasSemillas().pedirDescuadre = true;
    return guardarLaSiembra();
  }
  if (nombre === "siembra-anular") return anularLaSiembra();
  // ---------------------------------------------------------------------------------------------
  // Las personas y las empresas (T11, 03/10/2026)
  //
  // Todas las acciones con nombre literal (ninguna por variable): así el guardián de
  // `tests/test_los_botones_hacen_algo.py` puede comprobar una por una que el manejador las atiende.
  // ---------------------------------------------------------------------------------------------
  if (nombre === "contactos-ver") return abrirLosContactos();
  if (nombre === "contactos-buscar") {
    const suyo = estadoDeLosContactos();
    const campo = document.getElementById("contacto-buscar");
    suyo.buscado = campo ? campo.value.trim() : "";
    suyo.cargando = true;
    pantallaContactos();
    await recargarLosContactos();
    suyo.cargando = false;
    return pantallaContactos();
  }
  if (nombre === "contactos-buscar-limpiar") {
    const suyo = estadoDeLosContactos();
    suyo.buscado = "";
    return abrirLosContactos();
  }
  if (nombre === "contacto-nuevo") {
    // Corregir y dar de alta son el mismo formulario: al dar de alta **se olvida el que se estuviera
    // corrigiendo**, o el botón de guardar cambiaría el que se acaba de dejar (la misma trampa que
    // `abrirAsistente()` limpia con `corregir`).
    estadoDeLosContactos().corrigiendo = null;
    return abrirLaFichaDeUnContacto(null);
  }
  if (nombre === "contacto-abrir") {
    return abrirLaFichaDeUnContacto(Number(elemento.dataset.id));
  }
  if (nombre === "contacto-guardar") return guardarElContacto();
  if (nombre === "contacto-borrar") {
    const suyo = estadoDeLosContactos();
    suyo.borrando = true;
    suyo.error = "";
    return pantallaFichaDeContacto();
  }
  if (nombre === "contacto-borrar-no") {
    const suyo = estadoDeLosContactos();
    suyo.borrando = false;
    return pantallaFichaDeContacto();
  }
  if (nombre === "contacto-borrar-si") {
    return borrarElContacto(Number(elemento.dataset.id));
  }
  if (nombre === "contacto-papel") {
    return marcarElPapel(elemento.dataset.papel, elemento.dataset.puesto === "1");
  }
  if (nombre === "contacto-enlazar-abrir") return abrirLosNombresEscritos();
  if (nombre === "contacto-enlazar") return enlazarUnEscrito(elemento);
  if (nombre === "contacto-desenlazar") {
    return desenlazarUnEscrito(Number(elemento.dataset.id));
  }
  if (nombre === "contacto-escritos-buscar") {
    const suyo = estadoDeLosContactos();
    const campo = document.getElementById("escrito-buscar");
    suyo.buscadoEscritos = campo ? campo.value.trim() : "";
    suyo.cargando = true;
    pantallaNombresEscritos();
    await recargarLosEscritosSinEnlazar();
    suyo.cargando = false;
    return pantallaNombresEscritos();
  }
  if (nombre === "contacto-escritos-buscar-limpiar") {
    estadoDeLosContactos().buscadoEscritos = "";
    return abrirLosNombresEscritos();
  }
  if (nombre === "contactos-revisar-abrir") return abrirLaRevisionDeLosContactos();
  if (nombre === "contacto-migracion-apuntar") {
    return apuntarLaPropuesta([elemento.dataset.clave]);
  }
  if (nombre === "contacto-migracion-todas") {
    const revisar = estadoDeLosContactos().revisar || { propuestas: [] };
    // **Solo las seguras**: la pantalla no pinta botón para las dudosas, y aquí tampoco se mandan.
    // El servidor, además, se negaría (409) aunque se le pidieran.
    const claves = (revisar.propuestas || [])
      .filter((propuesta) => propuesta.segura)
      .map((propuesta) => propuesta.clave);
    return apuntarLaPropuesta(claves);
  }
  if (nombre === "contacto-migracion-deshacer") return deshacerLaMigracion();
  if (nombre === "albaran-nuevo") return abrirElAlbaranNuevo();
  if (nombre === "albaran-guardar") return guardarElAlbaran();
  if (nombre === "albaran-linea-mas") {
    // Se recoge lo escrito **antes** de repintar: añadir una línea no puede borrar lo de las otras (es la
    // trampa de pintar sobre un formulario sin leerlo, la misma que el fichero del cuaderno de la Junta).
    const albaran = recogeElAlbaran();
    albaran.lineas.push(lineaDeAlbaranVacia());
    estadoDelLibro().error = "";
    return pantallaNuevoAlbaran();
  }
  if (nombre === "albaran-linea-menos") {
    const albaran = recogeElAlbaran();
    albaran.lineas.splice(Number(elemento.dataset.indice), 1);
    estadoDelLibro().error = "";
    return pantallaNuevoAlbaran();
  }
  if (nombre === "albaran-abrir") {
    estadoDelLibro().anulando = false;
    return abrirLaRecepcion(Number(elemento.dataset.id));
  }
  if (nombre === "albaran-anular") {
    const libro = estadoDelLibro();
    libro.anulando = true;
    libro.error = "";
    libro.aviso = "";
    return pantallaRecepcion();
  }
  if (nombre === "albaran-anular-si") return anularElAlbaran(Number(elemento.dataset.id));
  if (nombre === "movimiento-nuevo") {
    return abrirElMovimientoAMano(elemento.dataset.tipo, Number(elemento.dataset.articulo));
  }
  if (nombre === "movimiento-guardar") return guardarElMovimiento();
  if (nombre === "salida-de-un-lote") {
    return abrirLaSalidaDeUnLote(elemento.dataset.tipo, Number(elemento.dataset.id));
  }
  if (nombre === "salida-guardar") return guardarLaSalida(Number(elemento.dataset.lote));
  if (nombre === "salida-descuadre-si") {
    return guardarLaSalida(Number(elemento.dataset.lote), { aceptarDescuadre: true });
  }
  if (nombre === "factura-enganchar") return abrirElEngancheDeLaFactura(Number(elemento.dataset.id));
  if (nombre === "factura-proponer") return proponerLaFactura(Number(elemento.dataset.id));
  if (nombre === "factura-enganchar-si") {
    return engancharLaFacturaElegida(Number(elemento.dataset.id));
  }
  if (nombre === "cultivo-ver-todos") {
    estado.errorCultivos = "";
    return pantallaCultivos();
  }
  // **El filtro de las que faltan** (30/09/2026): enseña solo las tierras a las que les falta decir qué
  // tienen, que es lo que convierte el aviso «a 10 parcelas les falta…» en algo que se puede arreglar. Y
  // siempre hay salida: el mismo botón con el filtro quitado.
  if (nombre === "cultivo-solo-las-que-faltan") {
    estado.soloLasQueFaltan = true;
    return pantallaCultivos();
  }
  if (nombre === "cultivo-ver-todas") {
    estado.soloLasQueFaltan = false;
    return pantallaCultivos();
  }
  if (nombre === "cultivo-decir") return pantallaDecirCultivo(elemento.dataset.id);
  if (nombre === "cultivo-guardar") return guardarCultivo(elemento.dataset.id);
  // Quitar el cultivo de una tierra (ronda 93): primero se pregunta, y la pregunta lleva lo que va a
  // desaparecer. Es el camino que estaba en el servidor desde la ronda 92 y no pedía ninguna pantalla.
  if (nombre === "cultivo-quitar") return preguntarSiQuitarElCultivo(elemento.dataset.id);
  if (nombre === "cultivo-quitar-si") return quitarElCultivo(elemento.dataset.id);
  if (nombre === "grupo-ver") {
    estado.errorGrupos = "";
    return pantallaGrupos();
  }
  if (nombre === "grupo-calcular") return calcularGrupos();
  if (nombre === "dictado") {
    estado.dictadoTexto = "";
    estado.errorDictado = "";
    return pantallaDictado();
  }
  if (nombre === "dictado-hablar") return hablar();
  if (nombre === "dictado-entender") return entenderDictado();
  if (nombre === "borrador-apuntar") return abrirDesdeBorrador(true);
  if (nombre === "borrador-corregir") return abrirDesdeBorrador(false);
  if (nombre === "firmar-abrir") return pantallaFirmar();
  if (nombre === "firmar-descargar") return descargarFicheroAFirmar();
  if (nombre === "firmar-subir") return subirFirma();
  if (nombre === "plan-ver") return pantallaPlanes();
  if (nombre === "plan-hacer") return abrirAsistente("plan", pasosPlanAbonado());
  if (nombre === "analisis-ver") return pantallaAnaliticas();
  if (nombre === "analisis-nuevo") return abrirAsistente("analitica", pasosAnalitica());
  if (nombre === "analisis-informe-subir" || nombre === "analisis-informe-subir-ahora") {
    return subirInformeDeAnalisis(elemento.dataset.id, `informe-${elemento.dataset.id}`);
  }
  if (nombre === "analisis-informe-bajar") return descargarInformeDeAnalisis(elemento.dataset.id);
  if (nombre === "ventas-ver") return pantallaVentas();
  if (nombre === "ventas-nueva") return abrirAsistente("venta", pasosVenta());
  // **Buscar y filtrar lo que se ha vendido** (T12): las dos cosas las hace el servidor, porque el pie
  // tiene que ser la cuenta del conjunto filtrado y porque sumar dinero en el navegador lo sumaría en
  // coma flotante. Aquí solo se apunta lo que se ha pedido y se vuelve a preguntar.
  if (nombre === "ventas-buscar") {
    const campo = document.getElementById("buscar_venta");
    estado.filtroVentas = { ...estado.filtroVentas, q: campo ? String(campo.value || "").trim() : "" };
    return recargarLaTablaDeVentas();
  }
  if (nombre === "ventas-ver-todas") {
    estado.filtroVentas = { q: "", solo: "", orden: estado.filtroVentas.orden, sentido: estado.filtroVentas.sentido };
    return recargarLaTablaDeVentas();
  }
  if (nombre === "ventas-solo-pendientes") {
    const solo = estado.filtroVentas.solo === "pendientes" ? "" : "pendientes";
    estado.filtroVentas = { ...estado.filtroVentas, solo };
    return recargarLaTablaDeVentas();
  }
  if (nombre === "ventas-solo-sin-importe") {
    const solo = estado.filtroVentas.solo === "sin_importe" ? "" : "sin_importe";
    estado.filtroVentas = { ...estado.filtroVentas, solo };
    return recargarLaTablaDeVentas();
  }
  if (nombre === "venta-importe") return pantallaImporteDeUnaEntrega(elemento.dataset.id);
  if (nombre === "venta-importe-guardar") return guardarElImporteDeUnaEntrega();
  if (nombre === "venta-ajuste") return pantallaAjusteDeUnaEntrega(elemento.dataset.id);
  if (nombre === "ajuste-elegir-tipo" || nombre === "ajuste-elegir-origen") {
    const campo = nombre === "ajuste-elegir-tipo" ? "tipo" : "origen";
    estado.borradorAjuste[campo] = elemento.dataset.valor;
    return pantallaAjusteDeUnaEntrega(estado.borradorAjuste.venta);
  }
  if (nombre === "ajuste-guardar") return guardarElAjuste();
  if (nombre === "ajuste-anular") return preguntarSiQuitarElAjuste(elemento.dataset.venta, elemento.dataset.id);
  if (nombre === "ajuste-anular-si") return quitarUnAjuste(elemento.dataset.venta, elemento.dataset.id);
  // La factura nuestra (T12): la lista, juntar entregas, la ficha y quitarla.
  if (nombre === "facturas-emitidas-ver") return pantallaFacturasEmitidas();
  if (nombre === "factura-emitida-nueva" || nombre === "ventas-facturar") {
    estado.errorVentas = "";
    return pantallaFacturarEntregas(elemento.dataset.id || null);
  }
  if (nombre === "facturar-marcar") {
    // Marcar y desmarcar una entrega para juntarla con otras: se vuelve a pintar y la marca se lee del
    // estado, que es lo que hace que lo marcado sobreviva al repintado.
    return pantallaFacturarEntregas(elemento.dataset.id);
  }
  if (nombre === "factura-emitida-guardar") return guardarLaFacturaEmitida();
  if (nombre === "factura-emitida-abrir") return pantallaUnaFacturaEmitida(elemento.dataset.id);
  if (nombre === "factura-emitida-anular") return preguntarSiQuitarLaFactura(elemento.dataset.id);
  if (nombre === "factura-emitida-anular-si") return quitarLaFacturaEmitida(elemento.dataset.id);
  // Los cobros (T12): la lista, apuntar uno, decir de qué factura es y deshacerlo.
  if (nombre === "cobros-ver") return pantallaCobros();
  if (nombre === "cobro-nuevo") return pantallaCobroNuevo(elemento.dataset.factura || null);
  if (nombre === "cobro-guardar") return guardarElCobro();
  if (nombre === "cobro-conciliar") {
    // Se pregunta contra qué factura con la lista de las que tienen algo pendiente: elegir a ciegas
    // entre cuatro números de factura no es elegir.
    const pendientes = (estado.facturasEmitidas || []).filter(
      (factura) => factura.pendiente && factura.pendiente !== "0.00",
    );
    if (!pendientes.length) {
      estado.errorVentas = t("cobro.no_hay_facturas", "");
      return pantallaCobros();
    }
    if (pendientes.length === 1) return conciliarUnCobro(elemento.dataset.id, pendientes[0].id);
    return pantallaElegirFacturaParaElCobro(elemento.dataset.id, pendientes);
  }
  if (nombre === "cobro-conciliar-con") {
    return conciliarUnCobro(elemento.dataset.cobro, elemento.dataset.factura);
  }
  if (nombre === "cobro-desconciliar") return conciliarUnCobro(elemento.dataset.id, null);
  if (nombre === "cobro-anular") return preguntarSiQuitarElCobro(elemento.dataset.id);
  if (nombre === "cobro-anular-si") return quitarUnCobro(elemento.dataset.id);
  if (nombre === "medidas-ver") return pantallaMedidas();
  if (nombre === "medidas-guardar") return guardarMedidas();
  if (nombre === "medidas-ninguna") {
    const borrador = borradorDeMedidas();
    borrador.aplicadas = [];
    borrador.observaciones = {};
    return pantallaMedidas();
  }
  // Quitar la declaración entera (ronda 93): la finca vuelve a estar sin contestar. Primero se pregunta.
  if (nombre === "medidas-quitar") return preguntarSiQuitarLasMedidas();
  if (nombre === "medidas-quitar-si") return quitarLasMedidas();
  // **Ordenar una tabla** (30/09/2026): se pulsa la cabecera de una columna y la lista se ordena por ella;
  // se vuelve a pulsar y se le da la vuelta. Es lo que se hace con 64 tierras («¿cuál es la más grande?»).
  // El orden **es de la pantalla** y no del aparato: en el móvil, las tarjetas salen en el mismo orden.
  if (nombre === "elegir-fila") {
    // Elegir una fila para verla en el panel de al lado (fase 3, 30/09/2026). Se acuerda por tabla y se
    // vuelve a pintar la pantalla de la que salió: la fila queda marcada y su ficha aparece al lado.
    const clave = elemento.dataset.tabla || "tierras";
    estado.filaElegida = estado.filaElegida || {};
    const yaEstaba = Number(estado.filaElegida[clave]) === Number(elemento.dataset.id);
    // Volver a tocar la misma fila la quita: es como se cierra el panel sin buscar un botón de cerrar.
    estado.filaElegida[clave] = yaEstaba ? null : Number(elemento.dataset.id);
    return repintarLaPantallaDeLaTabla(clave);
  }
  if (nombre === "ordenar-tabla") {
    const campo = elemento.dataset.campo;
    // **La tabla de la que viene el clic, no una cualquiera** (30/09/2026). Antes esto solo miraba si era la
    // del cuaderno o no, así que pulsar la cabecera de la tabla de facturas ordenaba **las tierras** y
    // mandaba al agricultor a otra pantalla. Ahora la clave se lee tal cual y se pinta la pantalla de esa
    // tabla: cada lista ordena la suya.
    const clave = elemento.dataset.tabla || "tierras";
    const antes = elOrdenDeLaTabla(clave);
    estado.ordenDeLaTabla[clave] =
      antes.campo === campo ? { campo, sentido: -antes.sentido } : { campo, sentido: 1 };
    // **La tabla de lo que se vende ordena el servidor** (T12): su importe está guardado como texto
    // decimal (`"9.00"` es mayor que `"121.00"` comparando como texto y menor comparando como número) y
    // las fechas se comparan por su valor, no por el texto formateado. Así que el orden se le manda a él
    // y él devuelve la tabla ordenada; el estado se guarda igual, para que la flecha de la cabecera diga
    // por dónde va.
    if (clave === "ventas") {
      estado.filtroVentas = {
        ...estado.filtroVentas,
        orden: campo,
        sentido: estado.ordenDeLaTabla[clave].sentido,
      };
      return recargarLaTablaDeVentas();
    }
    return repintarLaPantallaDeLaTabla(clave);
  }
  if (nombre === "medidas-marcar") {
    const borrador = recogeNotasDeMedidas();
    const codigo = elemento.dataset.codigo;
    borrador.aplicadas = borrador.aplicadas.includes(codigo)
      ? borrador.aplicadas.filter((c) => c !== codigo)
      : [...borrador.aplicadas, codigo];
    return pantallaMedidas();
  }
  if (nombre === "medidas-marcar-apunte") {
    // Dentro del asistente solo se marca y se desmarca: lo que se hizo esa vez.
    const b = estado.asistente.borrador;
    const codigo = elemento.dataset.codigo;
    if (!Array.isArray(b.medidas)) b.medidas = medidasAplicadasDeLaFinca();
    b.medidas = b.medidas.includes(codigo)
      ? b.medidas.filter((c) => c !== codigo)
      : [...b.medidas, codigo];
    return pintarAsistente();
  }
  if (nombre === "entrar") return entrar(elemento.dataset.modo);
  if (nombre === "entrar-certificado") return entrarConCertificado();
  if (nombre === "cambiar-modo-entrar") return pantallaEntrar(elemento.dataset.modo);
  if (nombre === "salir") return salir();
  if (nombre === "repetir") return repetir();
  if (nombre === "sacar-papel") return sacarPapel();
  if (nombre === "sacar-datos") return sacarDatos();
  if (nombre === "deshacer") return deshacer(elemento.dataset.tipo, elemento.dataset.id);
  // Corregir y borrar lo que ya está apuntado (ronda 91) o dado de alta (ronda 92: tierras y grupos).
  // Las tres acciones van con el tipo y el identificador de la cosa, que es lo que dicen los botones de
  // cada ficha. Se llaman «cosa» y no «apunte» porque desde la ronda 92 **también sirven para lo que no
  // es un apunte del cuaderno**: corregir una tierra no es corregir un apunte.
  if (nombre === "cosa-corregir") {
    return corregirAlgo(elemento.dataset.tipo, Number(elemento.dataset.id));
  }
  if (nombre === "cosa-borrar") {
    return preguntarSiBorrarAlgo(elemento.dataset.tipo, Number(elemento.dataset.id));
  }
  if (nombre === "cosa-borrar-si") {
    return borrarAlgo(elemento.dataset.tipo, Number(elemento.dataset.id));
  }
  if (nombre === "cosa-anular") {
    return anularAlgo(elemento.dataset.tipo, Number(elemento.dataset.id));
  }
  // Y corregir desde la pantalla de «apuntado»: es el momento en el que el agricultor se da cuenta de
  // la mitad de las equivocaciones (acaba de ver el resumen en el móvil).
  if (nombre === "hecho-corregir") {
    return corregirAlgo(elemento.dataset.tipo, Number(elemento.dataset.id));
  }
  if (nombre === "cambiar-letra") {
    document.body.classList.toggle("letra-grande");
    guardar(CLAVE_LETRA, document.body.classList.contains("letra-grande"));
    return;
  }

  // **El menú del móvil** (07/10/2026). Por debajo de 64 rem el armazón no cabe a la izquierda y estaba
  // escondido del todo: los 21 renglones seguían en el documento pero medían 0×0, así que **con el teclado
  // no se llegaba a las cuentas** (había que escribir la dirección). Estos dos botones lo abren y lo
  // cierran, y el mismo armazón sirve para los dos anchos.
  if (nombre === "menu-abrir") {
    estado.menuAbierto = true;
    // Se olvida lo pintado para que el armazón se vuelva a montar con la clase de abierto.
    estado.marcoPintado = "";
    pintarMarco(estado.ultimoMontado);
    // **El foco se queda donde estaba, y está anotado como pendiente** (07/10/2026). Lo suyo sería que
    // entrara en el menú al abrirlo, pero al hacerlo se rompía el paseo con teclado que mide
    // `scripts/comprobar_el_armazon.py` (que cuenta las pulsaciones desde el botón de abrir), y esa
    // comprobación es la que dice si la navegación funciona. Se deja como está y se apunta: quien va con
    // el teclado tiene que dar la vuelta al tabulador para entrar en el menú que acaba de abrir.
    return;
  }
  if (nombre === "menu-cerrar") {
    estado.menuAbierto = false;
    estado.marcoPintado = "";
    pintarMarco(estado.ultimoMontado);
    return;
  }

  if (nombre === "fecha-rapida") {
    // El campo viene del botón: el tratamiento tiene una fecha y un análisis tiene dos,
    // así que «hoy» tiene que saber a cuál se refiere.
    const campo = elemento.dataset.campo || "fecha";
    estado.asistente.borrador[campo] = elemento.dataset.valor;
    pintarAsistente();
    return;
  }

  if (nombre === "tipo-tratamiento") {
    // Ha dicho que no es en una parcela: se apunta de qué clase es y se pasa a elegir el
    // sitio. La parcela que hubiera elegido antes se olvida, para no mandar las dos.
    estado.asistente.borrador.tipo = elemento.dataset.tipo;
    estado.asistente.borrador.parcela_id = null;
    estado.asistente.error = null;
    irA(estado.asistente.indice + 1);
    return;
  }

  if (nombre === "elegir") {    const campo = elemento.dataset.campo;
    const valor = valorDeEleccion(elemento.dataset.valor);

    // En el mapa no hay asistente: lo que se elige ahí es de secano o de regadío, para la parcela
    // que se va a apuntar. Se guarda en el estado del mapa y se vuelve a pintar.
    if (!estado.asistente && estado.mapa) {
      recogeElMapa();
      estadoDelMapa()[campo] = valor;
      return pantallaMapa();
    }

    const numerico = ["parcela_id", "producto_id", "fertilizante_id", "aplicador_id", "equipo_id", "trabajo_id"];
    estado.asistente.borrador[campo] = numerico.includes(campo) ? Number(valor) : valor;
    // Al elegir la parcela se pone su superficie, que es lo normal: casi siempre se
    // trata la parcela entera. Se puede cambiar en el paso siguiente.
    if (campo === "parcela_id" && elemento.dataset.superficie) {
      estado.asistente.borrador.superficie_tratada_ha = elemento.dataset.superficie;
      estado.asistente.borrador.superficie_ha = elemento.dataset.superficie;
    }
    // Y al elegir un grupo, la superficie es la de **todas** sus parcelas juntas. Se olvida la
    // parcela que hubiera elegido antes: un apunte es de una parcela o de un grupo, no de las dos.
    if (campo === "grupo_id") {
      estado.asistente.borrador.parcela_id = null;
      if (elemento.dataset.superficie) {
        estado.asistente.borrador.superficie_tratada_ha = elemento.dataset.superficie;
        estado.asistente.borrador.superficie_ha = elemento.dataset.superficie;
      }
    }
    if (campo === "parcela_id") {
      estado.asistente.borrador.grupo_id = null;
    }
    // En una pantalla con varios campos (los opcionales agrupados) elegir no puede
    // saltar de pantalla: hay más cosas que contestar aquí.
    const paso = pasoActual();
    if (paso.campos && paso.campos.length > 1) {
      pintarAsistente();
      return;
    }
    irA(estado.asistente.indice + 1);
    return;
  }

  if (nombre === "asistente-seguir") {
    const asistente = estado.asistente;
    if (asistente.indice === asistente.pasos.length - 1) return guardarAsistente();
    return irA(asistente.indice + 1);
  }
  if (nombre === "asistente-atras") return irA(estado.asistente.indice - 1);
  if (nombre === "asistente-saltar") return irA(estado.asistente.indice + 1);

  // ---------------------------------------------------------------------------
  // La maquinaria (T14, E8, 03/10/2026)
  // ---------------------------------------------------------------------------
  //
  // Cada acción es una línea, y todas están aquí por el mismo motivo que las demás: el manejador es uno
  // solo, delegado en `document`, y un botón que se pinta y no se atiende es un botón que no hace nada.
  if (nombre === "maquinaria-ver") return abrirLaMaquinaria();
  if (nombre === "maquinaria-buscar") {
    // Lo que se busca vive en `estado` (y no solo en la casilla) porque el buscador repinta la pantalla al
    // filtrar: si viviera en el `<input>`, repintar lo borraría.
    const suyo = estadoDeLaMaquinaria();
    suyo.filtro = valorDeLaCasilla("maquinaria-buscar");
    return pantallaMaquinaria();
  }
  if (nombre === "maquinaria-ver-todas") {
    estadoDeLaMaquinaria().filtro = "";
    return pantallaMaquinaria();
  }
  if (nombre === "maquina-ver") return abrirUnaMaquina(Number(elemento.dataset.id));
  if (nombre === "maquina-nueva") {
    const suyo = estadoDeLaMaquinaria();
    suyo.error = "";
    suyo.aviso = "";
    // **Sin valores puestos a propósito**: la clase, la propiedad y la disponibilidad se preguntan y no
    // nacen contestadas, que es lo que evita dar por bueno lo que nadie ha dicho.
    suyo.borrador = {};
    suyo.formulario = { clase: "maquina", corrigiendo: false };
    return pantallaMaquinaria();
  }
  if (nombre === "maquina-corregir") {
    const suyo = estadoDeLaMaquinaria();
    suyo.error = "";
    suyo.aviso = "";
    suyo.borrador = {};
    suyo.formulario = { clase: "maquina", corrigiendo: true };
    return pantallaUnaMaquina();
  }
  if (nombre === "maquina-cancelar") {
    const suyo = estadoDeLaMaquinaria();
    suyo.formulario = null;
    suyo.borrador = null;
    suyo.error = "";
    return suyo.maquina ? pantallaUnaMaquina() : pantallaMaquinaria();
  }
  if (nombre === "maquina-elegir") {
    // Lo elegido se guarda en el borrador **antes** de repintar: al repintar se pierde lo que solo
    // estuviera en la pantalla, y eso ya costó una ronda con el fichero del cuaderno de la Junta.
    const suyo = estadoDeLaMaquinaria();
    suyo.borrador = { ...(suyo.borrador || {}), [elemento.dataset.campo]: elemento.dataset.valor };
    return suyo.maquina && suyo.formulario && suyo.formulario.corrigiendo
      ? pantallaUnaMaquina()
      : pantallaMaquinaria();
  }
  if (nombre === "maquina-guardar") return guardarLoDeLaMaquinaria();
  if (nombre === "maquina-traer-equipo") {
    const suyo = estadoDeLaMaquinaria();
    suyo.error = "";
    suyo.aviso = "";
    const resultado = await mandarCambio(
      `/api/maquinaria/desde-equipo/${Number(elemento.dataset.id)}`,
      "POST",
      {},
    );
    if (resultado.error) {
      suyo.error = resultado.error;
      return pantallaMaquinaria();
    }
    suyo.aviso = t("maquinaria.equipo_traido", "");
    await recargarLaMaquinaria();
    return abrirUnaMaquina(resultado.datos.id);
  }
  if (nombre === "maquina-declarar") {
    // **La declaración de una obligación**: qué le toca y de dónde sale. Se mandan los dos campos juntos
    // —el que se acaba de contestar y el que ya estaba— porque el servidor guarda una sola respuesta por
    // máquina y obligación, y porque «no le toca» sin decir quién lo dice es media respuesta.
    const suyo = estadoDeLaMaquinaria();
    const maquina = (suyo.maquina || {}).maquina || {};
    const tipo = elemento.dataset.tipo;
    const la_suya = (suyo.maquina.obligaciones || []).find((una) => una.tipo === tipo) || {};
    const campo = elemento.dataset.campo;
    // **`|| ""` y no `|| "no_se"`**: la opción «no es ninguno de esos» del equipo del cuaderno vale vacío a
    // propósito (es «quitar el enlace»), y `datosDelBoton` no escribe un `data-*` vacío, así que aquí llega
    // `undefined`. Tratarlo como «no lo sé» dejaría el enlace puesto para siempre.
    const valor = elemento.dataset.valor === undefined ? "" : elemento.dataset.valor;
    const aplicabilidad = campo === "aplicabilidad" ? valor : la_suya.aplicabilidad || "no_se";
    const origen =
      campo === "origen"
        ? valor
        : la_suya.opciones_origen && la_suya.opciones_origen.opciones
          ? (la_suya.opciones_origen.opciones.find((una) => una.elegido) || {}).valor || "no_se"
          : "no_se";
    suyo.error = "";
    const resultado = await mandarCambio(
      `/api/maquinaria/${maquina.id}/obligaciones/${tipo}`,
      "PUT",
      { aplicabilidad, origen, notas: null },
    );
    if (resultado.error) {
      suyo.error = resultado.error;
      return pantallaUnaMaquina();
    }
    await recargarLaFichaDeLaMaquina();
    await recargarLaMaquinaria();
    return pantallaUnaMaquina();
  }
  if (nombre === "maquina-inspeccion-nueva") {
    const suyo = estadoDeLaMaquinaria();
    suyo.error = "";
    suyo.aviso = "";
    suyo.borrador = { tipo: elemento.dataset.tipo || "iteaf", resultado: "no_consta" };
    suyo.formulario = { clase: "inspeccion", tipo: elemento.dataset.tipo || "iteaf" };
    return pantallaUnaMaquina();
  }
  if (nombre === "maquina-inspeccion-corregir") {
    const suyo = estadoDeLaMaquinaria();
    const cruda = ((suyo.maquinaCruda || {}).inspecciones || []).find(
      (una) => Number(una.id) === Number(elemento.dataset.id),
    );
    if (!cruda) return pantallaUnaMaquina();
    suyo.error = "";
    suyo.borrador = {
      tipo: cruda.tipo,
      resultado: cruda.resultado,
      documento_id: cruda.documento_id ? String(cruda.documento_id) : "",
    };
    suyo.formulario = { clase: "inspeccion", corrigiendo: cruda };
    return pantallaUnaMaquina();
  }
  if (nombre === "maquina-inspeccion-borrar") {
    const suyo = estadoDeLaMaquinaria();
    const maquina = (suyo.maquina || {}).maquina || {};
    suyo.error = "";
    const resultado = await mandarCambio(
      `/api/maquinaria/${maquina.id}/inspecciones/${Number(elemento.dataset.id)}`,
      "DELETE",
    );
    if (resultado.error) {
      suyo.error = resultado.error;
      return pantallaUnaMaquina();
    }
    suyo.aviso = t("maquinaria.corregida", "");
    await recargarLaFichaDeLaMaquina();
    await recargarLaMaquinaria();
    return pantallaUnaMaquina();
  }
  if (nombre === "maquina-averia-nueva") {
    const suyo = estadoDeLaMaquinaria();
    suyo.error = "";
    suyo.aviso = "";
    // La avería **no se contesta sola**: si sigue sin arreglar o no, lo dice el agricultor. `resuelta` se
    // queda sin poner para que la pregunta salga sin respuesta marcada.
    suyo.borrador = {};
    suyo.formulario = { clase: "averia" };
    return pantallaUnaMaquina();
  }
  if (nombre === "maquina-averia-corregir") {
    const suyo = estadoDeLaMaquinaria();
    const cruda = ((suyo.maquinaCruda || {}).averias || []).find(
      (una) => Number(una.id) === Number(elemento.dataset.id),
    );
    if (!cruda) return pantallaUnaMaquina();
    suyo.error = "";
    suyo.borrador = {};
    suyo.formulario = { clase: "averia", corrigiendo: cruda };
    return pantallaUnaMaquina();
  }
  if (nombre === "maquina-averia-borrar") {
    const suyo = estadoDeLaMaquinaria();
    const maquina = (suyo.maquina || {}).maquina || {};
    suyo.error = "";
    const resultado = await mandarCambio(
      `/api/maquinaria/${maquina.id}/averias/${Number(elemento.dataset.id)}`,
      "DELETE",
    );
    if (resultado.error) {
      suyo.error = resultado.error;
      return pantallaUnaMaquina();
    }
    suyo.aviso = t("maquinaria.corregida", "");
    await recargarLaFichaDeLaMaquina();
    await recargarLaMaquinaria();
    return pantallaUnaMaquina();
  }
  if (nombre === "maquina-anular") {
    // Anular **no es borrar**: se pregunta el motivo y se dice lo que pasa, porque lo anulado se queda en
    // el cuaderno tachado y deja de contar para la última inspección.
    const suyo = estadoDeLaMaquinaria();
    const que = elemento.dataset.que;
    suyo.error = "";
    suyo.formulario = null;
    suyo.anulando = {
      que,
      id: Number(elemento.dataset.id),
      titulo: que === "inspeccion" ? t("maquinaria.anular_inspeccion", "") : t("maquinaria.anular_averia", ""),
      pista: t("maquinaria.anular_pista", ""),
    };
    return pantallaUnaMaquina();
  }
  if (nombre === "maquina-anular-cancelar") {
    const suyo = estadoDeLaMaquinaria();
    suyo.anulando = null;
    return pantallaUnaMaquina();
  }
  if (nombre === "maquina-anular-confirmar") {
    const suyo = estadoDeLaMaquinaria();
    const maquina = (suyo.maquina || {}).maquina || {};
    const que = elemento.dataset.que;
    const motivo = valorDeLaCasilla("anular-motivo");
    if (!motivo) {
      suyo.error = t("maquinaria.anular_necesita_motivo", "");
      return pantallaUnaMaquina();
    }
    suyo.error = "";
    const base = `/api/maquinaria/${maquina.id}/${que === "inspeccion" ? "inspecciones" : "averias"}`;
    const resultado = await mandarCambio(`${base}/${Number(elemento.dataset.id)}/anular`, "POST", {
      motivo,
    });
    if (resultado.error) {
      suyo.error = resultado.error;
      return pantallaUnaMaquina();
    }
    suyo.anulando = null;
    suyo.aviso = t("maquinaria.anulada", "");
    await recargarLaFichaDeLaMaquina();
    await recargarLaMaquinaria();
    return pantallaUnaMaquina();
  }
  // Las cuentas de la explotación (T13, E7, 05/10/2026)
  const enLasCuentas = await atenderLasCuentas(nombre, elemento);
  if (enLasCuentas !== false) return enLasCuentas;
  // Los trabajos por tierra (T15, E9, 05/10/2026)
  const enLosTrabajos = await atenderLosTrabajos(nombre, elemento);
  if (enLosTrabajos !== false) return enLosTrabajos;
  if (nombre.startsWith("banco-")) return atenderLosBancos(nombre, elemento);
  if (nombre.startsWith("bandeja-")) return atenderLaBandeja(nombre, elemento);
});

window.addEventListener("online", () => {
  pintarAvisoPendientes();
  mandarPendientes();
});

window.addEventListener("offline", pintarAvisoPendientes);

// ---------------------------------------------------------------------------
// Las cuentas de la explotación (T13, E7, 05/10/2026)
// ---------------------------------------------------------------------------
//
// LO QUE ESTE BLOQUE HACE, Y LO QUE NO. Hace tres cosas y ninguna más:
//
//   1. **Pide los datos** a `GET /api/gastos` y los pasa a la pantalla, que no calcula nada.
//   2. **Recoge lo que el agricultor escribe** por los `id` de los campos y lo manda al servidor.
//   3. **Atiende las 17 acciones** de sus botones, una por una.
//
// Lo que **no** hace: ni una cuenta de dinero. Todos los importes, los repartos, los cuadres y los
// márgenes llegan calculados del servidor (`app/gastos.py`, con `Decimal`), porque en el navegador
// todo número es de coma flotante y el total de la pantalla dejaría de coincidir con el de la base
// por céntimos.

/** El estado de las cuentas, creado la primera vez que hace falta (como el del almacén). */
function estadoDeLasCuentas() {
  if (!estado.cuentas) {
    estado.cuentas = {
      // Lo que devolvió `GET /api/gastos`: las cinco listas, las tres columnas del coste, la caja,
      // los márgenes y lo que falta.
      datos: null,
      // La ficha de un gasto abierta (`GET /api/gastos/<id>`), o nada.
      gasto: null,
      // El formulario que está abierto: apuntar un gasto, repartirlo, apuntar un pago, una inversión
      // o una ayuda. `clase` dice cuál, y es lo que el botón de guardar manda al servidor.
      formulario: null,
      // El borrador: lo que el agricultor ha ido eligiendo (la categoría, el método de reparto, los
      // destinos). **Vive aquí y no en el DOM**: al repintar para enseñar una cosa nueva se perdería.
      borrador: null,
      anulando: null,
      filtro: "",
      guardando: false,
      error: "",
      aviso: "",
    };
  }
  return estado.cuentas;
}

/** El vocabulario de estas pantallas: el de las cuentas y los dos botones de corregir y borrar. */
function textosDeLasCuentas() {
  return {
    gasto: t("gastos", {}),
    acciones: accion("volver") ? { volver: accion("volver") } : {},
    tabla: t("tabla", {}),
  };
}

/** Abre «mis cuentas»: se pinta enseguida y se vuelve a pintar con lo que contesta el servidor. */
async function abrirLasCuentas() {
  const suyo = estadoDeLasCuentas();
  suyo.error = "";
  suyo.aviso = "";
  suyo.formulario = null;
  suyo.borrador = null;
  suyo.anulando = null;
  suyo.gasto = null;
  pantallaLasCuentas();
  await recargarLasCuentas();
  pantallaLasCuentas();
}

/** Vuelve a pedir las cuentas de la finca. */
async function recargarLasCuentas() {
  const suyo = estadoDeLasCuentas();
  const campana = estado.campana;
  const consulta = campana && campana.id ? `?campana_id=${campana.id}` : "";
  try {
    suyo.datos = await apiJson(`/api/gastos${consulta}`);
    suyo.error = "";
  } catch (fallo) {
    suyo.error = (fallo && fallo.message) || mensaje("no_se_pudo");
  }
  return suyo;
}

/** La lista de las cuentas, ya en React. */
function pantallaLasCuentas() {
  const suyo = estadoDeLasCuentas();
  const g = t("gastos", {});
  const datos = suyo.datos || {};
  const casan = (datos.gastos || []).filter((gasto) => {
    const busca = (suyo.filtro || "").toLocaleLowerCase("es");
    if (!busca) return true;
    return `${gasto.concepto || ""} ${gasto.proveedor || ""}`
      .toLocaleLowerCase("es")
      .includes(busca);
  });
  const cuantos = casan.length;
  return montar(() =>
    pantallaDeLasCuentas({
      textos: textosDeLasCuentas(),
      // El singular y el plural con las dos formas del servidor: «Tienes 1 gastos» es lo primero que
      // hace desconfiar de un programa.
      cuentas: { ...datos, gastos: casan },
      resumen: cuantos ? conCuenta(g, "cuantas", cuantos) : "",
      filtro: suyo.filtro,
      tabla: tablaDeLasCuentas(casan),
      formulario: elFormularioDeLasCuentas(suyo.formulario, suyo.borrador),
      anulando: suyo.anulando,
      guardando: suyo.guardando,
      error: suyo.error || "",
      aviso: suyo.aviso || "",
    }),
  );
}

/** La tabla del ordenador: una celda menos que columnas (la última, «Acciones», la pone la pieza). */
function tablaDeLasCuentas(gastos) {
  const g = t("gastos", {});
  const col = (clave) => t(`tabla.cuentas_${clave}`, "");
  const columnas = [
    { texto: col("concepto"), campo: "concepto" },
    { texto: col("coste") },
    { texto: col("va_a") },
    { texto: col("pagado") },
    { texto: col("pendiente") },
    { texto: col("estado") },
    { texto: col("acciones") },
  ];
  const filas = (gastos || []).map((gasto) => ({
    celdas: [
      {
        texto: gasto.concepto,
        accion: "gasto-abrir",
        datos: { id: gasto.id },
      },
      // **Un importe que no consta se enseña con su palabra, no con un cero.**
      { texto: gasto.importe ? gasto.texto_importe : g.no_se_sabe },
      {
        texto: gasto.repartos.length
          ? gasto.repartos.map((uno) => uno.etiqueta_destino || uno.destino).filter(Boolean).join(", ")
          : g.sin_asignar_corto,
        pista: gasto.esta_sin_repartir ? g.sin_asignar_explica : "",
      },
      { texto: gasto.texto_pagado },
      { texto: gasto.pendiente ? gasto.texto_pendiente : g.no_se_sabe },
      { texto: g[`estado_${gasto.estado}`] || "" },
    ],
    acciones: [],
  }));
  return {
    clave: "gastos",
    etiqueta: g.titulo,
    columnas,
    filas,
    resumen: filas.length
      ? rellena(t("tabla.resumen_cuentas", ""), {
          cuantas: filas.length,
          total: (estadoDeLasCuentas().datos || {}).coste_por_clase
            ? estadoDeLasCuentas().datos.coste_por_clase.texto_total_conocido
            : "",
        })
      : "",
  };
}

/** Abre la ficha de un gasto, pidiéndola a su puerta (`GET /api/gastos/<id>`). */
async function abrirUnGasto(id) {
  const suyo = estadoDeLasCuentas();
  if (!id) return abrirLasCuentas();
  suyo.error = "";
  suyo.aviso = "";
  suyo.formulario = null;
  suyo.borrador = null;
  suyo.anulando = null;
  let respuesta = null;
  try {
    respuesta = await api(`/api/gastos/${id}`);
  } catch (fallo) {
    respuesta = null;
  }
  if (!respuesta) {
    if (!navigator.onLine) return pantallaDeUnaDireccionQueNoSePuedeComprobar();
    avisarDelError(mensaje("no_se_pudo"));
    return;
  }
  if (respuesta.status === 404) return pantallaDeDireccionQueNoLlevaANingunaParte();
  if (!respuesta.ok) {
    avisarDelError(mensaje("no_se_pudo"));
    return;
  }
  suyo.gasto = await respuesta.json();
  pantallaUnGasto();
}

/** La ficha de un gasto, ya en React. */
function pantallaUnGasto() {
  const suyo = estadoDeLasCuentas();
  const gasto = suyo.gasto || {};
  const susPagos = [];
  for (const pago of (suyo.datos || {}).pagos || []) {
    for (const aplicacion of pago.aplicaciones || []) {
      if (aplicacion.gasto_id !== gasto.id) continue;
      susPagos.push({
        id: pago.id,
        aplicacion_id: aplicacion.id,
        texto_importe: pago.texto_importe,
        texto_aplicado: aplicacion.texto_importe,
      });
    }
  }
  return montar(() =>
    pantallaDeUnGasto({
      textos: textosDeLasCuentas(),
      gasto,
      pagos: susPagos,
      formulario: elFormularioDeLasCuentas(suyo.formulario, suyo.borrador),
      repartiendo:
        suyo.formulario && suyo.formulario.clase === "reparto"
          ? elFormularioDeLasCuentas(suyo.formulario, suyo.borrador)
          : null,
      anulando: suyo.anulando,
      guardando: suyo.guardando,
      error: suyo.error || "",
      aviso: suyo.aviso || "",
    }),
  );
}

/**
 * El formulario que está abierto, con sus bloques.
 *
 * **Los campos llevan su `id` y los botones de elegir su `campo`**: es lo único que este fichero
 * tiene para leer lo que el agricultor ha escrito. Y **ninguna pregunta nace contestada**: lo que no
 * haya elegido él va con `elegido: ""`, y la pantalla no marca ninguna opción.
 */
/**
 * Las tierras de la finca, para poder marcar entre cuáles se reparte un gasto.
 *
 * Las que ya están descargadas; si no hay ninguna (sin cobertura y sin datos), la lista sale vacía y la
 * pantalla lo dice en vez de ofrecer un reparto que no se puede hacer.
 */
function lasTierrasParaUnReparto() {
  return (estado.parcelas || []).map((parcela) => ({
    clave: String(parcela.id),
    nombre: parcela.alias || parcela.ref_sigpac || "",
    hectareas: parcela.superficie_ha === undefined ? null : parcela.superficie_ha,
  }));
}

/**
 * **Lo que se puede marcar para repartir un gasto, según a qué clase de sitio va** (ronda 9).
 *
 * POR QUÉ EXISTE ESTA FUNCIÓN, Y ES UN DEFECTO ARREGLADO: el formulario ofrecía repartir «entre tierras,
 * entre cultivos o entre máquinas», pero lo que se podía marcar era **siempre la lista de tierras**.
 * Eligiendo «máquina» y marcando tierras, el servidor guardaba un reparto que decía `maquina` con el
 * número de una tierra dentro: el libro de cuentas afirmaba algo falso, sin un solo error. Ahora cada
 * destino trae **sus** cosas, y lo que viaja es lo que se está viendo:
 *
 *  · **tierra**: su número en el cuaderno (el servidor le pone el nombre al enseñarlo);
 *  · **cultivo**: los cultivos que el agricultor tiene sembrados este año, por su nombre —los mismos que
 *    lee en «qué hay sembrado»—, que es lo que el servidor guarda y lo que se lee después;
 *  · **máquina**: sus máquinas, por su nombre, que es lo mismo que hace el resto del programa con ellas.
 *
 * Y **sin hectáreas para los cultivos y las máquinas**: un cultivo o una máquina no tienen superficie
 * propia, así que el método de las hectáreas solo se ofrece para las tierras (ver `losMetodosDelReparto`).
 */
function lasCosasParaUnReparto(destino) {
  if (destino === "cultivo") {
    const dichos = [];
    for (const fila of ((estado.cultivos || {}).parcelas || [])) {
      // **El cultivo de este año está en `actual`, y ahí dentro en `especie`** (`GET /api/cultivos`
      // devuelve, por tierra, lo que tiene sembrado este año y los anteriores). No es `fila.cultivo` ni
      // `fila.especie`: eso se dio por supuesto al escribirlo y la lista salía **vacía** —el mismo
      // defecto que el de los envases del almacén, y por eso lo cazó la ruta del navegador y no una
      // prueba de cableado, que se escribió con la misma suposición equivocada—. Una tierra que todavía
      // no dice qué tiene trae `actual: null`, y entonces no hay cultivo que ofrecer.
      const cultivo = (((fila || {}).actual || {}).especie || "").trim();
      if (cultivo && !dichos.some((uno) => uno.nombre === cultivo)) {
        dichos.push({ clave: cultivo, nombre: cultivo, hectareas: null });
      }
    }
    return dichos;
  }
  if (destino === "maquina") {
    // Las máquinas viven en el estado de los trabajos (ver `cargarLasMaquinasSiHacenFalta`), y quien
    // llama a esta función **ya se ha ocupado de que estén cargadas** antes de pintar el formulario.
    return ((estadoDeLosTrabajos().maquinas) || []).map((maquina) => ({
      clave: maquina.texto || "",
      nombre: maquina.texto || "",
      hectareas: null,
    }));
  }
  return lasTierrasParaUnReparto();
}

/**
 * Los métodos de reparto que se pueden usar según a qué se reparte.
 *
 * **«Por hectáreas» solo vale para las tierras**: las hectáreas son de una tierra, y ni un cultivo ni una
 * máquina tienen superficie propia. El servidor lo dice igual (`G48_las_hectareas_son_de_una_tierra`), y
 * aquí no se ofrece, que es la otra mitad: no se enseña un camino que la puerta va a cerrar.
 */
function losMetodosDelReparto(destino) {
  const todos = ((estado.interfaz || {}).metodos_de_reparto) || [];
  if (destino === "tierra") return todos.map((uno) => ({ valor: uno.valor, texto: uno.texto }));
  return todos
    .filter((uno) => uno.valor !== "area" && uno.valor !== "hectareas")
    .map((uno) => ({ valor: uno.valor, texto: uno.texto }));
}

/**
 * El `id` del campo donde se escribe lo que le toca a un destino del reparto.
 *
 * **Sin espacios ni tildes, y por eso hay una función**: un destino puede llamarse «El tractor» o
 * «TRIGO BLANDO», y un `id` con un espacio **no se puede buscar con un selector** (`#gasto-peso-El
 * tractor` son dos cosas para el navegador: el campo `#gasto-peso-El` y un elemento `tractor` dentro).
 * Se cambia todo lo que no sea letra, número o guion bajo por un guion bajo, **en los dos sitios** —al
 * pintar el campo y al leerlo—, y el nombre del destino se sigue leyendo entero.
 */
function idDelPesoDelReparto(clave) {
  return `gasto-peso-${String(clave).replace(/[^0-9A-Za-z_]/g, "_")}`;
}

/**
 * El borrador del reparto con esas tierras marcadas, **conservando lo que ya estaba escrito**.
 *
 * POR QUÉ SE CONSERVA: marcar una tierra repinta el formulario —como elegir una categoría—, así que
 * las horas o los importes que el agricultor ya había escrito en las otras tierras se perderían. Se
 * leen **antes** de repintar (pintar la pantalla vacía las casillas) y se devuelven en el borrador.
 */
function conLasTierrasMarcadas(borrador, marcadas) {
  const suyo = borrador || {};
  const antes = {};
  for (const peso of suyo.pesos || []) {
    const escrito = valorDeLaCasilla(idDelPesoDelReparto(peso.clave));
    if (escrito !== "") antes[peso.clave] = escrito;
  }
  const tierras = suyo.tierras || [];
  return {
    ...suyo,
    parcela_ids: marcadas,
    pesos: marcadas.map((clave) => {
      const tierra = tierras.find((una) => String(una.clave) === String(clave)) || {};
      return { clave: String(clave), nombre: tierra.nombre || "", valor: antes[clave] || "" };
    }),
  };
}

function elFormularioDeLasCuentas(cual, borrador) {
  if (!cual) return null;
  const g = t("gastos", {});
  const b = borrador || {};
  const elDestinoDelReparto = (suyo) => (suyo || {}).destino_tipo || "tierra";
  const opcionesDe = (lista, elegido) =>
    (lista || []).map((uno) => ({ valor: uno.valor, texto: uno.texto, elegido: uno.valor === elegido }));
  // **Lo que el agricultor ya tiene escrito manda sobre lo que venía del cuaderno** (06/10/2026).
  // Pintar la pantalla borra las casillas, y **elegir una categoría repinta**: sin esto, escribir «el
  // gasóleo de la siega» y después tocar la categoría «Gasóleo» dejaba el concepto —y el importe, y la
  // fecha— **en blanco**, así que al guardar salía «No se ha podido» y el agricultor no sabía por qué.
  // Se mira primero lo que hay en la pantalla y solo si esa casilla no está (el primer pintado) se usa
  // lo que traía el formulario. Es la misma trampa que este fichero ya cuenta para la ficha de una
  // máquina: «el agricultor escribe la matrícula, toca “Es mía” y la matrícula desaparece».
  const loQueYaEstaba = (id, siNo) => {
    const nodo = id ? document.getElementById(id) : null;
    return nodo ? nodo.value : siNo;
  };
  const base = {
    guardar: g.guardar,
    cancelar: g.cancelar,
    guardando: g.guardando,
    datos: { clase: cual.clase, id: cual.id || "" },
    bloques: [],
  };
  if (cual.clase === "gasto") {
    return {
      ...base,
      titulo: cual.id ? g.form_corregir_titulo : g.form_nuevo_titulo,
      pista: cual.id ? g.form_corregir_pista : g.form_nuevo_pista,
      bloques: [
        { tipo: "texto", id: "gasto-concepto", etiqueta: g.campo_concepto, pista: g.campo_concepto_pista, valor: loQueYaEstaba("gasto-concepto", cual.concepto || "") },
        {
          tipo: "opciones",
          campo: "categoria",
          etiqueta: g.campo_categoria,
          pista: g.campo_categoria_pista,
          elegido: b.categoria || cual.categoria || "",
          opciones: opcionesDe((estado.interfaz || {}).categorias_de_gasto, b.categoria || cual.categoria),
        },
        { tipo: "numero", id: "gasto-importe", etiqueta: g.campo_importe, pista: g.campo_importe_pista, valor: loQueYaEstaba("gasto-importe", cual.importe || "") },
        { tipo: "numero", id: "gasto-base", etiqueta: g.campo_base, valor: loQueYaEstaba("gasto-base", cual.base_imponible || "") },
        { tipo: "numero", id: "gasto-cuota", etiqueta: g.campo_cuota, valor: loQueYaEstaba("gasto-cuota", cual.cuota_iva || "") },
        { tipo: "fecha", id: "gasto-fecha", etiqueta: g.campo_fecha, valor: loQueYaEstaba("gasto-fecha", cual.fecha || "") },
        { tipo: "fecha", id: "gasto-vencimiento", etiqueta: g.campo_vencimiento, pista: g.campo_vencimiento_pista, valor: loQueYaEstaba("gasto-vencimiento", cual.vencimiento || "") },
        { tipo: "texto", id: "gasto-proveedor", etiqueta: g.campo_proveedor, valor: loQueYaEstaba("gasto-proveedor", cual.proveedor || "") },
      ],
    };
  }
  if (cual.clase === "reparto") {
    return {
      ...base,
      titulo: g.form_repartir_titulo,
      pista: g.form_repartir_pista,
      bloques: [
        // **A qué se reparte, y qué se puede marcar** (ronda 9). El destino manda: sus cosas son las que
        // se marcan, y sus métodos son los que se ofrecen. Ver `lasCosasParaUnReparto`.
        {
          tipo: "opciones",
          campo: "destino_tipo",
          etiqueta: g.campo_destino,
          pista: g.campo_destino_pista,
          elegido: b.destino_tipo || "tierra",
          opciones: [
            { valor: "tierra", texto: t("tabla.cuentas_tierra", ""), elegido: b.destino_tipo === "tierra" },
            { valor: "cultivo", texto: t("tabla.cuentas_cultivo", ""), elegido: b.destino_tipo === "cultivo" },
            { valor: "maquina", texto: t("maquinaria.titulo", ""), elegido: b.destino_tipo === "maquina" },
          ],
        },
        {
          tipo: "opciones",
          campo: "metodo",
          etiqueta: g.campo_metodo,
          elegido: b.metodo || "",
          opciones: opcionesDe(losMetodosDelReparto(elDestinoDelReparto(b)), b.metodo),
        },
        // **Entre qué se reparte**: las tierras, los cultivos o las máquinas, según lo que se haya
        // elegido arriba. Sin esto los cuatro métodos se quedaban sin saber a qué repartir, y con la
        // lista equivocada se guardaba un reparto que decía una cosa y apuntaba a otra.
        {
          tipo: "marcas",
          campo: "parcela_ids",
          etiqueta:
            elDestinoDelReparto(b) === "cultivo"
              ? g.campo_cultivos
              : elDestinoDelReparto(b) === "maquina"
                ? g.campo_maquinas
                : g.campo_tierras,
          pista: g.campo_tierras_pista,
          todas: g.marcar_todas,
          marcadas: b.parcela_ids || [],
          opciones: (b.tierras || []).map((tierra) => ({
            clave: String(tierra.clave),
            texto: tierra.nombre,
            marcada: (b.parcela_ids || []).map(String).includes(String(tierra.clave)),
          })),
        },
        // Las horas, los litros o lo que le toca a cada sitio: un campo por tierra marcada.
        //
        // **`pista` y no `sufijo`** (06/10/2026): el formulario pinta la línea de debajo del campo con
        // `bloque.pista` —es el nombre que usan todos los campos de esta pantalla—, así que con `sufijo`
        // la unidad **no salía nunca**: el agricultor veía «El Prado» y una casilla, sin saber si le
        // están pidiendo horas, litros o euros.
        ...(b.pesos || []).map((uno) => ({
          tipo: "numero",
          id: idDelPesoDelReparto(uno.clave),
          etiqueta: uno.nombre,
          pista:
            b.metodo === "horas"
              ? g.campo_horas
              : b.metodo === "consumo"
                ? g.campo_litros
                : g.campo_euros_del_trozo,
          valor: uno.valor || "",
        })),
      ],
    };
  }
  if (cual.clase === "pago") {
    return {
      ...base,
      titulo: g.form_pago_titulo,
      pista: g.form_pago_pista,
      bloques: [
        { tipo: "numero", id: "pago-importe", etiqueta: g.campo_importe, valor: loQueYaEstaba("pago-importe", "") },
        { tipo: "fecha", id: "pago-fecha", etiqueta: g.campo_fecha, valor: loQueYaEstaba("pago-fecha", hoy()) },
        { tipo: "texto", id: "pago-proveedor", etiqueta: g.campo_proveedor, valor: loQueYaEstaba("pago-proveedor", "") },
        {
          tipo: "opciones",
          campo: "forma",
          etiqueta: t("cobro.forma", ""),
          elegido: b.forma || "transferencia",
          opciones: opcionesDe((estado.interfaz || {}).formas_de_pago, b.forma || "transferencia"),
        },
      ],
    };
  }
  if (cual.clase === "inversion") {
    return {
      ...base,
      titulo: g.form_inversion_titulo,
      pista: g.form_inversion_pista,
      bloques: [
        { tipo: "texto", id: "inversion-concepto", etiqueta: g.campo_concepto, valor: loQueYaEstaba("inversion-concepto", "") },
        {
          tipo: "opciones",
          campo: "categoria",
          etiqueta: g.campo_categoria,
          elegido: b.categoria || "",
          opciones: opcionesDe((estado.interfaz || {}).categorias_de_inversion, b.categoria),
        },
        { tipo: "numero", id: "inversion-importe", etiqueta: g.campo_importe, pista: g.campo_importe_pista, valor: loQueYaEstaba("inversion-importe", "") },
        { tipo: "fecha", id: "inversion-fecha", etiqueta: g.campo_fecha, valor: loQueYaEstaba("inversion-fecha", "") },
        { tipo: "texto", id: "inversion-proveedor", etiqueta: g.campo_proveedor, valor: loQueYaEstaba("inversion-proveedor", "") },
      ],
    };
  }
  if (cual.clase === "ayuda") {
    return {
      ...base,
      titulo: g.form_ayuda_titulo,
      pista: g.form_ayuda_pista,
      bloques: [
        { tipo: "texto", id: "ayuda-concepto", etiqueta: g.campo_concepto, valor: loQueYaEstaba("ayuda-concepto", "") },
        { tipo: "texto", id: "ayuda-organismo", etiqueta: g.campo_proveedor, valor: loQueYaEstaba("ayuda-organismo", "") },
        { tipo: "numero", id: "ayuda-previsto", etiqueta: g.ayuda_prevista, valor: loQueYaEstaba("ayuda-previsto", "") },
        { tipo: "numero", id: "ayuda-concedido", etiqueta: g.ayuda_concedida, valor: loQueYaEstaba("ayuda-concedido", "") },
        { tipo: "numero", id: "ayuda-cobrado", etiqueta: g.ayuda_cobrada, valor: loQueYaEstaba("ayuda-cobrado", "") },
      ],
    };
  }
  return null;
}

/** Guarda lo que haya abierto, con la clase que diga el botón. */
async function guardarLasCuentas(datos) {
  const suyo = estadoDeLasCuentas();
  const clase = (datos && datos.clase) || "";
  const id = datos && datos.id ? Number(datos.id) : null;
  const b = suyo.borrador || {};
  const campos = (ids) => {
    const salida = {};
    for (const nombre of ids) salida[nombre] = valorDeLaCasilla(nombre);
    return salida;
  };
  suyo.guardando = true;
  suyo.error = "";
  suyo.aviso = "";
  // **Los campos se leen ANTES de pintar** (06/10/2026). Aquí estaba `pantallaLasCuentas()` primero, y
  // eso vaciaba los campos: `montarEn` limpia el contenedor (`innerHTML = ""`) y React pinta en su
  // siguiente vuelta, así que lo que se leyera entre una cosa y otra era **vacío**. El gasto se mandaba
  // sin concepto ni importe, el servidor lo rechazaba («un gasto tiene que decir qué fue») y el
  // agricultor veía «No se ha podido». Se encontró recorriendo el recorrido 2 en un navegador de
  // verdad, con un grabador delante de la aplicación.
  let ruta = "/api/gastos";
  let cuerpo = {};
  let metodo = "POST";
  if (clase === "gasto") {
    const suyos = campos(["gasto-concepto", "gasto-importe", "gasto-base", "gasto-cuota", "gasto-fecha", "gasto-vencimiento", "gasto-proveedor"]);
    cuerpo = {
      concepto: suyos["gasto-concepto"],
      // **Un importe vacío viaja como `null`**, nunca como 0: es la regla del encargo de punta a punta.
      importe: suyos["gasto-importe"] || null,
      base_imponible: suyos["gasto-base"] || null,
      cuota_iva: suyos["gasto-cuota"] || null,
      fecha: suyos["gasto-fecha"] || null,
      vencimiento: suyos["gasto-vencimiento"] || null,
      proveedor: suyos["gasto-proveedor"],
      categoria: b.categoria || "otro",
      campana_id: estado.campana ? estado.campana.id : null,
      clave_de_reenvio: claveDeReenvio("gasto"),
    };
    if (id) {
      metodo = "PUT";
      ruta = `/api/gastos/${id}`;
      delete cuerpo.clave_de_reenvio;
    }
  } else if (clase === "reparto") {
    metodo = "POST";
    ruta = `/api/gastos/${id}/repartos`;
    // **Lo que se ha escrito en cada tierra** (06/10/2026): las horas, los litros o lo que le toca a
    // cada una. Se lee de los campos que hay en la pantalla —uno por tierra marcada—, y de ahí salen
    // los pesos (para «por horas» y «por lo que se gastó») y los trozos (para «a mano»).
    const marcadas = (b.parcela_ids || []).map(String);
    const escritos = {};
    for (const clave of marcadas) {
      const escrito = valorDeLaCasilla(idDelPesoDelReparto(clave));
      if (escrito !== "") escritos[clave] = escrito;
    }
    const destino = b.destino_tipo || "tierra";
    const aMano = (b.metodo || "") === "manual";
    cuerpo = {
      metodo: b.metodo || "manual",
      destino_tipo: destino,
      // **`parcela_ids` solo cuando se reparte entre tierras**: es la lista de tierras, y para un cultivo
      // o una máquina las cosas que se marcan viajan **por su nombre** en los pesos (o en los trozos, si
      // es a mano), que es lo que el servidor guarda y lo que se lee después en la ficha del gasto.
      parcela_ids: destino === "tierra" ? marcadas : [],
      pesos: aMano ? {} : escritos,
      trozos: aMano
        ? marcadas
            .filter((clave) => escritos[clave] !== undefined)
            .map((clave) => ({ destino_tipo: destino, destino: clave, importe: escritos[clave] }))
        : [],
      confirmado: true,
    };
  } else if (clase === "pago") {
    cuerpo = {
      importe: valorDeLaCasilla("pago-importe"),
      fecha: valorDeLaCasilla("pago-fecha") || null,
      proveedor: valorDeLaCasilla("pago-proveedor"),
      forma: b.forma || "transferencia",
      clave_de_reenvio: claveDeReenvio("pago"),
      aplicaciones: b.aplicaciones || [],
    };
  } else if (clase === "inversion") {
    cuerpo = {
      concepto: valorDeLaCasilla("inversion-concepto"),
      importe: valorDeLaCasilla("inversion-importe") || null,
      fecha: valorDeLaCasilla("inversion-fecha") || null,
      proveedor: valorDeLaCasilla("inversion-proveedor"),
      categoria: b.categoria || "otro",
      campana_id: estado.campana ? estado.campana.id : null,
      clave_de_reenvio: claveDeReenvio("inversion"),
    };
  } else if (clase === "ayuda") {
    cuerpo = {
      concepto: valorDeLaCasilla("ayuda-concepto"),
      organismo: valorDeLaCasilla("ayuda-organismo"),
      importe_previsto: valorDeLaCasilla("ayuda-previsto") || null,
      importe_concedido: valorDeLaCasilla("ayuda-concedido") || null,
      importe_cobrado: valorDeLaCasilla("ayuda-cobrado") || null,
      campana_id: estado.campana ? estado.campana.id : null,
      clave_de_reenvio: claveDeReenvio("ayuda"),
    };
  }
  // Y **ahora sí**: se pinta con lo que se va a guardar ya leído (el botón dice que está guardando).
  pantallaLasCuentas();
  try {
    // **`method` y `body`, no `metodo` y `cuerpo`** (05/10/2026). Aquí ponía `api(ruta, { method: metodo, body: JSON.stringify(cuerpo) })`,
    // y `api` pasa sus opciones tal cual a `fetch`, que solo entiende `method` y `body`: el resultado era
    // **una petición GET sin datos**, así que **el botón de guardar de las cuentas no guardaba nada y no
    // saltaba ningún error**. Lo encontró el subagente de la pantalla de los extractos mientras leía este
    // fichero para escribir su bloque, y es el mismo tipo de fallo que el `campanaActual` que faltaba:
    // código escrito copiando formas, que nadie había ejecutado.
    const respuesta = await api(ruta, { method: metodo, body: JSON.stringify(cuerpo) });
    if (!respuesta.ok) {
      suyo.error = mensaje("no_se_pudo");
    } else {
      const contestado = await respuesta.json();
      suyo.aviso = (contestado.avisos || []).join(" ");
      suyo.formulario = null;
      suyo.borrador = null;
      await recargarLasCuentas();
    }
  } catch (fallo) {
    suyo.error = (fallo && fallo.message) || mensaje("no_se_pudo");
  }
  suyo.guardando = false;
  if (suyo.gasto) {
    await abrirUnGasto(suyo.gasto.id);
  } else {
    pantallaLasCuentas();
  }
}

/** Las 17 acciones de los botones de estas pantallas. */
async function atenderLasCuentas(nombre, elemento) {
  const suyo = estadoDeLasCuentas();
  const g = t("gastos", {});
  const id = Number(elemento.dataset.id || 0);
  if (nombre === "gastos-ver") return abrirLasCuentas();
  if (nombre === "gasto-abrir") return abrirUnGasto(id);
  if (nombre === "bancos-ver") return abrirLosBancos();
  if (nombre === "gastos-ver-todas") {
    suyo.filtro = "";
    return pantallaLasCuentas();
  }
  if (nombre === "gasto-nuevo") {
    suyo.formulario = { clase: "gasto", id: id || null };
    suyo.borrador = {};
    return suyo.gasto ? pantallaUnGasto() : pantallaLasCuentas();
  }
  if (nombre === "gasto-pago-nuevo") {
    suyo.formulario = { clase: "pago" };
    suyo.borrador = { aplicaciones: [] };
    return pantallaLasCuentas();
  }
  if (nombre === "gasto-inversion-nueva") {
    suyo.formulario = { clase: "inversion" };
    suyo.borrador = {};
    return pantallaLasCuentas();
  }
  if (nombre === "gasto-ayuda-nueva") {
    suyo.formulario = { clase: "ayuda" };
    suyo.borrador = {};
    return pantallaLasCuentas();
  }
  if (nombre === "gasto-repartir") {
    suyo.formulario = { clase: "reparto", id };
    // **Lo que se puede marcar para repartir** (06/10/2026, y sus tres clases desde la ronda 9): las
    // tierras, los cultivos o las máquinas ya están descargadas —cada una en su sitio—, así que no hace
    // falta pedir nada al servidor para ofrecerlas. Nace en «tierra», que es lo que se reparte casi
    // siempre; si el agricultor elige cultivo o máquina, se cambia la lista entera (ver `gasto-elegir`).
    suyo.borrador = {
      metodo: "",
      destino_tipo: "tierra",
      parcela_ids: [],
      tierras: lasCosasParaUnReparto("tierra"),
      pesos: [],
    };
    return pantallaUnGasto();
  }
  if (nombre === "gasto-marcar" || nombre === "gasto-marcar-todas") {
    // **Marcar una tierra para el reparto.** Se marcan las que se quieran (y con TODAS, las de la
    // finca). Cada vez que se marca o se desmarca, se rehace la lista de pesos: un campo por tierra
    // marcada, que es donde se escriben las horas, los litros o lo que le toca a cada una.
    const claves = new Set((suyo.borrador || {}).parcela_ids || []);
    if (nombre === "gasto-marcar-todas") {
      for (const tierra of (suyo.borrador || {}).tierras || []) claves.add(String(tierra.clave));
    } else {
      const clave = String(elemento.dataset.clave || "");
      if (!clave) return pantallaUnGasto();
      if (claves.has(clave)) claves.delete(clave);
      else claves.add(clave);
    }
    suyo.borrador = conLasTierrasMarcadas(suyo.borrador, [...claves]);
    return pantallaUnGasto();
  }
  if (nombre === "gasto-sin-asignar") {
    suyo.guardando = true;
    pantallaUnGasto();
    try {
      const respuesta = await api(`/api/gastos/${id}/sin-asignar`, {
        metodo: "POST",
        cuerpo: { porque: "no_se_reparte_porque_no_ha_dicho_el_metodo" },
      });
      const contestado = await respuesta.json();
      suyo.gasto = contestado.gasto;
      suyo.aviso = (contestado.avisos || []).join(" ");
    } catch (fallo) {
      suyo.error = (fallo && fallo.message) || mensaje("no_se_pudo");
    }
    suyo.guardando = false;
    return pantallaUnGasto();
  }
  if (nombre === "gasto-reparto-quitar") {
    const reparto = Number(elemento.dataset.reparto || 0);
    try {
      const respuesta = await api(`/api/gastos/${id}/repartos/${reparto}`, { metodo: "DELETE" });
      const contestado = await respuesta.json();
      suyo.gasto = contestado.gasto;
      suyo.aviso = (contestado.avisos || []).join(" ");
    } catch (fallo) {
      suyo.error = (fallo && fallo.message) || mensaje("no_se_pudo");
    }
    return pantallaUnGasto();
  }
  if (nombre === "gasto-elegir") {
    // **El borrador vive aquí y no en el DOM**: al repintar se perdería, y el agricultor tendría que
    // volver a elegir lo que ya había elegido.
    const campo = elemento.dataset.campo || "";
    const valor = elemento.dataset.valor || "";
    const antes = suyo.borrador || {};
    // **Cambiar de destino cambia lo que se marca** (ronda 9): las tierras, los cultivos y las máquinas
    // no comparten ni un nombre, así que lo marcado antes no vale para el destino nuevo y se empieza de
    // cero con **sus** cosas. Si no, quedarían marcadas tierras mientras el reparto dice «máquina», que
    // es el defecto que se arregló en el servidor: aquí se evita antes de llegar.
    if (campo === "destino_tipo" && valor !== antes.destino_tipo) {
      // **Y las máquinas hay que traerlas**: no se descargan al arrancar (ver
      // `cargarLasMaquinasSiHacenFalta`), así que sin esto el destino «máquina» saldría con la lista
      // vacía y el agricultor creería que no tiene ninguna.
      if (valor === "maquina") await cargarLasMaquinasSiHacenFalta();
      suyo.borrador = {
        ...antes,
        destino_tipo: valor,
        parcela_ids: [],
        tierras: lasCosasParaUnReparto(valor),
        pesos: [],
        // Y el método también se limpia si el que estaba ya no se ofrece (las hectáreas, para cultivos y
        // máquinas): un método elegido que no está en la lista no puede quedar escondido en el borrador.
        metodo: losMetodosDelReparto(valor).some((uno) => uno.valor === antes.metodo) ? antes.metodo : "",
      };
      return suyo.gasto ? pantallaUnGasto() : pantallaLasCuentas();
    }
    suyo.borrador = { ...antes, [campo]: valor };
    return suyo.gasto ? pantallaUnGasto() : pantallaLasCuentas();
  }
  if (nombre === "gasto-guardar") return guardarLasCuentas(elemento.dataset);
  if (nombre === "gasto-cancelar") {
    suyo.formulario = null;
    suyo.borrador = null;
    suyo.anulando = null;
    suyo.error = "";
    return suyo.gasto ? pantallaUnGasto() : pantallaLasCuentas();
  }
  if (nombre === "gasto-anular") {
    const clase = elemento.dataset.clase || "gasto";
    suyo.anulando = {
      titulo: `${g.anular} · ${clase === "pago" ? g.pagos_titulo : g.titulo}`,
      pista: g.anular_motivo,
      id: "gasto-motivo-anulacion",
      confirmar: g.anular_confirmar,
      cancelar: g.cancelar,
      datos: { id, clase },
      error: "",
    };
    return suyo.gasto ? pantallaUnGasto() : pantallaLasCuentas();
  }
  if (nombre === "gasto-anular-confirmar") {
    // **Sin motivo no se anula**: dentro de un año, ese motivo es lo único que explicará por qué está
    // tachado. El servidor también lo exige; aquí se dice antes para no hacer el viaje.
    const motivo = (valorDeLaCasilla("gasto-motivo-anulacion") || "").trim();
    if (!motivo) {
      suyo.anulando.error = mensaje("G22_para_anular_hace_falta_el_motivo");
      return suyo.gasto ? pantallaUnGasto() : pantallaLasCuentas();
    }
    const clase = elemento.dataset.clase || "gasto";
    const rutaBase =
      clase === "pago"
        ? `/api/gastos/pagos/${id}/anular`
        : clase === "inversion"
          ? `/api/gastos/inversiones/${id}/anular`
          : clase === "ayuda"
            ? `/api/gastos/subvenciones/${id}/anular`
            : `/api/gastos/${id}/anular`;
    try {
      const respuesta = await api(rutaBase, { metodo: "POST", cuerpo: { motivo } });
      const contestado = await respuesta.json();
      suyo.aviso = (contestado.avisos || []).join(" ");
      suyo.anulando = null;
      if (clase === "gasto" && contestado.gasto) suyo.gasto = contestado.gasto;
      await recargarLasCuentas();
    } catch (fallo) {
      suyo.error = (fallo && fallo.message) || mensaje("no_se_pudo");
    }
    return suyo.gasto && clase === "gasto" ? pantallaUnGasto() : pantallaLasCuentas();
  }
  if (nombre === "gasto-pago-conciliar") {
    // **Conciliar un pago no crea un gasto**: se dice contra qué va y ya está. Se reparte solo, por
    // orden y el más antiguo primero, que es la regla de cualquier cuenta corriente.
    const deudos = (suyo.datos.gastos || [])
      .filter((gasto) => gasto.pendiente && Number(gasto.pendiente) > 0)
      .map((gasto) => gasto.id);
    try {
      const respuesta = await api(`/api/gastos/pagos/${id}/conciliar`, {
        metodo: "POST",
        cuerpo: { automatico: true, gastos: deudos, aplicaciones: [] },
      });
      const contestado = await respuesta.json();
      suyo.aviso = (contestado.avisos || []).join(" ");
      await recargarLasCuentas();
    } catch (fallo) {
      suyo.error = (fallo && fallo.message) || mensaje("no_se_pudo");
    }
    return pantallaLasCuentas();
  }
  if (nombre === "gasto-pago-deshacer") {
    const aplicacion = Number(elemento.dataset.aplicacion || 0);
    try {
      const respuesta = await api(`/api/gastos/pagos/${id}/aplicaciones/${aplicacion}`, {
        metodo: "DELETE",
      });
      const contestado = await respuesta.json();
      suyo.aviso = (contestado.avisos || []).join(" ");
      await recargarLasCuentas();
      if (suyo.gasto) suyo.gasto = await apiJson(`/api/gastos/${suyo.gasto.id}`);
    } catch (fallo) {
      suyo.error = (fallo && fallo.message) || mensaje("no_se_pudo");
    }
    return suyo.gasto ? pantallaUnGasto() : pantallaLasCuentas();
  }
  return false;
}

// ---------------------------------------------------------------------------
// El extracto del banco y la conciliación (T20, E11, 06/10/2026)
// ---------------------------------------------------------------------------
//
// LO QUE ESTE BLOQUE HACE, Y LO QUE NO. Hace tres cosas y ninguna más:
//
//   1. **Pide los datos** —las cuentas, los movimientos, los papeles pendientes y las propuestas de un
//      movimiento— y se los pasa a la pantalla, que no calcula nada.
//   2. **Sube el fichero** que el agricultor ha elegido: primero a la vista previa (que **no guarda**) y,
//      cuando él lo dice, a la puerta que apunta los movimientos.
//   3. **Lee lo que el agricultor escribe** por los `id` de los campos y lo manda a su puerta.
//
// Lo que **no** hace: ni una cuenta de dinero. Los importes, los cuadres y lo que le queda por cuadrar
// llegan calculados del servidor (son `Decimal` y viajan como texto), y aquí lo único que se hace con
// ellos es **escribirlos** con `enEuros` (que devuelve vacío cuando el dato no consta, y nunca «0,00 €»).
//
// **Y no se conecta ningún banco.** Lo único que entra es el fichero que el agricultor ha subido: no hay
// claves, ni direcciones de banco, ni un sitio donde poner una credencial.

/** El estado de los bancos, creado la primera vez que hace falta (como el de las cuentas). */
function estadoDeLosBancos() {
  if (!estado.bancos) {
    estado.bancos = {
      cuentas: [],
      perfiles: [],
      movimientos: null,
      pendientes: [],
      cuentaElegida: "",
      perfilElegido: "",
      // **El fichero vive aquí y no en la casilla del formulario.** Repintar la pantalla borra el
      // `<input type="file">`, y lo que solo viviera ahí desaparece: es la trampa que ya costó una ronda
      // con el cuaderno de la Junta (ver AGENTS.md). Por eso se guarda al leerlo, que es lo que permite
      // apuntarlo después sin volver a pedírselo al agricultor.
      fichero: null,
      nombreDelFichero: "",
      vistaPrevia: null,
      resultado: null,
      leyendo: false,
      importando: false,
      filtro: "",
      estado: "",
      formulario: null,
      borrador: null,
      guardando: false,
      error: "",
      aviso: "",
      movimiento: null,
      propuestas: null,
      conciliado: null,
      deshecho: false,
      deshacer: false,
      correccion: null,
    };
  }
  return estado.bancos;
}

/** El vocabulario de esta pantalla: el del banco y el botón de VOLVER que ya está en los textos. */
function textosDeLosBancos() {
  return {
    bancos: t("bancos", {}),
    acciones: accion("volver") ? { volver: accion("volver") } : {},
  };
}

/**
 * Los importes de una respuesta, **escritos**, para que la pantalla no tenga que calcular nada.
 *
 * La API del banco manda los importes como texto decimal exacto («500.00»), que es lo correcto para
 * guardarlos y **no** es lo que se lee: el agricultor lee «500,00 €». Escribirlos aquí, con `enEuros` y
 * `formateaFecha`, deja el formateo del dinero en **un solo sitio** —el que ya usa toda la aplicación— y
 * hace que la pantalla sea tonta a propósito: no puede sumar, ni redondear, ni enseñar un `0,00 €` donde
 * el dato no consta (`enEuros` devuelve vacío).
 *
 * Se recorre **entero** y por eso no hay que acordarse de ningún campo: el día que la API devuelva un
 * importe nuevo, ya viene escrito.
 */
const CAMPOS_DE_DINERO_DEL_BANCO = [
  "importe",
  "saldo",
  "saldo_final",
  "imputado",
  "por_conciliar",
  "pendiente",
  "total",
  "sobrante",
  "entradas",
  "salidas",
];

function conLosImportesEscritos(valor) {
  if (Array.isArray(valor)) return valor.map(conLosImportesEscritos);
  if (valor && typeof valor === "object") {
    const copia = {};
    for (const [clave, dato] of Object.entries(valor)) copia[clave] = conLosImportesEscritos(dato);
    for (const clave of CAMPOS_DE_DINERO_DEL_BANCO) {
      // `texto_<campo>` es lo que enseña la pantalla. Cuando el dato no consta, `enEuros` devuelve
      // **vacío**, y la pantalla escribe su palabra («No consta», «No lo sé»): nunca un cero.
      if (clave in valor) copia[`texto_${clave}`] = enEuros(valor[clave]);
    }
    if ("fecha" in valor) copia.texto_fecha = valor.fecha ? formateaFecha(valor.fecha) : "";
    if ("vencimiento" in valor) {
      copia.texto_vencimiento = valor.vencimiento ? formateaFecha(valor.vencimiento) : "";
    }
    return copia;
  }
  return valor;
}

/** Abre «el banco y los papeles»: se pinta enseguida y se vuelve a pintar con lo que contesta el servidor. */
async function abrirLosBancos() {
  const suyo = estadoDeLosBancos();
  suyo.error = "";
  suyo.aviso = "";
  suyo.formulario = null;
  suyo.borrador = null;
  suyo.vistaPrevia = null;
  suyo.resultado = null;
  pantallaLosBancos();
  await recargarLosBancos();
  pantallaLosBancos();
}

/** Vuelve a pedir las cuentas, los movimientos y los papeles pendientes. */
async function recargarLosBancos() {
  const suyo = estadoDeLosBancos();
  try {
    const cuentas = await apiJson("/api/bancos/cuentas");
    suyo.cuentas = (cuentas || []).map((cuenta) => ({
      valor: cuenta.id,
      texto: [cuenta.nombre, cuenta.ultimos_digitos ? `·${cuenta.ultimos_digitos}` : ""]
        .filter(Boolean)
        .join(" "),
    }));
    if (!suyo.cuentaElegida && suyo.cuentas.length) suyo.cuentaElegida = suyo.cuentas[0].valor;
    const perfiles = await apiJson("/api/bancos/perfiles");
    suyo.perfiles = (perfiles || []).map((perfil) => ({ valor: perfil.id, texto: perfil.nombre }));
    const consulta = new URLSearchParams();
    if (suyo.cuentaElegida) consulta.set("cuenta_id", suyo.cuentaElegida);
    if (suyo.filtro) consulta.set("texto", suyo.filtro);
    if (suyo.estado) consulta.set("estado", suyo.estado);
    const suyos = consulta.toString();
    suyo.movimientos = conLosImportesEscritos(
      await apiJson(`/api/bancos/movimientos${suyos ? `?${suyos}` : ""}`),
    );
    suyo.pendientes = conLosImportesEscritos(await apiJson("/api/bancos/pendientes"));
    suyo.error = "";
  } catch (fallo) {
    suyo.error = (fallo && fallo.message) || mensaje("no_se_pudo");
  }
  return suyo;
}

/** La lista del banco, ya en React. */
function pantallaLosBancos() {
  const suyo = estadoDeLosBancos();
  const movimientos = (suyo.movimientos && suyo.movimientos.items) || [];
  const cuantos = (suyo.movimientos && suyo.movimientos.total) || 0;
  return montar(() =>
    pantallaDeLosBancos({
      textos: textosDeLosBancos(),
      cuentas: suyo.cuentas,
      perfiles: suyo.perfiles,
      cuentaElegida: suyo.cuentaElegida,
      perfilElegido: suyo.perfilElegido,
      ficheroElegido: suyo.nombreDelFichero,
      leyendo: suyo.leyendo,
      importando: suyo.importando,
      guardando: suyo.guardando,
      vistaPrevia: suyo.vistaPrevia,
      resultado: suyo.resultado,
      movimientos,
      agregados: (suyo.movimientos && suyo.movimientos.agregados) || {},
      // El singular y el plural con las dos formas del servidor (`conCuenta` elige `<base>_uno` cuando es
      // uno): «Tienes 1 movimientos» es lo primero que hace desconfiar de un programa.
      resumen: cuantos ? conCuenta(t("tabla", {}), "bancos_resumen", cuantos) : "",
      tabla: tablaDeLosMovimientos(movimientos),
      filtro: suyo.filtro,
      estado: suyo.estado,
      pendientes: suyo.pendientes,
      formulario: elFormularioDeLosBancos(suyo.formulario, suyo.borrador),
      error: suyo.error || "",
      aviso: suyo.aviso || "",
    }),
  );
}

/** La tabla del ordenador: una celda menos que columnas (la última, «Acciones», la pone la pieza). */
function tablaDeLosMovimientos(movimientos) {
  const b = t("bancos", {});
  const col = (clave) => t(`tabla.bancos_${clave}`, "");
  const columnas = [
    { texto: col("fecha"), campo: "fecha" },
    { texto: col("concepto") },
    { texto: col("cuenta") },
    { texto: col("importe") },
    { texto: col("estado") },
    { texto: col("por_conciliar") },
    { texto: t("tabla.acciones", "") },
  ];
  const filas = (movimientos || []).map((movimiento) => ({
    celdas: [
      { texto: movimiento.texto_fecha },
      { texto: movimiento.concepto, accion: "banco-abrir", datos: { id: movimiento.id } },
      { texto: movimiento.cuenta || b.no_consta },
      // **Un importe que no consta se enseña con su palabra, no con un cero.**
      {
        texto:
          movimiento.importe === null || movimiento.importe === undefined
            ? b.no_consta
            : movimiento.texto_importe,
      },
      { texto: b[`estado_${movimiento.estado}`] },
      {
        texto:
          movimiento.por_conciliar === null || movimiento.por_conciliar === undefined
            ? b.no_se_sabe
            : movimiento.texto_por_conciliar,
      },
    ],
    acciones: [
      {
        etiqueta: col("abrir"),
        accion: "banco-abrir",
        datos: { id: movimiento.id },
        clase: "boton-claro",
      },
    ],
  }));
  if (!filas.length) return null;
  return {
    clave: "bancos",
    etiqueta: t("tabla.bancos_etiqueta", ""),
    columnas,
    filas,
    resumen: "",
  };
}

/**
 * Abre la ficha de un movimiento: **pide sus propuestas al servidor**.
 *
 * Es lo que hace que esta pantalla se pueda enlazar y recargar: no vive de la lista que había antes, pide
 * sus datos a su puerta. Si esa puerta no contesta (sin cobertura), se dice **que no se ha podido
 * comprobar**, que no es lo mismo que decir que ese movimiento no está.
 */
async function abrirUnMovimientoDelBanco(id) {
  const suyo = estadoDeLosBancos();
  if (!id) return abrirLosBancos();
  suyo.movimiento = null;
  suyo.propuestas = null;
  suyo.conciliado = null;
  suyo.deshacer = false;
  suyo.correccion = null;
  suyo.error = "";
  suyo.aviso = "";
  pantallaUnMovimientoDelBanco();
  try {
    const datos = conLosImportesEscritos(await apiJson(`/api/bancos/movimientos/${id}/propuestas`));
    suyo.propuestas = datos;
    suyo.movimiento = datos.movimiento;
  } catch (fallo) {
    suyo.error = (fallo && fallo.message) || mensaje("no_se_pudo");
  }
  pantallaUnMovimientoDelBanco();
}

/** La ficha de un movimiento, ya en React. */
function pantallaUnMovimientoDelBanco() {
  const suyo = estadoDeLosBancos();
  const suyo2 = suyo.propuestas || {};
  const movimiento = suyo.movimiento || {};
  const pendientes = suyo2.pendientes || [];
  return montar(() =>
    pantallaDeUnMovimiento({
      textos: textosDeLosBancos(),
      movimiento,
      propuestas: suyo2.propuestas || [],
      pendientes,
      papeles: losPapelesParaElegir(pendientes),
      parejas: lasParejasDelTraspaso(movimiento),
      formulario: elFormularioDeLosBancos(suyo.correccion, suyo.borrador),
      resultado: suyo.conciliado,
      deshecho: suyo.deshacer,
      yaApuntado: suyo2.texto_ya_apuntado || "",
      guardando: suyo.guardando,
      cargando: !suyo.movimiento && !suyo.error,
      error: suyo.error || "",
      aviso: suyo.aviso || "",
    }),
  );
}

/** Los papeles a los que se puede apuntar dinero, para el desplegable de «apuntarlo a mano». */
function losPapelesParaElegir(pendientes) {
  const b = t("bancos", {});
  return (pendientes || []).map((papel) => ({
    valor: `${papel.clase}:${papel.documento_id}`,
    texto: [papel.que_es, papel.contraparte, papel.referencia, `${b.le_falta} ${papel.texto_pendiente}`]
      .filter(Boolean)
      .join(" · "),
  }));
}

/**
 * Los movimientos de **otras cuentas tuyas**, para atar un traspaso (A07).
 *
 * Lo que se filtra aquí es solo «de otra cuenta»: **el resto lo comprueba el servidor** y lo dice con su
 * frase («tienen que ser del mismo importe y uno tiene que entrar y el otro salir»). Filtrar el importe en
 * el navegador sería comparar dinero donde no toca; que decida quien tiene el dato.
 */
function lasParejasDelTraspaso(movimiento) {
  const suyo = estadoDeLosBancos();
  const items = (suyo.movimientos && suyo.movimientos.items) || [];
  return items
    .filter((otro) => otro.id !== movimiento.id && otro.cuenta_id !== movimiento.cuenta_id)
    .map((otro) => ({
      valor: otro.id,
      texto: [otro.texto_fecha, otro.concepto, otro.texto_importe].filter(Boolean).join(" · "),
    }));
}

/** El formulario que esté abierto, con sus bloques: el alta de una cuenta, el perfil o la corrección. */
function elFormularioDeLosBancos(cual, borrador) {
  if (!cual) return null;
  const b = t("bancos", {});
  const br = borrador || {};
  const opcionesDe = (lista, elegido) =>
    (lista || []).map((uno) => ({ valor: uno.valor, texto: uno.texto, elegido: uno.valor === elegido }));
  const base = {
    guardar: b.guardar,
    cancelar: b.cancelar,
    guardando: b.guardando,
    datos: { clase: cual.clase, id: cual.id || "" },
    bloques: [],
  };
  if (cual.clase === "cuenta") {
    return {
      ...base,
      titulo: b.form_cuenta_titulo,
      pista: b.form_cuenta_pista,
      bloques: [
        { tipo: "texto", id: "banco-cuenta-nombre", etiqueta: b.cuenta_nombre, pista: b.cuenta_nombre_pista, valor: "" },
        { tipo: "texto", id: "banco-cuenta-banco", etiqueta: b.cuenta_banco, pista: b.cuenta_banco_pista, valor: "" },
        { tipo: "texto", id: "banco-cuenta-ultimos", etiqueta: b.cuenta_ultimos, pista: b.cuenta_ultimos_pista, valor: "" },
      ],
    };
  }
  if (cual.clase === "perfil") {
    return {
      ...base,
      titulo: b.form_perfil_titulo,
      pista: b.form_perfil_pista,
      bloques: [
        { tipo: "texto", id: "banco-perfil-nombre", etiqueta: b.perfil_nombre, pista: b.perfil_nombre_pista, valor: "" },
        {
          tipo: "opciones",
          campo: "formato_de_fecha",
          etiqueta: b.perfil_fecha,
          elegido: br.formato_de_fecha || "",
          opciones: opcionesDe([
            { valor: "d/m/Y", texto: b.fecha_dmy },
            { valor: "m/d/Y", texto: b.fecha_mdy },
          ], br.formato_de_fecha),
        },
        {
          tipo: "opciones",
          campo: "decimal",
          etiqueta: b.perfil_decimal,
          elegido: br.decimal || "",
          opciones: opcionesDe([
            { valor: ",", texto: b.decimal_coma },
            { valor: ".", texto: b.decimal_punto },
          ], br.decimal),
        },
        {
          tipo: "opciones",
          campo: "sin_signo_quiere_decir",
          etiqueta: b.perfil_sin_signo,
          elegido: br.sin_signo_quiere_decir || "",
          opciones: opcionesDe([
            { valor: "entra", texto: b.sin_signo_entra },
            { valor: "sale", texto: b.sin_signo_sale },
          ], br.sin_signo_quiere_decir),
        },
      ],
    };
  }
  if (cual.clase === "correccion") {
    return {
      ...base,
      titulo: b.form_correccion_titulo,
      pista: b.form_correccion_pista,
      bloques: [
        { tipo: "numero", id: "banco-importe", etiqueta: b.correccion_importe, pista: b.correccion_importe_pista, valor: "" },
        {
          tipo: "opciones",
          campo: "signo",
          etiqueta: b.correccion_signo,
          elegido: br.signo || "",
          opciones: opcionesDe([
            { valor: "entra", texto: b.signo_entra },
            { valor: "sale", texto: b.signo_sale },
          ], br.signo),
        },
        { tipo: "texto", id: "banco-concepto", etiqueta: b.correccion_concepto, valor: "" },
        { tipo: "texto", id: "banco-motivo", etiqueta: b.correccion_motivo, pista: b.correccion_motivo_pista, valor: "" },
      ],
    };
  }
  return null;
}

/** Lee el extracto **sin guardar nada**: el fichero, la cuenta y (si la hay) la forma de escribir. */
async function leerElExtracto() {
  const suyo = estadoDeLosBancos();
  const casilla = document.getElementById("banco-fichero");
  const cuenta = valorDeLaCasilla("banco-cuenta");
  suyo.error = "";
  suyo.aviso = "";
  if (!casilla || !casilla.files || !casilla.files.length) {
    suyo.error = t("bancos.fichero", "");
    return pantallaLosBancos();
  }
  if (!cuenta) {
    suyo.error = t("bancos.elige_la_cuenta", "");
    return pantallaLosBancos();
  }
  // Sin cobertura no se puede subir un fichero de un tirón: se dice claro en vez de dejar al agricultor
  // esperando una barra que no avanza.
  if (!navigator.onLine) {
    suyo.error = aviso("no_se_pudo");
    return pantallaLosBancos();
  }
  // **El fichero se guarda antes de pintar**: repintar borra la casilla, y este objeto es lo único que
  // queda del fichero que el agricultor ha elegido.
  suyo.fichero = casilla.files[0];
  suyo.nombreDelFichero = casilla.files[0].name || "";
  suyo.cuentaElegida = cuenta;
  suyo.leyendo = true;
  pantallaLosBancos();
  const cuerpo = new FormData();
  cuerpo.append("fichero", suyo.fichero);
  cuerpo.append("cuenta_id", cuenta);
  if (suyo.perfilElegido) cuerpo.append("perfil_id", suyo.perfilElegido);
  try {
    const respuesta = await fetch("/api/bancos/extractos/vista-previa", {
      method: "POST",
      headers: { Authorization: `Bearer ${estado.token}` },
      body: cuerpo,
    });
    if (!respuesta.ok) {
      const detalle = await respuesta.json().catch(() => null);
      throw new Error((detalle && detalle.detail) || mensaje("no_se_pudo"));
    }
    suyo.vistaPrevia = conLosImportesEscritos(await respuesta.json());
    suyo.resultado = null;
  } catch (fallo) {
    suyo.error = (fallo && fallo.message) || mensaje("no_se_pudo");
  }
  suyo.leyendo = false;
  pantallaLosBancos();
}

/**
 * Apunta los movimientos del extracto. **Solo se llega aquí pulsando APUNTAR ESTOS MOVIMIENTOS**: leer no
 * ha guardado nada, y el fichero que se manda es **el que se guardó al leerlo** (la casilla ya no existe).
 */
async function importarElExtracto() {
  const suyo = estadoDeLosBancos();
  if (!suyo.fichero || !suyo.cuentaElegida) return leerElExtracto();
  suyo.importando = true;
  suyo.error = "";
  suyo.aviso = "";
  pantallaLosBancos();
  const cuerpo = new FormData();
  cuerpo.append("fichero", suyo.fichero);
  cuerpo.append("cuenta_id", suyo.cuentaElegida);
  if (suyo.perfilElegido) cuerpo.append("perfil_id", suyo.perfilElegido);
  // **La clave de reenvío**: reenviar la misma subida (el móvil sin cobertura) devuelve lo que pasó la
  // primera vez y **no apunta nada dos veces**.
  if (!suyo.claveDeLaSubida) suyo.claveDeLaSubida = claveDeReenvio("extracto");
  cuerpo.append("clave_de_reenvio", suyo.claveDeLaSubida);
  try {
    const respuesta = await fetch("/api/bancos/extractos/importar", {
      method: "POST",
      headers: { Authorization: `Bearer ${estado.token}` },
      body: cuerpo,
    });
    if (!respuesta.ok) {
      const detalle = await respuesta.json().catch(() => null);
      throw new Error((detalle && detalle.detail) || mensaje("no_se_pudo"));
    }
    suyo.resultado = conLosImportesEscritos(await respuesta.json());
    suyo.vistaPrevia = null;
    suyo.fichero = null;
    suyo.nombreDelFichero = "";
    suyo.claveDeLaSubida = null;
    await recargarLosBancos();
  } catch (fallo) {
    suyo.error = (fallo && fallo.message) || mensaje("no_se_pudo");
  }
  suyo.importando = false;
  pantallaLosBancos();
}

/** Baja el extracto en un fichero, como `sacarDatos()`: con el token y por un enlace de descarga.
 *
 * **Con los filtros que el agricultor tiene puestos en la pantalla** (06/10/2026). Antes solo mandaba la
 * cuenta, así que quien filtraba por texto o por estado —y veía, por ejemplo, 10 movimientos— pulsaba
 * EXPORTAR y se llevaba **todo el extracto**, sin que nada lo dijera. Es justo lo que el encargo llama
 * «no debe exportar silenciosamente las 64»: el fichero tiene que ser **lo que se está viendo**.
 */
async function exportarElExtracto() {
  const suyo = estadoDeLosBancos();
  try {
    const partes = [];
    if (suyo.cuentaElegida) partes.push(`cuenta_id=${suyo.cuentaElegida}`);
    if (suyo.filtro) partes.push(`texto=${encodeURIComponent(suyo.filtro)}`);
    if (suyo.estado) partes.push(`estado=${encodeURIComponent(suyo.estado)}`);
    const consulta = partes.length ? `?${partes.join("&")}` : "";
    const respuesta = await api(`/api/bancos/movimientos.csv${consulta}`);
    if (!respuesta.ok) throw new Error(mensaje("no_se_pudo"));
    const blob = await respuesta.blob();
    const enlace = document.createElement("a");
    enlace.href = URL.createObjectURL(blob);
    enlace.download = "extracto.csv";
    document.body.appendChild(enlace);
    enlace.click();
    enlace.remove();
  } catch (fallo) {
    avisarDelError(fallo.message);
  }
}

/** Guarda lo que haya abierto: la cuenta, la forma de escribir del banco o la corrección de un importe. */
async function guardarLosBancos(datos) {
  const suyo = estadoDeLosBancos();
  const clase = (datos && datos.clase) || "";
  const id = datos && datos.id ? Number(datos.id) : null;
  const br = suyo.borrador || {};
  suyo.guardando = true;
  suyo.error = "";
  suyo.aviso = "";
  pantallaLosBancos();
  try {
    if (clase === "cuenta") {
      await apiJson("/api/bancos/cuentas", {
        method: "POST",
        body: JSON.stringify({
          nombre: valorDeLaCasilla("banco-cuenta-nombre"),
          banco: valorDeLaCasilla("banco-cuenta-banco") || null,
          // Solo los cuatro últimos: el servidor los recorta otra vez, y aquí se dice para que se vea
          // que el número entero no viaja.
          ultimos_digitos: valorDeLaCasilla("banco-cuenta-ultimos") || null,
          clave_de_reenvio: claveDeReenvio("cuenta"),
        }),
      });
    } else if (clase === "perfil") {
      await apiJson("/api/bancos/perfiles", {
        method: "POST",
        body: JSON.stringify({
          nombre: valorDeLaCasilla("banco-perfil-nombre"),
          cuenta_id: suyo.cuentaElegida || null,
          formato_de_fecha: br.formato_de_fecha || null,
          decimal: br.decimal || null,
          sin_signo_quiere_decir: br.sin_signo_quiere_decir || null,
        }),
      });
    } else if (clase === "correccion") {
      const importe = valorDeLaCasilla("banco-importe");
      await apiJson(`/api/bancos/movimientos/${id}`, {
        method: "PUT",
        body: JSON.stringify({
          // **Un importe vacío viaja como `null`** («déjalo en no lo sé»), nunca como 0.
          importe: importe || null,
          signo: br.signo || null,
          concepto: valorDeLaCasilla("banco-concepto") || null,
          motivo: valorDeLaCasilla("banco-motivo") || null,
        }),
      });
    }
    suyo.formulario = null;
    suyo.correccion = null;
    suyo.borrador = null;
    await recargarLosBancos();
    if (suyo.movimiento) await abrirUnMovimientoDelBanco(suyo.movimiento.id);
  } catch (fallo) {
    suyo.error = (fallo && fallo.message) || mensaje("no_se_pudo");
  }
  suyo.guardando = false;
  if (suyo.movimiento) {
    pantallaUnMovimientoDelBanco();
  } else {
    pantallaLosBancos();
  }
}

/**
 * Cuadra un movimiento contra los papeles que el agricultor ha elegido.
 *
 * **Las imputaciones son las suyas, no las nuestras**: cuando pulsa APUNTAR ESTA se mandan **las de esa
 * propuesta, tal cual y en el orden del servidor** (el botón lleva su índice, y aquí se busca en la misma
 * lista que se le enseñó); y cuando apunta a mano se manda **un** papel, con la cantidad que haya escrito
 * o con `importe: null`, que es «reparte tú lo que quepa, del papel más antiguo al más nuevo».
 */
async function conciliarUnMovimiento(imputaciones) {
  const suyo = estadoDeLosBancos();
  if (!suyo.movimiento || !imputaciones.length) return;
  suyo.guardando = true;
  suyo.error = "";
  suyo.aviso = "";
  pantallaUnMovimientoDelBanco();
  try {
    const contestado = conLosImportesEscritos(
      await apiJson(`/api/bancos/movimientos/${suyo.movimiento.id}/conciliar`, {
        method: "POST",
        body: JSON.stringify({ imputaciones }),
      }),
    );
    suyo.movimiento = contestado.movimiento;
    await abrirUnMovimientoDelBanco(suyo.movimiento.id);
    // **El resultado se guarda DESPUÉS de recargar la ficha, y no antes.** `abrirUnMovimientoDelBanco`
    // limpia `conciliado` a propósito —al abrir un movimiento de cero no hay nada que contar—, así que
    // guardarlo antes lo borraba: el agricultor apuntaba el dinero y no veía **a qué papel** había ido,
    // que es justo lo que hay que poder comprobar para no apuntarlo dos veces. Hay una prueba que lo
    // comprueba en `tests_js/interfaz.test.js`.
    suyo.conciliado = contestado;
    suyo.deshacer = false;
  } catch (fallo) {
    suyo.error = (fallo && fallo.message) || mensaje("no_se_pudo");
  }
  suyo.guardando = false;
  pantallaUnMovimientoDelBanco();
}

/** Las 20 acciones de los botones de estas dos pantallas. */
async function atenderLosBancos(nombre, elemento) {
  const suyo = estadoDeLosBancos();
  const id = Number(elemento.dataset.id || 0);
  if (nombre === "banco-ver") return pantallaLosBancos();
  if (nombre === "banco-leer") return leerElExtracto();
  if (nombre === "banco-importar") return importarElExtracto();
  if (nombre === "banco-exportar") return exportarElExtracto();
  if (nombre === "banco-abrir") return abrirUnMovimientoDelBanco(id);
  if (nombre === "banco-cuenta-nueva") {
    suyo.formulario = { clase: "cuenta" };
    suyo.borrador = {};
    return pantallaLosBancos();
  }
  if (nombre === "banco-perfil-nuevo") {
    suyo.formulario = { clase: "perfil" };
    suyo.borrador = {};
    return pantallaLosBancos();
  }
  if (nombre === "banco-guardar") return guardarLosBancos(elemento.dataset);
  if (nombre === "banco-cancelar") {
    suyo.formulario = null;
    suyo.correccion = null;
    suyo.borrador = null;
    return suyo.movimiento ? pantallaUnMovimientoDelBanco() : pantallaLosBancos();
  }
  if (nombre === "banco-elegir") {
    suyo.borrador = { ...(suyo.borrador || {}), [elemento.dataset.campo]: elemento.dataset.valor };
    return suyo.movimiento && suyo.correccion
      ? pantallaUnMovimientoDelBanco()
      : pantallaLosBancos();
  }
  if (nombre === "banco-descartar") {
    suyo.vistaPrevia = null;
    suyo.fichero = null;
    suyo.nombreDelFichero = "";
    suyo.claveDeLaSubida = null;
    return pantallaLosBancos();
  }
  if (nombre === "banco-buscar") {
    suyo.filtro = valorDeLaCasilla("banco-buscar");
    suyo.estado = valorDeLaCasilla("banco-estado");
    await recargarLosBancos();
    return pantallaLosBancos();
  }
  if (nombre === "banco-ver-todos") {
    suyo.filtro = "";
    suyo.estado = "";
    await recargarLosBancos();
    return pantallaLosBancos();
  }
  if (nombre === "banco-conciliar-propuesta") {
    const indice = Number(elemento.dataset.indice || 0);
    const propuesta = ((suyo.propuestas || {}).propuestas || [])[indice];
    if (!propuesta) return pantallaUnMovimientoDelBanco();
    return conciliarUnMovimiento(propuesta.imputaciones);
  }
  if (nombre === "banco-conciliar-a-mano") {
    const elegido = valorDeLaCasilla("banco-papel");
    if (!elegido) return pantallaUnMovimientoDelBanco();
    const corte = elegido.indexOf(":");
    const cantidad = valorDeLaCasilla("banco-cantidad");
    return conciliarUnMovimiento([
      {
        clase: elegido.slice(0, corte),
        documento_id: Number(elegido.slice(corte + 1)),
        // Vacío es «reparte tú lo que quepa», que es lo que hace el servidor por orden.
        importe: cantidad || null,
      },
    ]);
  }
  if (nombre === "banco-deshacer") {
    suyo.guardando = true;
    suyo.error = "";
    suyo.aviso = "";
    pantallaUnMovimientoDelBanco();
    try {
      const contestado = conLosImportesEscritos(
        await apiJson(`/api/bancos/movimientos/${id}/desconciliar`, {
          method: "POST",
          body: JSON.stringify({ imputaciones: [] }),
        }),
      );
      suyo.movimiento = contestado.movimiento;
      await abrirUnMovimientoDelBanco(id);
      // Igual que al conciliar: el resultado va **después** de recargar, porque la recarga lo limpia.
      suyo.conciliado = contestado;
      suyo.deshacer = true;
    } catch (fallo) {
      suyo.error = (fallo && fallo.message) || mensaje("no_se_pudo");
    }
    suyo.guardando = false;
    return pantallaUnMovimientoDelBanco();
  }
  if (nombre === "banco-traspaso-atar" || nombre === "banco-traspaso-quitar") {
    const otro = nombre === "banco-traspaso-quitar" ? null : Number(valorDeLaCasilla("banco-pareja"));
    if (nombre === "banco-traspaso-atar" && !otro) return pantallaUnMovimientoDelBanco();
    suyo.guardando = true;
    suyo.error = "";
    pantallaUnMovimientoDelBanco();
    try {
      const contestado = conLosImportesEscritos(
        await apiJson(`/api/bancos/movimientos/${id}/traspaso`, {
          method: "POST",
          body: JSON.stringify({ otro_movimiento_id: otro }),
        }),
      );
      suyo.aviso = (contestado.avisos || []).join(" ");
      suyo.movimiento = contestado.movimiento;
      await abrirUnMovimientoDelBanco(id);
    } catch (fallo) {
      suyo.error = (fallo && fallo.message) || mensaje("no_se_pudo");
    }
    suyo.guardando = false;
    return pantallaUnMovimientoDelBanco();
  }
  if (nombre === "banco-corregir") {
    suyo.correccion = { clase: "correccion", id };
    suyo.borrador = {};
    return pantallaUnMovimientoDelBanco();
  }
}

// ---------------------------------------------------------------------------
// Los trabajos por tierra (T15, E9, 05/10/2026)
// ---------------------------------------------------------------------------
//
// LO QUE ESTE BLOQUE HACE, Y LO QUE NO. Hace lo mismo que el de las cuentas: pide los datos, recoge lo
// que el agricultor escribe y atiende las doce acciones de sus botones.
//
// **Y aquí sí hay una cosa que no hace ningún otro bloque: montar las frases de cada línea.** El
// servidor devuelve los trabajos en crudo (`{tipo, subtipo, fecha_prevista, dias_que_faltan…}`) y la
// pantalla espera la línea ya escrita («Laboreo · cultivador», «20/04/2026 · Faltan 19 días.»). Esa
// composición se hace **con las palabras del servidor y ninguna escrita aquí**: los rótulos salen de
// `textos.agenda` (los mismos que la pantalla usa para sus campos) y las frases del aviso, de
// `textos.mensaje` con su código. Lo que el programa no sabe decir todavía **no se dice**: la
// estimación de lo que gastaría un plan (`gastaria`) no se enseña porque no hay frase para decirla sin
// inventarla, y la fecha de un plan que ya pasó se enseña sola, sin contar días hacia atrás.

/** El estado de los trabajos, creado la primera vez que hace falta (como el de las cuentas). */
function estadoDeLosTrabajos() {
  if (!estado.trabajos) {
    estado.trabajos = {
      // Lo que devolvió `GET /api/trabajos`: lo previsto, lo hecho, los reenvíos quitados y los textos.
      datos: null,
      // La historia y el estado de una tierra (`GET /api/trabajos/tierra/<id>`), cuando se abre.
      tierra: null,
      // La ficha que está abierta: `modo` (planificar | reprogramar | hecho | corregir | anular), el
      // identificador del trabajo, lo que va en los campos y si lo que se está anulando es un plan
      // (que se **cancela**, no se anula: son dos puertas distintas y con la misma pantalla).
      formulario: null,
      // El vocabulario de la ficha: los tipos, los aperos y las máquinas de la finca.
      tipos: null,
      subtipos: [],
      maquinas: null,
      // Los envases del almacén, para poder decir de cuál sale lo que se gastó.
      insumos: null,
      cargando: false,
      guardando: false,
      error: "",
      aviso: "",
    };
  }
  return estado.trabajos;
}

/** El vocabulario de estas pantallas: la agenda y los botones que ya existen. */
function textosDeLosTrabajos() {
  return { agenda: t("agenda", {}), acciones: accion("volver") ? { volver: accion("volver") } : {} };
}

/** La tierra de un trabajo, por su nombre: un número de parcela no le dice nada a nadie. */
function laTierraDeUnTrabajo(trabajo) {
  if (!trabajo) return "";
  if (trabajo.grupo_id) return t("agenda.tierra", "");
  if (!trabajo.parcela_id) return "";
  const suya = (estado.parcelas || []).find((una) => Number(una.id) === Number(trabajo.parcela_id));
  return suya ? suya.alias : "";
}

/**
 * Cuándo es un trabajo, escrito.
 *
 * Lo que se dice, y lo que **no**:
 *   · Un trabajo **hecho**: su día, o «sin decir» si no lo tiene. Un trabajo sin fecha no es el más
 *     antiguo, es uno que no se sabe cuándo fue.
 *   · Un trabajo **previsto**: su día y, si el servidor sabe cuántos días faltan, la frase que ya
 *     existe para eso (`V8_faltan_dias`). Si el día ya pasó **no se cuentan días hacia atrás**: se
 *     enseña la fecha y ya está, porque «faltan -3 días» es una frase que no dice nada.
 *   · Un plan **sin día**: «sin decir», que es la respuesta del programa cuando no se sabe.
 */
function cuandoEsUnTrabajo(trabajo) {
  const esPlan = trabajo.de_donde === "previsto";
  const fecha = esPlan ? trabajo.fecha_prevista : trabajo.fecha;
  if (!fecha) return t("agenda.sin_decir", "");
  const elDia = formateaFecha(fecha);
  const dias = Number(trabajo.dias_que_faltan);
  if (esPlan && Number.isFinite(dias) && dias >= 0) {
    return `${elDia} · ${mensaje("V8_faltan_dias", { cuantos: dias })}`;
  }
  return elDia;
}

/** Lo que a un trabajo hecho le falta decir, con la palabra del servidor y sin inventar una frase. */
function loQueLeFaltaAUnTrabajo(trabajo) {
  const a = t("agenda", {}) || {};
  const sinDecir = a.sin_decir || "";
  const faltan = [];
  if (!trabajo.fecha) faltan.push(`${a.dia} · ${sinDecir}`);
  if (trabajo.superficie_ha === null || trabajo.superficie_ha === undefined) {
    faltan.push(`${a.hectareas} · ${sinDecir}`);
  }
  if (trabajo.horas === null || trabajo.horas === undefined) faltan.push(`${a.horas} · ${sinDecir}`);
  if (!trabajo.equipo_id) faltan.push(`${a.maquina} · ${sinDecir}`);
  return faltan;
}

/** Los avisos de «lo que no consta» del servidor, ya con su frase y su cuenta. */
function loQueNoConstaDeLosTrabajos(datos) {
  const avisos = [];
  // Los reenvíos del móvil que se han quitado: la misma petición dos veces es un trabajo, no dos, y lo
  // que se ha quitado **se cuenta** para que nadie crea que se ha perdido.
  if (datos.reenviados) avisos.push({ texto: mensaje("TJ11_el_trabajo_ya_estaba"), cuantos: datos.reenviados });
  // Y lo que no se ha podido comprobar: sin clave de reenvío no se puede saber si ya estaba apuntado.
  if (datos.aviso_codigo) avisos.push({ texto: mensaje(datos.aviso_codigo) });
  return avisos;
}

/** Abre «los trabajos»: se pinta enseguida y se vuelve a pintar con lo que contesta el servidor. */
async function abrirLosTrabajos() {
  const suyo = estadoDeLosTrabajos();
  suyo.error = "";
  suyo.aviso = "";
  suyo.formulario = null;
  suyo.tierra = null;
  suyo.cargando = true;
  pantallaLosTrabajos();
  try {
    suyo.datos = await apiJson("/api/trabajos");
  } catch (fallo) {
    suyo.error = (fallo && fallo.message) || mensaje("no_se_pudo");
  }
  suyo.cargando = false;
  return pantallaLosTrabajos();
}

/** La agenda, con lo previsto y lo hecho en dos listas y sin mezclarse. */
function pantallaLosTrabajos() {
  const suyo = estadoDeLosTrabajos();
  const datos = suyo.datos || {};
  return montar(() =>
    pantallaDeLosTrabajos({
      textos: textosDeLosTrabajos(),
      previstos: (datos.previstos || []).map((plan) => {
        // **El plan que ya se cumplió.** La agenda trae los planes cumplidos (y tiene que traerlos: el
        // plan sigue siendo lo que se pensó), así que la pantalla tiene que saber cuáles lo están o
        // pintaría «YA LO HE HECHO» sobre un trabajo ya apuntado, y ese botón solo puede acabar en un 409
        // del servidor. El vínculo lo puso el servidor al marcarlo: el hecho apunta al plan con
        // `previsto_id`.
        const hecho = (datos.hechos || []).find(
          (uno) => Number(uno.previsto_id) === Number(plan.id),
        );
        return {
          id: plan.id,
          titulo: etiquetaDeUnTrabajo(plan),
          cuando: cuandoEsUnTrabajo(plan),
          tierra: laTierraDeUnTrabajo(plan),
          // **La frase que impide el malentendido del ticket**: esto no ha gastado nada.
          no_gasta: t("agenda.lo_previsto_no_gasta", ""),
          // Y el día en que se cumplió, ya escrito. Es lo único que hace falta que venga de aquí: la frase
          // («Ya lo apuntaste como hecho:») la pide la pantalla a su vocabulario, como todas las demás.
          cuando_lo_hice: hecho ? cuandoEsUnTrabajo(hecho) : "",
        };
      }),
      hechos: (datos.hechos || []).map((hecho) => ({
        id: hecho.id,
        titulo: etiquetaDeUnTrabajo(hecho),
        cuando: cuandoEsUnTrabajo(hecho),
        tierra: laTierraDeUnTrabajo(hecho),
        faltan: loQueLeFaltaAUnTrabajo(hecho),
        anulado: Boolean(hecho.anulado),
        motivo_anulacion: hecho.motivo_anulacion || "",
        no_cuenta: mensaje("TJ3_el_apunte_esta_anulado"),
      })),
      lo_que_no_se_sabe: loQueNoConstaDeLosTrabajos(datos),
      error: suyo.error || "",
      cargando: suyo.cargando,
      // **Sin tierras no se puede planificar**, y el aviso trae el botón que lo arregla.
      puedePlanificar: (estado.parcelas || []).length > 0,
    }),
  );
}

/** Cómo se llama un trabajo: su tipo y, si es una labor de suelo, con qué apero. */
function etiquetaDeUnTrabajo(trabajo) {
  const tipos = t("trabajos", []) || [];
  const suyos = t("trabajos_de_labor", []) || [];
  const todos = [...tipos, ...suyos];
  const encontrado = todos.find((uno) => uno && uno.id === trabajo.tipo);
  const base = encontrado ? encontrado.texto : trabajo.tipo || "";
  if (!trabajo.subtipo) return base;
  // **El nombre de un apero es su propio código** (`rodillo`, `cultivador`…): son palabras que el
  // agricultor dice y el servidor no tiene otra lista de nombres para ellos. Igual que las unidades.
  return `${base} · ${trabajo.subtipo}`;
}

/** Los aperos de una labor de suelo, con su nombre, del servidor. */
function losSubtiposDeLaboreo() {
  // **El nombre de un apero es su propio código**, como el de las unidades (`unidades: {valor, texto}`):
  // `rodillo`, `cultivador`, `arado`… son palabras que el agricultor dice, y el servidor no tiene otra
  // lista de nombres para ellos. El día que se quieran en mayúscula o con tilde, van a `textos.py` y se
  // sirven con nombre propio, como los tipos.
  return (estadoDeLosTrabajos().subtipos || []).map((uno) => ({ valor: uno, texto: uno }));
}

/** Las tierras, para elegir en qué se hace el trabajo. */
function lasTierrasParaUnTrabajo() {
  return (estado.parcelas || []).map((una) => ({ valor: una.id, texto: una.alias }));
}

/** Los tipos de trabajo que el programa conoce, con el nombre que ya usa en sus botones. */
function losTiposDeUnTrabajo() {
  const suyos = estadoDeLosTrabajos();
  const dichos = [...(t("trabajos", []) || []), ...(t("trabajos_de_labor", []) || [])];
  return (suyos.tipos || []).map((codigo) => {
    const encontrado = dichos.find((uno) => uno && uno.id === codigo);
    return { valor: codigo, texto: encontrado ? encontrado.texto : codigo };
  });
}

/**
 * El vocabulario de la ficha: los tipos y los aperos, y las máquinas de la finca.
 *
 * Se piden **la primera vez que se abre una ficha** y se guardan: son listas que no cambian mientras se
 * trabaja, y pedirlas en cada repintado sería pedir cinco veces lo mismo. Los tipos y los aperos salen
 * de la puerta que el propio ticket tiene para eso (`GET /api/trabajos/que-falta`), que es la que dice
 * cuáles conoce el programa; las máquinas, de la maquinaria de la finca.
 */
async function cargarElVocabularioDeLosTrabajos() {
  const suyo = estadoDeLosTrabajos();
  if (suyo.tipos && suyo.maquinas) return;
  try {
    if (!suyo.tipos) {
      const vocabulario = await apiJson("/api/trabajos/que-falta");
      suyo.tipos = vocabulario.tipos || [];
      suyo.subtipos = vocabulario.subtipos_de_laboreo || [];
    }
    if (!suyo.maquinas) {
      const tabla = await apiJson("/api/maquinaria");
      suyo.maquinas = (tabla.maquinas || []).map((una) => ({ valor: una.id, texto: una.nombre }));
    }
  } catch (fallo) {
    suyo.error = (fallo && fallo.message) || mensaje("no_se_pudo");
  }
}

/**
 * Las máquinas de la finca, para **repartir un gasto entre ellas** (y para decir con cuál se hizo un
 * trabajo, que es lo otro que las usa).
 *
 * **Se piden cuando hacen falta, y no al arrancar**: la pantalla de las cuentas no las necesita para
 * nada más, y una lista que no se va a mirar no se descarga. Vive en el estado de los trabajos, que es
 * donde ya estaba —la ficha de un trabajo también las pide—, así que las dos pantallas comparten una
 * lista y no dos que puedan decir cosas distintas.
 */
async function cargarLasMaquinasSiHacenFalta() {
  const suyo = estadoDeLosTrabajos();
  if (suyo.maquinas) return suyo.maquinas;
  try {
    const tabla = await apiJson("/api/maquinaria");
    suyo.maquinas = (tabla.maquinas || []).map((una) => ({ valor: una.id, texto: una.nombre }));
  } catch (fallo) {
    suyo.maquinas = [];
    suyo.error = (fallo && fallo.message) || mensaje("no_se_pudo");
  }
  return suyo.maquinas;
}

/**
 * Los envases del almacén, para decir de cuál sale lo que se gastó.
 *
 * **El nombre del campo es `lotes`, y esto es un defecto que se encontró pulsando.** Esta función leía
 * `articulo.envases`, que **no existe** en lo que contesta `/api/almacen/existencias`: el servidor manda
 * los envases de un artículo en `articulo.lotes` (es lo mismo que pinta el libro del almacén, y su
 * respuesta se ve en el navegador). Con el nombre equivocado la lista salía **siempre vacía**, así que
 * el desplegable de insumos de la ficha de un trabajo no tenía ni una opción y **no se podía decir de
 * qué envase salió el producto**: la mitad del recorrido 4 («insumos y existencias») era imposible desde
 * la pantalla, y no lo decía nadie. No lo cazó ninguna prueba porque **ninguna** pasaba por aquí con
 * existencias de verdad: las de cableado de los trabajos mandaban `{articulos: []}`.
 */
async function cargarLosInsumosSiHacenFalta() {
  const suyo = estadoDeLosTrabajos();
  if (suyo.insumos) return suyo.insumos;
  try {
    const libro = await apiJson("/api/almacen/existencias");
    suyo.insumos = [];
    for (const articulo of libro.articulos || []) {
      for (const envase of articulo.lotes || []) {
        suyo.insumos.push({
          valor: envase.lote_id,
          texto: [articulo.nombre, envase.numero_lote].filter(Boolean).join(" · "),
        });
      }
    }
  } catch (fallo) {
    suyo.insumos = [];
    suyo.error = (fallo && fallo.message) || mensaje("no_se_pudo");
  }
  return suyo.insumos;
}

/**
 * Abre la ficha de un trabajo, en el modo que se le diga.
 *
 * Los cinco modos y lo que cambia en cada uno (lo dice la pantalla, no esto): planificar, reprogramar
 * (solo el día), marcar lo que de verdad se hizo, corregir y anular. El trabajo se busca **en lo que ya
 * está cargado** —el plan o el hecho— porque la agenda los trae todos: pedirlo otra vez sería pedir dos
 * veces lo mismo.
 */
async function abrirUnTrabajo(modo, id, tierra = null) {
  const suyo = estadoDeLosTrabajos();
  suyo.error = "";
  suyo.aviso = "";
  const datos = suyo.datos || {};
  const deDonde = modo === "planificar" || modo === "reprogramar" || modo === "hecho";
  const fuente = deDonde
    ? (datos.previstos || []).find((uno) => Number(uno.id) === Number(id))
    : (datos.hechos || []).find((uno) => Number(uno.id) === Number(id));
  const trabajo = fuente || null;
  // **Anular un plan es cancelarlo**, y son dos puertas distintas del servidor: se mira de dónde viene
  // el identificador y se guarda, para que el botón de guardar llame a la que toca.
  const esPlan = modo !== "anular" ? false : !(datos.hechos || []).some((uno) => Number(uno.id) === Number(id));
  // **Lo que el plan ya decía que se iba a gastar** (07/10/2026). Aquí iba vacío a pelo —`lote_id: ""`,
  // `cantidad: ""`— pasara lo que pasara, y el plan **sí trae sus insumos** del servidor. El resultado era
  // un defecto que no se ve: al abrir un tratamiento planificado para darlo por hecho, los campos de
  // almacén salían en blanco —el desplegable decía «No gasté nada»—, así que el trabajo se guardaba **sin
  // gastar nada** y **el almacén no se enteraba**. Y eso no se distingue de un trabajo en el que de verdad
  // no se gastó nada, que es lo que hace que nadie lo note hasta que cuadra mal la nave.
  //
  // Lo encontró el recorrido automático al comprobar el consumo de existencias (ronda 3 del encargo).
  const elInsumoDelPlan = ((trabajo && trabajo.insumos) || [])[0] || null;
  const borrador = {
    tipo: trabajo ? trabajo.tipo : "",
    subtipo: trabajo ? trabajo.subtipo || "" : "",
    parcela_id: trabajo && trabajo.parcela_id ? trabajo.parcela_id : tierra || "",
    fecha_prevista: trabajo && trabajo.fecha_prevista ? trabajo.fecha_prevista : "",
    fecha: trabajo && trabajo.fecha ? trabajo.fecha : "",
    superficie_ha: trabajo && trabajo.superficie_ha !== null ? trabajo.superficie_ha : "",
    horas: trabajo && trabajo.horas !== null ? trabajo.horas : "",
    equipo_id: trabajo && trabajo.equipo_id ? trabajo.equipo_id : "",
    lote_id: elInsumoDelPlan && elInsumoDelPlan.lote_id ? elInsumoDelPlan.lote_id : "",
    cantidad:
      elInsumoDelPlan && elInsumoDelPlan.cantidad !== null && elInsumoDelPlan.cantidad !== undefined
        ? elInsumoDelPlan.cantidad
        : "",
    unidad: elInsumoDelPlan && elInsumoDelPlan.unidad ? elInsumoDelPlan.unidad : "",
    observaciones: trabajo ? trabajo.observaciones || "" : "",
    motivo_anulacion: "",
  };
  suyo.formulario = { modo, id: trabajo ? trabajo.id : null, trabajo, borrador, repaso: [], esPlan };
  if (modo !== "anular") {
    await cargarElVocabularioDeLosTrabajos();
    await cargarLosInsumosSiHacenFalta();
  }
  return pantallaUnTrabajo();
}

/** La ficha: sus campos, sus opciones y lo que se había pensado (cuando se está marcando lo hecho). */
function pantallaUnTrabajo() {
  const suyo = estadoDeLosTrabajos();
  const suyoFormulario = suyo.formulario || { modo: "planificar", borrador: {} };
  const trabajo = suyoFormulario.trabajo;
  const a = t("agenda", {}) || {};
  const filasDelPrevisto = trabajo
    ? [
        { etiqueta: a.tipo, valor: etiquetaDeUnTrabajo(trabajo) },
        { etiqueta: a.dia_previsto, valor: cuandoEsUnTrabajo(trabajo) },
        trabajo.superficie_ha !== null && trabajo.superficie_ha !== undefined
          ? { etiqueta: a.hectareas_previstas, valor: formateaNumero(trabajo.superficie_ha, 2) }
          : null,
        trabajo.horas !== null && trabajo.horas !== undefined
          ? { etiqueta: a.horas_previstas, valor: formateaNumero(trabajo.horas, 2) }
          : null,
      ].filter(Boolean)
    : [];
  return montar(() =>
    pantallaDeUnTrabajo({
      textos: textosDeLosTrabajos(),
      modo: suyoFormulario.modo,
      borrador: suyoFormulario.borrador || {},
      tipos: losTiposDeUnTrabajo(),
      subtipos: losSubtiposDeLaboreo(),
      tierras: lasTierrasParaUnTrabajo(),
      maquinas: suyo.maquinas || [],
      insumos: suyo.insumos || [],
      unidades: (t("unidades", []) || []).map((una) => ({ valor: una, texto: una })),
      previsto: suyoFormulario.modo === "hecho" && trabajo ? { filas: filasDelPrevisto } : null,
      repaso: suyoFormulario.repaso || [],
      guardando: suyo.guardando,
      error: suyo.error || "",
    }),
  );
}

/** Lo que se ha escrito en la ficha, en los nombres que espera el servidor. */
function loEscritoEnLaFicha(modo) {
  const numero = (id) => {
    // **Con `aNumero` y no con `Number`** (06/10/2026): `Number("4,9")` es `NaN`, así que un agricultor
    // que escribiera las hectáreas con coma —que es como se escriben aquí, y lo que da el teclado
    // decimal del móvil— veía el trabajo guardado **sin hectáreas**, sin ningún error y sin saber por
    // qué. `aNumero` es la regla de la casa para leer un número escrito a mano (acepta la coma y los
    // miles) y la usan los demás formularios.
    const escrito = valorDeLaCasilla(id);
    return escrito === "" ? null : aNumero(escrito);
  };
  const texto = (id) => {
    const escrito = (valorDeLaCasilla(id) || "").trim();
    return escrito === "" ? null : escrito;
  };
  const borrador = {
    tipo: texto("trabajo-tipo"),
    subtipo: texto("trabajo-subtipo"),
    parcela_id: numero("trabajo-tierra"),
    superficie_ha: numero("trabajo-superficie"),
    horas: numero("trabajo-horas"),
    equipo_id: numero("trabajo-maquina"),
    observaciones: texto("trabajo-observaciones"),
  };
  if (modo === "reprogramar") return { fecha_prevista: texto("trabajo-fecha-prevista") };
  if (modo === "anular") return { motivo: texto("trabajo-motivo") };
  const esPlan = modo === "planificar";
  // La tierra del formulario, que es de la que va a salir el producto en un plan.
  const laTierraDelFormulario = numero("trabajo-tierra");
  const comun = esPlan
    ? { ...borrador, fecha_prevista: texto("trabajo-fecha-prevista") }
    : { ...borrador, fecha: texto("trabajo-fecha") };
  const lote = numero("trabajo-insumo");
  const cantidad = numero("trabajo-cantidad");
  const unidad = texto("trabajo-unidad");
  // **Un plan dice lo que va a gastar POR TIERRA** (07/10/2026): su puerta espera `lineas` —esta tierra,
  // esta cantidad de este envase—, y aquí se mandaba `insumos`, que **un plan no tiene**. Como el esquema
  // del servidor ignora lo que no conoce, no fallaba nada: el plan se guardaba **sin lo que iba a
  // gastar**, y por eso al marcarlo hecho no había nada que traer y el almacén no se enteraba nunca.
  //
  // Lo encontró el recorrido automático comprobando el consumo de existencias: el plan volvía con
  // `insumos: []` después de haber elegido el envase.
  if (esPlan) {
    return lote && cantidad && laTierraDelFormulario
      ? {
          ...comun,
          lineas: [
            {
              parcela_id: laTierraDelFormulario,
              lote_id: lote,
              cantidad,
              unidad: unidad || null,
            },
          ],
        }
      : comun;
  }
  return lote && cantidad
    ? { ...comun, insumos: [{ lote_id: lote, cantidad, unidad: unidad || null }] }
    : comun;
}

/** Guarda lo que se ha escrito, por la puerta que toca según el modo. */
async function guardarElTrabajo() {
  const suyo = estadoDeLosTrabajos();
  const formulario = suyo.formulario || {};
  const modo = formulario.modo;
  const id = formulario.id;
  const cuerpo = loEscritoEnLaFicha(modo);
  const campana_id = estado.campana ? estado.campana.id : null;
  const puertas = {
    planificar: ["POST", "/api/trabajos/previstos", { ...cuerpo, campana_id }],
    reprogramar: ["POST", `/api/trabajos/previstos/${id}/reprogramar`, cuerpo],
    hecho: ["POST", `/api/trabajos/previstos/${id}/hecho`, { ...cuerpo, campana_id }],
    // **Y la campaña también al corregir** (07/10/2026). Aquí iba `cuerpo` a secas, y el esquema del
    // servidor (`TrabajoEntrada`) exige `campana_id`: corregir un trabajo hecho contestaba **422 siempre**
    // —«No se ha podido guardar»— y no lo cazaba ninguna prueba, porque las de Python mandan la campaña a
    // mano y la de JavaScript solo mira que el método y la ruta sean los que son. Lo encontró la revisión
    // del recorrido comparando el cuerpo que manda esta pantalla con el esquema.
    corregir: ["PUT", `/api/trabajos/${id}`, { ...cuerpo, campana_id }],
    // **Un plan se cancela y un hecho se anula**: son dos puertas distintas con la misma pantalla (la
    // que pide el motivo), y por eso la puerta se elige con `esPlan` y no solo con el modo.
    anular: formulario.esPlan
      ? ["POST", `/api/trabajos/previstos/${id}/cancelar`, cuerpo]
      : ["POST", `/api/trabajos/${id}/anular`, cuerpo],
  };
  const [metodo, ruta, datos] = puertas[modo] || puertas.planificar;
  suyo.guardando = true;
  suyo.error = "";
  const resultado = await mandarCambio(ruta, metodo, datos);
  suyo.guardando = false;
  if (resultado.error) {
    suyo.error = resultado.error;
    return pantallaUnTrabajo();
  }
  // **Lo que el servidor ha comprobado se enseña antes de dar nada por bueno** cuando avisa de algo:
  // sin eso, un aviso que no se lee es un aviso que no existe.
  const avisos = (resultado.datos && resultado.datos.avisos) || [];
  if (avisos.length) {
    suyo.formulario.repaso = avisos;
    suyo.aviso = avisos.join(" ");
  }
  await abrirLosTrabajos();
  return pantallaLosTrabajos();
}

/** Abre la historia de una tierra: qué hay hoy, todo lo que ha pasado y lo que queda previsto. */
async function abrirLaHistoriaDeUnaTierra(parcelaId) {
  const suyo = estadoDeLosTrabajos();
  suyo.error = "";
  suyo.aviso = "";
  suyo.formulario = null;
  suyo.cargando = true;
  suyo.costes = null;
  pantallaLaHistoria();
  try {
    // **Dos puertas, porque son dos hechos de dos tickets**: los trabajos y su estado son del T15, y el
    // dinero que ha costado esa tierra es del T13. Cada una manda lo suyo y la pantalla los junta;
    // mezclarlos en una sola respuesta obligaría a que un ticket supiera del otro.
    const campana = estado.campana ? `?campana_id=${estado.campana.id}` : "";
    const [tierra, costes, laTierra] = await Promise.all([
      apiJson(`/api/trabajos/tierra/${Number(parcelaId)}`),
      // Si las cuentas no contestan, la historia se enseña igual: lo que falta es una parte, no la
      // pantalla. El bloque de los costes simplemente no sale.
      apiJson(`/api/gastos/de-una-tierra/${Number(parcelaId)}${campana}`).catch(() => null),
      // **Y la tierra, por su propia puerta** (07/10/2026): la respuesta del **estado** —la de arriba— habla
      // de trabajos y **no lleva el `dibujo`**, que es la forma de la parcela; por eso la ficha salía **sin
      // la forma de la tierra**, que es una regresión de este rediseño (se enseñaba en el panel, y el panel
      // se retiró). El dibujo **sí** viaja en la puerta de una tierra (`/api/parcelas/{id}`), así que se pide
      // ahí: una petición más, pequeña, y **cada dato por la puerta que lo tiene**. Si esa puerta falla, la
      // ficha se enseña igual, sin la forma.
      apiJson(`/api/parcelas/${Number(parcelaId)}`).catch(() => null),
    ]);
    // **La tierra viene envuelta** (07/10/2026): el objeto que devuelve el estado lleva la tierra **dentro**,
    // en `tierra.tierra` —lo lee así `pantallaLaHistoria`, que hace `const tierra = datos.tierra`—, y aquí se
    // estaba escribiendo **en el nivel de fuera**, así que el `dibujo` se quedaba en un sitio que nadie lee y
    // la ficha seguía sin la forma de la parcela. Es la **misma trampa del envoltorio** que ya apareció con
    // los trabajos (`{"previsto": {…}}`, `{"labor": {…}}`): se escribe donde se lee, no donde parece.
    if (laTierra && laTierra.dibujo && tierra.tierra) tierra.tierra.dibujo = laTierra.dibujo;
    suyo.tierra = tierra;
    suyo.costes = costes;
  } catch (fallo) {
    suyo.error = (fallo && fallo.message) || mensaje("no_se_pudo");
    suyo.tierra = null;
  }
  suyo.cargando = false;
  return pantallaLaHistoria();
}

/** La historia de una tierra, con sus líneas ya montadas. */
async function pantallaBuscar(textoDeLaDireccion = null) {
  /** La búsqueda global: se lee el cuadro, se pregunta al servidor y se pinta lo que conteste.
   *
   * Es la mitad del cable (la otra es su renglón en el menú y su dirección). **Lo que se enseña no se
   * decide aquí**: `nucleo.losGruposDeLaBusqueda` lo traduce y la pantalla lo pinta; esto solo pide.
   *
   * Si el servidor no contesta, **no se dice que no hay nada**: se dice que no se ha podido buscar. Son
   * dos cosas distintas, y confundirlas es lo que hace que un agricultor crea que no tiene algo que sí
   * tiene.
   */
  const cuadro = (() => {
    try {
      return document.getElementById("buscar_global");
    } catch (fallo) {
      return null;
    }
  })();
  const texto =
    textoDeLaDireccion !== null && textoDeLaDireccion !== undefined
      ? String(textoDeLaDireccion)
      : cuadro
        ? String(cuadro.value || "")
        : "";
  // **Y se apunta lo que se ha buscado** (07/10/2026): es de donde sale el texto que viaja en la
  // dirección (`#/buscar?texto=…`), que es lo que hace que recargar deje al agricultor donde estaba. Sin
  // esto, la pantalla se pinta pero se pierde lo que había escrito, que es una dirección a medias.
  estado.busqueda = { texto };
  let resultado = null;
  // **Sin nada escrito no se pregunta nada** (07/10/2026). Antes se pedía igual, y como la pantalla **no se
  // pinta hasta que el servidor contesta**, abrir `#/buscar` a secas dejaba al agricultor mirando la
  // pantalla anterior hasta que iba y volvía la petición — y en un momento lento, sin nada. Lo encontró el
  // recorrido automático al correr dentro de la suite (allí la petición tarda más y la puerta se caía).
  // Sin texto no hay nada que buscar: se pinta la pantalla ya, con su «escribe lo que buscas».
  if (texto) {
    try {
      resultado = await apiJson(`/api/buscar?texto=${encodeURIComponent(texto)}`);
    } catch (fallo) {
      resultado = null;
    }
  }
  return montar(() =>
    pantallaDeLaBusqueda({
      // **La clave de la pantalla** (07/10/2026): `montar` la necesita para lo que hace por todas las
      // pantallas —la dirección, el módulo marcado en el menú y la barra de contexto—. Sin ella, la
      // pantalla se pintaba pero no se apuntaba a dónde se había ido: la dirección no cambiaba y recargar
      // dejaba al agricultor fuera de su búsqueda. Es el camino central, y se usa **entero**.
      pantalla: "buscar",
      textos: { buscar: t("buscar", {}) },
      resultado,
      puedeBuscar: Boolean(estado.token),
      // **Y el texto, para que el cuadro lo enseñe**: al llegar por una dirección (`#/buscar?texto=…`) el
      // campo tiene que salir con lo que se buscó, y no vacío. Es la mitad de «recargar deja al agricultor
      // donde estaba»: la otra es que la dirección lo lleve.
      texto,
    }),
  );
}
function pantallaLaHistoria() {
  const suyo = estadoDeLosTrabajos();
  const datos = suyo.tierra || {};
  const a = t("agenda", {}) || {};
  const tierra = datos.tierra || {};
  const estadoDeLaTierra = datos.estado || null;
  const sinDecir = a.sin_decir || "";
  const valor = (numero) => (numero === null || numero === undefined ? sinDecir : formateaNumero(numero, 2));
  const nombreDeLaMaquina = (id) => {
    const suya = (estado.maquinaria || {}).maquinas || [];
    const encontrada = suya.find((una) => Number(una.id) === Number(id));
    return encontrada ? encontrada.nombre : sinDecir;
  };
  return montar(() =>
    pantallaDeLaTierra({
      textos: textosDeLosTrabajos(),
      tierra: {
        // **Con su identificador** (07/10/2026): la ficha no lo tenía, y sin él no puede ofrecer sus
        // propios botones —el de «lo que ha sido esta tierra», que lleva a sus versiones—, porque no sabría
        // de qué tierra son. El dato venía del servidor y se estaba tirando.
        id: tierra.id,
        nombre: tierra.alias || "",
        superficie: valor(tierra.superficie_ha),
        // **Y la referencia oficial** (07/10/2026): es **lo único** que el panel de la fila enseñaba y la
        // ficha no. Va primero el día que la ficha sea la única pantalla de una tierra (opción (a) del
        // encargo): antes de quitar el panel, la ficha tiene que tener todo lo que el panel daba.
        referencia: tierra.ref_sigpac || "",
        // **Y la forma de su recinto** (07/10/2026): se pintaba en el panel de la tierra, y al dejar la
        // ficha como pantalla única y retirar el panel, **el agricultor dejó de ver la forma de su tierra**
        // —una regresión de este rediseño, medida con el recorrido, que la mira—. Es lo mismo que dice el
        // comentario de arriba con la referencia: *antes de quitar el panel, la ficha tiene que tener todo lo
        // que el panel daba*. El dato viene ya en la tierra (`dibujo`, de `/api/parcelas`).
        dibujo: tierra.dibujo || "",
      },
      historial: ((datos.historial || {}).lineas || []).map((linea) => {
        const trabajo = linea.trabajo || {};
        return {
          titulo: etiquetaDeUnTrabajo(trabajo),
          cuando: cuandoEsUnTrabajo({ ...trabajo, de_donde: "hecho" }),
          filas: [
            { etiqueta: a.hectareas, valor: valor(trabajo.superficie_ha) },
            { etiqueta: a.horas, valor: valor(trabajo.horas) },
            { etiqueta: a.maquina, valor: trabajo.equipo_id ? nombreDeLaMaquina(trabajo.equipo_id) : sinDecir },
            ...(trabajo.insumos || []).map((insumo) => ({
              etiqueta: a.insumo,
              valor: [insumo.articulo, insumo.cantidad, insumo.unidad].filter(Boolean).join(" "),
            })),
          ],
          anulado: Boolean(linea.anulado),
          motivo_anulacion: linea.motivo_anulacion || "",
          no_cuenta: mensaje("TJ3_el_apunte_esta_anulado"),
          revisado: Boolean(linea.revisado),
          firmado: Boolean(linea.firmado),
        };
      }),
      estado: estadoDeLaTierra
        ? {
            cultivo_declarado: estadoDeLaTierra.cultivo_declarado || null,
            // **Un apero detrás de una siembra no borra lo sembrado**, y el servidor lo dice con su
            // código: aquí se traduce a su frase, que es lo que se pregunta al ver un rodillo.
            apero_no_cambia: estadoDeLaTierra.un_apero_no_cambia_lo_sembrado_codigo
              ? mensaje(estadoDeLaTierra.un_apero_no_cambia_lo_sembrado_codigo)
              : "",
            ultima_labor: Boolean(estadoDeLaTierra.ultima_labor),
            ultima_labor_titulo: estadoDeLaTierra.ultima_labor
              ? etiquetaDeUnTrabajo(estadoDeLaTierra.ultima_labor)
              : "",
            ultima_labor_cuando: estadoDeLaTierra.ultima_labor
              ? cuandoEsUnTrabajo({ ...estadoDeLaTierra.ultima_labor, de_donde: "hecho" })
              : "",
            previstos: (estadoDeLaTierra.que_queda_previsto || []).map((linea) => ({
              // **Con su identificador, para poder marcarlo hecho desde aquí** (07/10/2026): sin él, la
              // ficha podía enseñar lo previsto pero no había forma de decir «esto ya se hizo» desde la
              // tierra que se está mirando (había que ir a la agenda y buscarlo). Lo pidió la revisión del
              // recorrido (E3), y el identificador ya venía del servidor: solo no se estaba pasando.
              id: (linea.previsto || {}).id,
              titulo: etiquetaDeUnTrabajo(linea.previsto || {}),
              cuando: cuandoEsUnTrabajo({ ...linea, de_donde: "previsto" }),
            })),
          }
        : null,
      // Lo que no se puede saber de esta tierra, con su frase: la nascencia de una lluvia, lo que quedó
      // en el suelo después de la cosecha y lo que no se sembró.
      no_consta: [
        estadoDeLaTierra && estadoDeLaTierra.no_se_puede_deducir_la_nascencia_porque_codigo,
        estadoDeLaTierra && estadoDeLaTierra.no_se_puede_deducir_el_suelo_porque_codigo,
        estadoDeLaTierra && estadoDeLaTierra.no_se_sabe_que_se_sembro_codigo,
      ]
        .filter(Boolean)
        .map((codigo) => ({ texto: mensaje(codigo) })),
      // **Lo que ha costado esta tierra** (T13 + T15): las dos cifras separadas y la lista, cada línea
      // con su enlace a la ficha de ese gasto (donde están sus repartos y sus pagos). Si las cuentas no
      // han contestado, esto llega `null` y el bloque no sale: la historia se enseña igual.
      costes: suyo.costes,
      error: suyo.error || "",
    }),
  );
}

/**
 * Las doce acciones de los botones de los trabajos, una por una.
 *
 * Va aparte del manejador de clics por el mismo motivo que el de las cuentas: el manejador es uno solo
 * y ya tiene ochenta ramas, y este bloque se lee entero de una tirada. Devuelve `false` cuando la acción
 * no es suya, que es lo que hace que el manejador siga con las demás.
 */
async function atenderLosTrabajos(nombre, elemento) {
  const suyo = estadoDeLosTrabajos();
  const id = Number(elemento.dataset.id);
  if (nombre === "trabajos-ver") return abrirLosTrabajos();
  // **El botón que lleva a la historia de una tierra** (05/10/2026). Está aquí y no en otro sitio porque
  // lo que abre es una pantalla de este módulo; el botón se pinta en la ficha de la tierra (`app.js`,
  // `tierra.acciones`), que es donde el agricultor abre una tierra. **Hasta hoy no había ninguno**: la
  // pantalla existía, su dirección funcionaba, y no se llegaba a ella más que escribiéndola.
  if (nombre === "tierra-historia") return abrirLaHistoriaDeUnaTierra(id);
  // **Y sus versiones, desde la ficha** (07/10/2026): la pantalla existía y su dirección funcionaba, pero
  // no había ningún botón que llevara a ella. Es el mismo defecto que tenía la historia antes del T15.
  if (nombre === "tierra-versiones") return abrirLasVersionesDeUnaTierra(id);
  if (nombre === "trabajo-planificar") {
    // **La tierra que se está mirando viaja al formulario** (07/10/2026). Desde la ficha de una tierra, el
    // botón de planificar abría el formulario **sin la tierra**, así que salía «Elige la tierra» teniendo
    // el agricultor la tierra delante: el dato estaba cargado (`suyo.tierra.tierra.id`) y no se usaba. Lo
    // encontró la revisión del recorrido.
    const laQueSeEstaMirando = ((estadoDeLosTrabajos().tierra || {}).tierra || {}).id;
    return abrirUnTrabajo("planificar", null, laQueSeEstaMirando || null);
  }
  if (nombre === "trabajo-previsto-guardar") return guardarElTrabajo();
  if (nombre === "trabajo-abrir") return abrirUnTrabajo("reprogramar", id);
  if (nombre === "trabajo-reprogramar") return guardarElTrabajo();
  if (nombre === "trabajo-cancelar") {
    // **Cancelar un plan no es borrarlo**: se abre la pantalla que pide el motivo (la misma que la de
    // anular, porque es la misma pregunta) y al guardar se llama a la puerta de cancelar.
    suyo.error = "";
    suyo.aviso = "";
    suyo.formulario = { modo: "anular", id, trabajo: null, borrador: {}, repaso: [], esPlan: true };
    return pantallaUnTrabajo();
  }
  if (nombre === "trabajo-hecho") return abrirUnTrabajo("hecho", id);
  if (nombre === "trabajo-hecho-guardar") return guardarElTrabajo();
  if (nombre === "trabajo-corregir") return abrirUnTrabajo("corregir", id);
  if (nombre === "trabajo-guardar") return guardarElTrabajo();
  if (nombre === "trabajo-anular") return abrirUnTrabajo("anular", id);
  if (nombre === "trabajo-anular-confirmar") return guardarElTrabajo();
  return false;
}

// ---------------------------------------------------------------------------
// La bandeja documental (T08, S10, 06/10/2026)
// ---------------------------------------------------------------------------
//
// LO QUE ESTE BLOQUE HACE, Y LO QUE NO. Hace lo mismo que el del banco: pide los datos, recoge lo que el
// agricultor escribe y atiende las acciones de sus botones. Y tiene **tres cosas que no hace ningún otro**,
// las tres por el mismo motivo (el original no se toca y lo leído no es un dato):
//
//   1. **El fichero que se está subiendo vive en el estado**, como el del extracto del banco, y por lo
//      mismo: repintar la pantalla borra la casilla del fichero, y hay que volver a mandarlo al subirlo
//      después de comprobarlo. Es la trampa que ya costó una ronda con el cuaderno de la Junta.
//   2. **Nada se sube sin comprobarlo antes.** El botón de subir solo se pinta cuando el servidor ha dicho
//      que ese fichero no estaba (`bandeja-comprobar`), así que este bloque no tiene ninguna puerta por la
//      que se pueda subir un papel sin pasar por ahí.
//   3. **Aquí no se calcula ningún importe.** Los importes llegan del servidor en texto decimal y **ya
//      escritos** (el servidor manda `campos` y `textos`), y la pantalla solo los coloca. Lo único que se
//      escribe aquí es la fecha del papel y la de confirmarlo, con `formateaFecha`.

/** El estado de la bandeja, creado la primera vez que hace falta (como el de las cuentas). */
function estadoDeLaBandeja() {
  if (!estado.bandeja) {
    estado.bandeja = {
      // Lo que devolvió `GET /api/bandeja`: los papeles, el vocabulario y el pie ya compuesto.
      datos: null,
      // El papel que se está mirando, con su propuesta y sus enlaces (`GET /api/bandeja/<id>`).
      papel: null,
      // Con qué se puede enlazar: `GET /api/bandeja/candidatos?clase=…`.
      candidatos: [],
      // El fichero que se está subiendo, **en el estado** (ver la cabecera de este bloque).
      fichero: null,
      nombreDelFichero: "",
      // Lo que contestó `POST /api/bandeja/comprobar`: la huella y si ese papel ya estaba. **No ha
      // guardado nada.**
      comprobado: null,
      comprobando: false,
      subiendo: false,
      // El buscador y los dos filtros de la lista.
      filtro: "",
      estadoElegido: "sin_revisar",
      tipoElegido: "",
      // Lo que está puesto en la subida ahora mismo.
      tipoNuevoElegido: "",
      // La clase con la que se está buscando para enlazar, y lo que se ha escrito para buscarla.
      claseElegida: "",
      claseBuscada: "",
      buscandoCandidatos: false,
      // El formulario abierto (la revisión de un papel), con lo que se ha escrito.
      formulario: null,
      borrador: null,
      guardando: false,
      error: "",
      aviso: "",
    };
  }
  return estado.bandeja;
}

/** El vocabulario de estas pantallas: el de la bandeja y el botón de VOLVER que ya está en los textos. */
function textosDeLaBandeja() {
  return {
    bandeja: t("bandeja", {}),
    acciones: accion("volver") ? { volver: accion("volver") } : {},
  };
}

/** La fecha de un papel, escrita como se escribe aquí. Lo que no consta se queda vacío. */
function laFechaDeUnPapel(fecha) {
  return fecha ? formateaFecha(fecha) : "";
}

/**
 * Un papel, con las fechas escritas.
 *
 * Se escribe aquí la fecha (y no en la pantalla) por la regla de siempre: el formateo de las fechas vive
 * en un solo sitio (`formateaFecha`), y la pantalla no calcula ni formatea nada. Los importes **no se
 * tocan**: el servidor ya manda `campos` (el dato) y `textos` (el mismo, escrito).
 */
function conLasFechasEscritasDeLaBandeja(papel) {
  if (!papel) return papel;
  return {
    ...papel,
    texto_fecha: laFechaDeUnPapel(papel.fecha),
    texto_confirmado_en: papel.confirmado_en ? formateaFecha(papel.confirmado_en) : "",
  };
}

/** La lista de la bandeja, ya en React. */
function pantallaLaBandeja() {
  const suyo = estadoDeLaBandeja();
  const datos = suyo.datos || {};
  return montar(() =>
    pantallaDeLaBandeja({
      textos: textosDeLaBandeja(),
      papeles: (datos.papeles || []).map(conLasFechasEscritasDeLaBandeja),
      tipos: datos.tipos || [],
      estados: datos.estados || [],
      clases: datos.clases || [],
      resumen: datos.resumen || "",
      cuantos: datos.cuantos || 0,
      sinDecirDeQueEs: datos.sin_decir_de_que_es || 0,
      estadoElegido: suyo.estadoElegido,
      tipoElegido: suyo.tipoElegido,
      filtro: suyo.filtro,
      ficheroElegido: suyo.nombreDelFichero,
      tipoNuevoElegido: suyo.tipoNuevoElegido,
      comprobado: suyo.comprobado,
      comprobando: suyo.comprobando,
      subiendo: suyo.subiendo,
      formulario: elFormularioDeLaBandeja(suyo.formulario, suyo.borrador),
      guardando: suyo.guardando,
      error: suyo.error || "",
      aviso: suyo.aviso || "",
    }),
  );
}

/** La ficha de un papel, ya en React. */
function pantallaUnPapelDeLaBandeja() {
  const suyo = estadoDeLaBandeja();
  const papel = conLasFechasEscritasDeLaBandeja(suyo.papel);
  return montar(() =>
    pantallaDeUnPapelDeLaBandeja({
      textos: textosDeLaBandeja(),
      papel: papel || {},
      candidatos: suyo.candidatos,
      // Los otros papeles de la finca, para decir a cuál corrige este: el propio papel no sale de la lista
      // (un papel no se rectifica a sí mismo, y la puerta del servidor lo diría).
      papelesParaRectificar: (suyo.papelesParaRectificar || []).filter(
        (uno) => !papel || uno.valor !== papel.id,
      ),
      clases: (suyo.datos || {}).clases || [],
      claseElegida: suyo.claseElegida,
      claseBuscada: suyo.claseBuscada,
      buscandoCandidatos: suyo.buscandoCandidatos,
      formulario: elFormularioDeLaBandeja(suyo.formulario, suyo.borrador),
      guardando: suyo.guardando,
      cargando: !suyo.papel && !suyo.error,
      error: suyo.error || "",
      aviso: suyo.aviso || "",
    }),
  );
}

/** Abre la bandeja: se pinta enseguida y se vuelve a pintar con lo que contesta el servidor. */
async function abrirLaBandeja() {
  const suyo = estadoDeLaBandeja();
  suyo.error = "";
  suyo.aviso = "";
  suyo.formulario = null;
  suyo.borrador = null;
  suyo.papel = null;
  suyo.comprobado = null;
  suyo.fichero = null;
  suyo.nombreDelFichero = "";
  pantallaLaBandeja();
  await recargarLaBandeja();
  pantallaLaBandeja();
}

/** Vuelve a pedir la bandeja con el filtro que esté puesto. */
async function recargarLaBandeja() {
  const suyo = estadoDeLaBandeja();
  const consulta = new URLSearchParams();
  consulta.set("estado", suyo.estadoElegido || "sin_revisar");
  if (suyo.tipoElegido) consulta.set("tipo", suyo.tipoElegido);
  if (suyo.filtro) consulta.set("texto", suyo.filtro);
  try {
    suyo.datos = await apiJson(`/api/bandeja?${consulta.toString()}`);
    // Los otros papeles de la finca, para poder decir a cuál corrige este. Se piden con la lista y no con
    // cada ficha: son los mismos para todas.
    const todos = await apiJson("/api/bandeja?estado=todos");
    suyo.papelesParaRectificar = (todos.papeles || []).map((uno) => ({
      valor: uno.id,
      texto: [uno.titulo, uno.etiqueta_tipo, laFechaDeUnPapel(uno.fecha)].filter(Boolean).join(" · "),
    }));
    suyo.error = "";
  } catch (fallo) {
    suyo.error = (fallo && fallo.message) || mensaje("no_se_pudo");
  }
  return suyo;
}

/**
 * Abre la ficha de un papel: **pide sus datos al servidor**.
 *
 * Es lo que hace que esta pantalla se pueda enlazar y recargar: no vive de la lista que había antes, pide
 * su papel a su puerta. Si esa puerta no contesta (sin cobertura), se dice **que no se ha podido
 * comprobar**, que no es lo mismo que decir que ese papel no está.
 */
async function abrirUnPapelDeLaBandeja(id) {
  const suyo = estadoDeLaBandeja();
  if (!id) return abrirLaBandeja();
  suyo.papel = null;
  suyo.formulario = null;
  suyo.borrador = null;
  suyo.error = "";
  suyo.aviso = "";
  pantallaUnPapelDeLaBandeja();
  try {
    // **La lista se pide también aquí**, y no es un capricho: la ficha se puede abrir **directamente por
    // su dirección** (`#/papeles/bandeja/12`, un enlace que le mandan al agricultor), y sin la lista no
    // habría ni el vocabulario de las clases ni los otros papeles a los que este puede corregir. Son dos
    // peticiones al servidor y la pantalla sale entera, que es lo que se espera de una dirección.
    if (!suyo.datos) await recargarLaBandeja();
    suyo.papel = await apiJson(`/api/bandeja/${id}`);
    // Las clases que este papel sugiere (por su tipo) van delante; si no sugiere ninguna, se empieza por
    // el gasto, que es lo que más se enlaza.
    const clases = (suyo.datos && suyo.datos.clases) || [];
    suyo.claseElegida =
      (suyo.papel.clases_sugeridas || [])[0] || (clases[0] && clases[0].valor) || "gasto";
    suyo.claseBuscada = "";
    await buscarCandidatosDeLaBandeja();
  } catch (fallo) {
    suyo.error = (fallo && fallo.message) || mensaje("no_se_pudo");
  }
  pantallaUnPapelDeLaBandeja();
}

/** Pide los candidatos de la clase elegida: cosas que **ya están** en el cuaderno. */
async function buscarCandidatosDeLaBandeja() {
  const suyo = estadoDeLaBandeja();
  suyo.buscandoCandidatos = true;
  const consulta = new URLSearchParams();
  consulta.set("clase", suyo.claseElegida || "gasto");
  if (suyo.claseBuscada) consulta.set("texto", suyo.claseBuscada);
  try {
    const datos = await apiJson(`/api/bandeja/candidatos?${consulta.toString()}`);
    suyo.candidatos = datos.items || [];
  } catch (fallo) {
    suyo.candidatos = [];
    suyo.error = (fallo && fallo.message) || mensaje("no_se_pudo");
  }
  suyo.buscandoCandidatos = false;
}

/** La subida: leer el fichero que se ha elegido y comprobar si ese mismo papel ya estaba. */
async function comprobarElFicheroDeLaBandeja() {
  const suyo = estadoDeLaBandeja();
  const entrada = document.getElementById("bandeja-fichero");
  if (!entrada || !entrada.files || entrada.files.length === 0) {
    suyo.error = t("bandeja.fichero", "");
    pantallaLaBandeja();
    return;
  }
  // Sin cobertura no se puede subir un fichero de un tirón, así que se dice claro en vez de dejar al
  // agricultor esperando delante de una barra que no avanza. Es la misma decisión que en los papeles.
  if (!navigator.onLine) {
    suyo.error = aviso("no_se_pudo");
    pantallaLaBandeja();
    return;
  }
  // **El fichero se guarda en el estado**, porque repintar la pantalla borra la casilla y hay que volver a
  // mandarlo al subirlo.
  suyo.fichero = entrada.files[0];
  suyo.nombreDelFichero = suyo.fichero.name || "";
  suyo.tipoNuevoElegido = valorDeLaCasilla("bandeja-tipo-nuevo") || "";
  suyo.comprobado = null;
  suyo.error = "";
  suyo.aviso = "";
  suyo.comprobando = true;
  pantallaLaBandeja();
  try {
    const cuerpo = new FormData();
    cuerpo.append("fichero", suyo.fichero);
    const respuesta = await fetch("/api/bandeja/comprobar", {
      method: "POST",
      headers: { Authorization: `Bearer ${estado.token}` },
      body: cuerpo,
    });
    const datos = await respuesta.json().catch(() => null);
    if (!respuesta.ok) throw new Error((datos && datos.detail) || mensaje("no_se_pudo"));
    suyo.comprobado = datos;
  } catch (fallo) {
    // Si no se ha podido comprobar, **no se puede subir**: el botón de subir no se pinta sin la
    // comprobación, y eso es justo lo que impide que un duplicado entre sin decirlo.
    suyo.fichero = null;
    suyo.error = (fallo && fallo.message) || mensaje("no_se_pudo");
  }
  suyo.comprobando = false;
  pantallaLaBandeja();
}

/** Sube el papel: el fichero que ya se comprobó, con el tipo que se haya dicho. */
async function subirElPapelALaBandeja() {
  const suyo = estadoDeLaBandeja();
  if (!suyo.fichero) return pantallaLaBandeja();
  suyo.subiendo = true;
  suyo.error = "";
  suyo.aviso = "";
  pantallaLaBandeja();
  try {
    const cuerpo = new FormData();
    cuerpo.append("fichero", suyo.fichero);
    if (suyo.tipoNuevoElegido) cuerpo.append("tipo", suyo.tipoNuevoElegido);
    const respuesta = await fetch("/api/bandeja/subir", {
      method: "POST",
      headers: { Authorization: `Bearer ${estado.token}` },
      body: cuerpo,
    });
    const datos = await respuesta.json().catch(() => null);
    if (!respuesta.ok) throw new Error((datos && datos.detail) || mensaje("no_se_pudo"));
    suyo.aviso = (datos.avisos || []).join(" ");
    // El fichero y lo comprobado se olvidan: ya está guardado, y volver a subirlo sin querer crearía el
    // aviso de duplicado otra vez (que es lo que tiene que pasar).
    suyo.fichero = null;
    suyo.nombreDelFichero = "";
    suyo.comprobado = null;
    suyo.tipoNuevoElegido = "";
    await recargarLaBandeja();
  } catch (fallo) {
    suyo.error = (fallo && fallo.message) || mensaje("no_se_pudo");
  }
  suyo.subiendo = false;
  pantallaLaBandeja();
}

/**
 * Guarda lo que el agricultor ha aceptado de la lectura (`bandeja-revisar` → `bandeja-guardar`).
 *
 * Los campos salen de los `id` del formulario, que es como esta aplicación lee todo lo que se escribe, y
 * **vacío es «no lo sé»**: se manda la cadena vacía y el servidor lo guarda como nulo, que es lo que hace
 * que borrar un importe que el lector leyó mal sirva de algo.
 */
async function guardarLaRevisionDeLaBandeja() {
  const suyo = estadoDeLaBandeja();
  const id = (suyo.formulario || {}).id || (suyo.papel || {}).id;
  if (!id) return pantallaUnPapelDeLaBandeja();
  const campos = {};
  for (const campo of [
    "proveedor",
    "proveedor_nif",
    "numero_factura",
    "fecha",
    "base_imponible",
    "cuota_iva",
    "tipo_iva_pct",
    "total",
  ]) {
    campos[campo] = valorDeLaCasilla(`bandeja-${campo}`) || "";
  }
  suyo.guardando = true;
  suyo.error = "";
  suyo.aviso = "";
  pantallaUnPapelDeLaBandeja();
  try {
    const contestado = await apiJson(`/api/bandeja/${id}/revisar`, {
      method: "POST",
      body: JSON.stringify({ campos }),
    });
    suyo.aviso = (contestado.avisos || []).join(" ");
    suyo.papel = contestado.papel;
    suyo.formulario = null;
    suyo.borrador = null;
    await recargarLaBandeja();
  } catch (fallo) {
    suyo.error = (fallo && fallo.message) || mensaje("no_se_pudo");
  }
  suyo.guardando = false;
  pantallaUnPapelDeLaBandeja();
}

/** Una puerta del papel que solo cambia su estado: leerlo, confirmarlo, descartar la lectura o rectificar. */
async function hacerAlgoConElPapelDeLaBandeja(id, puerta, cuerpo = {}) {
  const suyo = estadoDeLaBandeja();
  if (!id) return pantallaUnPapelDeLaBandeja();
  suyo.guardando = true;
  suyo.error = "";
  suyo.aviso = "";
  pantallaUnPapelDeLaBandeja();
  try {
    const contestado = await apiJson(`/api/bandeja/${id}/${puerta}`, {
      method: "POST",
      body: JSON.stringify(cuerpo),
    });
    suyo.aviso = (contestado.avisos || []).join(" ");
    suyo.papel = contestado.papel;
    suyo.formulario = null;
    suyo.borrador = null;
    await recargarLaBandeja();
  } catch (fallo) {
    suyo.error = (fallo && fallo.message) || mensaje("no_se_pudo");
  }
  suyo.guardando = false;
  pantallaUnPapelDeLaBandeja();
}

/**
 * El formulario de la revisión, con sus campos puestos.
 *
 * Los valores que salen son **los que ya se han aceptado** si los hay, y si no **los que se han leído**: así
 * el agricultor corrige sobre lo que el programa propuso en vez de escribirlo todo, que es lo que hace que
 * una lectura aproveche aunque tenga una errata. Y el rótulo de cada campo es el del tipo de papel: no se
 * pregunta «¿cuál es la base imponible?» a quien está mirando un contrato.
 */
function elFormularioDeLaBandeja(cual, borrador) {
  if (!cual) return null;
  const b = t("bandeja", {});
  const br = borrador || {};
  const papel = estadoDeLaBandeja().papel || {};
  const propuesta = papel.la_propuesta || {};
  const aceptado = papel.lo_aceptado || {};
  const de = (campo) => {
    if (br[campo] !== undefined) return br[campo];
    const suyo = (aceptado.campos || {})[campo];
    if (suyo === undefined || suyo === null) return (propuesta.campos || {})[campo] || "";
    return suyo;
  };
  return {
    titulo: b.revisar_titulo,
    pista: b.revisar_pista,
    guardar: b.guardar,
    cancelar: b.cancelar,
    guardando: b.guardando,
    datos: { clase: "revision", id: papel.id || "" },
    error: "",
    bloques: [
      { tipo: "texto", id: "bandeja-proveedor", etiqueta: b.proveedor, valor: de("proveedor") },
      { tipo: "texto", id: "bandeja-proveedor_nif", etiqueta: b.nif_del_proveedor, valor: de("proveedor_nif") },
      { tipo: "texto", id: "bandeja-numero_factura", etiqueta: b.numero_de_factura, valor: de("numero_factura") },
      { tipo: "fecha", id: "bandeja-fecha", etiqueta: b.fecha, valor: de("fecha") },
      { tipo: "numero", id: "bandeja-base_imponible", etiqueta: b.base_imponible, valor: de("base_imponible") },
      { tipo: "numero", id: "bandeja-cuota_iva", etiqueta: b.cuota_de_iva, valor: de("cuota_iva") },
      { tipo: "numero", id: "bandeja-tipo_iva_pct", etiqueta: b.tipo_de_iva, valor: de("tipo_iva_pct") },
      { tipo: "numero", id: "bandeja-total", etiqueta: b.total, valor: de("total") },
    ],
  };
}

/**
 * Las 19 acciones de los botones de estas dos pantallas.
 *
 * **La 20 y la 21 (`papel-ver-todos` y `ir-inicio`) ya existían** y las atiende el manejador de siempre: por
 * eso no están aquí, y por eso la lista del informe las cuenta aparte.
 */
async function atenderLaBandeja(nombre, elemento) {
  const suyo = estadoDeLaBandeja();
  const id = Number(elemento.dataset.id || 0);
  if (nombre === "bandeja-ver") return abrirLaBandeja();
  if (nombre === "bandeja-abrir") return abrirUnPapelDeLaBandeja(id);
  if (nombre === "bandeja-comprobar") return comprobarElFicheroDeLaBandeja();
  if (nombre === "bandeja-subir") return subirElPapelALaBandeja();
  if (nombre === "bandeja-olvidar-fichero") {
    // Se olvida lo elegido y lo comprobado: es la salida de «este papel ya lo tenías», para poder elegir
    // otro fichero sin recargar la pantalla.
    suyo.fichero = null;
    suyo.nombreDelFichero = "";
    suyo.comprobado = null;
    suyo.error = "";
    return pantallaLaBandeja();
  }
  if (nombre === "bandeja-filtrar") {
    suyo.filtro = valorDeLaCasilla("bandeja-buscar");
    suyo.estadoElegido = valorDeLaCasilla("bandeja-estado") || "sin_revisar";
    suyo.tipoElegido = valorDeLaCasilla("bandeja-tipo") || "";
    await recargarLaBandeja();
    return pantallaLaBandeja();
  }
  if (nombre === "bandeja-ver-todas") {
    suyo.filtro = "";
    suyo.estadoElegido = "sin_revisar";
    suyo.tipoElegido = "";
    await recargarLaBandeja();
    return pantallaLaBandeja();
  }
  if (nombre === "bandeja-original") return descargarDocumento(id);
  if (nombre === "bandeja-leer") return hacerAlgoConElPapelDeLaBandeja(id, "leer");
  if (nombre === "bandeja-confirmar") return hacerAlgoConElPapelDeLaBandeja(id, "confirmar");
  if (nombre === "bandeja-descartar") {
    return hacerAlgoConElPapelDeLaBandeja(id, "descartar", {
      motivo: valorDeLaCasilla("bandeja-motivo-descartar"),
    });
  }
  if (nombre === "bandeja-clasificar") {
    return hacerAlgoConElPapelDeLaBandeja(id, "clasificar", {
      tipo: valorDeLaCasilla("bandeja-tipo-del-papel"),
    });
  }
  if (nombre === "bandeja-revisar") {
    // Abre el formulario con lo que ya hay puesto (lo aceptado o lo leído). No guarda nada todavía.
    suyo.formulario = { clase: "revision", id };
    suyo.borrador = {};
    return pantallaUnPapelDeLaBandeja();
  }
  if (nombre === "bandeja-guardar") return guardarLaRevisionDeLaBandeja();
  if (nombre === "bandeja-cancelar") {
    suyo.formulario = null;
    suyo.borrador = null;
    return pantallaUnPapelDeLaBandeja();
  }
  if (nombre === "bandeja-buscar-candidatos") {
    suyo.claseElegida = valorDeLaCasilla("bandeja-clase") || suyo.claseElegida;
    suyo.claseBuscada = valorDeLaCasilla("bandeja-candidato-buscar") || "";
    await buscarCandidatosDeLaBandeja();
    return pantallaUnPapelDeLaBandeja();
  }
  if (nombre === "bandeja-enlazar") {
    const elegido = valorDeLaCasilla("bandeja-candidato");
    if (!elegido) return pantallaUnPapelDeLaBandeja();
    // El candidato se manda con **su clase y su identificador**: la clase va en el dato del desplegable
    // (`clase:entidad_id`), como en la conciliación del banco, así que no hay que adivinarla.
    const corte = elegido.indexOf(":");
    return hacerAlgoConElPapelDeLaBandeja(id, "vincular", {
      clase: elegido.slice(0, corte),
      entidad_id: Number(elegido.slice(corte + 1)),
    });
  }
  if (nombre === "bandeja-desenlazar") {
    return hacerAlgoConElPapelDeLaBandeja(id, "desvincular", {
      clase: elemento.dataset.clase,
      entidad_id: Number(elemento.dataset.entidad),
    });
  }
  if (nombre === "bandeja-rectificar") {
    const alQueCorrige = valorDeLaCasilla("bandeja-rectifica-a");
    if (!alQueCorrige) return pantallaUnPapelDeLaBandeja();
    return hacerAlgoConElPapelDeLaBandeja(id, "rectificar", {
      rectifica_a_id: Number(alQueCorrije),
    });
  }
}


// --------------------------------------------------------------------- arranque

async function arrancar() {
  if (leer(CLAVE_LETRA, false)) document.body.classList.add("letra-grande");
  pintarAvisoPendientes();

  if (!estado.token) {
    estado.interfaz = leer(CLAVE_INTERFAZ, null) || {};
    pantallaEntrar("entrar");
    // La interfaz se carga igualmente, para poder escribir la pantalla de entrada en
    // castellano de verdad y no con textos de relleno. Y se mira si esta instalación
    // sabe leer el certificado, para saber si hay que enseñar el botón.
    Promise.all([cargarInterfaz(), mirarCertificado()])
      .then(() => {
        pintarPie();
        pantallaEntrar("entrar");
      })
      .catch(() => {});
    return;
  }

  await arrancarSesion();
}

if ("serviceWorker" in navigator) {
  // Si falla, no pasa nada: solo se pierde poder abrir la aplicación sin cobertura.
  navigator.serviceWorker.register("/service-worker.js").catch(() => {});
}

arrancar();
