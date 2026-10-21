/**
 * Tests del núcleo, con el ejecutor de tests que trae Node.
 *
 * No hace falta instalar nada: `node --test tests_js/` desde la carpeta `backend`.
 * Se prueba justo lo que en el navegador no se puede probar a mano: los números en
 * castellano, la cola de lo que queda pendiente sin cobertura y las comprobaciones
 * que se hacen en el móvil antes de molestar al servidor.
 */

import assert from "node:assert/strict";
import { test } from "node:test";

import {
  aNumero,
  avisoDelServidor,
  conCuenta,
  crearAlmacenMemoria,
  crearCola,
  decideQueHacer,
  diasDeEspera,
  diasHasta,
  fechaEnPalabras,
  formateaFecha,
  formateaNumero,
  primerAvisoBloqueante,
  queSePuedeRepetir,
  rellena,
  repetirUltimo,
  sinTildes,
  sumaDias,
  sumandoLoQueSeSabe,
  tierrasQueCasen,
  ultimoDeLaFinca,
  validaPaso,
  validaSuperficie,
} from "../web/nucleo.js";

// ---------------------------------------------------------------------------
// Números y fechas en castellano
// ---------------------------------------------------------------------------

test("los decimales se escriben con coma", () => {
  assert.equal(formateaNumero(0.8), "0,80");
  assert.equal(formateaNumero(1.944), "1,94");
});

test("los miles se separan con punto", () => {
  assert.equal(formateaNumero(1234.5, 1), "1.234,5");
});

test("lo que no es un número no se inventa", () => {
  assert.equal(formateaNumero(null), "");
  assert.equal(formateaNumero(undefined), "");
  assert.equal(formateaNumero(""), "");
  assert.equal(formateaNumero("hola"), "");
});

test("se acepta la coma que escribe de verdad un agricultor", () => {
  // En un teclado español se escribe 0,8. Si esto fallara, media aplicación se
  // rompería con el número más natural de escribir.
  assert.equal(aNumero("0,8"), 0.8);
  assert.equal(aNumero("2,43"), 2.43);
  assert.equal(aNumero("1.234,5"), 1234.5);
  assert.equal(aNumero(" 300 "), 300);
});

test("un punto solo con tres decimales son millares", () => {
  // "1.234" en España son mil doscientos treinta y cuatro. Interpretarlo como 1,234
  // sería un error de mil veces en una dosis o en kilos de abono.
  assert.equal(aNumero("1.234"), 1234);
  assert.equal(aNumero("1.000"), 1000);
});

test("un punto con otros decimales es un decimal", () => {
  // Esta es la trampa que hay que evitar: "0.8" NO son 8.
  assert.equal(aNumero("0.8"), 0.8);
  assert.equal(aNumero("2.4317"), 2.4317);
  assert.equal(aNumero(".5"), 0.5);
});

test("varios puntos son todos millares", () => {
  assert.equal(aNumero("1.234.567"), 1234567);
  assert.equal(aNumero("1.234.567,89"), 1234567.89);
});

test("un número vacío o absurdo devuelve nada, no cero", () => {
  // Devolver 0 sería peligroso: parecería que el agricultor ha echado cero kilos.
  assert.equal(aNumero(""), null);
  assert.equal(aNumero("  "), null);
  assert.equal(aNumero("mucho"), null);
  assert.equal(aNumero(null), null);
});

test("la fecha se lee en el orden español", () => {
  assert.equal(formateaFecha("2026-05-22"), "22/05/2026");
  assert.equal(formateaFecha(""), "");
});

test("la fecha en palabras se usa en los textos que se leen", () => {
  assert.equal(fechaEnPalabras("2026-05-01"), "1 de mayo");
  assert.equal(fechaEnPalabras("2026-01-15"), "15 de enero");
});

test("la suma de días cruza meses y años", () => {
  assert.equal(sumaDias("2026-05-01", 21), "2026-05-22");
  assert.equal(sumaDias("2026-12-25", 10), "2027-01-04");
});

test("los días que faltan se cuentan bien", () => {
  assert.equal(diasHasta("2026-05-22", "2026-05-13"), 9);
  assert.equal(diasHasta("2026-05-22", "2026-05-22"), 0);
  assert.equal(diasHasta("2026-05-22", "2026-05-25"), -3);
  assert.equal(diasHasta(null, "2026-05-25"), null);
});

