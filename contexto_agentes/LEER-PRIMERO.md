# CUE Digital: desarrollo continuo e investigación de referencias

Fecha: 11/10/2026. Destino: `F:\EspacioCodigo\CueDigital`.
Laboratorio: `F:\EspacioCodigo\ProyectoServidor\rea-sandbox`.
Este paquete organiza el trabajo autorizado por David; no afirma que la cola esté implementada.

## Arranque sin perder el contexto

1. Leer los AGENTS del laboratorio y de `estudiar-apps`, y `OPERAR.md`.
2. Leer este fichero, [VERIFICACION.md](VERIFICACION.md), [COLA.md](COLA.md)
   y [ESTADO.md](ESTADO.md).
3. En el destino leer `AGENTS.md`, `DESIGN.md` y estos documentos existentes:
   `docs/CONTRATO_IMPLEMENTACION_CRM.md`, `docs/ESPECIFICACION_DETALLADA_CRM_2026.md`,
   `docs/MATRIZ_NORMATIVA_CRM.md`, `docs/ESTADO_DEL_REDISENO.md`.
4. Comprobar estado de Git y cambios ajenos. Leer las rutas, modelos y pruebas del siguiente ticket.
5. Continuar el primer ticket EN_CURSO de este perfil, o el primero LISTO con dependencias cerradas.

Este perfil selecciona **CUE Digital**, no RadioPV ni facylf. No seguir la prioridad global W-04
ni la primera fila P-01 del laboratorio cuando el encargo sea este CRM. No modificar el estado
de otros proyectos. El laboratorio produce evidencia; la implementación se hace en el destino
con sus reglas. David ya ha solicitado el CRM y sus mejoras: no volver a preguntarle qué significa CRM.

## Producto que se pretende

Gestión integral de una explotación agraria: tierras, campañas, trabajos, compras, almacén,
ventas, pagos/cobros, contactos, maquinaria, mapas, documentación, preparación PAC y cuaderno.
Dos modos sobre los mismos datos: despacho denso y campo sencillo, accesible y con mala cobertura.
No trasladar pipelines comerciales, música o fútbol por el mero hecho de existir en una referencia.
Trasladar patrones que resuelvan una tarea agraria concreta.

La compra ya tiene un recorrido enlazado y cifras por identificador. Reutilizar esa estructura.
Las capacidades declaradas en documentos antiguos se contrastan antes de crear nuevas tablas.
No reescribir FastAPI/React-htm ni añadir otro framework para imitar una referencia.

## Ciclo continuo, con entregas cerrables

Por cada ticket:

1. Anotar problema, alcance y criterio de aceptación en ESTADO.
2. Inventariar qué existe: pantalla -> acción -> ruta -> modelo -> prueba. Registrar los huecos.
3. Elegir, si aporta valor, una referencia de COLA. Estudiar una función, no la aplicación completa.
4. Escribir un contrato pequeño con datos, estados, permisos, efectos y criterio de cierre.
5. Reproducir el fallo o crear la prueba de aceptación antes de corregirlo.
6. Implementar en el destino con un solo escritor por fichero compartido.
7. Recorrer desde la pantalla y contrastar registros por ID, no solo el total global.
8. Pedir revisión independiente de negocio y de interfaz; corregir defectos demostrados.
9. Ejecutar el cierre que exige AGENTS del destino, registrar evidencia y actualizar su contrato.
10. Marcar CERRADO y continuar el siguiente LISTO mientras el objetivo siga activo.

No acabar cada ronda con «cuando quieras sigo». No marcar terminado un bloque por haber localizado
el arreglo. No convertir regresiones de funciones exigidas en hallazgos informativos que dejan verde
el recorrido. Tampoco repetir suites completas sin nuevos cambios o dudas que lo justifiquen.

Una entrega admite progresos de investigación, pero cerrar exige una función implementada y comprobada.
Si hay bloqueo externo, registrar qué falta, si hay alternativa manual y qué tickets independientes
pueden avanzar. No simular un proveedor ni inventar normativa para poder marcarlo cerrado.
La continuidad depende de que DeepSeek tenga un objetivo activo: este paquete no instala un scheduler.

## Agentes y propiedad de los ficheros

- Coordinador: integración, estado y decisiones rutinarias dentro del alcance.
- Investigador: solo lectura de referencias, documentación, observaciones y propuestas.
- Implementador: ficheros asignados; un único escritor en `app.js`, `textos.py`, `models.py`,
  `database.py` y CSS cuando estén compartidos.
- Revisor: intenta falsar resultados con casos mínimos, sin alterar ficheros del implementador.

