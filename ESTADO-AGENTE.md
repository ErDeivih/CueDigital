titulo: CueDigital — la herramienta del agricultor de Castilla y León
resumen: CueDigital ya tiene el historial de la tierra que compara años, el calendario con totales y los filtros con tierra, fechas y CSV para la trazabilidad, y el SIGPAC con ventana propia de selección de parcela: se busca por la referencia del papel o por el pueblo elegido de la lista, se ve la ortofoto con los recintos resaltados y se puede dar de alta la tierra o aplicar ese contorno y sus datos oficiales a una tierra que ya existe. Todo verificado en Chrome y con el SIGPAC simulado en las pruebas. No queda ningún servidor de desarrollo abierto.
estado: en-curso
tarea: implementados el historial comparable, el calendario con totales, los filtros con trazabilidad y la ventana del SIGPAC con aplicación de contorno a una tierra existente
nivel: 2
siguiente: probar el GeoPackage con el fichero real de una provincia, el resto del apuntar del día a día (tratamientos, abonos, siembra, cosecha) y las pantallas de PAC y gastos
bloqueado: PSD2 (nivel 3, sin coste publicado y sin gasto aprobado); y siguen pendientes de terceros las licencias (CIT, IGN) y los formatos del expediente y del Cuecyl antiguo
fecha: 2026-11-06

## Lo que se ha hecho en esta ronda

1. **Historial de la tierra, comparable**: tabla **«Años anteriores»** en la ficha —año, cultivo y
   variedad, superficie, **abono total kg/ha**, **meses de abono en palabras**, **cosecha kg/ha** y
   número de labores— con «no consta» donde falta; y debajo el detalle del año (siembra, labores,
   tratamientos, abonos y cosecha). En el servidor, `abonos_kg_ha` va **null** si a algún abono le falta
   su kg/ha, y los meses van ordenados y sin repetir.
2. **Calendario con totales**: cada día dice cuántos trabajos, hectáreas y cantidades; el mes da su
   total con **cada unidad por su lado** (nunca kg + litros); el día de hoy va marcado con «Hoy».
3. **Filtros con trazabilidad**: tipo + **tierra** + **fechas**; los tipos se recalculan sobre lo
   filtrado, las tarjetas dan n, hectáreas y cantidades por unidad, y **«Descargar»** baja un CSV de
   lo filtrado (fecha, tipo, título, tierra, municipio, hectáreas, cantidad, unidad, por hectárea).
4. **Ventana propia del SIGPAC** (lo nuevo de esta ronda): modal que se abre desde el alta y desde la
   ficha, con **referencia** o **pueblo elegido de la lista** + agregado/zona/polígono/parcela, lista
   de recintos y **mapa con la ortofoto y todos los recintos resaltados**; «Usar esta parcela» da de
   alta la tierra o **aplica el contorno y los datos oficiales a la tierra existente**
   (`POST /api/parcelas/{id}/contorno`, con el recinto para no coger el trozo equivocado), cerrándose
   con aviso. Sin forma no se aplica nada. El `null` del SIGPAC se guarda `null` (nunca 0) y lo que ya
   había escrito el agricultor no se pisa.
5. **Sin servidores de desarrollo abiertos**: se apagaron los de las verificaciones y se mató un
   `uvicorn` de CueDigital que había quedado de una sesión anterior (puerto 49686). Las pruebas de
   servidor se hacen con `TestClient` y el arnés de Chrome levanta y apaga el suyo.

## La última pasada, sobre este mismo HEAD

    Python       5893 recogidas · 5891 superadas, 2 omitidas, 0 fallos
    JavaScript   1291 superadas, 0 fallos
    armazón nuevo en Chrome a 390/1024/1440, ficha, apuntar, calendario, filtros, facturas,
    cuaderno guiado, productos y ventana del SIGPAC                          0 fallos
    capturas                                            16 en docs/capturas-nuevo/

## Lo que sigue abierto

- **Probar el GeoPackage con el fichero real** de una provincia (600 MB): tiempo, memoria y si hace
  falta índice propio o guardar el `.gpkg` extraído.
- **Tratamientos, abonos, siembra y cosecha del día a día** en la app nueva y la **cola sin cobertura**.
- **PAC de años anteriores** y recintos por campaña de la Junta; pantallas propias de PAC y gastos.
- **PSD2**: dos presupuestos y decisión de gasto de David; sin código hasta contrato.
- Límites respetados: **no se ha tocado el `.env` ni las fixtures de firma**, no se ha abierto ni
  cambiado de rama y no se usa GitHub Actions. Push selectivo al final de la sesión.