test("los días de espera que quedan es la cuenta que ve el agricultor", () => {
  // Echado el 1 de mayo con 21 días: hasta el 22 no se puede coger. El 13 faltan 9.
  assert.equal(diasDeEspera("2026-05-01", 21, "2026-05-13"), 9);
  assert.equal(diasDeEspera("2026-05-01", 21, "2026-05-22"), 0);
  assert.equal(diasDeEspera("2026-05-01", 21, "2026-05-30"), -8);
  assert.equal(diasDeEspera("2026-05-01", null, "2026-05-30"), null);
});

// ---------------------------------------------------------------------------
// La cola de lo que queda pendiente sin cobertura
// ---------------------------------------------------------------------------

function colaDePrueba(inicial = {}) {
  let reloj = 0;
  return crearCola(crearAlmacenMemoria(inicial), {
    reloj: () => `2026-09-21T10:00:0${(reloj += 1)}Z`,
  });
}

test("una cola nueva está vacía", () => {
  assert.equal(colaDePrueba().tamano(), 0);
});

test("lo apuntado se guarda para mandarlo después", () => {
  const cola = colaDePrueba();
  cola.apuntar({ tipo: "tratamiento", datos: { fecha: "2026-05-01" } });
  assert.equal(cola.tamano(), 1);
});

test("cada apunte pendiente tiene su identificador", () => {
  const cola = colaDePrueba();
  const primero = cola.apuntar({ tipo: "tratamiento", datos: {} });
  const segundo = cola.apuntar({ tipo: "tratamiento", datos: {} });
  assert.ok(primero.id_local);
  assert.notEqual(primero.id_local, segundo.id_local);
});

test("lo apuntado sobrevive a cerrar el navegador", () => {
  // Este es el motivo de usar localStorage y no una variable en memoria: el
  // agricultor apunta sin cobertura, cierra el móvil y al volver tiene que seguir ahí.
  const almacen = crearAlmacenMemoria();
  const primera = crearCola(almacen);
  primera.apuntar({ tipo: "tratamiento", datos: { fecha: "2026-05-01" } });

  const segunda = crearCola(almacen);
  assert.equal(segunda.tamano(), 1);
  assert.equal(segunda.leer()[0].datos.fecha, "2026-05-01");
});

test("lo que ya se ha mandado se quita de la cola", () => {
  const cola = colaDePrueba();
  const apunte = cola.apuntar({ tipo: "tratamiento", datos: {} });
  cola.quitar(apunte.id_local);
  assert.equal(cola.tamano(), 0);
});

test("quitar uno no se lleva los demás", () => {
  const cola = colaDePrueba();
  const primero = cola.apuntar({ tipo: "tratamiento", datos: { fecha: "2026-05-01" } });
  cola.apuntar({ tipo: "tratamiento", datos: { fecha: "2026-05-02" } });
  cola.quitar(primero.id_local);
  assert.equal(cola.tamano(), 1);
  assert.equal(cola.leer()[0].datos.fecha, "2026-05-02");
});

test("si lo guardado está corrupto no se queda bloqueado", () => {
  // Antes muerto que dejar al agricultor sin poder apuntar nada.
  const cola = colaDePrueba({ "cuedigital.pendientes": "esto no es una lista" });
  assert.equal(cola.tamano(), 0);
  cola.apuntar({ tipo: "tratamiento", datos: {} });
  assert.equal(cola.tamano(), 1);
});

test("si el navegador no deja guardar, la aplicación no revienta", () => {
  const almacenQueFalla = {
    getItem: () => null,
    setItem: () => {
      throw new Error("almacenamiento bloqueado");
    },
  };
  const cola = crearCola(almacenQueFalla);
  assert.doesNotThrow(() => cola.apuntar({ tipo: "tratamiento", datos: {} }));
});

test("con la cola vacía no hay nada que hacer", () => {
  assert.deepEqual(decideQueHacer(colaDePrueba(), true), { accion: "nada", cuantos: 0 });
});

