# Revisión de cierre de roles y nuevas funciones PAC

Fecha: 18/10/2026. HEAD observado eec9e55, rama estabilizacion-2026-10-18.
Árbol inicialmente limpio. No se modifica código del CRM en esta revisión.

## Roles: recorrido ejecutado sobre esta revisión

Ejecutado verificar_los_permisos_por_rol.py con su servidor y base temporales:
53 comprobaciones, 0 fallos, salida 0. Visita los contextos de las acciones,
comprueba controles positivos del titular, ayudante, consulta y cambio de cuenta/finca.
Esto respalda el recorrido concreto; no es una certificación de todas las rutas del CRM.

## Defecto reproducido: dos años comparten la misma dirección de foto

El modelo identifica una versión por explotacion_id + anio + version.
POST /api/pac/foto calcula max(version)+1 dentro de ese año.
Sin embargo, GET /api/pac/foto/{version} y su exportación buscan solo explotación y versión.

Reproducción real contra API, sobre base temporal:
- Guardar año 2027: versión 1.
- Guardar año 2028: versión 1.
- Consultar la segunda mediante la dirección proporcionada por la API: devuelve año 2027,
  versión 1. El enlace no puede identificar cuál de las dos se quiere consultar.

Usar ID inmutable de la foto o explotación/año/versión en detalle y exportación. Devolver
la identidad completa y sus enlaces al guardar. No corregir con order_by/limit: elegir
una fila no elimina la ambigüedad. Probar dos años, varias versiones y otra explotación.

## PAC todavía no cierra el recorrido del usuario

El cliente actual solo consulta /api/pac/paquete. No hay llamadas a /escenario ni a
/foto ni controles de comparación, guardado o exportación de fotos en la pantalla PAC.
Las funciones puras y las rutas nuevas son infraestructura útil, no una interfaz entregada.

Construir un recorrido completo, sin cambiar lo declarado ni realizado:
abrir campaña objetivo → escoger cultivos hipotéticos → comparar alternativas → revisar
datos faltantes → guardar versión evaluada → abrir historial → exportar esa versión.
Mostrar fuente y alcance de cualquier evaluación; no convertir ausencia de regla legal en
cumplimiento. La hipótesis puede guardarse como borrador separado si el producto lo requiere:
persistir un borrador no lo convierte en una declaración oficial ni en un trabajo realizado.

## Identidad y consistencia al guardar

POST /foto recalcula el escenario contra el paquete actual, en vez de recibir una identidad
de la evaluación ya mostrada. No basta con que una foto permanezca inmutable DESPUÉS del alta:
hay que impedir que cambie entre la vista previa y el guardado sin que se informe.
Reproducido sobre base temporal: evaluar una parcela con alias «Alias visto al evaluar»,
cambiar después el alias en esa base y guardar la foto. El contenido guardado lleva
«Alias cambiado antes de guardar», distinto del evaluado. No hubo conflicto ni aviso.
Adoptar contenido evaluado validado por servidor o un identificador/huella de evaluación;
si cambió la base, conflicto explícito y opción de recalcular, no una sustitución silenciosa.
No confiar en contenido arbitrario enviado por el cliente para afirmar datos reales.

La numeración usa max+1. Probar dos guardados simultáneos y reintento tras respuesta perdida:
ningún error interno, ninguna versión sobrescrita y semántica explícita de nueva versión.

## Alcance de la comprobación

Las 14 pruebas seleccionadas de escenario PAC, foto e independencia entre campañas pasan.
También se reprodujo el fallo de identidad de dos años, sin guardar un test nuevo en el destino:
se emplearon en memoria las fixtures existentes y su base temporal.
No se ha ejecutado la suite completa ni una validación normativa de elegibilidad.

## Orden de continuidad

1. Corregir identidad de foto y consistencia entre evaluación mostrada y guardada.
2. Validar entrada con esquemas, años, campos y recintos de la explotación. Los errores
   de datos deben ser claros, sin 500 ni cambios parciales.
3. Construir pantalla de escenarios, comparación, versiones y exportación; capacidades
   explícitas y acciones incluidas en el inventario de permisos.
4. Pruebas de dos años, actualización entre vista y guardado, concurrencia, aislamiento,
   historial inmutable y exportación de la versión exacta.
5. Recorrido de navegador del usuario sobre servidor aislado y checks de AGENTS.
6. Después continuar las tareas listas de la cola, conservando commits revisables.

No reabrir el diagnóstico del cuenta-horas ni reiniciar la estabilización completa.
Los problemas descritos pertenecen a la PAC nueva y deben cerrarse en una entrega acotada.
