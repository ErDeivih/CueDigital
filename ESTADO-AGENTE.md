titulo: CueDigital — la herramienta del agricultor de Castilla y León
resumen: CueDigital ya compara los años de una tierra (qué se sembró, abono total kg/ha, meses de abono, cosecha kg/ha y labores), da los totales del calendario por día y por mes sin mezclar unidades, y filtra los trabajos por tipo, tierra y fechas mostrando cantidades por unidad y bajando un CSV para la trazabilidad. Con el cuaderno guiado y los productos con dosis cerrados antes, el bloque 4 queda con las piezas visibles hechas; falta probar el GeoPackage con el fichero real y llevar a la app nueva tratamientos, abonos, siembra y cosecha del día a día.
estado: en-curso
tarea: implementados el historial comparable por años, el calendario con totales y los filtros con tierra/fechas, cantidades por unidad y CSV
nivel: 2
siguiente: probar el GeoPackage real de una provincia, el resto del apuntar del día a día (tratamientos, abonos, siembra, cosecha) y las pantallas de PAC y gastos
bloqueado: PSD2 (nivel 3, sin coste publicado y sin gasto aprobado); y siguen pendientes de terceros las licencias (CIT, IGN) y los formatos del expediente y del Cuecyl antiguo
fecha: 2026-11-06

## Lo que se ha hecho en esta ronda

1. **Historial de la tierra, comparable**: en la ficha, tabla **«Años anteriores»** con una fila por
   año: año, cultivo y variedad, superficie, **abono total kg/ha**, **meses de abono en palabras**
   («marzo, mayo»), **cosecha kg/ha** y **número de labores**. Lo que no consta se dice «no consta»
   (nunca un 0 que afirme algo). Debajo sigue el detalle del año. El servidor añade el `resumen` por
   año; `abonos_kg_ha` va **null** si a algún abono le falta su kg/ha (una suma con un sumando menos
   no es una suma) y los meses van ordenados y sin repetir.
2. **Calendario con totales**: cada día con trabajo dice cuántos trabajos, hectáreas y cantidades
   (`data-dia-total`); el mes da su total (`data-calendario-totales`), **cada unidad por su lado**
   (nunca kg + litros); el día de hoy va marcado con la palabra «Hoy».
3. **Filtros con trazabilidad**: además del tipo, **selector de tierra** y **dos fechas**; la
   petición va al servidor con `parcela_id`, `desde` y `hasta` (404 si la tierra no es de la finca,
   422 si el rango es imposible), los tipos y sus cuentas se recalculan sobre lo filtrado, las
   tarjetas de resumen por tipo dan n, hectáreas y **cantidades por unidad**, y un botón
   **«Descargar»** baja el **CSV** de lo filtrado para la trazabilidad.
4. **Lo que ya estaba y sigue**: cuaderno guiado, productos y abonos con dosis por hectárea,
   apuntar el trabajo del día desde la tierra, facturas con fotos, contornos del SIGPAC (incluido el
   GeoPackage), y la app vieja viva en `/` para lo que aún no está migrado.

## La última pasada, sobre este mismo HEAD

    Python       5875 recogidas · 5873 superadas, 2 omitidas, 0 fallos
    JavaScript   1287 superadas, 0 fallos
    armazón nuevo en Chrome a 390/1024/1440, ficha, apuntar, calendario, filtros, facturas,
    cuaderno guiado y productos                                             0 fallos
    capturas                                            15 en docs/capturas-nuevo/

## Lo que sigue abierto

- **Probar el GeoPackage con el fichero real** de una provincia (600 MB): tiempo, memoria y si hace
  falta índice propio o guardar el `.gpkg` extraído.
- **Tratamientos, abonos, siembra y cosecha del día a día** en la app nueva (el trabajo de suelo ya
  está) y la **cola sin cobertura**.
- **PAC de años anteriores** y recintos por campaña de la Junta; pantallas propias de PAC y gastos.
- **PSD2**: dos presupuestos y decisión de gasto de David; sin código hasta contrato.
- Límites respetados: **no se ha tocado el `.env` ni las fixtures de firma**, no se ha abierto ni
  cambiado de rama y no se usa GitHub Actions. Push selectivo al final de la sesión.