test("sin cobertura se espera, no se pierde", () => {
  const cola = colaDePrueba();
  cola.apuntar({ tipo: "tratamiento", datos: {} });
  assert.deepEqual(decideQueHacer(cola, false), { accion: "esperar", cuantos: 1 });
});

test("al volver la cobertura se manda lo pendiente", () => {
  const cola = colaDePrueba();
  cola.apuntar({ tipo: "tratamiento", datos: {} });
  cola.apuntar({ tipo: "tratamiento", datos: {} });
  assert.deepEqual(decideQueHacer(cola, true), { accion: "mandar", cuantos: 2 });
});

// ---------------------------------------------------------------------------
// Repetir lo de la última vez
// ---------------------------------------------------------------------------

const ULTIMO_APUNTE = {
  tipo: "tratamiento",
  datos: {
    campana_id: 1,
    fecha: "2026-05-01",
    parcela_id: 3,
    superficie_tratada_ha: 2.43,
    producto_id: 7,
    dosis: 0.8,
    justificacion: "Vi la plaga o la hierba en el campo",
  },
};

test("repetir cambia la fecha y deja lo demás igual", () => {
  const repetido = repetirUltimo(ULTIMO_APUNTE, "2026-06-10");
  assert.equal(repetido.datos.fecha, "2026-06-10");
  assert.equal(repetido.datos.producto_id, 7);
  assert.equal(repetido.datos.dosis, 0.8);
  assert.equal(repetido.datos.parcela_id, 3);
  assert.equal(repetido.tipo, "tratamiento");
});

test("repetir no cambia el apunte original", () => {
  const original = JSON.parse(JSON.stringify(ULTIMO_APUNTE));
  repetirUltimo(ULTIMO_APUNTE, "2026-06-10");
  assert.deepEqual(ULTIMO_APUNTE, original);
});

test("sin nada apuntado antes, no hay nada que repetir", () => {
  assert.equal(repetirUltimo(null, "2026-06-10"), null);
  assert.equal(repetirUltimo({ tipo: "tratamiento" }, "2026-06-10"), null);
});

// ---------------------------------------------------------------------------
// El último apunte de la finca
//
// Hasta esta ronda, «lo mismo que la última vez» salía solo de lo que recordaba el móvil. Al
// estrenar teléfono, al entrar desde el ordenador de casa o si el navegador borraba sus datos,
// el agricultor se quedaba sin el atajo y, además, le decían que no había apuntado nada. Estos
// apuntes vienen del servidor, que es donde están de verdad.
// ---------------------------------------------------------------------------

/** Un tratamiento tal y como lo devuelve `/api/tratamientos` (los campos que se repiten). */
function tratamientoDeLaFinca(extra = {}) {
  return {
    id: 1,
    campana_id: 1,
    fecha: "2026-04-10",
    tipo: "parcela",
    parcela_id: 3,
    grupo_id: null,
    instalacion_id: null,
    superficie_tratada_ha: 4.9,
    justificacion: "Vi la hierba en el campo",
    plaga: "Hierbas adventicias",
    producto_id: 7,
    producto_nombre: "Glifosato 36 SL",
    dosis: 0.8,
    unidad_dosis: "L/ha",
    medidas: ["cubierta"],
    anulado: false,
    ...extra,
  };
}

test("sin tratamientos no hay nada que repetir", () => {
  assert.equal(ultimoDeLaFinca([]), null);
  assert.equal(ultimoDeLaFinca(null), null);
});

test("se coge el tratamiento más nuevo, aunque vengan desordenados", () => {
  const repetido = ultimoDeLaFinca([
    tratamientoDeLaFinca({ id: 1, fecha: "2026-04-10" }),
    tratamientoDeLaFinca({ id: 2, fecha: "2026-06-02", producto_id: 9 }),
    tratamientoDeLaFinca({ id: 3, fecha: "2026-01-15" }),
  ]);
  assert.equal(repetido.tipo, "tratamiento");
  assert.equal(repetido.datos.producto_id, 9, "no se ha cogido el tratamiento más nuevo");
  assert.equal(repetido.datos.fecha, "2026-06-02");
});

test("un tratamiento anulado no es la última vez", () => {
  const repetido = ultimoDeLaFinca([
    tratamientoDeLaFinca({ id: 1, fecha: "2026-04-10" }),
    tratamientoDeLaFinca({ id: 2, fecha: "2026-06-02", anulado: true }),
  ]);
  assert.equal(
    repetido.datos.fecha,
    "2026-04-10",
    "se ofrece repetir un tratamiento que el agricultor anuló",
  );
});