Máximo dos tickets en implementación si no comparten ficheros; si los comparten, serializar.
Antes de delegar escribir rutas permitidas y prohibidas, salida esperada y criterio de aceptación.
No reactivar un subagente con una tarea antigua mientras otro escribe sus ficheros.
Los informes de revisión no cierran tickets por sí solos.

## Usar referencias y REA sin gastar a ciegas

Primero documentación oficial, demo pública o código abierto. La UI se observa con navegador y
capturas; leer HTML o que exista un PNG no equivale a ver la pantalla. Si el modelo no tiene visión,
dejar esa revisión explícita y entregar las imágenes para un revisor que sí pueda verlas.
Stitch sirve para proponer jerarquía y layouts; se usa DESIGN.md, datos ficticios y no se copian
sus afirmaciones de cumplimiento o sus datos inventados. Reutilizar propuestas previas antes de generar.

REA se usa solo cuando una pregunta relevante depende de un artefacto empaquetado o su ejecución.
No descompilar el backend de un SaaS: el navegador no contiene su código del servidor.
Para fuente abierta, leer fuentes directamente. Para artefacto, resolver tipo y licencia antes del motor.
La existencia de un ejecutable no demuestra que todo su funcionamiento esté en él (por ejemplo, launchers).

Una investigación tendrá: tarea, referencia/versión, observado, hipótesis, desconocido,
evidencia con ruta/ev, decisión propia, lo descartado y prueba comparable en el destino.
Una captura acredita lo observado; una documentación acredita lo documentado; no mezclarlos.
No estudiar las veinte apps instaladas ni exigir aprender todos sus secretos antes de implementar.
Primera exploración corta; si no responde la pregunta, registrar el límite y probar otra referencia.
No repetir análisis gigantes. Resumen primero, evidencia completa en disco y cierre de sesión al terminar.

## Datos y seguridad de la verificación

La base real `backend/cuedigital.db` y sus adjuntos no se usan para pruebas. Las pruebas usan base,
adjuntos, puertos y perfiles de navegador temporales. Resolver la ruta efectiva antes de importar la app.
No apagar servidores por su puerto sin atribución de propietario, comando y directorio.
No leer ni enviar a referencias documentos privados, claves o cuentas bancarias reales.
No guardar secretos en documentación, capturas, prompts o trazas.

Todo registro pertenece a una explotación. Dinero con Decimal y moneda; cantidades con unidad;
fechas del hecho, del registro y de actualización diferenciadas. Desconocido no es cero ni aprobado.
Identidad del comando distinta de identidad comercial y de identidad de fichero.
Anular conserva auditoría y no destruye una firma histórica.
Los permisos se aplican en servidor y exportaciones, no solo ocultando botones.

## Cierre y diagnóstico

Evidencia mínima: comando/alcance, salida 0, cero fallos y errores, omisiones explicadas,
capturas/recorrido y resultados por ID. Los recuentos proceden de recogida real, no de sumar a mano.
Comparar autor/fecha/motivo con los valores esperados y leer JSON como JSON.
Esperar estados observables asociados al registro o petición probados; una tarjeta ajena no es señal.

Si una medida contradice el programa, no suponer que uno de los dos tiene razón: imprimir IDs,
tipos, unidades, respuestas y hechos antes de editar. Si tras dos intentos persiste el mismo diagnóstico
sin avance, detener ediciones exploratorias y pedir al revisor una reproducción mínima.
No ampliar la suite con guardianes de texto que sustituyan comprobaciones de comportamiento.

## Objetivo para pegar a DeepSeek

```text
/goal Continuar CUE Digital hasta completar los tickets listos del perfil
F:\EspacioCodigo\ProyectoServidor\rea-sandbox\estudiar-apps\perfiles\cuedigital.
Leer LEER-PRIMERO.md, VERIFICACION.md, COLA.md y ESTADO.md; después los contratos
y AGENTS del destino F:\EspacioCodigo\CueDigital.
Empezar por CRM-00 y continuar CRM-01, CRM-02 y el resto en orden de dependencias,
sin pedir nueva autorización para mejoras ya definidas ni terminar tras cada resumen.
Investigar referencias pertinentes y trasladar sus decisiones con código propio;
REA únicamente cuando un artefacto empaquetado responda una pregunta concreta.
Usar subagentes de investigación y revisión, un escritor por fichero compartido,
datos ficticios y servidores aislados. Cerrar cada ticket con sus criterios,
recorrido real, revisión visual y verificaciones exigidas por AGENTS.
Si un ticket depende de corpus, proveedor o acceso externo, documentar el bloqueo
y continuar los tickets independientes. No inventar datos ni declarar todo el CRM
terminado por haber pasado las pruebas antiguas. Mantener el estado de este perfil
y actualizar los contratos existentes del destino, sin crear un plan contradictorio.
```
