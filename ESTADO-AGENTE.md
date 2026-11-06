titulo: CueDigital — la herramienta del agricultor de Castilla y León
resumen: CueDigital tiene ya todo el bloque 4 con la pasada de móvil hecha de verdad: historial de la tierra por años (siembras, abonos en kg/ha y labores), calendario con totales por día y mes, filtros por tipo/tierra/fechas con cantidades y CSV, ventana propia del SIGPAC para elegir parcela y aplicar su contorno, y cuaderno guiado. A 390 y 360 px ninguna vista arrastra la página, la tabla de años se desplaza dentro de su caja, la ventana del SIGPAC ocupa la pantalla con «Cerrar» al alcance y la barra inferior no tapa el último botón. No queda ningún servidor de desarrollo abierto.
estado: en-curso
tarea: hecho el bloque 4 (historial, calendario, filtros, ventana del SIGPAC y cuaderno guiado) y la pasada móvil primero sin desbordes ni solapamientos
nivel: 2
siguiente: probar el GeoPackage con el fichero real de una provincia, el resto del apuntar del día a día (tratamientos, abonos, siembra, cosecha) y las pantallas de PAC y gastos
bloqueado: PSD2 (nivel 3, sin coste publicado y sin gasto aprobado); y siguen pendientes de terceros las licencias (CIT, IGN) y los formatos del expediente y del Cuecyl antiguo
fecha: 2026-11-06

## Lo que se ha hecho en esta ronda

1. **Móvil primero (390×844 y 360×640), medido en Chrome real**:
   - **Ventana del SIGPAC a pantalla completa**: antes se abría con 16 px de margen (358×812 y
     328×608) porque las reglas móviles del CSS quedaban antes que las de escritorio; ahora ocupa
     **390×844 y 360×640 desde (0,0)**, con cabecera y «Cerrar» siempre visibles, scroll dentro de
     la ventana y mapa de **269 px** (390) y **246 px** (360). El fondo no se mueve.
   - **Sin scroll horizontal en 8 vistas** (Hoy, Tierras, Calendario, Trabajos, Productos, Cuaderno,
     Facturas y ficha de la tierra): **0 px** de desborde a los dos anchos.
   - **Tabla de años**: se desplaza **dentro de su caja** (sin arrastrar la página), con la primera
     columna fija y letra legible; 530 px de contenido en una caja de 324/294.
   - **Barra inferior**: hueco de **96 px + `env(safe-area-inset-bottom)`**; el arnés comprueba que no
     tapa el último botón (se reserva el hueco y queda margen para el «home» del móvil).
   - **A 1024** se corrigió el selector del mapa, que se salía **25 px** (borde 1049 en ventana de
     1024). A 1440 sigue igual; la barra lateral y las rejillas no cambian.
   - **Calendario**: las celdas enseñan también las hectáreas del día (número + palabra + ha, nunca
     solo color) y los filtros de «Trabajos» pasan a **una columna por debajo de 480 px**.
2. **Historial de la tierra por años**: tabla **«Años anteriores»** con cultivo y variedad, superficie,
   **abono total kg/ha**, **meses de abono en palabras**, cosecha kg/ha y n.º de labores; «no consta»
   donde falta, y debajo el detalle del año (siembra, labores, tratamientos, abonos y cosecha).
3. **Calendario y filtros con trazabilidad**: totales por día y del mes sin mezclar unidades; filtros
   por tipo, tierra y fechas; cantidades por unidad; **CSV** de lo filtrado.
4. **Ventana del SIGPAC**: modal desde el alta y desde la ficha, búsqueda por referencia o por pueblo
   elegido de la lista, mapa con los recintos resaltados, y «Usar esta parcela» que da de alta o
   **aplica el contorno y los datos oficiales a una tierra existente** (idempotente, con auditoría,
   `null` donde el SIGPAC trae nulo y sin pisar lo del agricultor).
5. **Cuaderno guiado**: cuántas cosas faltan, agrupadas por dónde se arreglan, con botón a la pantalla
   y lo que bloquea el envío dicho con palabra.
6. **Sin servidores abiertos**: las verificaciones se hacen con uvicorn temporal + Chrome por CDP y se
   apagan; se mató además un `uvicorn` viejo de CueDigital (puerto 49686). No queda ningún proceso de
   CueDigital escuchando.

## La última pasada, sobre este mismo HEAD

    Python       5894 recogidas · 5892 superadas, 2 omitidas, 0 fallos
    JavaScript   1291 superadas, 0 fallos
    armazón nuevo en Chrome a 390/1024/1440, móvil 390/360, ficha, apuntar, calendario, filtros,
    facturas, cuaderno, productos y ventana del SIGPAC                        0 fallos
    capturas                                            18 en docs/capturas-nuevo/

## Lo que sigue abierto

- **Probar el GeoPackage con el fichero real** de una provincia (600 MB): tiempo, memoria y si hace
  falta índice propio o guardar el `.gpkg` extraído.
- **Tratamientos, abonos, siembra y cosecha del día a día** en la app nueva y la **cola sin cobertura**.
- **PAC de años anteriores** y recintos por campaña de la Junta; pantallas propias de PAC y gastos.
- **PSD2**: dos presupuestos y decisión de gasto de David; sin código hasta contrato.
- Límites respetados: **no se ha tocado el `.env` ni las fixtures de firma**, no se ha abierto ni
  cambiado de rama y no se usa GitHub Actions. Push selectivo al final de la sesión.