test("de la finca se saca todo lo que el asistente necesita para repetir", () => {
  // Si un nombre de campo no cuadra con el del asistente, el resumen sale con huecos y el
  // agricultor apunta un tratamiento sin producto. Es la comprobación que evita ese fallo.
  const { datos } = ultimoDeLaFinca([tratamientoDeLaFinca()]);
  assert.equal(datos.producto_id, 7);
  assert.equal(datos.parcela_id, 3);
  assert.equal(datos.dosis, 0.8);
  assert.equal(datos.unidad_dosis, "L/ha");
  assert.equal(datos.superficie_tratada_ha, 4.9);
  assert.equal(datos.justificacion, "Vi la hierba en el campo");
  assert.deepEqual(datos.medidas, ["cubierta"]);
  // Lo que no viene se queda a nulo, no en «undefined»: así el resumen no escribe la palabra
  // «undefined» delante del agricultor.
  assert.equal(datos.equipo_id, null);
  assert.equal(datos.observaciones, null);
});

test("repetir lo de la finca cambia el día, no lo demás", () => {
  const repetido = repetirUltimo(ultimoDeLaFinca([tratamientoDeLaFinca()]), "2026-09-30");
  assert.equal(repetido.datos.fecha, "2026-09-30");
  assert.equal(repetido.datos.producto_id, 7);
  assert.equal(repetido.datos.dosis, 0.8);
});

test("de los dos sitios se repite el más nuevo, no el del móvil por serlo", () => {
  const delMovil = { tipo: "fertilizacion", datos: { fecha: "2026-02-01", abono: "nitrato" } };
  const deLaFinca = ultimoDeLaFinca([tratamientoDeLaFinca({ fecha: "2026-06-02" })]);
  assert.equal(queSePuedeRepetir(delMovil, deLaFinca).tipo, "tratamiento");

  // Y al revés: si lo último se apuntó en este móvil (aunque no sea un tratamiento), manda eso.
  const delMovilNuevo = { tipo: "fertilizacion", datos: { fecha: "2026-07-01" } };
  assert.equal(queSePuedeRepetir(delMovilNuevo, deLaFinca).tipo, "fertilizacion");

  // Sin nada en el móvil, se usa lo de la finca; sin nada en la finca, lo del móvil.
  assert.equal(queSePuedeRepetir(null, deLaFinca).tipo, "tratamiento");
  assert.equal(queSePuedeRepetir(delMovil, null).tipo, "fertilizacion");
  assert.equal(queSePuedeRepetir(null, null), null);
});

// ---------------------------------------------------------------------------
// Comprobaciones que se hacen en el móvil
// ---------------------------------------------------------------------------

test("lo que hay que rellenar sí o sí se detecta", () => {
  assert.equal(validaPaso("parcela_id", null), "V18_sin_parcela");
  assert.equal(validaPaso("parcela_id", ""), "V18_sin_parcela");
  assert.equal(validaPaso("justificacion", "   "), "V10_sin_justificacion");
  assert.equal(validaPaso("producto_id", undefined), "V1_sin_registro");
  assert.equal(validaPaso("kg_ha_producto", ""), "F1_sin_cantidad");
});

test("lo que está relleno no da la lata", () => {
  assert.equal(validaPaso("parcela_id", 3), null);
  assert.equal(validaPaso("justificacion", "Vi pulgón"), null);
});

test("un campo que no es obligatorio no se comprueba", () => {
  assert.equal(validaPaso("observaciones", ""), null);
  assert.equal(validaPaso("inventado", ""), null);
});

test("no se puede tratar más hectáreas de las que tiene la parcela", () => {
  assert.equal(validaSuperficie(9, 2.43), "V4_superficie_excedida");
  assert.equal(validaSuperficie(2.43, 2.43), null);
  assert.equal(validaSuperficie(2.4301, 2.43), null);
});

test("en los abonos el aviso es el suyo, no el de los productos", () => {
  assert.equal(validaSuperficie(9, 2.43, true), "F2_superficie_excedida");
});

