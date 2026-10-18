/**
 * ***El inventario de acciones por su EFECTO REAL*** (18/10/2026, revision independiente).
 *
 * ## Por que existe
 *
 * *Antes habia un **clasificador por sufijos**: `guardar`, `anular`, `quitar`... *Y la revision demostro que
 * **se queda corto con la mitad**:*
 *
 *     contacto-borrar-si   -> ***borrarElContacto*** (DELETE del contacto)
 *     fusion-hacer         -> ***mandarCambio*** (POST de fusion)
 *     contacto-nota        -> apunta una nota       ·  contacto-baja -> cambia el uso
 *     banco-deshacer       -> deshace una conciliacion  ·  bandeja-confirmar -> confirma un papel
 *
 * ***«Una confirmacion puede ser precisamente la operacion destructiva»***, *y `borrar-si` no acaba en ningun
 * sufijo de los que habia. **Los sufijos son una heuristica sobre el nombre; esto es un inventario sobre lo que
 * la accion HACE.***
 *
 * ## Como se hizo
 *
 * *Se saco, del codigo, **que funcion atiende cada accion** y **si esa funcion manda algo que no es un GET** -
 * `method: "POST"|"PUT"|"PATCH"|"DELETE"`, o `mandarCambio`, que es el ayudante de la casa para escribir-.
 * Despues se quitaron las **de sesion** (`entrar`, `cambiar-finca`), que **no escriben datos** y esconderlas
 * dejaria al agricultor fuera.*
 *
 * ***Y una prueba vuelve a hacer ese analisis y compara***: *si alguien anade un manejador que escribe y no lo
 * apunta aqui, **falla** -y dice cual-.*
 *
 * ## Lo que NO es
 *
 * *No es «todo lo que escribe esta aqui» por fe: es lo que el analisis encuentra **hoy**. **Lo que aparezca
 * manana y no este, se queda sin esconder**, y por eso el guardian lo persigue.*
 */

/**
 * ***Las acciones que ESCRIBEN en la base de datos***, por el efecto real.
 *
 * *En orden alfabetico para que se pueda leer y comparar.*
 */
export const LAS_QUE_ESCRIBEN = new Set([
  "ajuste-anular-si",
  "ajuste-guardar",
  "albaran-anular-si",
  "analisis-nuevo",
  "asistente-seguir",
  "banco-conciliar-a-mano",
  "banco-conciliar-propuesta",
  "banco-corregir",
  "banco-deshacer",
  "banco-guardar",
  "banco-importar",
  "banco-leer",
  "bandeja-clasificar",
  "bandeja-comprobar",
  "bandeja-confirmar",
  "bandeja-descartar",
  "bandeja-desenlazar",
  "bandeja-enlazar",
  "bandeja-guardar",
  "bandeja-leer",
  "bandeja-rectificar",
  "bandeja-subir",
  "buscar-trozos",
  "canal-nuevo",
  "canal-principal",
  "canal-quitar",
  "cobro-anular-si",
  "cobro-conciliar",
  "cobro-conciliar-con",
  "cobro-desconciliar",
  "cobro-guardar",
  "contacto-alta",
  "contacto-baja",
  "contacto-borrar-si",
  "contacto-desenlazar",
  "contacto-enlazar",
  "contacto-guardar",
  "contacto-migracion-apuntar",
  "contacto-migracion-deshacer",
  "contacto-migracion-todas",
  "contacto-nota",
  "contacto-papel",
  "cosa-borrar-si",
  "cuaderno-leer",
  "cuaderno-traer",
  "cultivo-guardar",
  "cultivo-quitar-si",
  "dictado-entender",
  "factura-emitida-anular-si",
  "factura-emitida-guardar",
  "factura-enganchar-si",
  "factura-guardar",
  "factura-leer",
  "factura-papel-subir",
  "finca-anadir",
  "finca-quitar",
  "firmar-subir",
  "fusion-deshacer",
  "fusion-hacer",
  "gasto-pago-conciliar",
  "gasto-pago-deshacer",
  "grupo-calcular",
  "mapa-apuntar",
  "mapa-preguntar",
  "mapa-tocar",
  "maquina-anular-confirmar",
  "maquina-averia-borrar",
  "maquina-declarar",
  "maquina-guardar",
  "maquina-inspeccion-borrar",
  "maquina-traer-equipo",
  "medidas-guardar",
  "medidas-quitar-si",
  "mis-datos-guardar",
  "papel-guardar",
  "papel-nuevo",
  "papel-subir",
  "semilla-guardar",
  "siembra-aceptar-descuadre",
  "siembra-anular",
  "siembra-guardar",
  "t06-apuntar-lote",
  "t06-ensayar",
  "tarea-cancelar",
  "tarea-completar",
  "tarea-nueva",
  "trabajo-anular-confirmar",
  "trabajo-guardar",
  "trabajo-hecho-guardar",
  "trabajo-previsto-guardar",
  "trabajo-reprogramar",
  "trabajos-terceros-proponer",
  "traer-marcados",
]);

/**
 * ***Las de SESION***: *entrar, cambiar de finca. **No escriben datos**, y esconderlas dejaria al agricultor
 * fuera de su propio cuaderno. Se nombran para que se vea que **se pensaron**, no para esconderlas.*
 */
export const LAS_DE_SESION = new Set([
  "entrar",
  "entrar-certificado",
  "finca-entrar",
  "cambiar-finca",
  "reintentar-direccion",
]);

/**
 * ***Si esa accion escribe***, por el inventario y no por su nombre.
 *
 * *Una accion **que no este en ninguna de las dos listas** se trata como **consulta**: *el guardian es el que
 * impide que una escritura se quede sin apuntar, no un «por si acaso» que esconda media aplicacion-.*
 */
export function escribeEstaAccion(accion) {
  const nombre = String(accion || "");
  if (LAS_DE_SESION.has(nombre)) return false;
  return LAS_QUE_ESCRIBEN.has(nombre);
}