test("se comprueba con la coma española", () => {
  assert.equal(validaSuperficie("9,5", "2,43"), "V4_superficie_excedida");
  assert.equal(validaSuperficie("2,43", "2,43"), null);
});

// ---------------------------------------------------------------------------
// Leer lo que contesta el servidor
// ---------------------------------------------------------------------------

test("se saca el mensaje que impide guardar, ya escrito", () => {
  const respuesta = {
    detail: {
      puede_guardarse: false,
      avisos: [
        { codigo: "V3_dosis_excedida", mensaje: "Has puesto más de lo que permite la etiqueta.", bloquea: true },
      ],
    },
  };
  assert.equal(primerAvisoBloqueante(respuesta), "Has puesto más de lo que permite la etiqueta.");
});

test("de varios avisos se coge el que bloquea, no uno cualquiera", () => {
  const respuesta = {
    detail: {
      avisos: [
        { codigo: "V8_dias_de_espera", mensaje: "Aviso informativo", bloquea: false },
        { codigo: "V10_sin_justificacion", mensaje: "Pon por qué lo has echado.", bloquea: true },
      ],
    },
  };
  assert.equal(primerAvisoBloqueante(respuesta), "Pon por qué lo has echado.");
});

test("una respuesta sin avisos no revienta", () => {
  assert.equal(primerAvisoBloqueante(null), null);
  assert.equal(primerAvisoBloqueante({}), null);
  assert.equal(primerAvisoBloqueante({ detail: {} }), null);
});

test("el motivo del servidor se aprovecha venga como aviso o como frase suelta", () => {
  // Las dos formas que usa el servidor, y las dos son frases que lee el agricultor. La segunda se perdía:
  // un 403 con su frase acababa en «No se ha podido mandar», que no dice qué pasa ni qué hacer (ronda 89).
  assert.equal(
    avisoDelServidor({
      detail: { avisos: [{ mensaje: "Has puesto más de lo que permite la etiqueta.", bloquea: true }] },
    }),
    "Has puesto más de lo que permite la etiqueta.",
  );
  assert.equal(
    avisoDelServidor({ detail: "Solo el titular de la finca puede decidir quién más entra." }),
    "Solo el titular de la finca puede decidir quién más entra.",
  );
});

test("lo que no es una frase para el agricultor no se le enseña", () => {
  // Los fallos de formato de FastAPI (`detail` como lista de «field required») no son una frase, y una
  // frase vacía tampoco: en esos casos se usa el aviso general, que al menos dice que no se ha podido.
  assert.equal(avisoDelServidor({ detail: [{ loc: ["body", "correo"], msg: "field required" }] }), null);
  assert.equal(avisoDelServidor({ detail: "   " }), null);
  assert.equal(avisoDelServidor(null), null);
  assert.equal(avisoDelServidor({}), null);
  assert.equal(avisoDelServidor({ detail: {} }), null);
});

// ---------------------------------------------------------------------------
// Rellenar los textos que vienen del servidor
// ---------------------------------------------------------------------------

test("los huecos se rellenan con sus datos", () => {
  assert.equal(
    rellena("La parcela tiene {parcela} hectáreas y has puesto {usada}.", {
      parcela: "2,43",
      usada: "9,00",
    }),
    "La parcela tiene 2,43 hectáreas y has puesto 9,00.",
  );
});

test("el mismo hueco repetido se rellena en los dos sitios", () => {
  assert.equal(rellena("{a} y otra vez {a}", { a: "trigo" }), "trigo y otra vez trigo");
});

test("un hueco sin dato se deja ver, no se escribe undefined", () => {
  // Un "undefined" en pantalla asusta y no dice nada; un hueco se ve y se corrige.
  assert.equal(rellena("Hola {nombre}", {}), "Hola {nombre}");
  assert.equal(rellena("Hola {nombre}", { nombre: null }), "Hola {nombre}");
});

test("un texto sin huecos se devuelve igual", () => {
  assert.equal(rellena("Apuntado.", {}), "Apuntado.");
  assert.equal(rellena("", {}), "");
  assert.equal(rellena(null, {}), "");
});

// ---------------------------------------------------------------------------
// El buscador de tierras (rediseño de la ronda 82)
//
// Con 51 tierras, apuntar dónde se ha echado el producto era recorrer la lista entera. El buscador es lo
// que hace que se escriba «prado» y salga esa tierra. **La búsqueda se prueba aquí** y no en los tests de
// la pantalla porque es la única forma de probarla con datos inventados, una por una: una búsqueda que no
// encontrara lo que hay que encontrar sería peor que no tener buscador.
// ---------------------------------------------------------------------------

/** Tres tierras, como las devuelve `/api/parcelas`. */
const TRES_TIERRAS = [
  { id: 1, alias: "El Prado", municipio: "Calvarrasa de Arriba", ref_sigpac: "37-70-0-0-503-51-1" },
  {
    id: 2,
    alias: "Las Suertes de Arriba",
    municipio: "Peñaranda de Bracamonte",
    ref_sigpac: "37-70-0-0-112-4-2",
  },
  { id: 3, alias: "El Vallejo Llano", municipio: "Macotera", ref_sigpac: "37-70-0-0-88-9-1" },
];

test("un texto se compara sin tildes, sin mayúsculas y sin espacios de más", () => {
  // Quien escribe con una mano y con guantes no pone tildes, y el programa no puede castigarle por eso.
  assert.equal(sinTildes("Peñaranda"), "penaranda");
  assert.equal(sinTildes("  EL   Prado "), "el prado");
  assert.equal(sinTildes(null), "");
  assert.equal(sinTildes(undefined), "");
});

test("el buscador encuentra una tierra por su nombre, sin tildes ni mayúsculas", () => {
  assert.deepEqual(tierrasQueCasen(TRES_TIERRAS, "prado").map((t) => t.alias), ["El Prado"]);
  assert.deepEqual(tierrasQueCasen(TRES_TIERRAS, "VALLEJO").map((t) => t.alias), ["El Vallejo Llano"]);
});

test("el buscador encuentra una tierra por el pueblo, aunque se escriba sin la tilde", () => {
  assert.deepEqual(tierrasQueCasen(TRES_TIERRAS, "penaranda").map((t) => t.alias), [
    "Las Suertes de Arriba",
  ]);
  assert.deepEqual(tierrasQueCasen(TRES_TIERRAS, "Peñaranda").map((t) => t.alias), [
    "Las Suertes de Arriba",
  ]);
});

test("el buscador encuentra una tierra por el número del SIGPAC, escrito de cualquier manera", () => {
  // En el visor del SIGPAC se copia «37-70-0-0-503-51-1», y quien lo escribe de memoria teclea
  // «37 70 503»: los ceros sueltos de la referencia no distinguen nada, así que dan igual.
  assert.deepEqual(tierrasQueCasen(TRES_TIERRAS, "503").map((t) => t.id), [1]);
  assert.deepEqual(tierrasQueCasen(TRES_TIERRAS, "503-51").map((t) => t.id), [1]);
  assert.deepEqual(tierrasQueCasen(TRES_TIERRAS, "37 70 503").map((t) => t.id), [1]);
  assert.deepEqual(tierrasQueCasen(TRES_TIERRAS, "37-70-0-0-112-4-2").map((t) => t.id), [2]);
});

test("una cifra suelta no da por buena cualquier tierra", () => {
  // Buscar «5» no puede sacar las cincuenta y una tierras: los números se comparan en trozos de dos cifras
  // o más. («51» sí casa con «…-51-1», que es un trozo de su referencia: eso es una búsqueda de verdad.)
  const sinNombreQueCase = [{ id: 9, alias: "Una tierra", municipio: "", ref_sigpac: "37-70-0-0-88-9-1" }];
  assert.deepEqual(tierrasQueCasen(sinNombreQueCase, "5").map((t) => t.id), []);
  assert.deepEqual(tierrasQueCasen(TRES_TIERRAS, "51").map((t) => t.id), [1]);
});

test("sin nada escrito el buscador no esconde nada", () => {
  assert.equal(tierrasQueCasen(TRES_TIERRAS, "").length, 3);
  assert.equal(tierrasQueCasen(TRES_TIERRAS, "   ").length, 3);
  assert.equal(tierrasQueCasen(TRES_TIERRAS, null).length, 3);
});

test("lo que no está no sale, y una tierra sin SIGPAC no revienta la búsqueda", () => {
  // Nada inventado: si no casa, no sale. Y una tierra apuntada a mano (sin número del SIGPAC) no puede
  // romper la búsqueda de las demás.
  assert.deepEqual(tierrasQueCasen(TRES_TIERRAS, "cebada"), []);
  const conUnaSinSigpac = [...TRES_TIERRAS, { id: 4, alias: "La Vega", municipio: "", ref_sigpac: null }];
  assert.deepEqual(tierrasQueCasen(conUnaSinSigpac, "vega").map((t) => t.id), [4]);
  assert.deepEqual(tierrasQueCasen(conUnaSinSigpac, "88-9").map((t) => t.id), [3]);
});

// ---------------------------------------------------------------------------
// Los textos que llevan una cuenta (rediseño de la ronda 84)
//
// «1 cosas apuntadas esperando a que haya cobertura» es lo primero que hace desconfiar de un programa, y ese
// aviso sale en la cabecera justo cuando el agricultor está en el campo sin cobertura. El servidor manda el
// singular y el plural; aquí se elige, igual que hace `con_cuenta` en `textos.py`.
// ---------------------------------------------------------------------------

test("la cuenta se dice en singular cuando es uno, y en plural cuando son varios", () => {
  const textos = {
    pendientes: "{cuantos} cosas apuntadas",
    pendientes_uno: "1 cosa apuntada",
  };
  assert.equal(conCuenta(textos, "pendientes", 1), "1 cosa apuntada");
  assert.equal(conCuenta(textos, "pendientes", 3), "3 cosas apuntadas");
});

test("la cuenta también rellena los textos escritos con «cuantas»", () => {
  // Los textos están escritos en femenino o en masculino según la frase, así que el hueco puede ser
  // `{cuantos}` o `{cuantas}`: los dos se rellenan con el mismo número.
  const textos = { hojas_datos: "{cuantas} hojas de 25 llevan datos tuyos" };
  assert.equal(conCuenta(textos, "hojas_datos", 5), "5 hojas de 25 llevan datos tuyos");
});

test("sin el singular escrito se usa el plural de siempre, y sin texto no se inventa nada", () => {
  // En pantalla nunca se queda un hueco: es lo que hacía antes de existir el singular. Lo que impide que el
  // singular falte es la prueba `TestSingularYPlural`, en Python.
  assert.equal(conCuenta({ cuantos: "{cuantos} papeles" }, "cuantos", 1), "1 papeles");
  assert.equal(conCuenta({}, "cuantos", 2), "");
  assert.equal(conCuenta(null, "cuantos", 2), "");
});

test("el singular vale escrito con «uno» y con «una»", () => {
  // **30/09/2026, y esto pasó dos veces.** Cuando el sustantivo es femenino —«1 venta apuntada», «1 tierra»—
  // el texto de `textos.py` está escrito con `_una`, que es como se lee; esta función solo miraba `_uno`, así
  // que con una sola venta la frase salía en plural («1 ventas apuntadas»). La primera vez se renombraron las
  // claves de los pies de las tablas; la segunda (el panel de mando) se arregló aquí, probando las dos formas:
  // el que escribe el texto lo pone como se lee.
  const femenino = {
    cuantas: "{cuantas} ventas apuntadas",
    cuantas_una: "1 venta apuntada",
  };
  assert.equal(conCuenta(femenino, "cuantas", 1), "1 venta apuntada");
  assert.equal(conCuenta(femenino, "cuantas", 2), "2 ventas apuntadas");
  // Y `_uno` manda cuando están las dos (no hay dos textos distintos para lo mismo).
  const lasDos = { cuantas: "{cuantas} ventas", cuantas_uno: "una venta", cuantas_una: "1 venta apuntada" };
  assert.equal(conCuenta(lasDos, "cuantas", 1), "una venta");
});

// ---------------------------------------------------------------------------
// Lo que no se sabe no suma cero (A14, 05/10/2026)
//
// El defecto que estas pruebas vigilan estaba en seis sitios de la interfaz y era siempre el mismo:
// `suma + (Number(...) || 0)`. Un hueco —`null`, que en este programa quiere decir «no lo sé»— sumaba
// cero, y el total se leía como si estuviera completo. La cuenta se hace ahora en un solo sitio
// (`sumandoLoQueSeSabe`) y estas pruebas son las que impiden que vuelva a hacerse a mano.
// ---------------------------------------------------------------------------

test("suma lo que se sabe y cuenta lo que no, en vez de contar el hueco como cero", () => {
  const tierras = [
    { superficie_ha: 4.9 },
    { superficie_ha: null }, // «no lo sé», no «0 ha»
    { superficie_ha: 3.2 },
    { superficie_ha: undefined }, // el campo que no vino
    { superficie_ha: "" }, // el campo en blanco
  ];
  const cuenta = sumandoLoQueSeSabe(tierras, (tierra) => tierra.superficie_ha);
  // **La comparación va redondeada, y no es un descuido**: `4.9 + 3.2` en coma flotante da
  // `8.100000000000001`, y eso es cierto en cualquier programa. Lo que se comprueba aquí es la **cuenta**
  // (que el hueco no suma y se cuenta), no la aritmética del ordenador; en pantalla el número se pinta con
  // `formateaNumero`, que ya lo redondea a los decimales que se enseñan.
  assert.equal(Number(cuenta.suma.toFixed(4)), 8.1, "la suma son las que lo traen, y ni un cero de más");
  assert.equal(cuenta.sin_decir, 3, "y hay que poder decir cuántas faltan");
});

test("una cifra que no se puede leer tampoco se convierte en cero", () => {
  // Es la otra mitad del mismo defecto: `Number("por ahí")` es `NaN`, y `NaN || 0` es 0. Con eso, un dato
  // ilegible entraba en el total como un cero silencioso.
  const cuenta = sumandoLoQueSeSabe([{ kilos: "por ahí" }, { kilos: 100 }], (venta) => venta.kilos);
  assert.equal(cuenta.suma, 100);
  assert.equal(cuenta.sin_decir, 1);
});

test("un número escrito como texto sí se suma, y el cero de verdad es un cero", () => {
  // Y para que lo de arriba no se pase de listo: «2,5»… no, la coma no: aquí los números llegan del
  // servidor como números o como texto con punto. Y un 0 **de verdad** —una venta de cero kilos, que es
  // un dato— suma lo que es: cero, y no cuenta como «no se sabe».
  const cuenta = sumandoLoQueSeSabe([{ kilos: "2.5" }, { kilos: 0 }], (venta) => venta.kilos);
  assert.equal(cuenta.suma, 2.5);
  assert.equal(cuenta.sin_decir, 0, "un cero dicho es un dato, no un hueco");
});

test("una lista vacía o que no llegó no es un error: es cero y nada sin decir", () => {
  assert.deepEqual(sumandoLoQueSeSabe([], (uno) => uno), { suma: 0, sin_decir: 0 });
  assert.deepEqual(sumandoLoQueSeSabe(null, (uno) => uno), { suma: 0, sin_decir: 0 });
  assert.deepEqual(sumandoLoQueSeSabe(undefined), { suma: 0, sin_decir: 0 });
});

test("sin decir de dónde coger el número, suma la lista tal cual", () => {
  // El caso de una lista de números: `sumandoLoQueSeSabe([1, 2, null])` no necesita el segundo argumento.
  assert.deepEqual(sumandoLoQueSeSabe([1, 2, null]), { suma: 3, sin_decir: 1 });
});


test("las métricas tienen números españoles y unidades legibles sin cambiar la magnitud", async () => {
  const { presentarMetrica } = await import("../web/nucleo.js");
  const textos = { no_se_sabe: "No se sabe", unidades: { ha_de_trabajo: "ha trabajadas" } };
  const original = { valor: 1234.5, unidad: "ha_de_trabajo", clave: "trabajo" };
  const vista = presentarMetrica(original, textos);
  assert.equal(vista.texto_valor, "1.234,50 · ha trabajadas");
  assert.equal(vista.unidad, original.unidad);
  assert.equal(original.texto_valor, undefined);
  assert.equal(presentarMetrica({ ...original, valor: 0 }, textos).texto_valor, "0,00 · ha trabajadas");
  assert.equal(presentarMetrica({ ...original, valor: null }, textos).texto_valor, "No se sabe · ha trabajadas");
});
